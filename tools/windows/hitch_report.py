#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

"""Where the emulator's threads spend the frames that hitch (EDEN_FPS_LOG hitch file plus an
EDEN_NX2_SAMPLE_PROFILE capture of the same run).

    python -I tools/windows/hitch_report.py hitch_<title>_<date>.csv nx2_samples_<pid>.bin \
        --exe build/release/bin/lichii.exe --symbolizer tools\\windows\\dbghelp-symbolizer.cmd

Samples taken during a frame of --min-ms or more are compared, per thread, with the samples of
the other frames: functions are listed by how much more of the thread's time they take in
hitching frames (inclusive), so the work that appears only when the game stutters stands out.
"""

import argparse
import collections
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nx2"))
import sample_report  # noqa: E402

IDLE_MARKERS = ("ntdll.dll+", "KERNELBASE.dll+", "win32u.dll+")


def load_hitches(path, min_ms):
    with open(path, newline="") as file:
        rows = [r for r in csv.DictReader(file) if float(r["ms"]) >= min_ms]
    return sorted((int(r["end_ns"]) - int(float(r["ms"]) * 1e6), int(r["end_ns"])) for r in rows)


def in_windows(windows, t):
    lo, hi = 0, len(windows)
    while lo < hi:
        mid = (lo + hi) // 2
        if windows[mid][1] < t:
            lo = mid + 1
        else:
            hi = mid
    return lo < len(windows) and windows[lo][0] <= t <= windows[lo][1]


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("hitches")
    parser.add_argument("samples")
    parser.add_argument("--exe", default="lichii.exe")
    parser.add_argument("--symbolizer", default="llvm-symbolizer")
    parser.add_argument("--min-ms", type=float, default=25.0)
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--tas-fps", help="EDEN_FPS_LOG csv of the run: only count the samples "
                        "taken while a TAS script played (a scripted benchmark)")
    args = parser.parse_args()

    with open(args.samples, "rb") as file:
        sample_file = sample_report.parse(file.read())
    if args.tas_fps:
        with open(args.tas_fps, newline="") as file:
            ends = [int(r["end_ns"]) for r in csv.DictReader(file) if r.get("tas") == "1"]
        if not ends:
            sys.exit("no TAS seconds with end_ns in " + args.tas_fps)
        begin, end = ends[0] - 1_000_000_000, ends[-1]
        to_ns_bench = 1e9 / sample_file.qpc_frequency
        sample_file.samples = [s for s in sample_file.samples
                               if begin <= s[1] * to_ns_bench <= end]
        print("TAS window: %.0f s, %d samples" % ((end - begin) / 1e9, len(sample_file.samples)))
    windows = load_hitches(args.hitches, args.min_ms)
    to_ns = 1e9 / sample_file.qpc_frequency
    first = sample_file.samples[0][1] * to_ns if sample_file.samples else 0
    last = sample_file.samples[-1][1] * to_ns if sample_file.samples else 0
    covered = [w for w in windows if w[1] >= first and w[0] <= last]
    print("%d hitching frames of %.0f ms or more, %d inside the %.0f s profile (%.1f s of them)"
          % (len(windows), args.min_ms, len(covered), (last - first) / 1e9,
             sum(e - s for s, e in covered) / 1e9))
    if not covered:
        return

    symbolizer = sample_report.Symbolizer(args.exe if os.path.exists(args.exe) else None,
                                          args.samples + ".symcache.json", args.symbolizer)
    stacks = sample_report.symbolize_samples(sample_file, os.path.basename(args.exe), symbolizer)

    totals = collections.defaultdict(lambda: [0, 0])
    inclusive = collections.defaultdict(lambda: [collections.Counter(), collections.Counter()])
    for (_tag, qpc, _frames), (thread, stack) in zip(sample_file.samples, stacks):
        side = 1 if in_windows(covered, qpc * to_ns) else 0
        totals[thread][side] += 1
        for name in set(stack):
            if not name.startswith(IDLE_MARKERS):
                inclusive[thread][side][name] += 1

    for thread in sorted(totals):
        normal, hitch = totals[thread]
        if not hitch or not normal:
            continue
        print("\n== %s: %d samples in hitches, %d in other frames" % (thread, hitch, normal))
        rows = []
        for name in set(inclusive[thread][0]) | set(inclusive[thread][1]):
            share_hitch = inclusive[thread][1][name] / hitch
            share_normal = inclusive[thread][0][name] / normal
            rows.append((share_hitch - share_normal, share_hitch, share_normal, name))
        rows.sort(reverse=True)
        print("  +delta  hitch  other  function (inclusive share of the thread)")
        for delta, share_hitch, share_normal, name in rows[:args.top]:
            print("  %+5.1f%% %5.1f%% %5.1f%%  %s"
                  % (100 * delta, 100 * share_hitch, 100 * share_normal, name[:150]))


if __name__ == "__main__":
    main()
