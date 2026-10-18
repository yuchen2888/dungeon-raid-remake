#!/usr/bin/env python3
"""Real ARMv7/NEON input routines versus reconstructed native 64-bit code."""
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
def f32(x): return struct.unpack('<f', struct.pack('<f', x))[0]
def bits(x): return struct.unpack('<I', struct.pack('<f', x))[0]
def unbits(x): return struct.unpack('<f', struct.pack('<I', x))[0]
class Point(C.Structure): _fields_ = [('x', C.c_float), ('y', C.c_float)]
class Touch(C.Structure): _fields_ = [('phase', C.c_int32), ('point', Point)]
class Tile(C.Structure): _fields_ = [('center', Point), ('size', C.c_float)]
class Board(C.Structure): _fields_ = [('offset', C.c_float), ('pitch', C.c_float), ('tiles', Tile * 36)]

class Native:
    def __init__(self):
        self.lib = C.CDLL(str(HERE / 'recovered_input_native.dylib'))
        for op in ('start', 'drag'):
            fn = getattr(self.lib, 'dr_touch_' + op)
            fn.argtypes, fn.restype = [C.POINTER(Touch), C.c_float, C.c_float], None
        for op in ('end', 'interrupted'):
            fn = getattr(self.lib, 'dr_touch_' + op)
            fn.argtypes, fn.restype = [C.POINTER(Touch)], None
        self.lib.dr_tile_at.argtypes, self.lib.dr_tile_at.restype = [C.POINTER(Board), C.POINTER(Point)], C.c_void_p
        self.lib.dr_is_selected.argtypes, self.lib.dr_is_selected.restype = [C.POINTER(Tile), C.POINTER(Point)], C.c_bool
    def run(self, case):
        op = case['op']; point = Point(*case.get('point', (0, 0)))
        if op == 'tile_at':
            board = Board(); board.offset, board.pitch = case['offset'], case['pitch']
            ptr = self.lib.dr_tile_at(C.byref(board), C.byref(point))
            return -1 if not ptr else (ptr - C.addressof(board.tiles)) // C.sizeof(Tile)
        if op == 'is_selected':
            tile = Tile(Point(*case['center']), case['size'])
            return int(self.lib.dr_is_selected(C.byref(tile), C.byref(point)))
        state = Touch(case['before'][0], Point(unbits(case['before'][1]), unbits(case['before'][2])))
        fn = getattr(self.lib, 'dr_touch_' + op)
        if op in ('start', 'drag'): fn(C.byref(state), point.x, point.y)
        else: fn(C.byref(state))
        return [state.phase, bits(state.point.x), bits(state.point.y)]

def original_runner():
    from verify_original import Original, TILE, GAME, STOP
    from unicorn.arm_const import UC_ARM_REG_SP, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_C1_C0_2, UC_ARM_REG_FPEXC, UC_ARM_REG_FPSCR
    old = Original(); u = old.uc
    u.mem_map(0x1400000, 0x10000)
    u.reg_write(UC_ARM_REG_C1_C0_2, u.reg_read(UC_ARM_REG_C1_C0_2) | (15 << 20))
    u.reg_write(UC_ARM_REG_FPEXC, 0x40000000)
    u.reg_write(UC_ARM_REG_FPSCR, 0)
    addresses = dict(start=0x89A4, drag=0x89BC, end=0x89D0, interrupted=0x89D8,
                     tile_at=0x89E0, is_selected=0x3D9A4)
    def run(case):
        op = case['op']; point = case.get('point', (0, 0))
        u.mem_write(TILE + 0x300, struct.pack('<ff', *point))
        r0, r1, r2 = GAME, TILE + 0x300, 0
        if op == 'tile_at':
            u.mem_write(GAME + 0x165C8, struct.pack('<f', case['offset']))
            u.mem_write(GAME + 0x5E50, struct.pack('<f', case['pitch']))
        elif op == 'is_selected':
            r0 = TILE
            u.mem_write(TILE + 0x54, struct.pack('<ff', *case['center']))
            u.mem_write(TILE + 0x80, struct.pack('<f', case['size']))
        else:
            u.mem_write(GAME + 0x10, struct.pack('<iII', *case['before']))
            r1, r2 = bits(point[0]), bits(point[1])
        for reg, value in ((UC_ARM_REG_R0, r0), (UC_ARM_REG_R1, r1), (UC_ARM_REG_R2, r2),
                           (UC_ARM_REG_SP, 0x140FFF0), (UC_ARM_REG_LR, STOP | 1)):
            u.reg_write(reg, value)
        u.emu_start(addresses[op] | 1, STOP, timeout=100000, count=200)
        assert u.reg_read(UC_ARM_REG_PC) == STOP
        result = u.reg_read(UC_ARM_REG_R0)
        if op == 'tile_at':
            if result == 0: return -1
            assert (result - GAME - 0x5E58) % 608 == 0
            return (result - GAME - 0x5E58) // 608
        if op == 'is_selected': return result
        return list(struct.unpack('<iII', u.mem_read(GAME + 0x10, 12)))
    return run, old, addresses

def cases():
    rng = random.Random(0xD134F32)
    edge = [-2.0, -0.0, 0.0, f32(1/6), 0.5, 1.0, 1.5, 2.0]
    for phase, op, x, y in itertools.product(range(4), ('start', 'drag', 'end', 'interrupted'), edge, edge):
        yield dict(op=op, before=[phase, bits(0.123), bits(-0.456)], point=[x, y])
    for offset, pitch in itertools.product([0.0, -0.05, 0.075], [f32(1/6), 0.16, 0.2]):
        top = f32(f32(offset) + f32(0.246875))
        xs = [f32(k * pitch) for k in range(-1, 8)]
        ys = [top, f32(top + 1)] + [f32(top + f32(k * pitch)) for k in range(-1, 8)]
        # Include the immediate f32 neighbours of every cell boundary.
        xs = [unbits(bits(x) + d) for x in xs for d in (-1, 0, 1) if 0 < bits(x) + d < 0x7F800000]
        ys = [unbits(bits(y) + d) for y in ys for d in (-1, 0, 1) if 0 < bits(y) + d < 0x7F800000]
        for x, y in itertools.product(xs, ys):
            yield dict(op='tile_at', offset=f32(offset), pitch=f32(pitch), point=[x, y])
    for _ in range(3000):
        yield dict(op='tile_at', offset=f32(rng.uniform(-.1, .1)), pitch=f32(rng.uniform(.15, .2)),
                   point=[f32(rng.uniform(-.3, 1.3)), f32(rng.uniform(0, 1.6))])
    for size in [0.0, .05, .1, f32(1/6), .25, 1.0]:
        radius = f32(f32(size) * f32(.8))
        distances = [radius, f32(radius * .99), f32(radius * 1.01), 0.0]
        if radius:
            distances += [unbits(bits(radius)-1), unbits(bits(radius)+1)]
        for d, sign, axis in itertools.product(distances, [-1, 1], range(2)):
            point = [0.0, 0.0]; point[axis] = f32(d * sign)
            yield dict(op='is_selected', center=[0., 0.], size=f32(size), point=point)
    for _ in range(3000):
        yield dict(op='is_selected', center=[f32(rng.random()), f32(rng.random())],
                   size=f32(rng.uniform(.01, .4)), point=[f32(rng.random()), f32(rng.random())])

def main():
    native = Native(); counts = {}; fixtures = []
    replay = '--replay' in sys.argv
    if replay:
        source = json.loads((HERE / 'input_original_results.json').read_text())
        for case in source:
            got = native.run(case)
            assert got == case['expected'], (case, got)
            counts[case['op']] = counts.get(case['op'], 0) + 1
    else:
        run, original, addresses = original_runner()
        for i, case in enumerate(cases()):
            expected, got = run(case), native.run(case)
            assert got == expected, (i, case, 'original', expected, 'recovered', got)
            counts[case['op']] = counts.get(case['op'], 0) + 1
            fixtures.append({**case, 'expected':expected})
        (HERE / 'input_original_results.json').write_text(json.dumps(fixtures, separators=(',', ':'))+'\n')
        ranges = []
        sizes = dict(start=0x18, drag=0x14, end=8, interrupted=8, tile_at=0xA4, is_selected=0x48)
        for name, address in addresses.items():
            data = original.bytes_at(address, sizes[name])
            (HERE / ('original_input_' + name + '.bin')).write_bytes(data)
            ranges.append(dict(name=name, address=hex(address), size=len(data), sha256=hashlib.sha256(data).hexdigest()))
        (HERE / 'input_provenance.json').write_text(json.dumps(ranges, indent=2)+'\n')
    result = dict(status='passed', machine=platform.machine(), native_pointer_bytes=C.sizeof(C.c_void_p),
                  mode='native fixture replay' if replay else 'original ARMv7/NEON differential execution',
                  checks=counts, total_checks=sum(counts.values()),
                  scope='Six recovered input functions, finite coordinates; no full UI or game rendering')
    (HERE / ('input_verification_arm64.json' if replay else 'input_verification.json')).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
if __name__ == '__main__': main()
