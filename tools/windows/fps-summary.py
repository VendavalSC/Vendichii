#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

"""Summarizes EDEN_FPS_LOG files (src/core/perf_stats.cpp).

    python -I tools/windows/fps-summary.py [csv ...] [--skip 30] [--tas]

With no files, reads the newest five in %APPDATA%/eden/log. --skip drops the first seconds
(boot, menus, shader compilation). Per file: mean fps, the worst second's fps, the share of
seconds under 59 fps, the mean 1% low and the worst frame.
"""

import argparse
import csv
import glob
import os


def summarize(path, skip, tas):
    with open(path, newline="") as f:
        # Logs from before the header fix have a NUL after the header line
        lines = f.read().replace("\0", "").splitlines()
    rows = [r for r in csv.DictReader(lines) if float(r["seconds"]) >= skip]
    if tas:
        rows = [r for r in rows if r.get("tas") == "1"]
    if not rows:
        return f"{os.path.basename(path)}: no seconds after --skip {skip}" + (" with a TAS playing" if tas else "")
    fps = [float(r["fps"]) for r in rows]
    low = [float(r["low1_fps"]) for r in rows]
    worst = max(float(r["max_ms"]) for r in rows)
    under = sum(1 for v in fps if v < 59) / len(fps) * 100
    return (f"{os.path.basename(path)}: {len(rows)} s, mean {sum(fps) / len(fps):.1f} fps, "
            f"worst second {min(fps):.1f}, under 59 fps {under:.0f}% of seconds, "
            f"1% low {sum(low) / len(low):.1f}, worst frame {worst:.1f} ms")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="*")
    parser.add_argument("--skip", type=float, default=30)
    parser.add_argument("--tas", action="store_true",
                        help="only the seconds a TAS script was playing (a scripted benchmark)")
    args = parser.parse_args()
    files = args.files
    if not files:
        logs = os.path.join(os.environ.get("APPDATA", ""), "eden", "log", "fps_*.csv")
        files = sorted(glob.glob(logs), key=os.path.getmtime)[-5:]
    for path in files:
        print(summarize(path, 0 if args.tas else args.skip, args.tas))


if __name__ == "__main__":
    main()
