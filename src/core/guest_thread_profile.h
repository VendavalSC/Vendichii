// SPDX-License-Identifier: GPL-3.0-or-later

#pragma once

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cstdlib>
#include <map>
#include <string>
#include <thread>
#include <vector>

#include <fmt/format.h>

#include "common/logging.h"
#include "common/thread.h"
#include "core/hardware_properties.h"
#include "core/hle/kernel/k_scheduler.h"
#include "core/hle/kernel/k_thread.h"
#include "core/hle/kernel/kernel.h"

// EDEN_GUEST_THREAD_PROFILE=1: about 1000 times a second, which guest thread each guest core runs.
// Every 10 s the log lists the busiest guest threads (share of one core, the cores they ran on,
// their priority) and marks the one that presents frames (nx2:vi2 PresentClientBuffer), so the
// thread that sets the frame rate can be told from loaders (Ocarina decompresses on cores 4/5).
namespace Core::GuestThreadProfile {

/// Thread id of the guest thread that sent the last present.
inline std::atomic<u64> g_present_thread{0};

inline bool Enabled() {
    static const bool enabled = [] {
        const char* const value = std::getenv("EDEN_GUEST_THREAD_PROFILE");
        return value != nullptr && value[0] == '1';
    }();
    return enabled;
}

inline std::jthread Start(Kernel::KernelCore& kernel) {
    if (!Enabled()) {
        return {};
    }
    return std::jthread{[&kernel](std::stop_token stop) {
        Common::SetCurrentThreadName("GuestThreadProfile");
        struct Entry {
            u64 samples{};
            std::array<u64, Hardware::NUM_CPU_CORES> per_core{};
            s32 priority{};
        };
        std::map<u64, Entry> threads;
        std::array<u64, Hardware::NUM_CPU_CORES> idle{};
        u64 ticks = 0;
        auto window = std::chrono::steady_clock::now();
        while (!stop.stop_requested()) {
            std::this_thread::sleep_for(std::chrono::milliseconds{1});
            ++ticks;
            for (size_t core = 0; core < Hardware::NUM_CPU_CORES; ++core) {
                const Kernel::KScheduler& scheduler = kernel.Scheduler(core);
                Kernel::KThread* const thread = scheduler.GetSchedulerCurrentThread();
                if (thread == nullptr || scheduler.IsIdle()) {
                    ++idle[core];
                    continue;
                }
                Entry& entry = threads[thread->GetThreadId()];
                ++entry.samples;
                ++entry.per_core[core];
                entry.priority = thread->GetPriority();
            }
            const auto now = std::chrono::steady_clock::now();
            if (now - window < std::chrono::seconds{10} || ticks == 0) {
                continue;
            }
            std::vector<std::pair<u64, Entry>> sorted(threads.begin(), threads.end());
            std::ranges::sort(sorted, [](const auto& a, const auto& b) {
                return a.second.samples > b.second.samples;
            });
            const u64 presenter = g_present_thread.load(std::memory_order_relaxed);
            std::string idle_text;
            for (size_t core = 0; core < idle.size(); ++core) {
                idle_text += fmt::format(" {}:{:.0f}%", core, 100.0 * idle[core] / ticks);
            }
            LOG_INFO(Core, "Guest threads in the last {} ms; idle per core{}", ticks, idle_text);
            for (size_t i = 0; i < std::min<size_t>(sorted.size(), 12); ++i) {
                const auto& [id, entry] = sorted[i];
                std::string cores;
                for (size_t core = 0; core < entry.per_core.size(); ++core) {
                    if (entry.per_core[core] * 20 >= entry.samples) {
                        cores += fmt::format("{}:{:.0f}% ", core, 100.0 * entry.per_core[core] /
                                                                  entry.samples);
                    }
                }
                LOG_INFO(Core, "  thread {} {:5.1f}% of a core, priority {}, on cores {}{}", id,
                         100.0 * entry.samples / ticks, entry.priority, cores,
                         id == presenter ? " <- presents frames" : "");
            }
            threads.clear();
            idle.fill(0);
            ticks = 0;
            window = now;
        }
    }};
}

} // namespace Core::GuestThreadProfile
