// SPDX-License-Identifier: GPL-3.0-or-later

#pragma once

// vulkan_core.h only: video_core/vulkan_common/vulkan.h pulls in Xlib on Linux, whose
// `#define Success 0` breaks headers included after this one (nvdata.h's NvResult::Success).
#include <vulkan/vulkan_core.h>

namespace Vulkan {

/// Called when a driver fails a pipeline build. For VK_ERROR_OUT_OF_HOST_MEMORY, logs once per
/// session what it means: on Windows the commit limit (RAM plus page file) is reached, which a
/// Switch 2 game's 14 GiB of committed guest memory makes likely on 16 GB hosts (#462).
void ReportPipelineBuildFailure(VkResult result);

/// For a build that ran out of host or video memory: waits a little (other builds and the texture
/// cache free memory meanwhile) and returns true while `attempt` is below the retry limit. An 8 GB
/// card that filled up otherwise lost those pipelines for the session and drew nothing with them.
[[nodiscard]] bool RetryPipelineBuild(VkResult result, int attempt);

} // namespace Vulkan
