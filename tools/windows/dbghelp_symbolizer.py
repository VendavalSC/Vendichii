#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

"""A stand-in for llvm-symbolizer on Windows machines without LLVM, built on DbgHelp.

    python -I tools/windows/dbghelp_symbolizer.py --obj=lichii.exe --relative-address \
        --inlines --output-style=JSON < rvas.txt

Reads one RVA per line and prints one JSON line per RVA, {"Symbol": [{"FunctionName": ...}]},
innermost inline frame first, which is all tools/nx2/sample_report.py reads. Use it there with
--symbolizer tools\\windows\\dbghelp-symbolizer.cmd (the .pdb must sit next to the .exe).
"""

import ctypes
import ctypes.wintypes as wt
import json
import os
import sys

SYMOPT_UNDNAME = 0x2
SYMOPT_FAIL_CRITICAL_ERRORS = 0x200
MAX_NAME = 1024
BASE = 0x140000000


class SymbolInfo(ctypes.Structure):
    _fields_ = [
        ("SizeOfStruct", wt.ULONG), ("TypeIndex", wt.ULONG), ("Reserved", ctypes.c_uint64 * 2),
        ("Index", wt.ULONG), ("Size", wt.ULONG), ("ModBase", ctypes.c_uint64),
        ("Flags", wt.ULONG), ("Value", ctypes.c_uint64), ("Address", ctypes.c_uint64),
        ("Register", wt.ULONG), ("Scope", wt.ULONG), ("Tag", wt.ULONG), ("NameLen", wt.ULONG),
        ("MaxNameLen", wt.ULONG), ("Name", wt.WCHAR * MAX_NAME),
    ]


def main():
    obj = next((arg.split("=", 1)[1] for arg in sys.argv[1:] if arg.startswith("--obj=")), None)
    if obj is None:
        sys.exit("dbghelp_symbolizer: --obj=<exe> is required")
    obj = os.path.abspath(obj)

    dbghelp = ctypes.WinDLL("dbghelp.dll")
    dbghelp.SymLoadModuleExW.restype = ctypes.c_uint64
    dbghelp.SymLoadModuleExW.argtypes = [wt.HANDLE, wt.HANDLE, wt.LPCWSTR, wt.LPCWSTR,
                                         ctypes.c_uint64, wt.DWORD, ctypes.c_void_p, wt.DWORD]
    dbghelp.SymFromAddrW.argtypes = [wt.HANDLE, ctypes.c_uint64, ctypes.POINTER(ctypes.c_uint64),
                                     ctypes.POINTER(SymbolInfo)]
    dbghelp.SymAddrIncludeInlineTrace.restype = wt.DWORD
    dbghelp.SymAddrIncludeInlineTrace.argtypes = [wt.HANDLE, ctypes.c_uint64]
    dbghelp.SymQueryInlineTrace.argtypes = [wt.HANDLE, ctypes.c_uint64, wt.DWORD, ctypes.c_uint64,
                                            ctypes.c_uint64, ctypes.POINTER(wt.DWORD),
                                            ctypes.POINTER(wt.DWORD)]
    dbghelp.SymFromInlineContextW.argtypes = [wt.HANDLE, ctypes.c_uint64, wt.DWORD,
                                              ctypes.POINTER(ctypes.c_uint64),
                                              ctypes.POINTER(SymbolInfo)]

    # Any unique value works as the session handle when no real process is attached.
    process = wt.HANDLE(0x5E5E)
    dbghelp.SymSetOptions(SYMOPT_UNDNAME | SYMOPT_FAIL_CRITICAL_ERRORS)
    if not dbghelp.SymInitializeW(process, os.path.dirname(obj), False):
        sys.exit("dbghelp_symbolizer: SymInitialize failed")
    if not dbghelp.SymLoadModuleExW(process, None, obj, None, BASE, 0, None, 0):
        sys.exit("dbghelp_symbolizer: can't load " + obj)

    info = SymbolInfo()
    displacement = ctypes.c_uint64()

    def name_at(address, context=None):
        info.SizeOfStruct = 88  # sizeof(SYMBOL_INFOW), Name[1] and padding included
        info.MaxNameLen = MAX_NAME
        found = (dbghelp.SymFromInlineContextW(process, address, context,
                                               ctypes.byref(displacement), ctypes.byref(info))
                 if context is not None else
                 dbghelp.SymFromAddrW(process, address, ctypes.byref(displacement),
                                      ctypes.byref(info)))
        return info.Name if found else None

    out = sys.stdout
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        address = BASE + int(line, 0)
        names = []
        inlines = dbghelp.SymAddrIncludeInlineTrace(process, address)
        context = wt.DWORD()
        frame = wt.DWORD()
        if inlines and dbghelp.SymQueryInlineTrace(process, address, 0, address, address,
                                                   ctypes.byref(context), ctypes.byref(frame)):
            for i in range(inlines):
                name = name_at(address, context.value + i)
                if name:
                    names.append(name)
        outer = name_at(address)
        if outer and (not names or names[-1] != outer):
            names.append(outer)
        out.write(json.dumps({"Symbol": [{"FunctionName": n} for n in names or ["??"]]}) + "\n")


if __name__ == "__main__":
    main()
