#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

"""Names the guest code behind the [jit] samples of an EDEN_NX2_SAMPLE_PROFILE capture.

    python -I tools/windows/jit_report.py nx2_samples_<pid>.bin perf-<pid>.map \
        [--threads CPUCore_*] [--tas-fps fps_<title>_<date>.csv] [--top 40]

The map is dynarmic's perf map (EDEN_JIT_PERF_MAP=<dir> on Windows): one line per translated
block, "host_start size a64_<guest pc>_fpcr<fpcr>". Each sample whose innermost frame lies in a
block counts for that block's guest PC; blocks are also grouped by 4 KiB guest page, a rough
stand-in for the game function they belong to. When the code cache was cleared ("CLEAR <ns>"),
the latest block registered at an address wins.
"""

import argparse
import bisect
import collections
import csv
import fnmatch
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nx2"))
import sample_report  # noqa: E402


def load_map(path):
    blocks = {}
    clears = 0
    with open(path) as file:
        for line in file:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "CLEAR":
                clears += 1
                continue
            if len(parts) < 3:
                continue
            start, size, name = int(parts[0], 16), int(parts[1], 16), parts[2]
            blocks[start] = (start + size, name)  # later registrations replace earlier ones
    starts = sorted(blocks)
    return starts, blocks, clears


def guest_pc(name):
    # a64_<16 hex digits>_fpcr<8 hex digits>
    if name.startswith("a64_") and len(name) > 20:
        try:
            return int(name[4:20], 16)
        except ValueError:
            pass
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("samples")
    parser.add_argument("perf_map")
    parser.add_argument("--threads", default="CPUCore_*")
    parser.add_argument("--tas-fps")
    parser.add_argument("--top", type=int, default=40)
    args = parser.parse_args()

    with open(args.samples, "rb") as file:
        sample_file = sample_report.parse(file.read())
    to_ns = 1e9 / sample_file.qpc_frequency
    samples = sample_file.samples
    if args.tas_fps:
        with open(args.tas_fps, newline="") as file:
            ends = [int(r["end_ns"]) for r in csv.DictReader(file) if r.get("tas") == "1"]
        begin, end = ends[0] - 1_000_000_000, ends[-1]
        samples = [s for s in samples if begin <= s[1] * to_ns <= end]

    starts, blocks, clears = load_map(args.perf_map)
    print("%d blocks in the map, %d code cache clears" % (len(blocks), clears))

    by_block = collections.Counter()
    by_page = collections.Counter()
    named = collections.Counter()
    totals = collections.Counter()
    for tag, _qpc, frames in samples:
        thread = sample_file.threads.get(tag, "thread %d" % tag)
        if not fnmatch.fnmatch(thread, args.threads) or not frames:
            continue
        totals["all"] += 1
        address = frames[0]
        base, _path = sample_report.find_module(sample_file.modules, address)
        if base is not None:
            continue
        totals["jit"] += 1
        i = bisect.bisect_right(starts, address) - 1
        if i < 0 or address >= blocks[starts[i]][0]:
            totals["unmapped"] += 1
            continue
        name = blocks[starts[i]][1]
        pc = guest_pc(name)
        if pc is None:
            named[name] += 1
            continue
        by_block[pc] += 1
        by_page[pc >> 12] += 1

    jit = totals["jit"] or 1
    print("%s samples: %d, in JIT code %d (%.1f%%), unmapped %d"
          % (args.threads, totals["all"], totals["jit"], 100 * totals["jit"] / max(totals["all"], 1),
             totals["unmapped"]))
    print("\nJIT helpers (dispatchers, memory fallbacks):")
    for name, count in named.most_common(10):
        print("  %5.1f%%  %s" % (100 * count / jit, name))
    print("\nHottest guest pages (share of JIT samples):")
    covered = 0.0
    for page, count in by_page.most_common(args.top):
        covered += count / jit
        print("  %5.1f%%  cum %5.1f%%  0x%016x" % (100 * count / jit, 100 * covered, page << 12))
    print("\nHottest guest blocks:")
    for pc, count in by_block.most_common(args.top):
        print("  %5.1f%%  0x%016x" % (100 * count / jit, pc))


if __name__ == "__main__":
    main()
