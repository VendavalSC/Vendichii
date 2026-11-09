// SPDX-FileCopyrightText: Copyright 2026 Eden Emulator Project
// SPDX-License-Identifier: GPL-3.0-or-later

// SPDX-FileCopyrightText: 2017 Citra Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <iomanip>
#include <iterator>
#include <mutex>
#include <numeric>
#include <sstream>
#include <thread>
#include <fmt/chrono.h>
#include <fmt/ranges.h>
#include "common/fs/file.h"
#include "common/fs/fs.h"
#include "common/fs/path_util.h"
#include "common/settings.h"
#include "common/tas_state.h"
#include "core/perf_stats.h"

using namespace std::chrono_literals;
using DoubleSecs = std::chrono::duration<double, std::chrono::seconds::period>;
using std::chrono::duration_cast;
using std::chrono::microseconds;

// Purposefully ignore the first five frames, as there's a significant amount of overhead in
// booting that we shouldn't account for
constexpr std::size_t IgnoreFrames = 5;

namespace Core {

PerfStats::PerfStats(u64 title_id_) : title_id(title_id_) {
    const char* const fps_log = std::getenv("EDEN_FPS_LOG");
    if (fps_log == nullptr || fps_log[0] == '0' || title_id == 0) {
        return;
    }
    const std::time_t t = std::time(nullptr);
    std::ostringstream date;
    date << std::put_time(std::localtime(&t), "%F-%H-%M-%S");
    const auto filepath = Common::FS::GetEdenPath(Common::FS::EdenPath::LogDir) /
                          fmt::format("fps_{:016X}_{}.csv", title_id, date.str());
    if (!Common::FS::CreateParentDir(filepath)) {
        return;
    }
    fps_log_file = std::make_unique<Common::FS::IOFile>(
        filepath, Common::FS::FileAccessMode::Write, Common::FS::FileType::TextFile);
    if (!fps_log_file->IsOpen()) {
        fps_log_file.reset();
        return;
    }
    void(fps_log_file->WriteString(
        std::string_view{"seconds,fps,avg_ms,low1_fps,max_ms,tas,end_ns\n"}));
    fps_log_intervals_ms.reserve(256);

    // Frames of 25 ms or more, timed on the steady clock (QPC on Windows) so that
    // tools/windows/hitch_report.py can line them up with EDEN_NX2_SAMPLE_PROFILE samples.
    fps_hitch_file = std::make_unique<Common::FS::IOFile>(
        filepath.parent_path() / fmt::format("hitch_{:016X}_{}.csv", title_id, date.str()),
        Common::FS::FileAccessMode::Write, Common::FS::FileType::TextFile);
    if (fps_hitch_file->IsOpen()) {
        void(fps_hitch_file->WriteString(std::string_view{"end_ns,ms\n"}));
    } else {
        fps_hitch_file.reset();
    }
}

PerfStats::~PerfStats() {
    if (!Settings::values.record_frame_times || title_id == 0) {
        return;
    }

    const std::time_t t = std::time(nullptr);
    std::ostringstream stream;
    std::copy(perf_history.begin() + IgnoreFrames, perf_history.begin() + current_index,
              std::ostream_iterator<double>(stream, "\n"));

    const auto path = Common::FS::GetEdenPath(Common::FS::EdenPath::LogDir);
    // %F Date format expanded is "%Y-%m-%d"
    const auto filename = fmt::format("{}_{:016X}.csv",
        [&] {
            std::ostringstream oss;
            oss << std::put_time(std::localtime(&t), "%F-%H-%M");
            return oss.str();
        }(),
        title_id);

    const auto filepath = path / filename;

    if (Common::FS::CreateParentDir(filepath)) {
        Common::FS::IOFile file(filepath, Common::FS::FileAccessMode::Write,
                                Common::FS::FileType::TextFile);
        void(file.WriteString(stream.str()));
    }
}

void PerfStats::BeginSystemFrame() {
    std::scoped_lock lock{object_mutex};

    frame_begin = Clock::now();
}

void PerfStats::EndSystemFrame() {
    std::scoped_lock lock{object_mutex};

    auto frame_end = Clock::now();
    const auto frame_time = frame_end - frame_begin;
    if (current_index < perf_history.size()) {
        perf_history[current_index++] =
            std::chrono::duration<double, std::milli>(frame_time).count();
    }
    accumulated_frametime += frame_time;
    system_frames += 1;

    previous_frame_length = frame_end - previous_frame_end;
    previous_frame_end = frame_end;
}

void PerfStats::EndGameFrame() {
    game_frames.fetch_add(1, std::memory_order_relaxed);
    if (fps_log_file) {
        LogGameFrame();
    }
}

void PerfStats::LogGameFrame() {
    std::scoped_lock lock{fps_log_mutex};

    const auto now = Clock::now();
    if (fps_log_last_frame == Clock::time_point{}) {
        fps_log_start = now;
        fps_log_window_start = now;
        fps_log_last_frame = now;
        return;
    }
    const double interval_ms =
        std::chrono::duration<double, std::milli>(now - fps_log_last_frame).count();
    fps_log_intervals_ms.push_back(interval_ms);
    fps_log_last_frame = now;
    if (fps_hitch_file && interval_ms >= 25.0) {
        void(fps_hitch_file->WriteString(fmt::format(
            "{},{:.2f}\n",
            std::chrono::duration_cast<std::chrono::nanoseconds>(now.time_since_epoch()).count(),
            interval_ms)));
    }
    if (now - fps_log_window_start < 1s) {
        return;
    }

    const double window_s = duration_cast<DoubleSecs>(now - fps_log_window_start).count();
    const size_t count = fps_log_intervals_ms.size();
    const double avg_ms =
        std::accumulate(fps_log_intervals_ms.begin(), fps_log_intervals_ms.end(), 0.0) /
        static_cast<double>(count);
    // 1% low: the frame time 99% of this second's frames beat
    std::ranges::sort(fps_log_intervals_ms);
    const double p99_ms = fps_log_intervals_ms[std::min(count - 1, count * 99 / 100)];
    void(fps_log_file->WriteString(fmt::format(
        "{:.1f},{:.1f},{:.2f},{:.1f},{:.2f},{},{}\n",
        duration_cast<DoubleSecs>(now - fps_log_start).count(),
        static_cast<double>(count) / window_s, avg_ms, 1000.0 / p99_ms,
        fps_log_intervals_ms.back(), Common::g_tas_playing.load(std::memory_order_relaxed) ? 1 : 0,
        std::chrono::duration_cast<std::chrono::nanoseconds>(now.time_since_epoch()).count())));
    void(fps_log_file->Flush());
    if (fps_hitch_file) {
        void(fps_hitch_file->Flush());
    }

    fps_log_intervals_ms.clear();
    fps_log_window_start = now;
}

double PerfStats::GetMeanFrametime() const {
    std::scoped_lock lock{object_mutex};

    if (current_index <= IgnoreFrames) {
        return 0;
    }

    const double sum = std::accumulate(perf_history.begin() + IgnoreFrames,
                                       perf_history.begin() + current_index, 0.0);
    return sum / static_cast<double>(current_index - IgnoreFrames);
}

PerfStatsResults PerfStats::GetAndResetStats(microseconds current_system_time_us) {
    std::scoped_lock lock{object_mutex};

    const auto now = Clock::now();
    // Walltime elapsed since stats were reset
    const auto interval = duration_cast<DoubleSecs>(now - reset_point).count();

    const auto system_us_per_second = (current_system_time_us - reset_point_system_us) / interval;
    const auto current_frames = static_cast<double>(game_frames.load(std::memory_order_relaxed));
    const auto current_fps = current_frames / interval;
    const PerfStatsResults results{
        .system_fps = static_cast<double>(system_frames) / interval,
        .average_game_fps = (current_fps + previous_fps) / 2.0,
        .frametime = duration_cast<DoubleSecs>(accumulated_frametime).count() /
                     static_cast<double>(system_frames),
        .emulation_speed = system_us_per_second.count() / 1'000'000.0,
    };

    // Reset counters
    reset_point = now;
    reset_point_system_us = current_system_time_us;
    accumulated_frametime = Clock::duration::zero();
    system_frames = 0;
    game_frames.store(0, std::memory_order_relaxed);
    previous_fps = current_fps;

    return results;
}

double PerfStats::GetLastFrameTimeScale() const {
    std::scoped_lock lock{object_mutex};

    constexpr double FRAME_LENGTH = 1.0 / 60;
    return duration_cast<DoubleSecs>(previous_frame_length).count() / FRAME_LENGTH;
}

void SpeedLimiter::DoSpeedLimiting(microseconds current_system_time_us) {
    if (Settings::values.use_multi_core.GetValue() ||
        !Settings::SpeedLimitEnabled()) {
        return;
    }

    auto now = Clock::now();

    const double sleep_scale = Settings::SpeedLimit() / 100.0;

    // Max lag caused by slow frames. Shouldn't be more than the length of a frame at the current
    // speed percent or it will clamp too much and prevent this from properly limiting to that
    // percent. High values means it'll take longer after a slow frame to recover and start
    // limiting
    const microseconds max_lag_time_us = duration_cast<microseconds>(
        std::chrono::duration<double, std::chrono::microseconds::period>(25ms / sleep_scale));
    speed_limiting_delta_err += duration_cast<microseconds>(
        std::chrono::duration<double, std::chrono::microseconds::period>(
            (current_system_time_us - previous_system_time_us) / sleep_scale));
    speed_limiting_delta_err -= duration_cast<microseconds>(now - previous_walltime);
    speed_limiting_delta_err =
        std::clamp(speed_limiting_delta_err, -max_lag_time_us, max_lag_time_us);

    if (speed_limiting_delta_err > microseconds::zero()) {
        std::this_thread::sleep_for(speed_limiting_delta_err);
        auto now_after_sleep = Clock::now();
        speed_limiting_delta_err -= duration_cast<microseconds>(now_after_sleep - now);
        now = now_after_sleep;
    }

    previous_system_time_us = current_system_time_us;
    previous_walltime = now;
}

} // namespace Core
