// SPDX-License-Identifier: GPL-3.0-or-later

#include <atomic>
#include <chrono>
#include <thread>

#include "common/logging.h"
#include "common/memory_detect.h"
#include "video_core/renderer_vulkan/pipeline_build_failure.h"

namespace Vulkan {

void ReportPipelineBuildFailure(VkResult result) {
    static std::atomic_flag reported;
    if (result != VK_ERROR_OUT_OF_HOST_MEMORY || reported.test_and_set()) {
        return;
    }
#ifdef _WIN32
    // The system-wide commit and limit (GetPerformanceInfo). GlobalMemoryStatusEx would give the
    // process's own limit instead when that is lower, which the page file doesn't change.
    const Common::ProcessMemoryUsage usage = Common::GetProcessMemoryUsage();
    if (usage.system_commit_limit != 0) {
        constexpr double GiB = 1024.0 * 1024.0 * 1024.0;
        LOG_CRITICAL(Render_Vulkan,
                     "The GPU driver ran out of host memory building a pipeline: Windows commit is "
                     "{:.1f} of {:.1f} GiB. The commit limit is RAM plus the page file, and a "
                     "Switch 2 game commits 14 GiB of guest memory when it starts. If commit is "
                     "near the limit, enlarge the page file. Pipelines that fail draw nothing.",
                     static_cast<double>(usage.system_commit) / GiB,
                     static_cast<double>(usage.system_commit_limit) / GiB);
        return;
    }
#endif
    LOG_CRITICAL(Render_Vulkan,
                 "The GPU driver ran out of host memory building a pipeline. Close other programs "
                 "or add swap; until then, pipelines that fail draw nothing.");
}

bool RetryPipelineBuild(VkResult result, int attempt) {
    if ((result != VK_ERROR_OUT_OF_HOST_MEMORY && result != VK_ERROR_OUT_OF_DEVICE_MEMORY) ||
        attempt >= 4) {
        return false;
    }
    LOG_WARNING(Render_Vulkan, "Pipeline build ran out of memory, retrying ({} of 4)", attempt + 1);
    std::this_thread::sleep_for(std::chrono::milliseconds{250 * (attempt + 1)});
    return true;
}

} // namespace Vulkan
