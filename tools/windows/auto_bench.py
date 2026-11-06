#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

"""Runs the scripted camera benchmark without anyone at the controls.

    python -I tools/windows/auto_bench.py --label <name> [--set NAME=VALUE ...] [--nav nav.json]

It boots the game with the debug server on (EDEN_NX2_DEBUG_SERVER), replays --nav (debug server
input steps that get from boot to the saved game, with waits), starts the loaded TAS script
through EDEN_TAS_START_FILE, waits for it to end and closes the emulator. EDEN_NX2_FLASH_WATCH
counts one- and two-frame flashes of the presented image meanwhile. The result (fps of the TAS
seconds, flashes) is appended to %APPDATA%/eden/log/auto_bench.jsonl and printed.
"""

import argparse
import csv
import glob
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "nx2"))
import debug_mcp  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
EXE = os.path.join(REPO, "build", "release", "bin", "lichii.exe")
LOG_DIR = os.path.join(os.environ["APPDATA"], "eden", "log")
SERVER = "127.0.0.1:6545"


def running_lichii():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq lichii.exe", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    return "lichii.exe" in out.lower()


def wait_for(emulator, predicate, seconds, what):
    end = time.time() + seconds
    while time.time() < end:
        try:
            status = emulator.call("status", {}, 10)
            if predicate(status):
                return status
        except debug_mcp.EmulatorError:
            pass
        time.sleep(1)
    raise TimeoutError("timed out waiting for " + what)


def run_nav(emulator, steps):
    for step in steps:
        if "wait" in step:
            time.sleep(step["wait"])
        elif "screenshot" in step:
            emulator.call("screenshot", {"save": step["screenshot"]}, 60)
        else:
            frames = sum(s.get("frames", 0) for s in step["steps"])
            emulator.call("input_sequence", {"steps": step["steps"]}, frames // 10 + 60)


def summarize(fps_csv, log_path):
    with open(fps_csv, newline="") as file:
        rows = [r for r in csv.DictReader(file) if r.get("tas") == "1"]
    result = {"tas_seconds": len(rows)}
    if rows:
        fps = [float(r["fps"]) for r in rows]
        low = [float(r["low1_fps"]) for r in rows]
        result.update(mean_fps=round(sum(fps) / len(fps), 1),
                      low1_fps=round(sum(low) / len(low), 1), worst_second=min(fps))
        begin_ns, end_ns = int(rows[0]["end_ns"]) - 1_000_000_000, int(rows[-1]["end_ns"])
    flashes = 0
    with open(log_path, errors="replace") as file:
        for line in file:
            if "Flash watch: frame" in line and "flashed in" in line:
                flashes += 1
    result["flashes"] = flashes
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", required=True)
    parser.add_argument("--set", action="append", default=[], help="NAME=VALUE environment")
    parser.add_argument("--nav", default=os.path.join(HERE, "oot_kokiri_nav.json"))
    parser.add_argument("--game", required=True)
    parser.add_argument("--tas-seconds", type=int, default=72)
    parser.add_argument("--keep-open", action="store_true", help="leave the game running")
    args = parser.parse_args()

    if running_lichii():
        sys.exit("another Lichii is running: close it first (benchmarks need the machine alone)")

    start_file = os.path.join(LOG_DIR, "tas.start")
    flash_dir = os.path.join(LOG_DIR, "flash-watch")
    os.makedirs(flash_dir, exist_ok=True)
    env = dict(os.environ)
    env.update(EDEN_FPS_LOG="1", EDEN_TAS_REALTIME="1", EDEN_NX2_DEBUG_SERVER=SERVER,
               EDEN_TAS_START_FILE=start_file, EDEN_NX2_FLASH_WATCH=flash_dir,
               EDEN_NX2_FLASH_WATCH_PASSES="0")
    for pair in args.set:
        name, _, value = pair.partition("=")
        env[name] = value

    before = set(glob.glob(os.path.join(LOG_DIR, "fps_*.csv")))
    process = subprocess.Popen([EXE, "-g", args.game], env=env)
    emulator = debug_mcp.Emulator(SERVER)
    try:
        wait_for(emulator, lambda s: s.get("powered_on") and s.get("presents", 0) > 30, 180,
                 "the game to boot")
        with open(args.nav) as file:
            run_nav(emulator, json.load(file))
        open(start_file, "w").close()
        time.sleep(args.tas_seconds)
    finally:
        emulator.close()
        if not args.keep_open:
            process.terminate()
            try:
                process.wait(30)
            except subprocess.TimeoutExpired:
                process.kill()
    time.sleep(2)
    fps_csv = max(set(glob.glob(os.path.join(LOG_DIR, "fps_*.csv"))) - before,
                  key=os.path.getmtime)
    result = {"label": args.label, "set": args.set, "fps_csv": os.path.basename(fps_csv)}
    result.update(summarize(fps_csv, os.path.join(LOG_DIR, "eden_log.txt")))
    with open(os.path.join(LOG_DIR, "auto_bench.jsonl"), "a") as file:
        file.write(json.dumps(result) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
