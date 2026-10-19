#!/usr/bin/env python3
"""Actual ProcessAttack phase-6 health damage instructions vs native source.

  health : [0x14a14,0x14ae4) vs dr_process_attack_health_damage
  rounds : repeated attacks on carried state; each round sets phase 6 (as
           0x146e0 does), runs absorption [0x14790,0x147e4), then, only if
           that left phase 6, the health segment. Native runs absorb + health.
Game::ProcessVampires is not recovered: the original call is stubbed and
recorded as an ordered event, as is the native Vampires callback. It only
writes vampire tile health (Tile+0xac), never the fields compared here.
Labels, poison/health bars, help and audio are adapted presentation calls.
"""
import ctypes as C
import hashlib
import json
import random
import re
import struct
from verify_attack_absorb import (Original as AbsorbOriginal, Native as AbsorbNative,
    START as ABSORB, MID as ABSORB_END, PHASE, DAMAGE, ENEMY9, GAME, HERE)
from unicorn.arm_const import (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,
    UC_ARM_REG_R8,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC)

START,END=0x14a14,0x14ae4
HEALTH,UI_HEALTH,POISON=0xbd98,0x5994,0x15540
INTERFACE,HEALTH_QUAD=0x4cdc,0x4d4c
LABEL_POS={2:0xbd30,7:0x15518}

class Event(C.Structure):
    _fields_=[(k,C.c_int32) for k in ('kind','a','b','c','d')]
CALLBACK=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(Event))
class Hooks(C.Structure):
    _fields_=[('context',C.c_void_p),('event',CALLBACK)]

class Original(AbsorbOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.health_visits={}
        self.health_calls={}
        for symbol,name in [('__ZN4Game10QueueSoundE5Sound','sound'),('__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif','label'),
                            ('__ZN9Interface9SetPoisonEi','poison'),('__ZN4Game15ProcessVampiresEv','vampires'),
                            ('__ZN9Interface14ShowHelpHealthEv','help'),('__ZN9Interface15UpdateHealthBarER4Quadi','bar')]:
            m=re.search(r'^'+symbol+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol
            self.health_calls[int(m[1],16)]=name
        self.in_health=False
    def hook(self,u,address,size,context):
        if not self.in_health:return super().hook(u,address,size,context)
        if START<=address<END:self.health_visits[hex(address)]=self.health_visits.get(hex(address),0)+1
        if address==END:u.emu_stop();return
        name=self.health_calls.get(address)
        if not name:return
        r=[C.c_int32(u.reg_read(x)).value for x in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        if name=='sound':assert r[0]==GAME;e=[1,r[1],0,0,0]
        elif name=='label':
            colour,scale=struct.unpack('<ii',u.mem_read(u.reg_read(UC_ARM_REG_SP),8))
            assert r[0]==GAME and r[2]==GAME+LABEL_POS[r[1]];e=[2,r[1],r[3],colour,scale]
        elif name=='poison':assert r[0]==GAME+INTERFACE;e=[3,r[1],0,0,0]
        elif name=='vampires':assert r[0]==GAME;e=[4,0,0,0,0]
        elif name=='help':assert r[0]==GAME+INTERFACE;e=[5,0,0,0,0]
        else:assert r[0]==GAME+INTERFACE and r[1]==GAME+HEALTH_QUAD;e=[6,r[2],0,0,0]
        self.events.append(['H']+e);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def load(self,c):
        super().load(c)
        for offset,key in ((HEALTH,'health'),(UI_HEALTH,'ui_health'),(POISON,'poison')):self.write(offset,c[key])
    def state(self):
        return {k:self.read(o) for k,o in (('phase',PHASE),('damage',DAMAGE),('enemy9',ENEMY9),('health',HEALTH),
                ('ui_health',UI_HEALTH),('poison',POISON),('armour',0xbda4),('ui',0x59c0))}
    def health(self):
        self.events=[];self.in_health=True;before=bytearray(self.u.mem_read(GAME,0x20000))
        for reg,value in [(UC_ARM_REG_R8,GAME),(UC_ARM_REG_SP,0x1000f00),(UC_ARM_REG_LR,0x1200001)]:self.u.reg_write(reg,value)
        try:self.u.emu_start(START|1,0x1200000,timeout=0,count=10000)
        finally:self.in_health=False
        assert self.u.reg_read(UC_ARM_REG_PC)==END
        for offset in (PHASE,ENEMY9,HEALTH,UI_HEALTH,POISON):before[offset:offset+4]=self.u.mem_read(GAME+offset,4)
        assert bytes(before)==bytes(self.u.mem_read(GAME,0x20000)),'unexpected gameplay write'
        return dict(**self.state(),events=self.events[:])
    def round(self,damage,enemy9):
        self.write(PHASE,6);self.write(DAMAGE,damage);self.write(ENEMY9,enemy9)
        a=self.run(ABSORB_END);out=dict(absorbed=a['absorbed'],events=a['events'])
        if self.read(PHASE)==6:out['events']+=self.health()['events']
        return dict(**out,**self.state())

class Native(AbsorbNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_attack_shield_native.dylib'))
        self.health_fn=lib.dr_process_attack_health_damage
        self.health_fn.argtypes=[C.c_void_p,C.POINTER(Hooks)];self.health_fn.restype=None
        self.health_callback=CALLBACK(lambda _,p:self.events.append(['H']+[getattr(p.contents,k) for k in ('kind','a','b','c','d')]))
        self.health_hooks=Hooks(None,self.health_callback)
    def load(self,c):
        super().load(c);r=self.resource
        r.health,r.ui_health,r.poison=c['health'],c['ui_health'],c['poison']
    def state(self):
        d,r=self.damage,self.resource
        return dict(phase=d.phase,damage=d.incoming_damage,enemy9=d.enemy9_damage,health=r.health,ui_health=r.ui_health,
                    poison=r.poison,armour=self.preview.armour_current,ui=r.ui_armour)
    def health(self):
        self.events=[];board=bytes(self.stroke);armour=self.preview.armour_current
        self.health_fn(C.addressof(self.damage),C.byref(self.health_hooks))
        assert bytes(self.stroke)==board and self.preview.armour_current==armour
        return dict(**self.state(),events=self.events[:])
    def round(self,damage,enemy9):
        d=self.damage;d.phase,d.incoming_damage,d.enemy9_damage=6,damage,enemy9
        a=self.run(ABSORB_END);out=dict(absorbed=a['absorbed'],events=a['events'])
        if d.phase==6:out['events']+=self.health()['events']
        return dict(**out,**self.state())

def main():
    old,new=Original(),Native();rng=random.Random(0xD134022)
    counts={'boundary':0,'random':0,'rounds':0};floored=bars=vampire_calls=health_rounds=0
    def check(c,a,b,group):
        if a!=b:
            (HERE/'attack_health_failure.json').write_text(json.dumps(dict(case=c,original=a,native=b),indent=2))
            raise AssertionError('attack_health_failure.json')
        counts[group]+=1
    def single(c,group):
        nonlocal floored,bars
        old.load(c);new.load(c);a,b=old.health(),new.health();check(c,a,b,group)
        floored+=a['health']==0 and c['health']-c['damage']<0;bars+=any(e[1]==6 for e in a['events'])
    def case(**k):
        c=dict(board=[[2,0] for _ in range(36)],armour=0,ui=0,chance=50,seeds=[7]*6,phase=6,damage=0,enemy9=0,health=0,ui_health=0,poison=0)
        c.update(k);return c
    for health in (0,1,5,30,100):
     for ui_same in (True,False):
      for damage in (-3,0,1,5,29,30,31,200):
       for enemy9 in (-1,0,3,50):
        for poison in (-1,0,3,10):
            single(case(health=health,ui_health=health if ui_same else health+7,damage=damage,enemy9=enemy9,poison=poison),'boundary')
    for _ in range(800):
        health=rng.randrange(150)
        single(case(health=health,ui_health=rng.choice([health,rng.randrange(150)]),damage=rng.randrange(-5,160),
                    enemy9=rng.randrange(-3,40),poison=rng.randrange(-2,30),phase=rng.randrange(1,8)),'random')
    for game in range(6):
        c=case(board=[[rng.randrange(5),rng.randrange(33)] for _ in range(36)],armour=rng.randrange(0,25),ui=0,chance=rng.randrange(0,101),
               seeds=[rng.getrandbits(32) for _ in range(6)],health=rng.randrange(40,200),ui_health=0,poison=rng.randrange(0,5))
        old.load(c);new.load(c)
        for step in range(40):
            damage,enemy9=rng.randrange(0,30),rng.choice([0,0,rng.randrange(1,8)])
            a,b=old.round(damage,enemy9),new.round(damage,enemy9)
            check(dict(game=game,step=step,damage=damage,enemy9=enemy9),a,b,'rounds')
            health_rounds+=any(e[0]=='H' for e in a['events']);vampire_calls+=sum(e[0]=='H' and e[1]==4 for e in a['events'])
    assert all(hex(a) in old.health_visits for a in (0x14a72,0x14a90,0x14abe,0x14ac4,0x14ad4))
    report=dict(status='passed',comparisons=sum(counts.values()),by_group=counts,health_floored=floored,health_bar_updates=bars,
                rounds_reaching_health=health_rounds,vampire_callbacks=vampire_calls,
                range=dict(start=hex(START),end_exclusive=hex(END)),
                original='Actual ProcessAttack [0x14a14,0x14ae4); rounds chain actual absorption [0x14790,0x147e4) before it',
                boundaries=['Game::ProcessVampires stubbed as ordered callback (not recovered)','labels/poison bar/health bar/help/audio adapted',
                            'phase 6 set by harness as 0x146e0 does; no phase animation, scheduler or game-over check'],
                scope='Shared health/UI health/poison plus phase, remaining damage and enemy-9 fields; no complete enemy phase claim',
                byte_sha256=hashlib.sha256(old.machine.bytes_at(START,END-START)).hexdigest(),branch_visits=old.health_visits)
    (HERE/'attack_health_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
