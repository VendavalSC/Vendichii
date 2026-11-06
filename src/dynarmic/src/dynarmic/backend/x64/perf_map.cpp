// SPDX-FileCopyrightText: Copyright 2026 Eden Emulator Project
// SPDX-License-Identifier: GPL-3.0-or-later

/* This file is part of the dynarmic project.
 * Copyright (c) 2018 MerryMage
 * SPDX-License-Identifier: 0BSD
 */

#include <cstddef>
#include <string>
#include <fmt/format.h>

#include "dynarmic/backend/x64/perf_map.h"
#include "common/common_types.h"
#if (defined(__linux__) && !defined(__ANDROID__)) || defined(_WIN32)
#    include <chrono>
#    include <cstdio>
#    include <cstdlib>
#    include <mutex>
#    ifdef _WIN32
#        include <process.h>
#    else
#        include <sys/types.h>
#        include <unistd.h>
#    endif

namespace Dynarmic::Backend::X64 {

namespace {
std::mutex mutex;
std::FILE* file = nullptr;
bool disabled = false;

// Linux: perf's PERF_BUILDID_DIR. Windows: EDEN_JIT_PERF_MAP=<dir>, read with the sample profiler
// (tools/windows/jit_report.py) to name the guest code behind [jit] samples.
void OpenFile() {
#    ifdef _WIN32
    const char* perf_dir = std::getenv("EDEN_JIT_PERF_MAP");
    const int pid = _getpid();
#    else
    const char* perf_dir = std::getenv("PERF_BUILDID_DIR");
    const pid_t pid = getpid();
#    endif
    if (!perf_dir) {
        file = nullptr;
        disabled = true;
        return;
    }

    const std::string filename = fmt::format("{:s}/perf-{:d}.map", perf_dir, pid);

    file = std::fopen(filename.c_str(), "w");
    if (!file) {
        disabled = true;
        return;
    }

    std::setvbuf(file, nullptr, _IONBF, 0);
}
}  // anonymous namespace

namespace detail {
void PerfMapRegister(const void* start, const void* end, std::string_view friendly_name) {
    if (start == end) {
        // Nothing to register
        return;
    }

    std::lock_guard guard{mutex};

    if (!file) {
        if (disabled) {
            return;
        }
        OpenFile();
        if (!file) {
            return;
        }
    }

    const std::string line = fmt::format("{:016x} {:016x} {:s}\n", reinterpret_cast<u64>(start), reinterpret_cast<u64>(end) - reinterpret_cast<u64>(start), friendly_name);
    std::fwrite(line.data(), sizeof *line.data(), line.size(), file);
}
}  // namespace detail

void PerfMapClear() {
    std::lock_guard guard{mutex};

    if (!file) {
        return;
    }

#    ifdef _WIN32
    // The cache's addresses are reused after a clear: mark when, on the steady clock (QPC), instead
    // of starting the file over, so samples from before the clear still find their blocks.
    const auto now = std::chrono::steady_clock::now().time_since_epoch();
    const std::string line = fmt::format(
        "CLEAR {}\n", std::chrono::duration_cast<std::chrono::nanoseconds>(now).count());
    std::fwrite(line.data(), sizeof *line.data(), line.size(), file);
#    else
    std::fclose(file);
    file = nullptr;
    OpenFile();
#    endif
}

}  // namespace Dynarmic::Backend::X64

#endif
