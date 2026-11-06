#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

"""Names AArch64 instruction words with dynarmic's own decoder table (frontend/A64/decoder/a64.inc),
first match in file order, as the decoder does. No disassembler needed: it answers which
instructions hot guest code is made of, not their operands.

    python -I tools/windows/a64_classify.py <read_memory json (as u32)> <base address> [pc ...]

With PCs (block starts from jit_report.py), it lists each block's instructions up to its first
branch; without, it prints the instruction mix of the whole range.
"""

import collections
import json
import os
import re
import sys

TABLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src", "dynarmic",
                     "src", "dynarmic", "frontend", "A64", "decoder", "a64.inc")
BRANCHES = ("B_", "BL", "BR", "BLR", "RET", "CBZ", "CBNZ", "TBZ", "TBNZ", "B_cond", "RETA",
            "BRA_BLRA", "SVC", "BRK", "HLT", "ERET")


def load_table():
    entries = []
    for line in open(TABLE):
        m = re.match(r'\s*INST\((\w+),\s*"([^"]*)",\s*"([01a-zA-Z\-]{32})"\)', line)
        if not m:
            continue
        name, _desc, bits = m.groups()
        mask = value = 0
        for i, c in enumerate(bits):
            bit = 1 << (31 - i)
            if c in "01":
                mask |= bit
                if c == "1":
                    value |= bit
        entries.append((mask, value, name))
    return entries


def classify(entries, word):
    for mask, value, name in entries:
        if word & mask == value:
            return name
    return "?"


def is_branch(name):
    return any(name == b or name.startswith(b + "_") for b in BRANCHES) or name in (
        "B_uncond", "BL", "BR", "BLR", "RET", "CBZ", "CBNZ", "TBZ", "TBNZ", "B_cond")


def main():
    data = json.load(open(sys.argv[1]))
    words = [int(x, 16) if isinstance(x, str) else int(x) for x in data["u32"]]
    base = int(sys.argv[2], 0)
    entries = load_table()
    pcs = [int(p, 0) for p in sys.argv[3:]]
    if not pcs:
        mix = collections.Counter(classify(entries, w) for w in words)
        for name, count in mix.most_common(40):
            print("%5d  %s" % (count, name))
        return
    for pc in pcs:
        index = (pc - base) // 4
        print("block 0x%x:" % pc)
        for i in range(index, min(index + 64, len(words))):
            name = classify(entries, words[i])
            print("   %x  %08x  %s" % (base + 4 * i, words[i], name))
            if is_branch(name):
                break


if __name__ == "__main__":
    main()
