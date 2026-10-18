#!/usr/bin/env python3
"""Compare the native ARM64 code against results captured from original bytes."""
import ctypes as C
import json
from pathlib import Path
import platform

from verify_original import Tile, native_tile, native_state

ROOT = Path(__file__).resolve().parent
assert platform.machine() == "arm64", "Run this stage natively on Apple silicon"
lib = C.CDLL(str(ROOT / "recovered_combat_native.dylib"))
for name in ("get_attack", "get_poison"):
    fn = getattr(lib, "dr_" + name)
    fn.argtypes, fn.restype = [C.POINTER(Tile)], C.c_int32
lib.dr_add_poison.argtypes, lib.dr_add_poison.restype = [C.POINTER(Tile), C.c_int32], None
lib.dr_pointer_size.restype = C.c_uint32
assert lib.dr_pointer_size() == 8
fixtures = json.loads((ROOT / "original_results.json").read_text())
for i, row in enumerate(fixtures):
    tile, context, character = native_tile(row["attack"], row["before"], row["race"])
    op = row["op"]
    if op == "add_poison":
        lib.dr_add_poison(C.byref(tile), row["amount"])
    else:
        actual = getattr(lib, "dr_" + op)(C.byref(tile))
        assert actual == row["expected_return"], (i, op, actual, row)
    assert native_state(tile) == tuple(row["after"]), (i, op, native_state(tile), row)
    if "expected_attack_after" in row:
        assert lib.dr_get_attack(C.byref(tile)) == row["expected_attack_after"]
result = {"status": "passed", "machine": platform.machine(), "pointer_bytes": 8,
          "original_fixture_count": len(fixtures),
          "scope": "Three recovered functions; whole game not ported or tested"}
(ROOT / "verification_arm64.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
