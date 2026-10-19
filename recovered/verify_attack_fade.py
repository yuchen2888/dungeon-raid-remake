#!/usr/bin/env python3
"""Actual ProcessAttack phase-7 overlay fade [0x14ae4,0x14b56) vs native.

Quad::SetAlpha executes as original code (it only stores the byte into the
four vertex colours), so the overlay alpha that doubles as the phase timer is
carried by the original instructions themselves. Frame time is Game+4.
"""
import ctypes as C
import hashlib
import json
import random
import re
import struct
from verify_attack_shield import Original as ShieldOriginal, GAME, TILE, STOP, HERE
from verify_attack_absorb import AttackDamage
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R8,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC

START,END,EXIT=0x14ae4,0x14b56,0x14be0
PHASE,DT,ALTERNATE=0xb8a8,0x4,0xbfba
QUADS=[0xb91c,0xb8ac,0xb98c]
VERTEX_ALPHA=(0xf,0x23,0x37,0x4b)

class Event(C.Structure):
    _fields_=[(k,C.c_int32) for k in ('kind','a','b')]
CALLBACK=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(Event))
class Hooks(C.Structure):
    _fields_=[('context',C.c_void_p),('event',CALLBACK)]

def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]

class Original(ShieldOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.fade_visits={}
        m=re.search(r'^__ZN4Quad8SetAlphaEh:\n\s*([0-9a-f]+):',text,re.M);self.set_alpha=int(m[1],16)
    def hook(self,u,address,size,_):
        if START<=address<END:self.fade_visits[hex(address)]=self.fade_visits.get(hex(address),0)+1
        if address==EXIT:u.emu_stop();return
        if address==self.set_alpha:   # record, then let the original store run
            self.events.append([1,QUADS.index(u.reg_read(UC_ARM_REG_R0)-GAME),u.reg_read(UC_ARM_REG_R1)&0xff])
    def load(self,c):
        self.u.mem_write(GAME,b'\0'*0x20000);self.write(PHASE,c['phase'])
        self.u.mem_write(GAME+ALTERNATE,bytes([c['alternate']]))
        for q in QUADS:
            for v in VERTEX_ALPHA:self.u.mem_write(GAME+q+v,bytes([0x5a]))
        self.u.mem_write(GAME+QUADS[0]+0xf,bytes([c['alpha']]))
    def run(self,dt):
        self.events=[];self.u.mem_write(GAME+DT,struct.pack('<f',dt));before=bytearray(self.u.mem_read(GAME,0x20000))
        for reg,value in [(UC_ARM_REG_R8,GAME),(UC_ARM_REG_SP,TILE+0xf00),(UC_ARM_REG_LR,STOP|1)]:self.u.reg_write(reg,value)
        self.u.emu_start(START|1,STOP,timeout=1000000,count=1000)
        assert self.u.reg_read(UC_ARM_REG_PC)==EXIT
        for _,quad,value in self.events:
            assert all(self.u.mem_read(GAME+QUADS[quad]+v,1)[0]==value for v in VERTEX_ALPHA)
        for offset in [PHASE]+[q+v for q in QUADS for v in VERTEX_ALPHA]:
            n=4 if offset==PHASE else 1;before[offset:offset+n]=self.u.mem_read(GAME+offset,n)
        assert bytes(before)==bytes(self.u.mem_read(GAME,0x20000)),'unexpected gameplay write'
        return dict(phase=self.read(PHASE),alpha=self.u.mem_read(GAME+QUADS[0]+0xf,1)[0],events=self.events[:])

class Native:
    def __init__(self):
        lib=C.CDLL(str(HERE/'recovered_attack_shield_native.dylib'));self.fn=lib.dr_process_attack_fade
        self.fn.argtypes=[C.POINTER(AttackDamage),C.POINTER(C.c_uint8),C.c_float,C.c_bool,C.POINTER(Hooks)];self.fn.restype=None
        self.callback=CALLBACK(lambda _,p:self.events.append([p.contents.kind,p.contents.a,p.contents.b]));self.hooks=Hooks(None,self.callback)
    def load(self,c):
        self.state=AttackDamage(None,c['phase'],0,0);self.alpha=C.c_uint8(c['alpha']);self.alternate=bool(c['alternate'])
    def run(self,dt):
        self.events=[];self.fn(C.byref(self.state),C.byref(self.alpha),dt,self.alternate,C.byref(self.hooks))
        return dict(phase=self.state.phase,alpha=self.alpha.value,events=self.events[:])

def main():
    old,new=Original(),Native();rng=random.Random(0x14AE4);counts={'boundary':0,'random':0,'frames':0};to8=0
    def compare(c,dt,group):
        nonlocal to8
        a,b=old.run(dt),new.run(dt)
        if a!=b:
            (HERE/'attack_fade_failure.json').write_text(json.dumps(dict(case=c,dt=dt,original=a,native=b),indent=2))
            raise AssertionError('attack_fade_failure.json')
        counts[group]+=1;to8+=a['phase']==8 and c.get('phase',7)==7
        return a
    dts=[0.0,1e-45,1e-38,f32(1/1800),f32(1/900),f32(1/240),f32(1/60),f32(1/30),0.5,f32(255/900),f32(256/900),10.0]
    for phase in (6,7,8):
     for alternate in (0,1):
      for alpha in (0,1,2,127,128,159,160,161,254,255):
       for dt in dts:
        c=dict(phase=phase,alternate=alternate,alpha=alpha);old.load(c);new.load(c);compare(c,dt,'boundary')
    for _ in range(1500):
        c=dict(phase=rng.choice([7,7,7,rng.randrange(1,9)]),alternate=rng.randrange(2),alpha=rng.randrange(256))
        dt=f32(rng.choice([rng.uniform(0,0.1),rng.uniform(0,2),rng.uniform(0,10)]))
        old.load(c);new.load(c);compare(c,dt,'random')
    for game in range(30):
        c=dict(phase=7,alternate=game%2,alpha=255);old.load(c);new.load(c)
        for _ in range(400):
            a=compare(c,f32(rng.choice([1/60,1/30,rng.uniform(0,0.05)])),'frames')
            if a['phase']==8:break
        assert a['phase']==8
    assert all(hex(a) in old.fade_visits for a in (0x14af0,0x14b1c,0x14b24,0x14b3e,0x14b48))
    report=dict(status='passed',comparisons=sum(counts.values()),by_group=counts,phase8_transitions=to8,
                range=dict(start=hex(START),end_exclusive=hex(END)),
                original='Actual ProcessAttack phase-7 fade and Quad::SetAlpha',
                boundaries=['frame time written to Game+4 by the harness','valid domain finite 0<=dt<=10 (VCVT saturation not modelled beyond it)',
                            'phase 8 handling (outside ProcessAttack) not covered'],
                scope='Phase field, overlay alpha byte (phase timer) and both quad alpha updates',
                byte_sha256=hashlib.sha256(old.machine.bytes_at(START,END-START)).hexdigest(),branch_visits=old.fade_visits)
    (HERE/'attack_fade_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='branch_visits'}))

if __name__=='__main__':main()
