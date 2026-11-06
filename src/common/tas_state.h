// SPDX-License-Identifier: GPL-3.0-or-later

#pragma once

#include <atomic>

namespace Common {

/// Whether a TAS script is playing (InputCommon::TasInput::Tas), so EDEN_FPS_LOG can mark the
/// seconds of a scripted benchmark.
inline std::atomic<bool> g_tas_playing{false};

} // namespace Common
