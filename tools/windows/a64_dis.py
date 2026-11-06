#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

"""A small AArch64 disassembler for reading hot guest code without LLVM: the integer, load/store
and branch forms games' hot loops are made of. Anything else is named by dynarmic's decoder table
(a64_classify.py) with its raw word.

    python -I tools/windows/a64_dis.py <read_memory json (as u32)> <base address> [start [count]]
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a64_classify  # noqa: E402

CONDS = ["eq", "ne", "hs", "lo", "mi", "pl", "vs", "vc", "hi", "ls", "ge", "lt", "gt", "le",
         "al", "nv"]


def bits(w, hi, lo):
    return (w >> lo) & ((1 << (hi - lo + 1)) - 1)


def sx(value, width):
    return value - (1 << width) if value & (1 << (width - 1)) else value


def reg(n, sf, sp=False):
    if n == 31:
        return ("sp" if sf else "wsp") if sp else ("xzr" if sf else "wzr")
    return ("x" if sf else "w") + str(n)


def dis(w, pc):
    sf = bits(w, 31, 31)
    rd, rn, rm = bits(w, 4, 0), bits(w, 9, 5), bits(w, 20, 16)
    # Branches
    if bits(w, 31, 26) in (0b000101, 0b100101):
        return ("bl" if bits(w, 31, 31) else "b") + " 0x%x" % (pc + sx(bits(w, 25, 0), 26) * 4)
    if bits(w, 31, 24) == 0b01010100:
        return "b.%s 0x%x" % (CONDS[bits(w, 3, 0)], pc + sx(bits(w, 23, 5), 19) * 4)
    if bits(w, 30, 25) == 0b011010:
        op = "cbnz" if bits(w, 24, 24) else "cbz"
        return "%s %s, 0x%x" % (op, reg(rd, sf), pc + sx(bits(w, 23, 5), 19) * 4)
    if bits(w, 30, 25) == 0b011011:
        op = "tbnz" if bits(w, 24, 24) else "tbz"
        bit = (bits(w, 31, 31) << 5) | bits(w, 23, 19)
        return "%s %s, #%d, 0x%x" % (op, reg(rd, bit >= 32), bit, pc + sx(bits(w, 18, 5), 14) * 4)
    if w & 0xfffffc1f == 0xd65f0000:
        return "ret" + ("" if rn == 30 else " x%d" % rn)
    if w & 0xfffffc1f == 0xd61f0000:
        return "br x%d" % rn
    if w & 0xfffffc1f == 0xd63f0000:
        return "blr x%d" % rn
    # Add/sub immediate
    if bits(w, 28, 23) == 0b100010:
        op = ["add", "adds", "sub", "subs"][bits(w, 30, 29)]
        imm = bits(w, 21, 10) << (12 if bits(w, 22, 22) else 0)
        if op == "subs" and rd == 31:
            return "cmp %s, #0x%x" % (reg(rn, sf, True), imm)
        return "%s %s, %s, #0x%x" % (op, reg(rd, sf, op in ("add", "sub")), reg(rn, sf, True), imm)
    # Add/sub shifted register
    if bits(w, 28, 24) == 0b01011 and bits(w, 21, 21) == 0:
        op = ["add", "adds", "sub", "subs"][bits(w, 30, 29)]
        shift = ["lsl", "lsr", "asr", "ror"][bits(w, 23, 22)]
        amount = bits(w, 15, 10)
        tail = (", %s #%d" % (shift, amount)) if amount else ""
        if op == "subs" and rd == 31:
            return "cmp %s, %s%s" % (reg(rn, sf), reg(rm, sf), tail)
        if op == "sub" and rn == 31:
            return "neg %s, %s%s" % (reg(rd, sf), reg(rm, sf), tail)
        return "%s %s, %s, %s%s" % (op, reg(rd, sf), reg(rn, sf), reg(rm, sf), tail)
    # Logical shifted register
    if bits(w, 28, 24) == 0b01010:
        op = ["and", "bic", "orr", "orn", "eor", "eon", "ands", "bics"][
            (bits(w, 30, 29) << 1) | bits(w, 21, 21)]
        shift = ["lsl", "lsr", "asr", "ror"][bits(w, 23, 22)]
        amount = bits(w, 15, 10)
        tail = (", %s #%d" % (shift, amount)) if amount else ""
        if op == "orr" and rn == 31 and not amount:
            return "mov %s, %s" % (reg(rd, sf), reg(rm, sf))
        if op == "ands" and rd == 31:
            return "tst %s, %s%s" % (reg(rn, sf), reg(rm, sf), tail)
        return "%s %s, %s, %s%s" % (op, reg(rd, sf), reg(rn, sf), reg(rm, sf), tail)
    # Move wide
    if bits(w, 28, 23) == 0b100101:
        op = ["movn", "?", "movz", "movk"][bits(w, 30, 29)]
        return "%s %s, #0x%x, lsl #%d" % (op, reg(rd, sf), bits(w, 20, 5), bits(w, 22, 21) * 16)
    # Bitfield (lsl/lsr/asr/ubfx aliases)
    if bits(w, 28, 23) == 0b100110:
        opc, immr, imms = bits(w, 30, 29), bits(w, 21, 16), bits(w, 15, 10)
        size = 64 if sf else 32
        if opc == 2 and imms == size - 1:
            return "lsr %s, %s, #%d" % (reg(rd, sf), reg(rn, sf), immr)
        if opc == 2 and imms + 1 == immr:
            return "lsl %s, %s, #%d" % (reg(rd, sf), reg(rn, sf), size - 1 - imms)
        if opc == 0 and imms == size - 1:
            return "asr %s, %s, #%d" % (reg(rd, sf), reg(rn, sf), immr)
        name = ["sbfm", "bfm", "ubfm"][opc] if opc < 3 else "?"
        return "%s %s, %s, #%d, #%d" % (name, reg(rd, sf), reg(rn, sf), immr, imms)
    # Data processing (2 source): shifts by register, divides
    if bits(w, 30, 21) == 0b0011010110:
        op = {2: "udiv", 3: "sdiv", 8: "lslv", 9: "lsrv", 10: "asrv", 11: "rorv"}.get(
            bits(w, 15, 10), "dp2")
        return "%s %s, %s, %s" % (op, reg(rd, sf), reg(rn, sf), reg(rm, sf))
    # Conditional select
    if bits(w, 29, 21) == 0b011010100:
        op = ["csel", "csinc", "csinv", "csneg"][(bits(w, 30, 30) << 1) | bits(w, 10, 10)]
        return "%s %s, %s, %s, %s" % (op, reg(rd, sf), reg(rn, sf), reg(rm, sf),
                                      CONDS[bits(w, 15, 12)])
    # Conditional compare (register / immediate)
    if bits(w, 29, 21) == 0b111010010:
        op = "ccmp" if bits(w, 30, 30) else "ccmn"
        second = ("#%d" % rm) if bits(w, 11, 11) else reg(rm, sf)
        return "%s %s, %s, #%d, %s" % (op, reg(rn, sf), second, bits(w, 3, 0),
                                       CONDS[bits(w, 15, 12)])
    # Load/store register (unsigned offset, pre/post index, unscaled, register offset)
    if bits(w, 29, 27) == 0b111 and bits(w, 26, 26) == 0:
        size, opc = bits(w, 31, 30), bits(w, 23, 22)
        load = opc != 0
        x = size == 3 or (opc in (2,) and size < 2)
        name = ("ldr" if load else "str") + {0: "b", 1: "h", 2: "", 3: ""}[size]
        if opc >= 2 and size < 3:
            name = "ldrs" + {0: "b", 1: "h", 2: "w"}[size]
        rt = reg(rd, size == 3 or (opc == 2), False)
        base = reg(rn, 1, True)
        if bits(w, 25, 24) == 0b01:
            off = bits(w, 21, 10) << size
            return "%s %s, [%s, #0x%x]" % (name, rt, base, off)
        if bits(w, 21, 21) == 1 and bits(w, 11, 10) == 0b10:
            ext = ["?", "?", "uxtw", "lsl", "?", "?", "sxtw", "sxtx"][bits(w, 15, 13)]
            amt = (" #%d" % size) if bits(w, 12, 12) else ""
            return "%s %s, [%s, %s, %s%s]" % (name, rt, base, reg(rm, bits(w, 13, 13)), ext, amt)
        imm9 = sx(bits(w, 20, 12), 9)
        mode = bits(w, 11, 10)
        if mode == 0b01:
            return "%s %s, [%s], #%d" % (name, rt, base, imm9)
        if mode == 0b11:
            return "%s %s, [%s, #%d]!" % (name, rt, base, imm9)
        if mode == 0b00:
            return "%s %s, [%s, #%d]" % (name.replace("ldr", "ldur").replace("str", "stur"), rt,
                                         base, imm9)
    # Load/store pair (integer)
    if bits(w, 29, 27) == 0b101 and bits(w, 26, 26) == 0:
        x = bits(w, 31, 31)
        name = "ldp" if bits(w, 22, 22) else "stp"
        imm = sx(bits(w, 21, 15), 7) * (8 if x else 4)
        r1, r2, base = reg(rd, x), reg(bits(w, 14, 10), x), reg(rn, 1, True)
        mode = bits(w, 24, 23)
        if mode == 0b01:
            return "%s %s, %s, [%s], #%d" % (name, r1, r2, base, imm)
        if mode == 0b11:
            return "%s %s, %s, [%s, #%d]!" % (name, r1, r2, base, imm)
        return "%s %s, %s, [%s, #%d]" % (name, r1, r2, base, imm)
    return None


def main():
    data = json.load(open(sys.argv[1]))
    words = [int(x, 16) if isinstance(x, str) else int(x) for x in data["u32"]]
    base = int(sys.argv[2], 0)
    start = int(sys.argv[3], 0) if len(sys.argv) > 3 else base
    count = int(sys.argv[4], 0) if len(sys.argv) > 4 else len(words)
    table = a64_classify.load_table()
    first = (start - base) // 4
    for i in range(first, min(first + count, len(words))):
        pc = base + 4 * i
        text = dis(words[i], pc) or ("<%s>" % a64_classify.classify(table, words[i]))
        print("%x: %08x  %s" % (pc, words[i], text))


if __name__ == "__main__":
    main()
