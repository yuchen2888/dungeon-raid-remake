#!/usr/bin/env python3
"""Compare recovered RNG with real ARMv7 instructions, including seed state.

All five original functions plus original Clamp execute unchanged. The only
hook is platform libm floorf. No random-number generator is stubbed.
"""
from pathlib import Path
import ctypes as C
import hashlib
import json
import math
import os
import random
import struct
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
os.environ['RAID_UNICORN_TCI'] = '1'
from verify_original import Original, STOP, TILE
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_SP, UC_ARM_REG_C1_C0_2,
    UC_ARM_REG_FPEXC, UC_ARM_REG_FPSCR)

class State(C.Structure):
    _fields_ = [('seeds', C.c_uint32 * 6)]

def float_bits(value):
    return struct.unpack('<I', struct.pack('<f',value))[0]

def main():
    old = Original()
    u = old.uc
    u.reg_write(UC_ARM_REG_C1_C0_2, u.reg_read(UC_ARM_REG_C1_C0_2) | (15 << 20))
    u.reg_write(UC_ARM_REG_FPEXC, 0x40000000)
    u.reg_write(UC_ARM_REG_FPSCR, 0)
    floor_calls = 0
    def floor_hook(uc, address, size, _):
        nonlocal floor_calls
        if address == 0x194e20:
            value = struct.unpack('<f',struct.pack('<I',uc.reg_read(UC_ARM_REG_R0)))[0]
            uc.reg_write(UC_ARM_REG_R0,float_bits(float(math.floor(value))))
            uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
            floor_calls += 1
    u.hook_add(UC_HOOK_CODE, floor_hook)
    def call(address, *args):
        for reg,arg in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2),args):
            u.reg_write(reg, arg & 0xffffffff)
        u.reg_write(UC_ARM_REG_SP,TILE + 0xf00)
        u.reg_write(UC_ARM_REG_LR,STOP|1)
        u.emu_start(address|1,STOP,count=1000)
        assert u.reg_read(UC_ARM_REG_PC) == STOP
        return u.reg_read(UC_ARM_REG_R0)
    seed_va = 0x1eac20
    lib = C.CDLL(str(HERE/'recovered_random_native.dylib'))
    lib.dr_random_unit.argtypes=[C.POINTER(C.c_uint32)]
    lib.dr_random_unit.restype=C.c_float
    lib.dr_random_set_seed.argtypes=[C.POINTER(State),C.c_uint32,C.c_uint32]
    lib.dr_random_set_seed.restype=None
    lib.dr_random_get_seed.argtypes=[C.POINTER(State),C.c_uint32]
    lib.dr_random_get_seed.restype=C.c_uint32
    lib.dr_random_flush.argtypes=[C.POINTER(State)]
    lib.dr_random_flush.restype=None
    lib.dr_random_int.argtypes=[C.POINTER(State),C.c_int32,C.c_int32,C.c_uint32]
    lib.dr_random_int.restype=C.c_int32
    rng=random.Random(0xD1342026)
    counts=dict(set_seed=0,get_seed=0,flush=0,unit=0,integer=0)
    def sync(values):
        state=State((C.c_uint32*6)(*values))
        u.mem_write(seed_va,struct.pack('<6I',*values))
        return state
    def compare(state):
        assert list(state.seeds)==list(struct.unpack('<6I',u.mem_read(seed_va,24)))
    boundaries=[0,1,2,1023,1024,0x7fffffff,0x80000000,0xfffffffe,0xffffffff]
    for value in boundaries:
        for stream in list(range(9))+[0xffffffff]:
            state=sync([rng.getrandbits(32) for _ in range(6)])
            call(0x1b6c0,value,stream)
            lib.dr_random_set_seed(C.byref(state),value,stream)
            compare(state);counts['set_seed']+=1
            assert call(0x1b724,stream)==lib.dr_random_get_seed(C.byref(state),stream)
            compare(state);counts['get_seed']+=1
    for initial in boundaries+[rng.getrandbits(32) for _ in range(40)]:
        seed=C.c_uint32(initial)
        u.mem_write(seed_va,struct.pack('<I',initial))
        for _ in range(32):
            result=call(0x1b76c,seed_va)
            value=lib.dr_random_unit(C.byref(seed))
            assert result==float_bits(value)
            assert seed.value==struct.unpack('<I',u.mem_read(seed_va,4))[0]
            counts['unit']+=1
    state=sync(boundaries[:6])
    for _ in range(64):
        call(0x1b6ec);lib.dr_random_flush(C.byref(state));compare(state)
        counts['flush']+=1
    ranges=[(0,0),(0,1),(1,5),(5,1),(-10,10),(-20,-2),(0,100),
            (1,33),(0,39),(-1000000,1000000),(1000000,-1000000)]
    samples=[]
    for initial in boundaries+[rng.getrandbits(32) for _ in range(20)]:
        state=sync([initial]*6)
        for a,b in ranges:
            for stream in range(6):
                for _ in range(3):
                    result=C.c_int32(call(0x1bca0,a,b,stream)).value
                    native=lib.dr_random_int(C.byref(state),a,b,stream)
                    assert result==native,(a,b,stream,result,native)
                    compare(state);counts['integer']+=1
                    if initial==1 and (a,b)==(1,5):
                        samples.append(dict(stream=stream,result=result,seeds=list(state.seeds)))
    report=dict(status='passed',mode='native ARM64 versus original ARMv7 via TCI',
                checks=counts,platform_floorf_calls=floor_calls,
                original_game_bytes_modified=False,
                hooks=['platform floorf only'],
                scope='Five RNG functions, six independent streams; integer bounds tested within +/-1,000,000. Startup seed policy, float-range Rand and complete gameplay not restored here.',
                sample_original_outputs=samples)
    (HERE/'random_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    specs=[('SetRandSeed',0x1b6c0,44,'dr_random_set_seed'),
           ('GetRandSeed',0x1b724,24,'dr_random_get_seed'),
           ('FlushRandSeeds',0x1b6ec,56,'dr_random_flush'),
           ('RandUnitF',0x1b76c,60,'dr_random_unit'),
           ('RandI',0x1bca0,128,'dr_random_int')]
    provenance=dict(source_executable_sha256=hashlib.sha256((HERE.parent/'DungeonRaid-original').read_bytes()).hexdigest(),
        native_source='recovered_random.cpp',functions=[dict(name=n,address=hex(a),size=z,
          sha256=hashlib.sha256(old.bytes_at(a,z)).hexdigest(),native_function=f) for n,a,z,f in specs],
        integration='Not yet connected to reconstructed board/refill; old fixtures retain explicit RNG adapters')
    (HERE/'random_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(json.dumps(dict(status='passed',checks=counts,floor_calls=floor_calls)))

if __name__=='__main__':main()
