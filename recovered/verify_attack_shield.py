#!/usr/bin/env python3
"""Actual ProcessAttack shield-wear instructions vs native shared-state source.

Preceding damage calculation/phase scheduling and subsequent health damage are
outside this test. Original GetEnemyCount/RandI/RandUnitF/Clamp execute intact.
Only platform floorf and shield/audio presentation are adapted.
"""
import ctypes as C
import hashlib
import json
import math
import os
import random
import re
import struct
os.environ['RAID_UNICORN_TCI']='1'
from verify_original import Original as Machine, GAME, TILE, STOP
from verify_match import Match
from verify_preview import Preview
from verify_resources import Resource
from verify_stroke import State as Stroke, HERE
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,
    UC_ARM_REG_R5,UC_ARM_REG_R8,UC_ARM_REG_R10,UC_ARM_REG_SP,UC_ARM_REG_LR,
    UC_ARM_REG_PC,UC_ARM_REG_C1_C0_2,UC_ARM_REG_FPEXC,UC_ARM_REG_FPSCR)

START,END,SEEDS=0x147e4,0x1487e,0x1eac20
class Event(C.Structure):
    _fields_=[(k,C.c_int32) for k in ('kind','a','b','c','d')]
CALLBACK=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(Event))
class Hooks(C.Structure):
    _fields_=[('context',C.c_void_p),('event',CALLBACK)]

def bits(value):return struct.unpack('<I',struct.pack('<f',value))[0]

class Original:
    def __init__(self):
        self.machine=Machine();self.u=self.machine.uc;self.events=[];self.pending=None
        u=self.u;u.reg_write(UC_ARM_REG_C1_C0_2,u.reg_read(UC_ARM_REG_C1_C0_2)|(15<<20))
        u.reg_write(UC_ARM_REG_FPEXC,0x40000000);u.reg_write(UC_ARM_REG_FPSCR,0)
        text=(HERE.parent/'armv7-disassembly.txt').read_text()
        self.presentation={}
        for symbol,kind in [('__ZN9Interface17UpdateShieldValueEv',2),
                            ('__ZN4Game21InialiseShieldShatterEv',3),('__ZN4Game10QueueSoundE5Sound',4)]:
            m=re.search(r'^'+symbol+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol
            self.presentation[int(m[1],16)]=kind
        self.visits={}
        u.hook_add(UC_HOOK_CODE,self.hook)
    def read(self,offset):return struct.unpack('<i',self.u.mem_read(GAME+offset,4))[0]
    def write(self,offset,value):self.u.mem_write(GAME+offset,struct.pack('<i',value))
    def hook(self,u,address,size,_):
        if START<=address<END:self.visits[hex(address)]=self.visits.get(hex(address),0)+1
        if address==END:u.emu_stop();return
        if self.pending==address:
            value=C.c_int32(u.reg_read(UC_ARM_REG_R0)).value
            self.events.append([1,0,100,5,value]);self.pending=None
        if address==0x1bca0:
            assert [u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)]==[0,100,5]
            self.pending=u.reg_read(UC_ARM_REG_LR)&~1
        if address==0x194e20:
            value=struct.unpack('<f',struct.pack('<I',u.reg_read(UC_ARM_REG_R0)))[0]
            u.reg_write(UC_ARM_REG_R0,bits(float(math.floor(value))))
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        kind=self.presentation.get(address)
        if kind:
            value=self.read(0x59c0) if kind==2 else u.reg_read(UC_ARM_REG_R1) if kind==4 else 0
            self.events.append([kind,value,0,0,0]);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def load(self,c):
        self.u.mem_write(GAME,b'\0'*0x20000)
        for i,(kind,enemy) in enumerate(c['board']):
            self.write(0x5e58+608*i+0x9c,kind);self.write(0x5e58+608*i+0x24c,enemy)
        self.write(0xbda4,c['armour']);self.write(0x59c0,c['ui']);self.write(0xbdc8,c['chance'])
        self.u.mem_write(SEEDS,struct.pack('<6I',*c['seeds']))
    def step(self,absorbed):
        self.events=[];self.pending=None;before=bytearray(self.u.mem_read(GAME,0x20000))
        for reg,value in [(UC_ARM_REG_R8,GAME),(UC_ARM_REG_R10,absorbed),
                          (UC_ARM_REG_SP,TILE+0xf00),(UC_ARM_REG_LR,STOP|1)]:self.u.reg_write(reg,value)
        self.u.emu_start(START|1,STOP,timeout=0,count=100000)
        assert self.u.reg_read(UC_ARM_REG_PC)==END and self.pending is None
        result=dict(lost=self.u.reg_read(UC_ARM_REG_R5),armour=self.read(0xbda4),ui=self.read(0x59c0),
                    seeds=list(struct.unpack('<6I',self.u.mem_read(SEEDS,24))),events=self.events[:])
        for offset in (0xbda4,0x59c0):before[offset:offset+4]=self.u.mem_read(GAME+offset,4)
        assert bytes(before)==bytes(self.u.mem_read(GAME,0x20000)),'unexpected gameplay write'
        return result

class Native:
    def __init__(self):
        lib=C.CDLL(str(HERE/'recovered_attack_shield_native.dylib'))
        self.fn=lib.dr_process_attack_shield_wear
        self.fn.argtypes=[C.POINTER(Resource),C.c_int32,C.c_int32,C.POINTER(Hooks)];self.fn.restype=C.c_int32
        self.callback=CALLBACK(lambda _,p:self.events.append([getattr(p.contents,k) for k in ('kind','a','b','c','d')]))
        self.hooks=Hooks(None,self.callback)
    def load(self,c):
        self.stroke=Stroke();self.preview=Preview();self.match=Match();self.resource=Resource()
        self.match.stroke=C.pointer(self.stroke);self.match.preview=C.pointer(self.preview);self.resource.match=C.pointer(self.match)
        for i,(kind,enemy) in enumerate(c['board']):
            self.stroke.selection.tiles[i].rule.type=kind;self.stroke.selection.tiles[i].rule.enemy=enemy
        self.preview.armour_current=c['armour'];self.resource.ui_armour=c['ui'];self.chance=c['chance']
        self.match.random.seeds[:]=c['seeds']
    def step(self,absorbed):
        self.events=[];board=bytes(self.stroke);resource=bytearray(bytes(self.resource))
        lost=self.fn(C.byref(self.resource),absorbed,self.chance,C.byref(self.hooks))
        offset=Resource.ui_armour.offset;resource[offset:offset+4]=struct.pack('<i',self.resource.ui_armour)
        assert bytes(self.stroke)==board and bytes(self.resource)==bytes(resource)
        return dict(lost=lost,armour=self.preview.armour_current,ui=self.resource.ui_armour,
                    seeds=list(self.match.random.seeds),events=self.events[:])

def main():
    old,new=Original(),Native();rng=random.Random(0xD134020);counts={'boundary':0,'random':0,'continuous_steps':0}
    random_calls=forced_cases=0
    def compare(c,absorbed,group):
        nonlocal random_calls,forced_cases
        a,b=old.step(absorbed),new.step(absorbed)
        if a!=b:
            (HERE/'attack_shield_failure.json').write_text(json.dumps(dict(case=c,absorbed=absorbed,original=a,native=b),indent=2))
            raise AssertionError('attack_shield_failure.json')
        counts[group]+=1;random_calls+=sum(e[0]==1 for e in a['events'])
        if any(kind==1 and enemy==29 for kind,enemy in c['board']):
            forced_cases+=1;assert a['lost']==absorbed and not any(e[0]==1 for e in a['events'])
        return a
    for absorbed in (0,1,2,5,36):
     for chance in (-1,0,1,50,100,101):
      for enemy_mode in range(3):
       for ui_mode in range(3):
        for seed in (0,1,0xffffffff):
            c=dict(board=[[2,0] for _ in range(36)],armour=40,ui=[40,0,40-absorbed][ui_mode],chance=chance,seeds=[(seed+i)&0xffffffff for i in range(5)]+[seed])
            if enemy_mode:c['board'][17]=[1 if enemy_mode==1 else 2,29]
            old.load(c);new.load(c);compare(c,absorbed,'boundary')
    for n in range(700):
        absorbed=rng.randrange(65);armour=absorbed+rng.randrange(60)
        c=dict(board=[[rng.randrange(5),rng.randrange(33)] for _ in range(36)],armour=armour,ui=rng.randrange(130),chance=rng.randrange(-1,102),seeds=[rng.getrandbits(32) for _ in range(6)])
        old.load(c);new.load(c);compare(c,absorbed,'random')
    for enemy in (0,29):
        c=dict(board=[[2,0] for _ in range(36)],armour=500,ui=500,chance=41,seeds=[rng.getrandbits(32) for _ in range(6)])
        c['board'][3]=[1,enemy];old.load(c);new.load(c)
        for _ in range(50):compare(c,3,'continuous_steps')
    assert all(hex(a) in old.visits for a in (0x1481c,0x14826,0x14836,0x14842,0x14866,0x1486c,0x14876))
    report=dict(status='passed',cases=sum(counts.values()),by_group=counts,random_calls=random_calls,
                forced_enemy_cases=forced_cases,range=dict(start=hex(START),end_exclusive=hex(END)),
                original='Actual ProcessAttack subsection, GetEnemyCount, RandI, RandUnitF, Clamp',
                boundaries=['absorbed damage supplied from prior stage (R10)','platform floorf','shield UI/shatter and audio','no full phase scheduler or health damage'],
                scope='Shared board/armour/UI/RNG state and ordered events; no complete enemy phase claim',
                byte_sha256=hashlib.sha256(old.machine.bytes_at(START,END-START)).hexdigest(),branch_visits=old.visits)
    (HERE/'attack_shield_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
