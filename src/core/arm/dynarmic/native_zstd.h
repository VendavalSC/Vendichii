// SPDX-License-Identifier: GPL-3.0-or-later

#pragma once

#include <atomic>
#include <cstring>
#include <map>
#include <memory>
#include <mutex>
#include <utility>
#include <vector>

#include <zstd.h>

#include "common/common_types.h"
#include "common/logging.h"

// Runs a game's ZSTD_decompressMultiFrame with the host's zstd. A built-in patch
// (core/file_sys/patch_manager.cpp, "Native zstd (built-in)") puts BRK #NativeZstd::Imm on the
// function's first instruction, a PACIBSP; ExceptionRaised calls TryRun for it.
//
// Ocarina of Time (Switch 2) decompresses streamed data with zstd on its main threads: up to
// ~500 KiB frames while the camera turns, which took ~25% (guest core 4) and ~45% (guest core 5)
// of their JIT time in the Kokiri Forest benchmark. The function's caller re-initializes the
// DCtx before every call and reads nothing of it afterwards, only the returned size.
namespace Core::NativeZstd {

/// BRK #0x5A57 ("ZW").
inline constexpr u32 Imm = 0x5A57;
inline constexpr u32 Instruction = 0xD4200000U | (Imm << 5);

struct Stats {
    std::atomic<u64> calls{};
    std::atomic<u64> in_bytes{};
    std::atomic<u64> out_bytes{};
    std::atomic<u64> fallbacks{};
};

inline Stats& GetStats() {
    static Stats stats;
    return stats;
}

/// Native DDicts by guest dictionary (content address, size): created once, as the game does.
inline ZSTD_DDict* CachedDDict(u64 content, u64 size, const std::vector<u8>& bytes) {
    static std::mutex mutex;
    static std::map<std::pair<u64, u64>, std::pair<std::vector<u8>, ZSTD_DDict*>> cache;
    std::scoped_lock lock{mutex};
    auto [it, inserted] = cache.try_emplace({content, size});
    auto& [cached_bytes, ddict] = it->second;
    if (!inserted && cached_bytes != bytes) {
        ZSTD_freeDDict(ddict);
        ddict = nullptr;
    }
    if (ddict == nullptr) {
        cached_bytes = bytes;
        ddict = ZSTD_createDDict(cached_bytes.data(), cached_bytes.size());
    }
    return ddict;
}

/// x0 dctx, x1 dst, x2 dstCapacity, x3 src, x4 srcSize, x5 dict, x6 dictSize, x7 ddict (as
/// ZSTD_decompressMultiFrame). On success writes dst, sets x0 to the size and returns to x30.
/// Otherwise leaves the registers alone: the guest's own function runs from the next instruction.
template <typename Jit, typename Memory>
bool TryRun(Jit& jit, Memory& memory) {
    const u64 dst = jit.GetRegister(1);
    const u64 capacity = jit.GetRegister(2);
    const u64 src = jit.GetRegister(3);
    const u64 src_size = jit.GetRegister(4);
    const u64 dict = jit.GetRegister(5);
    const u64 dict_size = jit.GetRegister(6);
    const u64 ddict = jit.GetRegister(7);
    constexpr u64 Limit = 256ULL << 20;
    Stats& stats = GetStats();
    if (src_size == 0 || src_size > Limit || capacity > Limit) {
        stats.fallbacks.fetch_add(1, std::memory_order_relaxed);
        return false;
    }

    thread_local std::vector<u8> input;
    thread_local std::vector<u8> output;
    thread_local std::vector<u8> dictionary;
    thread_local std::unique_ptr<ZSTD_DCtx, decltype(&ZSTD_freeDCtx)> dctx{ZSTD_createDCtx(),
                                                                          &ZSTD_freeDCtx};
    input.resize(src_size);
    output.resize(capacity);
    if (!memory.ReadBlock(src, input.data(), input.size())) {
        stats.fallbacks.fetch_add(1, std::memory_order_relaxed);
        return false;
    }

    // ZSTD_DDict starts { dictBuffer, dictContent, dictSize } in every zstd since 1.3.
    u64 dict_address = dict;
    u64 dict_length = dict_size;
    if (ddict != 0) {
        dict_address = memory.Read64(ddict + 8);
        dict_length = memory.Read64(ddict + 16);
    }
    size_t result;
    if (dict_address != 0 && dict_length != 0) {
        if (dict_length > Limit) {
            stats.fallbacks.fetch_add(1, std::memory_order_relaxed);
            return false;
        }
        dictionary.resize(dict_length);
        if (!memory.ReadBlock(dict_address, dictionary.data(), dictionary.size())) {
            stats.fallbacks.fetch_add(1, std::memory_order_relaxed);
            return false;
        }
        ZSTD_DDict* const native_ddict = CachedDDict(dict_address, dict_length, dictionary);
        result = native_ddict == nullptr
                     ? size_t(-1)
                     : ZSTD_decompress_usingDDict(dctx.get(), output.data(), output.size(),
                                                  input.data(), input.size(), native_ddict);
    } else {
        result = ZSTD_decompressDCtx(dctx.get(), output.data(), output.size(), input.data(),
                                     input.size());
    }
    if (ZSTD_isError(result)) {
        if (stats.fallbacks.fetch_add(1, std::memory_order_relaxed) < 8) {
            LOG_WARNING(Core_ARM, "Native zstd: {} for {:#x} bytes (dict {:#x}); the game's own runs",
                        ZSTD_getErrorName(result), src_size, dict_length);
        }
        return false;
    }
    memory.WriteBlock(dst, output.data(), result);
    jit.SetRegister(0, result);
    jit.SetPC(jit.GetRegister(30));

    const u64 calls = stats.calls.fetch_add(1, std::memory_order_relaxed) + 1;
    stats.in_bytes.fetch_add(src_size, std::memory_order_relaxed);
    stats.out_bytes.fetch_add(result, std::memory_order_relaxed);
    if ((calls & (calls - 1)) == 0) {
        LOG_INFO(Core_ARM, "Native zstd: {} frames, {} MiB in, {} MiB out, {} left to the game",
                 calls, stats.in_bytes.load(std::memory_order_relaxed) >> 20,
                 stats.out_bytes.load(std::memory_order_relaxed) >> 20,
                 stats.fallbacks.load(std::memory_order_relaxed));
    }
    return true;
}

} // namespace Core::NativeZstd
