#!/usr/bin/env python3
"""Actual Tile::SetSpecialType 0x3f43c, Game::Shapeshift 0x918c and Game::Healing 0x12e68 vs native
dr_set_special_type / dr_shapeshift / dr_healing (recovered_schedule), on the shared state of
verify_attack_all.py. They were callbacks of the match and resource units (MatchEventKind::SetSpecialType /
Shapeshift, ResourceEventKind::Healing).

Each original function runs from its entry to its return. SetSpecialType runs Tile::SetType as original
code with the generation harness recording its calls (as in verify_generation.py); Shapeshift runs RandI
as original code. Recorded and skipped, in the resource harness's form: Quad::SetUV (generation harness),
Interface::UpdateSkills, QueueAchievement and Interface::UpdateHealthBar.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_input_gate import Original as GateOriginal, Native as GateNative
from verify_attack_all import scenario
from verify_generation import Generation
from verify_resources import Resource
from verify_stroke import HERE, I32, U8

SPECIAL,SHAPESHIFT,HEALING=0x3f43c,0x918c,0x12e68
SYMBOLS={'__ZN9Interface12UpdateSkillsEv':'skills','__ZN4Game16QueueAchievementE11Achievementf':'achievement',
         '__ZN9Interface15UpdateHealthBarER4Quadi':'health'}

class Original(GateOriginal):
    def __init__(self):
        super().__init__();self.small=None;self.small_calls={}
        text=(HERE.parent/'armv7-disassembly.txt').read_text()
        for symbol,name in SYMBOLS.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol;self.small_calls[int(m[1],16)]=name
        # the match harness models SetSpecialType and Shapeshift as boundaries; here the original functions run
        self.match_calls={k:v for k,v in self.match_calls.items() if k not in (SPECIAL,SHAPESHIFT)}
    def hook(self,u,address,size,context):
        if self.small in ('shapeshift','healing'):
            name=self.small_calls.get(address);lr=u.reg_read(self.LR)&~1
            if name and (SHAPESHIFT<lr<0x91c4 or HEALING<lr<0x12ee8):
                r=[C.c_int32(u.reg_read(v)).value for v in self.regs]
                if name=='skills':e=[2,0,0,0,0]
                elif name=='achievement':e=[12,r[1],r[2],0,0]
                else:assert r[0]==self.GAME+0x4cdc and r[1]==self.GAME+0x4d4c;e=[3,r[2],0,0,0]
                self.small_events.append(e);u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def run(self,which,entry,args):
        u=self.u;self.small=which;self.small_events=[];self.gen_events=[];self.pending_gen=None
        if which=='special':self.gen_active=True
        for reg,v in zip(self.regs,args):u.reg_write(reg,v)
        u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1)
        try:u.emu_start(entry|1,self.STOP,timeout=0,count=500000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.small=None;self.gen_active=False
        G=self.GAME;s=lambda a:C.c_int32(self.read(a)).value
        return dict(events=self.small_events if which!='special' else self.gen_events,gen=self.gen_status() if which=='special' else None,
                    health=[s(G+0xbd98),s(G+0x5994)],skills=[s(0x1700090+0x100*i) for i in range(4)],
                    seeds=list(struct.unpack('<6I',u.mem_read(0x1eac20,24))))
    def special(self,tile,special):return self.run('special',SPECIAL,[self.tile(tile),special])
    def shapeshift(self):return self.run('shapeshift',SHAPESHIFT,[self.GAME])
    def healing(self):return self.run('healing',HEALING,[self.GAME])

class Native(GateNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_schedule_native.dylib'))
        self.special_fn=lib.dr_set_special_type;self.special_fn.restype=None;self.special_fn.argtypes=[C.c_void_p,C.c_uint32,I32,C.c_void_p]
        self.shape_fn=lib.dr_shapeshift;self.shape_fn.restype=None;self.shape_fn.argtypes=[C.c_void_p,C.c_void_p]
        self.heal_fn=lib.dr_healing;self.heal_fn.restype=None;self.heal_fn.argtypes=[C.c_void_p,C.c_void_p]
    def small_state(self,which):
        r=self.r
        return dict(events=self.resource_events if which!='special' else self.gen_events,gen=self.gen_status() if which=='special' else None,
                    health=[r.health,r.ui_health],skills=list(r.skill_current),seeds=list(self.m.random.seeds))
    def special(self,tile,special):
        self.gen_events=[];self.special_fn(C.addressof(self.gen),tile,special,C.addressof(self.gen_hooks));return self.small_state('special')
    def shapeshift(self):
        self.resource_events=[];self.shape_fn(C.addressof(self.r),C.addressof(self.resource_hooks));return self.small_state('shapeshift')
    def healing(self):
        self.resource_events=[];self.heal_fn(C.addressof(self.r),C.addressof(self.resource_hooks));return self.small_state('healing')

def main():
    old,new=Original(),Native();rng=random.Random(0x918c);counts={};healed=refilled=0
    def compare(c,which,a,b):
        if a!=b:
            (HERE/'small_units_failure.json').write_text(json.dumps(dict(case=c,which=which,original=a,native=b),indent=2))
            raise AssertionError(f'small_units_failure.json ({which})')
        counts[which]=counts.get(which,0)+1
    for n in range(400):
        c,_=scenario(rng);r=c['resources']
        r.update(health_max=rng.choice([20,40,61,100]),health_bonus=rng.choice([0,3,-2]),skill_count=rng.choice([0,1,2,4,rng.randrange(5)]),
                 skill_max=[rng.randrange(1,9) for _ in range(4)],skill_current=[rng.randrange(0,9) for _ in range(4)])
        r['health']=rng.choice([0,1,4,9,10,15,25,rng.randrange(-3,60)]);r['ui_health']=rng.choice([r['health'],0,(r['health_max']+r['health_bonus'])//4])
        c['moving_list']=[];c['gate']=dict(tokens_pending=0,flare_count=0,phase=0,touch_phase=0,input_target=-1,rune=0)
        old.load(c);new.load(c)
        which=('special','shapeshift','healing')[n%3]
        if which=='special':
            tile,special=rng.randrange(36),rng.choice([0,1,2,3,rng.randrange(8)])
            a,b=old.special(tile,special),new.special(tile,special)
        elif which=='shapeshift':a,b=old.shapeshift(),new.shapeshift();refilled+=bool(a['events'])
        else:a,b=old.healing(),new.healing();healed+=bool(a['events'])
        compare(c,which,a,b)
    assert healed and refilled,(healed,refilled)
    report=dict(status='passed',comparisons=counts,healed=healed,shapeshifts=refilled,
                functions=[dict(symbol='__ZN4Tile14SetSpecialTypeE15SpecialTileType',address=hex(SPECIAL),native='dr_set_special_type'),
                           dict(symbol='__ZN4Game10ShapeshiftEv',address=hex(SHAPESHIFT),native='dr_shapeshift'),
                           dict(symbol='__ZN4Game7HealingEv',address=hex(HEALING),native='dr_healing')],
                original='Actual functions with original Tile::SetType (generation harness) and RandI',
                boundaries=['Quad::SetUV, Interface::UpdateSkills, QueueAchievement, Interface::UpdateHealthBar recorded'])
    (HERE/'small_units_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
