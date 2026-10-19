#!/usr/bin/env python3
"""Actual ProcessAttack armour-absorption instructions vs native source.

Two runs per case on the same original memory/registers:
  absorb : [0x14790,0x147e4)  vs dr_process_attack_armour_absorb
  chain  : [0x14790,0x1487e)  vs absorb followed by dr_process_attack_shield_wear
so the shield-wear R10 input is produced by original code, not supplied.
Entry registers R4=Game+0xbe84, R5=Game+0xbda4, R6=0.5f are the values the
preceding phase-5 code leaves; earlier phase scheduling, health damage and
counterattack are outside this test. Labels/audio/shield UI are adapted.
"""
import ctypes as C
import hashlib
import json
import random
import re
import struct
from verify_attack_shield import Original as ShieldOriginal, Native as ShieldNative, GAME, TILE, STOP, HERE
from verify_resources import Resource
from unicorn.arm_const import (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R4,
    UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R8,UC_ARM_REG_R10,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC)

START,MID,END=0x14790,0x147e4,0x1487e
PHASE,DAMAGE,ENEMY9,ARMOUR,UI,CHANCE=0xb8a8,0xbe84,0x1553c,0xbda4,0x59c0,0xbdc8
LABEL_POS=0x15518
FAKE_LABEL=0x13fff00   # stack-held SimpleLabel* at [sp,#0x34]; only its identity is checked

class AbsorbEvent(C.Structure):
    _fields_=[(k,C.c_int32) for k in ('kind','a','b','c','d')]
ABSORB_CALLBACK=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(AbsorbEvent))
class AbsorbHooks(C.Structure):
    _fields_=[('context',C.c_void_p),('event',ABSORB_CALLBACK)]
class AttackDamage(C.Structure):
    _fields_=[('resources',C.POINTER(Resource)),('phase',C.c_int32),('incoming_damage',C.c_int32),('enemy9_damage',C.c_int32)]

class Original(ShieldOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.stop=END;self.absorb_visits={}
        self.labels={}
        for symbol,kind in [('__ZN11SimpleLabel9SetNumberEi',1),('__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif',2)]:
            m=re.search(r'^'+symbol+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol
            self.labels[int(m[1],16)]=kind
    def hook(self,u,address,size,context):
        if START<=address<MID:self.absorb_visits[hex(address)]=self.absorb_visits.get(hex(address),0)+1
        if address==self.stop:u.emu_stop();return
        kind=self.labels.get(address)
        if kind:
            r=[C.c_int32(u.reg_read(x)).value for x in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
            if kind==1:
                assert r[0]==FAKE_LABEL;self.events.append(['A',1,r[1],0,0,0])
            else:
                sp=u.reg_read(UC_ARM_REG_SP);assert r[0]==GAME and r[2]==GAME+LABEL_POS
                colour,scale=struct.unpack('<iI',u.mem_read(sp,8))
                self.events.append(['A',2,r[1],r[3],colour,C.c_int32(scale).value])
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        return super().hook(u,address,size,context)
    def load(self,c):
        super().load(c)
        for offset,key in ((PHASE,'phase'),(DAMAGE,'damage'),(ENEMY9,'enemy9')):self.write(offset,c[key])
    def run(self,stop):
        self.events=[];self.pending=None;self.stop=stop;before=bytearray(self.u.mem_read(GAME,0x20000))
        sp=TILE+0xf00;self.u.mem_write(sp+0x34,struct.pack('<I',FAKE_LABEL))
        for reg,value in [(UC_ARM_REG_R8,GAME),(UC_ARM_REG_R4,GAME+DAMAGE),(UC_ARM_REG_R5,GAME+ARMOUR),
                          (UC_ARM_REG_R6,0x3f000000),(UC_ARM_REG_R10,0xdeadbeef),
                          (UC_ARM_REG_SP,sp),(UC_ARM_REG_LR,STOP|1)]:self.u.reg_write(reg,value)
        self.u.emu_start(START|1,STOP,timeout=0,count=100000)
        assert self.u.reg_read(UC_ARM_REG_PC)==stop and self.pending is None
        result=dict(absorbed=C.c_int32(self.u.reg_read(UC_ARM_REG_R10)).value,
                    **{k:self.read(o) for k,o in (('phase',PHASE),('damage',DAMAGE),('enemy9',ENEMY9),('armour',ARMOUR),('ui',UI))},
                    seeds=list(struct.unpack('<6I',self.u.mem_read(0x1eac20,24))),events=self.events[:])
        if stop==END:result['lost']=self.u.reg_read(UC_ARM_REG_R5)
        allowed=(PHASE,DAMAGE,ENEMY9)+((ARMOUR,UI) if stop==END else ())
        for offset in allowed:before[offset:offset+4]=self.u.mem_read(GAME+offset,4)
        assert bytes(before)==bytes(self.u.mem_read(GAME,0x20000)),'unexpected gameplay write'
        return result

class Native(ShieldNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_attack_shield_native.dylib'))
        self.absorb=lib.dr_process_attack_armour_absorb
        self.absorb.argtypes=[C.POINTER(AttackDamage),C.POINTER(AbsorbHooks)];self.absorb.restype=C.c_int32
        self.absorb_callback=ABSORB_CALLBACK(lambda _,p:self.events.append(['A']+[getattr(p.contents,k) for k in ('kind','a','b','c','d')]))
        self.absorb_hooks=AbsorbHooks(None,self.absorb_callback)
    def load(self,c):
        super().load(c);self.damage=AttackDamage(C.pointer(self.resource),c['phase'],c['damage'],c['enemy9'])
    def run(self,stop):
        self.events=[];board=bytes(self.stroke);resource=bytes(self.resource)
        absorbed=self.absorb(C.byref(self.damage),C.byref(self.absorb_hooks))
        assert bytes(self.stroke)==board and bytes(self.resource)==resource
        result=dict(absorbed=absorbed,phase=self.damage.phase,damage=self.damage.incoming_damage,enemy9=self.damage.enemy9_damage,
                    armour=self.preview.armour_current,ui=self.resource.ui_armour,seeds=list(self.match.random.seeds))
        if stop==END:
            events=self.events;wear=self.step(absorbed);self.events=events+wear['events']
            result.update(armour=wear['armour'],ui=wear['ui'],seeds=wear['seeds'],lost=wear['lost'])
        result['events']=self.events[:]
        return result

def main():
    old,new=Original(),Native();rng=random.Random(0xD134021)
    counts={'boundary':0,'random':0,'continuous_steps':0};chain_random_calls=0;phase7=0
    def compare(c,stop,group):
        nonlocal chain_random_calls,phase7
        a,b=old.run(stop),new.run(stop)
        if a!=b:
            (HERE/'attack_absorb_failure.json').write_text(json.dumps(dict(case=c,stop=hex(stop),original=a,native=b),indent=2))
            raise AssertionError('attack_absorb_failure.json')
        counts[group]+=1;phase7+=a['phase']==7 and c.get('phase',5)!=7
        if stop==END:chain_random_calls+=sum(e[0]==1 for e in a['events'])
        return a
    def both(c,group):
        for stop in (MID,END):old.load(c);new.load(c);compare(c,stop,group)
    for damage in (0,1,4,5,6,40):
     for armour in (0,1,5,40):
      for enemy9 in (-1,0,3):
       for phase in (5,7):
        for enemy29 in (False,True):
            c=dict(board=[[2,0] for _ in range(36)],armour=armour,ui=armour,chance=50,seeds=[0x1234567+i for i in range(6)],
                   phase=phase,damage=damage,enemy9=enemy9)
            if enemy29:c['board'][20]=[1,29]
            both(c,'boundary')
    for n in range(600):
        armour=rng.randrange(70)
        c=dict(board=[[rng.randrange(5),rng.randrange(33)] for _ in range(36)],armour=armour,ui=rng.choice([armour,rng.randrange(130)]),
               chance=rng.randrange(-1,102),seeds=[rng.getrandbits(32) for _ in range(6)],
               phase=rng.choice([5,5,5,rng.randrange(1,8)]),damage=rng.randrange(80),enemy9=rng.randrange(-2,20))
        both(c,'random')
    # Continuous: one board, armour wears down over repeated attacks; state carried (no reloads).
    c=dict(board=[[2,0] for _ in range(36)],armour=60,ui=60,chance=45,seeds=[rng.getrandbits(32) for _ in range(6)],phase=5,damage=0,enemy9=0)
    old.load(c);new.load(c)
    for step in range(80):
        damage,enemy9=rng.randrange(12),rng.randrange(4)
        old.write(DAMAGE,damage);old.write(ENEMY9,enemy9);old.write(PHASE,5)
        new.damage.incoming_damage=damage;new.damage.enemy9_damage=enemy9;new.damage.phase=5
        compare(dict(step=step,damage=damage,enemy9=enemy9),END,'continuous_steps')
    assert all(hex(a) in old.absorb_visits for a in (0x147a4,0x147ae,0x147c2,0x147d6,0x147de))
    report=dict(status='passed',cases=sum(counts.values()),by_group=counts,phase7_transitions=phase7,chain_random_calls=chain_random_calls,
                range=dict(start=hex(START),end_exclusive=hex(MID)),chain=dict(start=hex(START),end_exclusive=hex(END)),
                original='Actual ProcessAttack [0x14790,0x1487e): absorption, then shield wear with GetEnemyCount/RandI/RandUnitF/Clamp',
                boundaries=['entry R4/R5/R6 set as preceding phase-5 code leaves them','SimpleLabel::SetNumber/AddSimpleLabel/shield UI/audio adapted',
                            'platform floorf','no phase scheduler, health damage, counterattack or vampires'],
                scope='Shared armour/UI/RNG plus phase, incoming damage and enemy-9 label fields; no complete enemy phase claim',
                byte_sha256=hashlib.sha256(old.machine.bytes_at(START,MID-START)).hexdigest(),
                chain_byte_sha256=hashlib.sha256(old.machine.bytes_at(START,END-START)).hexdigest(),branch_visits=old.absorb_visits)
    (HERE/'attack_absorb_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
