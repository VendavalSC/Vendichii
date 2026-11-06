#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

"""Breaks at main+offset `hits` times through Eden's gdbstub and prints x0-x7 plus the first bytes
at the pointers given (by register name), then detaches.

    python -I tools/windows/gdb_args.py <main+offset hex> <hits> [reg:len ...]
"""

import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nx2"))
import gdb_callers  # noqa: E402
import gdbrsp  # noqa: E402


def main():
    offset, hits = int(sys.argv[1], 16), int(sys.argv[2])
    peeks = [(p.split(":")[0], int(p.split(":")[1])) for p in sys.argv[3:]]
    rsp = gdbrsp.Rsp(6543)
    rsp.s.sendall(b"\x03")
    print("interrupted:", rsp._read_packet()[:40], flush=True)
    base = gdb_callers.main_base()
    target = base + offset
    print("main at %#x, breaking at %#x" % (base, target), flush=True)
    rsp.cmd(f"Z0,{target:x},4")
    started = time.time()
    for hit in range(hits):
        rsp.cmd("c")
        regs = rsp.regs()
        if regs.get("pc") != target:
            print("stopped elsewhere at %#x" % regs.get("pc", 0))
            break
        print("\n== hit %d at +%.2f s lr=main+%#x" % (hit, time.time() - started, regs["x30"] - base))
        print("   " + " ".join("x%d=%#x" % (i, regs["x%d" % i]) for i in range(8)))
        for name, length in peeks:
            data = rsp.mem(regs[name], length)
            print("   [%s] %s" % (name, data.hex(" ")))
        rsp.cmd(f"z0,{target:x},4")
        rsp.cmd("s")
        rsp.cmd(f"Z0,{target:x},4")
    rsp.cmd(f"z0,{target:x},4")
    pkt = b"D"
    rsp.s.sendall(b"$" + pkt + b"#" + f"{sum(pkt) & 0xff:02x}".encode())
    print("\ndetached", flush=True)


if __name__ == "__main__":
    main()
