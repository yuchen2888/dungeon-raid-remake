#!/usr/bin/env python3
"""Phase-6 health damage with the REAL Game::ProcessVampires on shared state.

Original side: ProcessAttack [0x14a14,0x14ae4) runs with its ProcessVampires
call executing the original function (GetMortalEnemyType, Tile::GetAttack,
Tile::AddHealth included). Native side: dr_process_attack_health_damage, whose
ordered Vampires event invokes dr_process_vampires on a GenerationState that
shares the same MatchState, board, resources and combat tiles.
Presentation calls (labels, text, bars, help, audio) are recorded as events.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_attack_health import (Original as HealthOriginal, Native as HealthNative, Hooks as HealthHooks,
    CALLBACK as HEALTH_CALLBACK, START, END, PHASE, ENEMY9, HEALTH, UI_HEALTH, POISON, GAME, HERE)
from verify_encounters import Hooks as EncHooks, EVENT as ENC_EVENT
from verify_generation import Generation
from verify_refill import Refill
from verify_path import Path
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R8,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC

TILES,STRIDE,RACE=0x5e58,608,0x1556c
VAMPIRES,VAMPIRES_END,ADD_HEALTH,ADD_HEALTH_END=0xdaf8,0xdc30,0x3dc6c,0x3dc98

class Original(HealthOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.vcalls={};self.vamp_visits={}
        for symbol,name in [('__ZN4Tile10UpdateTextEbbb','text'),('__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif','label'),
                            ('__ZN4Game10QueueSoundE5Sound','sound')]:
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol
            self.vcalls[int(m[1],16)]=name
    def index(self,address):
        i,rest=divmod(address-GAME-TILES,STRIDE);assert rest==0 and 0<=i<36;return i
    def hook(self,u,address,size,context):
        if self.in_health:
            if VAMPIRES<=address<VAMPIRES_END or ADD_HEALTH<=address<ADD_HEALTH_END:
                self.vamp_visits[hex(address)]=self.vamp_visits.get(hex(address),0)+1
            if address==VAMPIRES:
                assert u.reg_read(UC_ARM_REG_R0)==GAME;self.events.append(['H',4,0,0,0,0]);return   # run the real function
            lr=u.reg_read(UC_ARM_REG_LR)&~1;name=self.vcalls.get(address)
            if name and (VAMPIRES<=lr<VAMPIRES_END or ADD_HEALTH<=lr<ADD_HEALTH_END):
                r=[u.reg_read(x) for x in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)];s=lambda v:C.c_int32(v).value
                if name=='text':e=[7,self.index(r[0]),r[1]&0xff,r[2]&0xff,r[3]&0xff,0]
                elif name=='label':
                    sp=u.reg_read(UC_ARM_REG_SP);colour,scale=struct.unpack('<ii',u.mem_read(sp,8))
                    assert r[0]==GAME;e=[2,self.index(r[2]-0x54),r[1],s(r[3]),colour,scale]
                else:assert r[0]==GAME;e=[1,-1,r[1],0,0,0]
                self.events.append(['V']+e);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        return super().hook(u,address,size,context)
    def load(self,c):
        super().load(c);self.write(RACE,c['race'])
        for i,t in enumerate(c['tiles']):
            base=TILES+STRIDE*i;self.write(base+0x70,GAME);self.u.mem_write(GAME+base+0x84,bytes([t['matched']]))
            for offset,key in ((0xa4,'attack'),(0xac,'health'),(0xb0,'max_health'),(0x238,'poison')):self.write(base+offset,t[key])
    def tiles(self):return [[self.read(TILES+STRIDE*i+0xac),self.read(TILES+STRIDE*i+0xb0)] for i in range(36)]
    def state(self):return dict(**super().state(),tiles=self.tiles())
    def health(self):
        self.events=[];self.in_health=True;before=bytearray(self.u.mem_read(GAME,0x20000))
        for reg,value in [(UC_ARM_REG_R8,GAME),(UC_ARM_REG_SP,0x1000f00),(UC_ARM_REG_LR,0x1200001)]:self.u.reg_write(reg,value)
        try:self.u.emu_start(START|1,0x1200000,timeout=0,count=100000)
        finally:self.in_health=False
        assert self.u.reg_read(UC_ARM_REG_PC)==END
        allowed=[PHASE,ENEMY9,HEALTH,UI_HEALTH,POISON]+[TILES+STRIDE*i+o for i in range(36) for o in (0xac,0xb0)]
        for offset in allowed:before[offset:offset+4]=self.u.mem_read(GAME+offset,4)
        assert bytes(before)==bytes(self.u.mem_read(GAME,0x20000)),'unexpected gameplay write'
        return dict(**self.state(),events=self.events[:])

class Native(HealthNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_encounters_native.dylib'))
        self.vampires=lib.dr_process_vampires;self.vampires.argtypes=[C.POINTER(Generation),C.POINTER(EncHooks)];self.vampires.restype=None
        def health_event(_,p):
            e=p.contents;self.events.append(['H',e.kind,e.a,e.b,e.c,e.d])
            if e.kind==4:self.vampires(C.byref(self.gen),C.byref(self.enc_hooks))
        def encounter_event(_,p):
            e=p.contents;self.events.append(['V',e.kind,e.tile,e.a,e.b,e.c,e.d])
        self.health_callback=HEALTH_CALLBACK(health_event);self.health_hooks=HealthHooks(None,self.health_callback)
        self.enc_callback=ENC_EVENT(encounter_event);self.enc_hooks=EncHooks(None,self.enc_callback,None)
    def load(self,c):
        super().load(c);self.stroke.selection.character.race=c['race']
        self.path=Path();self.path.match=C.pointer(self.match);self.refill=Refill();self.refill.path=C.pointer(self.path)
        self.gen=Generation();self.gen.refill=C.pointer(self.refill);self.gen.resources=C.pointer(self.resource)
        for i,t in enumerate(c['tiles']):
            self.stroke.selection.tiles[i].rule.matched=t['matched'];k=self.path.combat[i]
            k.attack,k.health,k.poison.current=t['attack'],t['health'],t['poison'];self.gen.tiles[i].max_health=t['max_health']
    def tiles(self):return [[self.path.combat[i].health,self.gen.tiles[i].max_health] for i in range(36)]
    def state(self):return dict(**super().state(),tiles=self.tiles())

def board(rng,race):
    kinds=[];tiles=[]
    for i in range(36):
        vampire=rng.random()<.3
        kinds.append([1,20] if vampire else [rng.randrange(5),rng.randrange(33)])
        health=rng.randrange(-2,60);tiles.append(dict(matched=int(rng.random()<.15),attack=rng.randrange(0,15),health=health,
            max_health=rng.choice([health,health+rng.randrange(1,30),rng.randrange(0,60)]),poison=rng.choice([0,0,rng.randrange(1,5)])))
    return kinds,tiles

def main():
    old,new=Original(),Native();rng=random.Random(0x14A92);counts={'single':0,'rounds':0};vampire_events=0;health_rounds=0
    def check(c,a,b,group):
        nonlocal vampire_events
        if a!=b:
            (HERE/'attack_vampires_failure.json').write_text(json.dumps(dict(case=c,original=a,native=b),indent=2))
            raise AssertionError('attack_vampires_failure.json')
        counts[group]+=1;vampire_events+=sum(e[0]=='V' for e in a['events'])
    def case(race,kinds,tiles,**k):
        c=dict(board=kinds,tiles=tiles,race=race,armour=0,ui=0,chance=50,seeds=[rng.getrandbits(32) for _ in range(6)],
               phase=6,damage=0,enemy9=0,health=0,ui_health=0,poison=0);c.update(k);return c
    for race in range(10):
        for _ in range(30):
            kinds,tiles=board(rng,race);health=rng.randrange(0,120)
            c=case(race,kinds,tiles,health=health,ui_health=rng.choice([health,0]),damage=rng.randrange(-2,60),enemy9=rng.randrange(-1,8),poison=rng.randrange(0,6))
            old.load(c);new.load(c);check(c,old.health(),new.health(),'single')
    for race in range(10):
        kinds,tiles=board(rng,race)
        c=case(race,kinds,tiles,armour=rng.randrange(0,8),health=rng.randrange(80,250),poison=rng.randrange(0,3))
        old.load(c);new.load(c)
        for step in range(30):
            damage,enemy9=rng.randrange(0,25),rng.choice([0,0,rng.randrange(1,6)])
            a,b=old.round(damage,enemy9),new.round(damage,enemy9)
            check(dict(race=race,step=step,damage=damage,enemy9=enemy9),a,b,'rounds');health_rounds+=any(e[0]=='H' for e in a['events'])
    assert old.vamp_visits.get(hex(0xdb4c)) and old.vamp_visits.get(hex(0xdb5c)) and old.vamp_visits.get(hex(0x3dc6c))
    report=dict(status='passed',comparisons=sum(counts.values()),by_group=counts,rounds_reaching_health=health_rounds,vampire_events=vampire_events,
                mortal_path_visits=old.vamp_visits[hex(0xdb4c)],capped_path_visits=old.vamp_visits[hex(0xdb5c)],
                original='Actual ProcessAttack [0x14a14,0x14ae4) with the real ProcessVampires/AddHealth/GetMortalEnemyType/GetAttack; rounds chain absorption [0x14790,0x147e4)',
                boundaries=['presentation calls adapted as ordered events','phase 6 set by harness as 0x146e0 does; no phase animation, scheduler or game-over check'],
                scope='Shared board, combat health/max, race, resources, phase and damage fields across both native modules')
    (HERE/'attack_vampires_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
