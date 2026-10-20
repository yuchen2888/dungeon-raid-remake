#!/usr/bin/env python3
"""Execute original ARMv7 bytes and compare with native ARM64 reconstruction.

Only three self-contained functions are executed. This does not launch the game,
emulate iOS, or validate the rest of its game loop. No external calls are hooked.
"""
from __future__ import annotations

import ctypes as C
import hashlib
import itertools
import json
import platform
from pathlib import Path
import random
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ("tools-x86" if platform.machine() == "x86_64" else "tools")))
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_LITTLE_ENDIAN
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_LR, UC_ARM_REG_PC

FUNCTIONS = {"get_attack": 0x3D21C, "add_poison": 0x3D25C, "get_poison": 0x3D290}
TILE, GAME, STOP = 0x1000000, 0x1100000, 0x1200000
CLASS_TABLE, CLASS_STRIDE, SELECTED_CLASS = 0x15564, 388, 0x1648C


def armv7_slice(data):
    magic, count = struct.unpack_from(">II", data)
    assert magic == 0xCAFEBABE
    for i in range(count):
        cpu, subtype, offset, size, _align = struct.unpack_from(">5I", data, 8 + i * 20)
        if cpu == 12 and (subtype & 0xFFFFFF) == 9:
            return data[offset:offset + size]
    raise ValueError("No ARMv7 slice")


def segments(data):
    magic, cpu, _subtype, _kind, ncmds, _size, _flags = struct.unpack_from("<7I", data)
    assert magic == 0xFEEDFACE and cpu == 12
    cursor = 28
    result = []
    for _ in range(ncmds):
        cmd, size = struct.unpack_from("<II", data, cursor)
        assert size >= 8
        if cmd == 1:
            raw = struct.unpack_from("<II16s8I", data, cursor)
            name = raw[2].split(b"\0")[0].decode()
            vmaddr, vmsize, fileoff, filesize = raw[3:7]
            if filesize:
                result.append((name, vmaddr, vmsize, fileoff, filesize))
        cursor += size
    return result


class Original:
    def __init__(self):
        # This installed Unicorn build crashes inside mem_map on Apple silicon.
        # Fail before entering it; native ARM64 fixture replays do not construct
        # this executor and remain supported.
        if sys.platform == "darwin" and platform.machine() == "arm64" and not __import__("os").environ.get("RAID_UNICORN_TCI"):
            raise RuntimeError("Run original-instruction tests with /usr/bin/arch -x86_64 /usr/bin/python3; use native Python for fixture replay only")
        original_path = ROOT / "DungeonRaid-original"
        if original_path.exists():
            self.binary = armv7_slice(original_path.read_bytes())
            self.segments = segments(self.binary)
        else:
            # The proof bundle includes only these exact 168 original bytes.
            self.binary = Path(__file__).with_name("original_functions.bin").read_bytes()
            self.segments = [("__TEXT", 0x3D21C, len(self.binary), 0, len(self.binary))]
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_LITTLE_ENDIAN)
        for _name, vmaddr, vmsize, fileoff, filesize in self.segments:
            start, end = vmaddr & ~4095, (vmaddr + vmsize + 4095) & ~4095
            self.uc.mem_map(start, end - start)
            self.uc.mem_write(vmaddr, self.binary[fileoff:fileoff + filesize])
        self.uc.mem_map(TILE, 0x1000)
        self.uc.mem_map(GAME, 0x20000)
        self.uc.mem_map(STOP, 0x1000)

    def write_i32(self, addr, value):
        self.uc.mem_write(addr, struct.pack("<I", value & 0xFFFFFFFF))

    def set_tile(self, attack, state, race, class_index):
        self.write_i32(TILE + 0xA4, attack)
        self.write_i32(TILE + 0x70, GAME)
        for offset, value in zip((0x238, 0x23C, 0x240), state[:3]):
            self.write_i32(TILE + offset, value)
        self.uc.mem_write(TILE + 0x244, bytes(state[3:5]))
        self.write_i32(TILE + 0x248, state[5])
        self.write_i32(GAME + SELECTED_CLASS, class_index)
        for i in range(8):
            self.write_i32(GAME + CLASS_TABLE + i * CLASS_STRIDE + 8,
                           race if i == class_index else (0 if race == 1 else 1))

    def state(self):
        p = self.uc.mem_read(TILE + 0x238, 20)
        return (*struct.unpack_from("<iii", p), p[12], p[13], struct.unpack_from("<I", p, 16)[0])

    def call(self, name, amount=0):
        self.uc.reg_write(UC_ARM_REG_R0, TILE)
        self.uc.reg_write(UC_ARM_REG_R1, amount & 0xFFFFFFFF)
        self.uc.reg_write(UC_ARM_REG_LR, STOP | 1)
        self.uc.emu_start(FUNCTIONS[name] | 1, STOP, timeout=0, count=100)
        assert self.uc.reg_read(UC_ARM_REG_PC) == STOP, "Function did not return normally"
        return C.c_int32(self.uc.reg_read(UC_ARM_REG_R0)).value

    def bytes_at(self, address, size):
        for _name, vmaddr, _vmsize, fileoff, filesize in self.segments:
            if vmaddr <= address and address + size <= vmaddr + filesize:
                start = fileoff + address - vmaddr
                return self.binary[start:start + size]
        raise ValueError("Function bytes outside file-backed segment")


class Poison(C.Structure):
    _fields_ = [("current", C.c_int32), ("next", C.c_int32), ("following", C.c_int32),
                ("active", C.c_uint8), ("clearing", C.c_uint8), ("progress", C.c_uint32)]


class ClassState(C.Structure):
    _fields_ = [("race_selector", C.c_int32)]


class Context(C.Structure):
    _fields_ = [("active_class", C.POINTER(ClassState))]


class Tile(C.Structure):
    _fields_ = [("base_attack", C.c_int32), ("poison", Poison), ("game", C.POINTER(Context))]


def native_tile(attack, state, race):
    character = ClassState(race)
    context = Context(C.pointer(character))
    tile = Tile(attack, Poison(*state), C.pointer(context))
    return tile, context, character


def native_state(tile):
    p = tile.poison
    return p.current, p.next, p.following, p.active, p.clearing, p.progress


def main():
    lib = C.CDLL(str(Path(__file__).with_name("recovered_combat_native.dylib")))
    for name in ("get_attack", "get_poison"):
        fn = getattr(lib, "dr_" + name)
        fn.argtypes, fn.restype = [C.POINTER(Tile)], C.c_int32
    lib.dr_add_poison.argtypes, lib.dr_add_poison.restype = [C.POINTER(Tile), C.c_int32], None
    lib.dr_pointer_size.restype = C.c_uint32
    assert C.sizeof(C.c_void_p) == lib.dr_pointer_size() == 8
    original = Original()
    counts = {"get_attack": 0, "add_poison": 0, "get_poison": 0, "sequence_steps": 0}
    fixtures = []
    rng = random.Random(0xD00D134)

    # Boundaries, both branches, and all selected-class slots used by the harness.
    attacks = [-2147483648, -1, 0, 1, 2, 3, 10, 11, 2147483647]
    poisons = [-1, 0, 1, 2, 100, 2147483647]
    races = [-1, 0, 1, 2, 7]
    attack_cases = list(itertools.product(attacks, poisons, races, range(8)))
    attack_cases += [(rng.randint(0, 2147483647), rng.randint(0, 1000),
                      rng.randrange(5), rng.randrange(8)) for _ in range(3000)]
    for attack, poison, race, index in attack_cases:
        state = (poison, 9, 3, 1, 0, 0x3F000000)
        original.set_tile(attack, state, race, index)
        tile, _context, _character = native_tile(attack, state, race)
        old, new = original.call("get_attack"), lib.dr_get_attack(C.byref(tile))
        assert old == new, ("get_attack", attack, poison, race, index, old, new)
        assert original.state() == native_state(tile) == state
        fixtures.append({"op": "get_attack", "attack": attack, "before": state,
                         "race": race, "expected_return": old, "after": state})
        counts["get_attack"] += 1

    edge = [-2147483648, -1, 0, 1, 2, 2147483647]
    states = [(a, b, c, 0, 1, 0x3F000000) for a, b, c in itertools.product(edge, repeat=3)]
    states += [(rng.randint(-100, 500), rng.randint(-100, 500), rng.randint(-100, 500),
                rng.randrange(2), rng.randrange(2), rng.getrandbits(32)) for _ in range(1500)]
    for state in states:
        for amount in edge:
            original.set_tile(10, state, 1, 0)
            tile, _context, _character = native_tile(10, state, 1)
            original.call("add_poison", amount)
            lib.dr_add_poison(C.byref(tile), amount)
            assert original.state() == native_state(tile), ("add_poison", state, amount)
            fixtures.append({"op": "add_poison", "attack": 10, "before": state,
                             "race": 1, "amount": amount, "after": original.state()})
            counts["add_poison"] += 1
        original.set_tile(10, state, 1, 0)
        tile, _context, _character = native_tile(10, state, 1)
        old, new = original.call("get_poison"), lib.dr_get_poison(C.byref(tile))
        assert old == new and original.state() == native_state(tile), ("get_poison", state)
        fixtures.append({"op": "get_poison", "attack": 10, "before": state,
                         "race": 1, "expected_return": old, "after": original.state()})
        counts["get_poison"] += 1

    # Exercise accumulation, expiration and reapplication over consecutive turns.
    for _ in range(150):
        state = (0, 0, 0, 0, 0, 0)
        original.set_tile(11, state, 1, 3)
        tile, _context, _character = native_tile(11, state, 1)
        for _ in range(30):
            before = original.state()
            if rng.randrange(3) == 0:
                amount = rng.randrange(1, 100)
                original.call("add_poison", amount)
                lib.dr_add_poison(C.byref(tile), amount)
                row = {"op": "add_poison", "amount": amount}
            else:
                old = original.call("get_poison")
                assert old == lib.dr_get_poison(C.byref(tile))
                row = {"op": "get_poison", "expected_return": old}
            old_attack = original.call("get_attack")
            assert old_attack == lib.dr_get_attack(C.byref(tile))
            assert original.state() == native_state(tile)
            fixtures.append({**row, "attack": 11, "before": before, "race": 1,
                             "expected_attack_after": old_attack, "after": original.state()})
            counts["sequence_steps"] += 1

    sizes = {"get_attack": 0x40, "add_poison": 0x34, "get_poison": 0x34}
    result = {"status": "passed", "native_pointer_bytes": lib.dr_pointer_size(),
              "original_arch": "armv7/Thumb-2", "recovered_arch": platform.machine(),
              "engine": "Unicorn", "engine_version": "2.1.4", "checks": counts,
              "total_checks": sum(counts.values()),
              "original_functions": {
                  name: {"virtual_address": hex(address),
                         "extracted_bytes": sizes[name],
                         "sha256": hashlib.sha256(original.bytes_at(address, sizes[name])).hexdigest()}
                  for name, address in FUNCTIONS.items()},
              "scope": "Three recovered functions only; not a playable game or full damage pipeline",
              "example": {"base_attack": 11, "poison": 1, "race_selector": 1, "effective_attack": 5}}
    destination = Path(__file__).with_name("verification.json")
    destination.write_text(json.dumps(result, indent=2) + "\n")
    Path(__file__).with_name("original_results.json").write_text(json.dumps(fixtures) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
