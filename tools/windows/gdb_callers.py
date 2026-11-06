#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

"""Finds who calls a guest function, through Eden's gdbstub (use_gdbstub in the config).

    python -I tools/windows/gdb_callers.py <main+offset hex> <trigger file> [hits] [port]

Connects, lets the game run, waits until <trigger file> exists (the game is where the function
runs), then breaks at the main module's base + offset (the base is read from the log, it moves
every boot) `hits` times. Each hit prints x0-x7, sp, lr and the frame pointer chain, then the
breakpoint is removed and the debugger detaches.
"""

import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nx2"))
import gdbrsp  # noqa: E402

LOG = os.path.join(os.environ["APPDATA"], "eden", "log", "eden_log.txt")


def main_base():
    base = None
    with open(LOG, errors="replace") as file:
        for line in file:
            m = re.search(r"Module main loaded at (0x[0-9a-f]+)", line)
            if m:
                base = int(m.group(1), 16)
    return base


def main():
    offset = int(sys.argv[1], 16)
    trigger = sys.argv[2]
    hits = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    port = int(sys.argv[4]) if len(sys.argv) > 4 else 6543
    rsp = gdbrsp.Rsp(port)
    for _ in range(240):
        reason = rsp.cmd("?")
        m = re.search(r"thread:([0-9a-f]+);", reason)
        if m and int(m.group(1), 16) < 0x10000:
            break
        time.sleep(0.5)
    print("connected:", reason, flush=True)
    # Let the game run until the trigger appears.
    pkt = b"c"
    rsp.s.sendall(b"$" + pkt + b"#" + f"{sum(pkt) & 0xff:02x}".encode())
    while not os.path.exists(trigger):
        time.sleep(1)
    base = main_base()
    target = base + offset
    print("main at %#x, breaking at %#x" % (base, target), flush=True)
    rsp.s.sendall(b"\x03")
    print("interrupted:", rsp._read_packet(), flush=True)
    print("set bp:", rsp.cmd(f"Z0,{target:x},4"), flush=True)
    for hit in range(hits):
        stop = rsp.cmd("c")
        regs = rsp.regs()
        print("\n== hit %d (%s) pc=%#x" % (hit, stop[:40], regs.get("pc", 0)))
        print("   " + " ".join("x%d=%#x" % (i, regs["x%d" % i]) for i in range(8)))
        print("   sp=%#x lr=%#x fp=%#x" % (regs["sp"], regs["x30"], regs["x29"]))
        chain = [regs["x30"]]
        fp = regs["x29"]
        for _ in range(12):
            frame = rsp.mem(fp, 16)
            if len(frame) < 16:
                break
            prev, ret = int.from_bytes(frame[:8], "little"), int.from_bytes(frame[8:], "little")
            if ret == 0 or prev <= fp:
                break
            chain.append(ret)
            fp = prev
        print("   callers: " + " <- ".join("main+%#x" % (a - base) if base <= a < base + 0x4ea0000
                                          else "%#x" % a for a in chain), flush=True)
        if regs.get("pc") != target:
            break
        # Step past the breakpoint before continuing.
        rsp.cmd(f"z0,{target:x},4")
        rsp.cmd("s")
        rsp.cmd(f"Z0,{target:x},4")
    rsp.cmd(f"z0,{target:x},4")
    pkt = b"D"
    rsp.s.sendall(b"$" + pkt + b"#" + f"{sum(pkt) & 0xff:02x}".encode())
    print("\ndetached", flush=True)


if __name__ == "__main__":
    main()
