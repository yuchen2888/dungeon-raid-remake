#!/usr/bin/env python3
"""Actual Game::ProcessVampires 0xdaf8 and Tile::AddHealth 0x3dc6c vs native.

Whole original functions execute, including GetMortalEnemyType, Tile::GetAttack
and (on the mortal-enemy path) Tile::AddHealth. Only Tile::UpdateText,
Game::AddSimpleLabel and Game::QueueSound called from these two functions are
adapted presentation calls, recorded as ordered events.
"""
import json
import random
import re
import ctypes as C
from verify_encounters import Original as EncOriginal, Native as EncNative, Hooks, configure
from verify_generation import Generation
from verify_stroke import HERE, I32

VAMPIRES,VAMPIRES_END=0xdaf8,0xdc30
ADD_HEALTH,ADD_HEALTH_END=0x3dc6c,0x3dc98

class Original(EncOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.vamp_calls={};self.vamp_active=False;self.vamp_visits={}
        for symbol,name in [('__ZN4Tile10UpdateTextEbbb','text'),('__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif','label'),
                            ('__ZN4Game10QueueSoundE5Sound','sound')]:
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol
            self.vamp_calls[int(m[1],16)]=name
    def hook(self,u,address,size,context):
        if not self.vamp_active:return super().hook(u,address,size,context)
        if VAMPIRES<=address<VAMPIRES_END or ADD_HEALTH<=address<ADD_HEALTH_END:
            self.vamp_visits[hex(address)]=self.vamp_visits.get(hex(address),0)+1
        name=self.vamp_calls.get(address);lr=u.reg_read(self.LR)&~1
        if not name or not (VAMPIRES<=lr<VAMPIRES_END or ADD_HEALTH<=lr<ADD_HEALTH_END):return super().hook(u,address,size,context)
        r=[u.reg_read(v) for v in self.regs];signed=lambda v:C.c_int32(v).value;sp=u.reg_read(self.SP)
        if name=='text':e=[7,self.index(r[0]),r[1]&0xff,r[2]&0xff,r[3]&0xff,0]
        elif name=='label':
            assert r[0]==self.GAME;e=[2,self.index(r[2]-0x54),r[1],signed(r[3]),signed(self.read(sp)),signed(self.read(sp+4))]
        else:assert r[0]==self.GAME;e=[1,-1,r[1],0,0,0]
        self.enc_events.append(e);u.reg_write(self.PC,u.reg_read(self.LR))
    def vampires(self,key,i=0,amount=0):
        self.enc_events=[];self.gen_events=[];self.refill_events=[];self.vamp_active=True
        try:
            if key=='vampires':self.call(VAMPIRES,[self.GAME])
            else:self.call(ADD_HEALTH,[self.tile(i),amount])
        finally:self.vamp_active=False
        return self.enc_status()

class Native(EncNative):
    def __init__(self):
        super().__init__()
        self.enc_lib.dr_process_vampires.argtypes=[C.POINTER(Generation),C.POINTER(Hooks)];self.enc_lib.dr_process_vampires.restype=None
        self.enc_lib.dr_tile_add_health.argtypes=[C.POINTER(Generation),C.c_uint32,I32,C.POINTER(Hooks)];self.enc_lib.dr_tile_add_health.restype=None
    def vampires(self,key,i=0,amount=0):
        self.enc_events=[];self.gen_events=[];self.refill_events=[]
        if key=='vampires':self.enc_lib.dr_process_vampires(C.byref(self.gen),C.byref(self.enc_hooks))
        else:self.enc_lib.dr_tile_add_health(C.byref(self.gen),i,amount,C.byref(self.enc_hooks))
        return self.enc_status()

def main():
    old,new=Original(),Native();rng=random.Random(0xDAF8);counts={'add_health':0,'boundary':0,'random':0,'repeated':0}
    healed=capped=skipped=0
    def compare(c,key,args,group):
        nonlocal healed,capped,skipped
        a,b=old.vampires(key,*args),new.vampires(key,*args)
        if a!=b:
            (HERE/'vampires_failure.json').write_text(json.dumps(dict(case=c,key=key,args=args,original=a,native=b),indent=2))
            raise AssertionError('vampires_failure.json')
        counts[group]+=1;labels=[e for e in a['encounters'] if e[0]==2];healed+=len(labels)
        return a
    def vampire(c,i,matched=0,attack=3,health=10,max_health=20):
        c['board'][i].update(type=1,enemy=20,matched=matched);c['combat'][i]['attack']=attack;c['combat'][i]['health']=health
        c['extras'][i]['max_health']=max_health
    # Tile::AddHealth directly: wrap-around add and max raise.
    for health in (-5,0,10,90,2**31-1):
     for amount in (-3,0,1,7,100):
      for max_health in (0,10,95,200):
        c=configure();c['combat'][17]['health']=health;c['extras'][17]['max_health']=max_health
        old.load(c);new.load(c);compare(c,'add_health',(17,amount),'add_health')
    # ProcessVampires: every race (mortal path), health vs cap, matched/type/enemy filters, poison-affected attack.
    for race in range(10):
     for health,max_health in ((0,10),(5,10),(9,10),(10,10),(11,10),(-2,4)):
      for attack in (0,1,3,12):
       for poison in (0,3):
        c=configure();c['game']['race']=race
        for i in range(36):c['board'][i].update(type=2,enemy=0,matched=0)
        vampire(c,4,attack=attack,health=health,max_health=max_health);c['combat'][4]['poison'][0]=poison
        vampire(c,22,matched=1,attack=attack,health=health,max_health=max_health)        # matched: skipped
        c['board'][30].update(type=1,enemy=19,matched=0)                                  # other enemy: skipped
        c['board'][11].update(type=3,enemy=20,matched=0)                                  # not an enemy tile: skipped
        vampire(c,35,attack=attack+1,health=health-1,max_health=max_health+2)
        old.load(c);new.load(c);compare(c,'vampires',(),'boundary')
    for n in range(400):
        c=configure();c['game']['race']=rng.randrange(10)
        for i in range(36):
            enemy=20 if rng.random()<.35 else rng.randrange(33)
            c['board'][i].update(type=1 if rng.random()<.8 else rng.randrange(5),enemy=enemy,matched=int(rng.random()<.2))
            c['combat'][i]['attack']=rng.randrange(0,40);c['combat'][i]['health']=rng.randrange(-3,120)
            c['combat'][i]['poison'][0]=rng.choice([0,0,rng.randrange(1,6)]);c['extras'][i]['max_health']=rng.randrange(0,130)
        old.load(c);new.load(c);compare(c,'vampires',(),'random')
    # Repeated attack rounds on carried state: vampires climb to their cap (or past it on the mortal path).
    for race in range(10):
        c=configure();c['game']['race']=race
        for i in range(36):c['board'][i].update(type=2,enemy=0,matched=0)
        for i in (0,7,14,21,28,35):vampire(c,i,attack=1+i%5,health=1,max_health=25)
        old.load(c);new.load(c)
        for _ in range(12):compare(dict(race=race),'vampires',(),'repeated')
    mortal_path=old.vamp_visits.get(hex(0xdb4c),0);cap_path=old.vamp_visits.get(hex(0xdb5c),0)
    assert mortal_path and cap_path and all(hex(a) in old.vamp_visits for a in (0xdb72,0xdb74,0xdc04,0x3dc92))
    report=dict(status='passed',comparisons=sum(counts.values()),by_group=counts,vampire_heals=healed,
                mortal_enemy_path_visits=mortal_path,capped_path_visits=cap_path,
                functions=[dict(symbol='__ZN4Game15ProcessVampiresEv',address=hex(VAMPIRES),native='dr_process_vampires'),
                           dict(symbol='__ZN4Tile9AddHealthEi',address=hex(ADD_HEALTH),native='dr_tile_add_health')],
                original='Actual ProcessVampires, AddHealth, GetMortalEnemyType and Tile::GetAttack',
                boundaries=['UpdateText/AddSimpleLabel/QueueSound adapted as ordered events','not yet called from the native health-damage segment by any scheduler'],
                scope='Shared board, combat health, max_health, race and poison-adjusted attack; no complete enemy phase claim',
                branch_visits=old.vamp_visits)
    (HERE/'vampires_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='branch_visits'}))

if __name__=='__main__':main()
