#!/usr/bin/env python3
"""Actual EndOfTurn [0x13cda,0x13d12) + [0x13af2,0x13b3c) + loop head [0x13daa,0x13dc8)
vs native dr_end_turn_abilities (recovered_turn).

The original runs from 0x13cda (R8=Game) to 0x13b3c: Tile+0x254 cleared for all
tiles, the whole original ProcessCripples (MatchTile with match/token hooks),
then the column-major loop calling the whole original ActivateAbility (as in
verify_activate_ability.py: unrecovered ability functions recorded, generation
hooks active only inside ActivateAbility).
"""
import ctypes as C
import json
import random
from verify_activate_ability import Original as ActivateOriginal, Native as ActivateNative, TurnHooks
from verify_generation import Generation, Hooks as GenerationHooks
from verify_attack_all import scenario
from verify_path import Path
from verify_stroke import HERE, U8

ENTRY,STOP=0x13cda,0x13b3c
RANGES=[(0x13cda,0x13d12),(0x13af2,0x13b3c),(0x13daa,0x13dc8)]
ACTIVATE,AFTER=0x3f09c,0x13b2a
FUNCS={0xbd20:'mimic',0xaf68:'resurrect',0xcae0:'cripples'}

class Original(ActivateOriginal):
    def hook(self,u,address,size,context):
        if self.looping:
            if any(a<=address<b for a,b in RANGES):self.loop_visits[hex(address)]=self.loop_visits.get(hex(address),0)+1
            if address in FUNCS:self.current=FUNCS[address]
            if address==ACTIVATE:self.gen_active=self.activating=True
            elif address==AFTER:self.gen_active=self.activating=False
        return super().hook(u,address,size,context)
    def run_loop(self):
        self.turn_events=[];self.ability_events=[];self.match_events=[];self.token_events=[];self.path_events=[];self.gen_events=[];self.pending_gen=None
        self.looping=True;self.ability_stack=[];self.mode=None;u=self.u
        self.all_events=[];self.enc_events=[];self.refill_events=[];self.motion_events=[];self.int_sets={}
        self.ranges=self.ability_ranges();self.all_running=True   # MoveMatchedTiles/SwapTiles switching inside abilities
        from unicorn.arm_const import UC_ARM_REG_R8
        u.reg_write(UC_ARM_REG_R8,self.GAME);u.reg_write(self.SP,0x140ff00);u.reg_write(self.LR,self.STOP|1)
        try:
            u.emu_start(ENTRY|1,STOP,timeout=0,count=20000000);assert u.reg_read(self.PC)==STOP,hex(u.reg_read(self.PC))
        finally:
            self.looping=False;self.current=None;self.activating=False;self.all_running=False
            self.gen_active=self.path_active=self.refill_active=self.enc_active=False
        path,enc=self.path_status(),self.enc_status()
        for t in path['combat']+enc['refill']['combat']:t['enemy_state']=C.c_int32(t['enemy_state']).value
        return dict(path=path,enc=enc,turn=self.turn_events[:],ability=self.ability_events[:],activated=self.activated())
    def __init__(self):
        super().__init__();self.looping=False;self.loop_visits={}

class Native(ActivateNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_turn_native.dylib'))
        self.loop_fn=lib.dr_end_turn_abilities
        self.loop_fn.argtypes=[C.POINTER(Path),C.POINTER(Generation),C.POINTER(U8),C.POINTER(TurnHooks),C.POINTER(GenerationHooks)];self.loop_fn.restype=None
    def run_loop(self):
        self.turn_events=[];self.ability_events=[];self.match_events=[];self.token_events=[];self.path_events=[];self.gen_events=[]
        self.all_events=[];self.enc_events=[];self.refill_events=[];self.motion_events=[]
        self.loop_fn(C.byref(self.path_state),C.byref(self.gen),self.flags_254,C.byref(self.activate_hooks),C.byref(self.gen_hooks))
        return dict(path=self.path_status(),enc=self.enc_status(),turn=self.turn_events[:],ability=self.ability_events[:],activated=list(self.flags_254))

def main():
    old,new=Original(),Native();rng=random.Random(0x13AF2);count=0;stats=dict(abilities=0,cripples=0,resurrections=0,mimics=0)
    def compare(c):
        nonlocal count
        a,b=old.run_loop(),new.run_loop()
        if a!=b:
            (HERE/'turn_abilities_failure.json').write_text(json.dumps(dict(case=c,original=a,native=b),indent=2))
            raise AssertionError('turn_abilities_failure.json')
        count+=1;stats['abilities']+=len(a['ability']);stats['cripples']+=sum(1 for e in a['turn'] if e[0]=='achievement' and e[1]==53)
        stats['resurrections']+=sum(1 for e in a['turn'] if e[0]=='label' and e[2]==38);stats['mimics']+=sum(1 for e in a['turn'] if e[0]=='label' and e[2]==20)
    for n in range(160):
        c,_=scenario(rng);c['path_state']['turn']=rng.choice([1,50,100,rng.randrange(1,2000)]);c['match']['spawn_enabled_14ae0']=rng.randrange(5)
        c['game']['race']=rng.choice([7,7,rng.randrange(10)]);c['activated']=[int(rng.random()<.5) for _ in range(36)]
        for i,t in enumerate(c['board']):
            if t['type']==1:t['enemy']=rng.choice([0,0,3,10,17,19,28,32,32,rng.randrange(0,35)])
            t['enemy_state']=rng.choice([0,1,1,2,5,rng.randrange(-2,9)]);c['combat'][i]['flag25e']=rng.randrange(2)
            c['combat'][i]['health']=rng.randrange(-1,15);c['combat'][i]['defence']=rng.randrange(0,15);t['matched']=int(rng.random()<.1)
        old.load(c);new.load(c);compare(c)
        if n%4==0:compare(dict(again=n))   # second turn on the carried state
    assert all(v for v in stats.values()) and all(hex(a) in old.loop_visits for a in (0x13cda,0x13af2,0x13b04,0x13b26,0x13b34,0x13daa))
    report=dict(status='passed',comparisons=count,**stats,ranges=[[hex(a),hex(b)] for a,b in RANGES],stop=hex(STOP),
                original='Actual EndOfTurn ability segment with original ProcessCripples (+MatchTile) and ActivateAbility (+MimicDefence/Resurrect/GenerateStats/UpdateValues)',
                boundaries=['19 unrecovered ability functions recorded (TurnHooks.ability)','entry state at 0x13cda (R8=Game) set by the harness'],
                scope='Full shared board, combat, match state, tokens, generation extras and RNG; Tile+0x254',branch_visits=old.loop_visits)
    (HERE/'turn_abilities_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='branch_visits'}))

if __name__=='__main__':main()
