// SPDX-FileCopyrightText: Copyright 2026 Eden Emulator Project
// SPDX-License-Identifier: GPL-3.0-or-later

// SPDX-FileCopyrightText: Copyright 2021 yuzu Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <sstream>
#include <fmt/ranges.h>

#include "common/fs/file.h"
#include "common/fs/fs_types.h"
#include "common/fs/path_util.h"
#include "common/logging.h"
#include "common/settings.h"
#include "common/tas_state.h"
#include "input_common/drivers/tas_input.h"

namespace InputCommon::TasInput {

enum class Tas::TasAxis : u8 {
    StickX,
    StickY,
    SubstickX,
    SubstickY,
    Undefined,
};

// Supported keywords and buttons from a TAS file
constexpr std::array<std::pair<std::string_view, TasButton>, 18> text_to_tas_button = {
    std::pair{"KEY_A", TasButton::BUTTON_A},
    {"KEY_B", TasButton::BUTTON_B},
    {"KEY_X", TasButton::BUTTON_X},
    {"KEY_Y", TasButton::BUTTON_Y},
    {"KEY_LSTICK", TasButton::STICK_L},
    {"KEY_RSTICK", TasButton::STICK_R},
    {"KEY_L", TasButton::TRIGGER_L},
    {"KEY_R", TasButton::TRIGGER_R},
    {"KEY_PLUS", TasButton::BUTTON_PLUS},
    {"KEY_MINUS", TasButton::BUTTON_MINUS},
    {"KEY_DLEFT", TasButton::BUTTON_LEFT},
    {"KEY_DUP", TasButton::BUTTON_UP},
    {"KEY_DRIGHT", TasButton::BUTTON_RIGHT},
    {"KEY_DDOWN", TasButton::BUTTON_DOWN},
    {"KEY_SL", TasButton::BUTTON_SL},
    {"KEY_SR", TasButton::BUTTON_SR},
    // These buttons are disabled to avoid TAS input from activating hotkeys
    // {"KEY_CAPTURE", TasButton::BUTTON_CAPTURE},
    // {"KEY_HOME", TasButton::BUTTON_HOME},
    {"KEY_ZL", TasButton::TRIGGER_ZL},
    {"KEY_ZR", TasButton::TRIGGER_ZR},
};

Tas::Tas(std::string input_engine_) : InputEngine(std::move(input_engine_)) {
    const char* const realtime_env = std::getenv("EDEN_TAS_REALTIME");
    realtime = realtime_env != nullptr && realtime_env[0] == '1';
    for (size_t player_index = 0; player_index < PLAYER_NUMBER; player_index++) {
        PadIdentifier identifier{
            .guid = Common::UUID{},
            .port = player_index,
            .pad = 0,
        };
        PreSetController(identifier);
        for (int button = 0; button < 64; ++button) {
            PreSetButton(identifier, button);
        }
        for (int axis = 0; axis < static_cast<int>(TasAxis::Undefined); ++axis) {
            PreSetAxis(identifier, axis);
        }
    }
    ClearInput();
    if (!Settings::values.tas_enable) {
        needs_reset = true;
        return;
    }
    LoadTasFiles();
}

Tas::~Tas() {
    Stop();
}

void Tas::LoadTasFiles() {
    script_length = 0;
    for (size_t i = 0; i < commands.size(); i++) {
        LoadTasFile(i, 0);
        if (commands[i].size() > script_length) {
            script_length = commands[i].size();
        }
    }
}

void Tas::LoadTasFile(size_t player_index, size_t file_index) {
    commands[player_index].clear();

    std::string file = Common::FS::ReadStringFromFile(
        Common::FS::GetEdenPath(Common::FS::EdenPath::TASDir) /
            fmt::format("script{}-{}.txt", file_index, player_index + 1),
        Common::FS::FileType::BinaryFile);
    std::istringstream command_line(file);
    std::string line;
    int frame_no = 0;
    while (std::getline(command_line, line, '\n')) {
        if (line.empty()) {
            continue;
        }

        std::vector<std::string> seg_list;
        {
            std::istringstream line_stream(line);
            std::string segment;
            while (std::getline(line_stream, segment, ' ')) {
                seg_list.push_back(std::move(segment));
            }
        }

        if (seg_list.size() < 4) {
            continue;
        }

        try {
            const auto num_frames = std::stoi(seg_list[0]);
            while (frame_no < num_frames) {
                commands[player_index].emplace_back();
                frame_no++;
            }
        } catch (const std::invalid_argument&) {
            LOG_ERROR(Input, "Invalid argument: '{}' at command {}", seg_list[0], frame_no);
        } catch (const std::out_of_range&) {
            LOG_ERROR(Input, "Out of range: '{}' at command {}", seg_list[0], frame_no);
        }

        TASCommand command = {
            .buttons = ReadCommandButtons(seg_list[1]),
            .l_axis = ReadCommandAxis(seg_list[2]),
            .r_axis = ReadCommandAxis(seg_list[3]),
        };
        commands[player_index].push_back(command);
        frame_no++;
    }
    LOG_INFO(Input, "TAS file loaded! {} frames", frame_no);
}

void Tas::WriteTasFile(std::u8string_view file_name) {
    std::string output_text;
    for (size_t frame = 0; frame < record_commands.size(); frame++) {
        const TASCommand& line = record_commands[frame];
        output_text += fmt::format("{} {} {} {}\n", frame, WriteCommandButtons(line.buttons),
                                   WriteCommandAxis(line.l_axis), WriteCommandAxis(line.r_axis));
    }

    const auto tas_file_name = Common::FS::GetEdenPath(Common::FS::EdenPath::TASDir) / file_name;
    const auto bytes_written =
        Common::FS::WriteStringToFile(tas_file_name, Common::FS::FileType::TextFile, output_text);
    if (bytes_written == output_text.size()) {
        LOG_INFO(Input, "TAS file written to file!");
    } else {
        LOG_ERROR(Input, "Writing the TAS-file has failed! {} / {} bytes written", bytes_written,
                  output_text.size());
    }
}

void Tas::RecordInput(u64 buttons, TasAnalog left_axis, TasAnalog right_axis) {
    last_input = {
        .buttons = buttons,
        .l_axis = left_axis,
        .r_axis = right_axis,
    };
}

std::tuple<TasState, size_t, std::array<size_t, PLAYER_NUMBER>> Tas::GetStatus() const {
    TasState state;
    std::array<size_t, PLAYER_NUMBER> lengths{0};
    if (is_recording) {
        lengths[0] = record_commands.size();
        return {TasState::Recording, record_commands.size(), lengths};
    }

    if (is_running) {
        state = TasState::Running;
    } else {
        state = TasState::Stopped;
    }

    for (size_t i = 0; i < PLAYER_NUMBER; i++) {
        lengths[i] = commands[i].size();
    }

    return {state, current_command, lengths};
}

void Tas::UpdateThread() {
    if (!Settings::values.tas_enable) {
        if (is_running) {
            Stop();
        }
        return;
    }

    // EDEN_TAS_START_FILE=<path>: a script starts the loaded TAS from the beginning by creating
    // that file (tools/windows/auto_bench.py), as Ctrl+F6 then Ctrl+F5 would.
    static const char* const start_file = std::getenv("EDEN_TAS_START_FILE");
    if (start_file != nullptr && !is_running && !is_recording) {
        std::error_code error;
        if (std::filesystem::remove(start_file, error)) {
            needs_reset = true;
            is_running = true;
            LOG_INFO(Input, "TAS started by {}", start_file);
        }
    }

    size_t steps = 1;
    if (realtime) {
        const auto now = std::chrono::steady_clock::now();
        if (!tick_origin) {
            tick_origin = now;
            ticks_done = 0;
        }
        const size_t due = static_cast<size_t>((now - *tick_origin) * 60 / std::chrono::seconds{1});
        steps = due - ticks_done;
        ticks_done = due;
    }

    if (is_recording) {
        record_commands.insert(record_commands.end(), steps, last_input);
    }
    if (needs_reset) {
        current_command = 0;
        needs_reset = false;
        tick_origin.reset();
        LoadTasFiles();
        LOG_DEBUG(Input, "tas_reset done");
    }

    Common::g_tas_playing.store(is_running, std::memory_order_relaxed);
    if (!is_running) {
        ClearInput();
        return;
    }
    if (steps == 0) {
        return;
    }
    if (current_command < script_length) {
        LOG_DEBUG(Input, "Playing TAS {}/{}", current_command, script_length);
        const size_t first = current_command;
        current_command = (std::min)(current_command + steps, script_length);
        for (size_t player_index = 0; player_index < commands.size(); player_index++) {
            // Commands this frame skipped over still press their buttons, so a tap that lasted
            // one 1/60 s tick is not lost at a lower frame rate.
            TASCommand command{};
            for (size_t frame = first; frame < current_command; ++frame) {
                if (frame < commands[player_index].size()) {
                    const u64 buttons = command.buttons | commands[player_index][frame].buttons;
                    command = commands[player_index][frame];
                    command.buttons = buttons;
                }
            }

            ApplyCommand(player_index, command);
        }
    } else {
        is_running = Settings::values.tas_loop.GetValue();
        LoadTasFiles();
        current_command = 0;
        ClearInput();
    }
}

void Tas::ClearInput() {
    for (size_t player_index = 0; player_index < commands.size(); ++player_index) {
        ApplyCommand(player_index, {});
    }
}

void Tas::ApplyCommand(size_t player_index, const TASCommand& command) {
    const PadIdentifier identifier{
        .guid = Common::UUID{},
        .port = player_index,
        .pad = 0,
    };
    for (std::size_t i = 0; i < sizeof(command.buttons) * 8; ++i) {
        const bool button_status = (command.buttons & (1LLU << i)) != 0;
        const int button = static_cast<int>(i);
        if (GetButton(identifier, button) != button_status) {
            SetButton(identifier, button, button_status);
        }
    }
    SetTasAxis(identifier, TasAxis::StickX, command.l_axis.x);
    SetTasAxis(identifier, TasAxis::StickY, command.l_axis.y);
    SetTasAxis(identifier, TasAxis::SubstickX, command.r_axis.x);
    SetTasAxis(identifier, TasAxis::SubstickY, command.r_axis.y);
}

TasAnalog Tas::ReadCommandAxis(const std::string& line) const {
    std::vector<std::string> seg_list;
    {
        std::istringstream line_stream(line);
        std::string segment;
        while (std::getline(line_stream, segment, ';')) {
            seg_list.push_back(std::move(segment));
        }
    }

    if (seg_list.size() < 2) {
        LOG_ERROR(Input, "Invalid axis data: '{}'", line);
        return {};
    }

    try {
        const float x = std::stof(seg_list.at(0)) / 32767.0f;
        const float y = std::stof(seg_list.at(1)) / 32767.0f;
        return {x, y};
    } catch (const std::invalid_argument&) {
        LOG_ERROR(Input, "Invalid argument: '{}'", line);
    } catch (const std::out_of_range&) {
        LOG_ERROR(Input, "Out of range: '{}'", line);
    }
    return {};
}

u64 Tas::ReadCommandButtons(const std::string& line) const {
    std::istringstream button_text(line);
    std::string button_line;
    u64 buttons = 0;
    while (std::getline(button_text, button_line, ';')) {
        for (const auto& [text, tas_button] : text_to_tas_button) {
            if (text == button_line) {
                buttons |= static_cast<u64>(tas_button);
                break;
            }
        }
    }
    return buttons;
}

std::string Tas::WriteCommandButtons(u64 buttons) const {
    std::string returns;
    for (const auto& [text_button, tas_button] : text_to_tas_button) {
        if ((buttons & static_cast<u64>(tas_button)) != 0) {
            returns += fmt::format("{};", text_button);
        }
    }
    return returns.empty() ? "NONE" : returns;
}

std::string Tas::WriteCommandAxis(TasAnalog analog) const {
    return fmt::format("{};{}", analog.x * 32767, analog.y * 32767);
}

void Tas::SetTasAxis(const PadIdentifier& identifier, TasAxis axis, f32 value) {
    if (GetAxis(identifier, static_cast<int>(axis)) != value) {
        SetAxis(identifier, static_cast<int>(axis), value);
    }
}

void Tas::StartStop() {
    if (!Settings::values.tas_enable) {
        return;
    }
    if (is_running) {
        Stop();
    } else {
        is_running = true;
        tick_origin.reset();
    }
}

void Tas::Stop() {
    is_running = false;
}

void Tas::Reset() {
    if (!Settings::values.tas_enable) {
        return;
    }
    needs_reset = true;
}

bool Tas::Record() {
    if (!Settings::values.tas_enable) {
        return true;
    }
    is_recording = !is_recording;
    tick_origin.reset();
    return is_recording;
}

void Tas::SaveRecording(bool overwrite_file) {
    if (is_recording) {
        return;
    }
    if (record_commands.empty()) {
        return;
    }
    WriteTasFile(u8"record.txt");
    if (overwrite_file) {
        WriteTasFile(u8"script0-1.txt");
    }
    needs_reset = true;
    record_commands.clear();
}

} // namespace InputCommon::TasInput
