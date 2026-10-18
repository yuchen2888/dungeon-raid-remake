#!/usr/bin/env python3
"""Compare recovered rules against original ARMv7, or replay on native ARM64.

Original mode executes real list traversal and game/class helper instructions.
No function calls are replaced by algorithm stubs.
"""
from __future__ import annotations
import ctypes as C
import hashlib
import itertools
import json
from pathlib import Path
import platform
import random
import struct
import sys

HERE = Path(__file__).resolve().parent

class Tile(C.Structure):
    _fields_ = [(name, C.c_int32) for name in
                ("type", "special", "enemy", "enemy_state", "x", "y")] + [
                (name, C.c_uint8) for name in ("flag231", "flag255", "matched")]
class Character(C.Structure):
    _fields_ = [("race", C.c_int32), ("flaws", C.c_int32 * 4)]
class Game(C.Structure):
    _fields_ = [("turn", C.c_int32), ("character", Character), ("board", C.POINTER(Tile))]

def tile(**kwargs):
    values = dict(type=1, special=2, enemy=0, enemy_state=0, x=2, y=2,
                  flag231=0, flag255=0, matched=0)
    values.update(kwargs)
    return values

class Native:
    def __init__(self):
        self.lib = C.CDLL(str(HERE / "recovered_rules_native.dylib"))
        signatures = {
            "can_match": ([C.POINTER(Tile), C.POINTER(C.POINTER(Tile)), C.c_size_t, C.c_bool], C.c_bool),
            "damage_type": ([C.POINTER(Game), C.POINTER(C.POINTER(Tile)), C.c_size_t, C.c_size_t], C.c_int32),
            "nearest_unmatched": ([C.POINTER(Game), C.c_int32, C.c_int32], C.c_int32),
            "enemy_count": ([C.POINTER(Game), C.c_int32], C.c_int32),
            "have_flaw": ([C.POINTER(Character), C.c_int32], C.c_bool),
            "mortal_enemy": ([C.c_int32], C.c_int32),
        }
        for name, (args, result) in signatures.items():
            fn = getattr(self.lib, "dr_" + name)
            fn.argtypes, fn.restype = args, result

    def run(self, case):
        op = case["op"]
        board = (Tile * 36)(*[Tile(**t) for t in case.get("board", [tile(type=0)] * 36)])
        character = Character(case.get("race", 0), (C.c_int32 * 4)(*case.get("flaws", [255] * 4)))
        game = Game(case.get("turn", 10), character, board)
        objects = [Tile(**t) for t in case.get("path", [])]
        path = (C.POINTER(Tile) * len(objects))(*[C.pointer(t) for t in objects])
        if op == "can_match":
            candidate = Tile(**case["tile"])
            return int(self.lib.dr_can_match(C.byref(candidate), path, len(objects), case["flag"]))
        if op == "damage_type":
            return self.lib.dr_damage_type(C.byref(game), path, len(objects), case["index"])
        if op == "nearest_unmatched":
            return self.lib.dr_nearest_unmatched(C.byref(game), case["x"], case["y"])
        if op == "enemy_count": return self.lib.dr_enemy_count(C.byref(game), case["enemy"])
        if op == "have_flaw": return int(self.lib.dr_have_flaw(C.byref(character), case["flaw"]))
        if op == "mortal_enemy": return self.lib.dr_mortal_enemy(case["race"])
        raise ValueError(op)

def original_runner():
    from verify_original import Original, TILE, GAME, STOP, CLASS_TABLE, CLASS_STRIDE, SELECTED_CLASS
    from unicorn.arm_const import UC_ARM_REG_SP, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_LR, UC_ARM_REG_PC
    addresses = {"can_match": 0x3F644, "damage_type": 0x3F790, "nearest_unmatched": 0x8A94,
                 "enemy_count": 0x8CB8, "have_flaw": 0x111608, "mortal_enemy": 0x1116F0}
    original = Original()
    u = original.uc
    u.mem_map(TILE + 0x1000, 0x10000)
    stack, sentinel, nodes, iterator = 0x1400000, 0x1500000, 0x1500100, 0x1501000
    u.mem_map(stack, 0x10000)
    u.mem_map(sentinel, 0x2000)
    def pack_tile(t):
        block = bytearray(608)
        for key, offset in (("type", 0x9C), ("special", 0xA0), ("enemy", 0x24C),
                            ("enemy_state", 0x250), ("x", 0x74), ("y", 0x78)):
            struct.pack_into("<i", block, offset, t[key])
        struct.pack_into("<I", block, 0x70, GAME)
        for key, offset in (("flag231", 0x231), ("flag255", 0x255), ("matched", 0x84)):
            block[offset] = t[key]
        return bytes(block)
    blank_board = pack_tile(tile(type=0)) * 36
    def run(case):
        op = case["op"]
        board = case.get("board")
        u.mem_write(GAME + 0x5E58, b"".join(map(pack_tile, board)) if board else blank_board)
        original.write_i32(GAME + 0xC, case.get("turn", 10))
        ci = case.get("class_index", 0)
        original.write_i32(GAME + SELECTED_CLASS, ci)
        cp = GAME + CLASS_TABLE + ci * CLASS_STRIDE
        original.write_i32(cp + 8, case.get("race", 0))
        for i, flaw in enumerate(case.get("flaws", [255] * 4)):
            original.write_i32(cp + 0x20 + 4 * i, flaw)
        path = case.get("path", [])
        ptrs = [TILE + 0x1000 + i * 0x300 for i in range(len(path))]
        for ptr, t in zip(ptrs, path): u.mem_write(ptr, pack_tile(t))
        n = len(path)
        u.mem_write(sentinel, struct.pack("<II", nodes if n else sentinel, nodes + (n - 1) * 16 if n else sentinel))
        for i, ptr in enumerate(ptrs):
            u.mem_write(nodes + i * 16, struct.pack("<III", nodes + (i + 1) * 16 if i + 1 < n else sentinel,
                        nodes + (i - 1) * 16 if i else sentinel, ptr))
        if op == "can_match":
            u.mem_write(TILE, pack_tile(case["tile"]))
            args = (TILE, sentinel, int(case["flag"]), 0)
        elif op == "damage_type":
            i = case["index"]
            original.write_i32(iterator, nodes + 16 * i)
            args = (ptrs[i], sentinel, iterator, 0)
        elif op == "nearest_unmatched": args = (GAME, case["x"], case["y"], 0)
        elif op == "enemy_count": args = (GAME, case["enemy"], 0, 0)
        elif op == "have_flaw": args = (cp, case["flaw"], 0, 0)
        elif op == "mortal_enemy": args = (case["race"], 0, 0, 0)
        else: raise ValueError(op)
        for reg, value in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3), args):
            u.reg_write(reg, value & 0xFFFFFFFF)
        u.reg_write(UC_ARM_REG_SP, stack + 0xFFF0)
        u.reg_write(UC_ARM_REG_LR, STOP | 1)
        u.emu_start(addresses[op] | 1, STOP, timeout=100000, count=10000)
        assert u.reg_read(UC_ARM_REG_PC) == STOP
        return C.c_int32(u.reg_read(UC_ARM_REG_R0)).value
    return run, original, addresses

def cases():
    rng = random.Random(0xD134C0DE)
    for race in [-2147483648, -1, 0, *range(1, 12), 255, 2147483647]:
        yield dict(op="mortal_enemy", race=race)
    for flaws in itertools.product([0, 1, 255], repeat=4):
        for target in [0, 1, 2, 255, -1]:
            yield dict(op="have_flaw", flaws=flaws, flaw=target, class_index=rng.randrange(10))
    # Exhaust every column occupancy mask and every legal search origin.
    for mask, x, y in itertools.product(range(64), range(6), range(7)):
        board = [tile(type=0, x=i % 6, y=i // 6) for i in range(36)]
        for row in range(6): board[row * 6 + x]["matched"] = (mask >> row) & 1
        yield dict(op="nearest_unmatched", board=board, x=x, y=y)
    for _ in range(250):
        board = [tile(type=rng.randrange(6), enemy=rng.choice([0, 14, 27, 30, 32]),
                      matched=rng.randrange(2)) for _ in range(36)]
        yield dict(op="enemy_count", board=board, enemy=rng.choice([0, 14, 27, 30, 32, 255]))
    # Cartesian product covers the ordinary 6 tile types and state ordering.
    variants = [tile(type=ty, special=sp, enemy=en, enemy_state=es, flag231=f231, flag255=f255)
                for ty in range(6) for sp in (0, 1, 2) for en, es in ((0, 0), (32, 0), (32, 1))
                for f231, f255 in ((0, 0), (1, 0), (0, 1))]
    for t in variants:
        for flag in (False, True): yield dict(op="can_match", tile=t, path=[], flag=flag)
        for last in [tile(type=ty) for ty in range(6)] + [tile(type=1, enemy=32, enemy_state=1), tile(type=4, flag231=1)]:
            for flag in (False, True): yield dict(op="can_match", tile=t, path=[last], flag=flag)
    for _ in range(3000):
        yield dict(op="can_match", tile=rng.choice(variants),
                   path=[rng.choice(variants) for _ in range(rng.randrange(1, 8))], flag=bool(rng.randrange(2)))
    # Directional damage rules: next/previous refer to list traversal order.
    for enemy, race, position, ny, py, turn, flaw, protector in itertools.product(
            [0, 14, 27, 30, 32], [0, 1, 2, 3], range(3), [1, 2, 3], [1, 2, 3],
            [4, 5], [0, 255], [False, True]):
        path = [tile(x=2, y=py), tile(enemy=enemy, x=2, y=2), tile(x=2, y=ny)]
        if position == 0: path = path[1:]; index = 0
        elif position == 2: path = path[:2]; index = 1
        else: index = 1
        board = [tile(type=0)] * 36
        if protector: board[17] = tile(enemy=30)
        yield dict(op="damage_type", path=path, index=index, race=race, turn=turn,
                   flaws=[flaw, 255, 255, 255], board=board, class_index=rng.randrange(10))
    for _ in range(1000):
        path = [tile(type=rng.randrange(6), enemy=rng.choice([0, 9, 14, 27, 30, 32]),
                     enemy_state=rng.randrange(2), x=rng.randrange(6), y=rng.randrange(6))
                for _ in range(rng.randrange(1, 10))]
        yield dict(op="damage_type", path=path, index=rng.randrange(len(path)),
                   race=rng.randrange(10), turn=rng.randrange(12),
                   flaws=[rng.choice([0, 255]), 255, 255, 255], class_index=rng.randrange(10))

def main():
    native = Native()
    replay = "--replay" in sys.argv
    counts = {}
    fixtures = []
    if replay:
        source = json.loads((HERE / "rules_original_results.json").read_text())
        for i, case in enumerate(source):
            got = native.run(case)
            assert got == case["expected"], (i, case, got)
            counts[case["op"]] = counts.get(case["op"], 0) + 1
    else:
        run, original, addresses = original_runner()
        for i, case in enumerate(cases()):
            expected, got = run(case), native.run(case)
            assert got == expected, (i, case, "original", expected, "recovered", got)
            counts[case["op"]] = counts.get(case["op"], 0) + 1
            fixtures.append({**case, "expected": expected})
        (HERE / "rules_original_results.json").write_text(json.dumps(fixtures, separators=(",", ":")) + "\n")
        sizes = {"can_match": 0x14C, "damage_type": 0x10C, "nearest_unmatched": 0x44,
                 "enemy_count": 0x54, "have_flaw": 0x20, "mortal_enemy": 0x3C}
        ranges = []
        for name, address in addresses.items():
            data = original.bytes_at(address, sizes[name])
            (HERE / ("original_" + name + ".bin")).write_bytes(data)
            ranges.append(dict(name=name, address=hex(address), size=len(data), sha256=hashlib.sha256(data).hexdigest()))
        (HERE / "rules_provenance.json").write_text(json.dumps(ranges, indent=2) + "\n")
    result = dict(status="passed", machine=platform.machine(), native_pointer_bytes=C.sizeof(C.c_void_p),
                  mode="native fixture replay" if replay else "original ARMv7 differential execution",
                  checks=counts, total_checks=sum(counts.values()),
                  scope="Six recovered rules; does not verify complete game or rendering")
    destination = HERE / ("rules_verification_arm64.json" if replay else "rules_verification.json")
    destination.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))

if __name__ == "__main__": main()
