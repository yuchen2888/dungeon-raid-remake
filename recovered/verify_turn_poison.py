#!/usr/bin/env python3
"""Actual EndOfTurn loop B (poisoned enemies) [0x13a1c,0x13af0) + loop head
[0x13d88,0x13daa) vs native dr_end_turn_poison_enemies (recovered_turn).

The original runs from 0x13a1c (it zeroes [sp,#0x24] itself; R8=Game) until
0x13cda, where the Tile+0x254 reset starts. Tile::GetPoison runs as original
code; MatchTile runs as the original function with the existing match/token
hooks, native wires match_tile to dr_match_tile. Own UpdateText /
AddSimpleLabel / AddParticles / QueueAchievement calls are recorded in
canonical form.
"""
import ctypes as C
import json
import random
import re
from verify_attack_all import Original as AllOriginal, Native as AllNative, scenario
from verify_turn_burn import Native as BurnNative, TurnHooks, EVENT, MATCH, TILES, STRIDE, RESTING
from verify_path import Path
from verify_stroke import HERE

LOOP,LOOP_END,HEAD,HEAD_END,STOP=0x13a1c,0x13af2,0x13d88,0x13daa,0x13cda
SYMBOLS={'__ZN4Tile10UpdateTextEbbb':'text','__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif':'label',
         '__ZN4Game16QueueAchievementE11Achievementf':'achievement','__ZN4Game12AddParticlesEP4Tile12ParticleType':'particles'}

class Original(AllOriginal):
    ranges,entry,stop_at=[(LOOP,LOOP_END),(HEAD,HEAD_END)],LOOP,STOP
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.calls={};self.poison_visits={};self.recording=False
        for symbol,name in SYMBOLS.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol;self.calls[int(m[1],16)]=name
    def tile_of(self,address,offset=0):
        i,rest=divmod(address-self.GAME-TILES-offset,STRIDE);assert rest==0 and 0<=i<36,hex(address);return i
    def hook(self,u,address,size,context):
        if self.recording and getattr(self,'mode',None) is None:
            if self.in_range(address):self.poison_visits[hex(address)]=self.poison_visits.get(hex(address),0)+1
            lr=u.reg_read(self.LR)&~1;name=self.calls.get(address)
            if name and self.in_range(lr):
                r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value;sp=u.reg_read(self.SP)
                if name=='text':e=['text',self.tile_of(r[0]),r[1]&0xff,r[2]&0xff,r[3]&0xff]
                elif name=='label':
                    o=r[2]-self.GAME-RESTING;assert o%8==0 and 0<=o//8<36
                    e=['label_rest',o//8,r[1],s(r[3]),s(self.read(sp)),s(self.read(sp+4))]
                elif name=='achievement':e=['achievement',r[1],s(r[2])]
                else:e=['particles',self.tile_of(r[1]),r[2]]
                self.turn_events.append(e);u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def poison(self):
        self.turn_events=[];self.recording=True
        try:result=self.run_original()
        finally:self.recording=False
        return dict(**result,turn=self.turn_events[:])

class Native(BurnNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_turn_native.dylib'))
        self.poison_fn=lib.dr_end_turn_poison_enemies;self.poison_fn.argtypes=[C.POINTER(Path),C.POINTER(TurnHooks)];self.poison_fn.restype=None
    def poison(self):
        self.reset();self.poison_fn(C.byref(self.path_state),C.byref(self.turn_hooks))
        return dict(path=self.path_status(),enc=self.enc_status(),all=self.all_events[:],turn=self.turn_events[:])

def poison_case(rng):
    c,_=scenario(rng);c['game']['race']=rng.choice([0,1,1,rng.randrange(10)])
    for i,t in enumerate(c['board']):
        if rng.random()<.6:
            cur=rng.choice([0,1,2,5,rng.randrange(1,30),-3]);nxt=rng.choice([0,0,2,rng.randrange(0,9)])
            c['combat'][i]['poison']=[cur,nxt,rng.choice([0,0,1,4]),rng.randrange(2),rng.randrange(2),rng.randrange(0,2**32)]
            c['combat'][i]['health']=rng.choice([1,2,5,rng.randrange(-2,40),2**31-1])
    return c

def main():
    old,new=Original(),Native();rng=random.Random(0x13A1C);count=0;matched=survived=0
    for _ in range(240):
        c=poison_case(rng);old.load(c);new.load(c)
        a,b=old.poison(),new.poison()
        if a!=b:
            (HERE/'turn_poison_failure.json').write_text(json.dumps(dict(case=c,original=a,native=b),indent=2))
            raise AssertionError('turn_poison_failure.json')
        count+=1;survived+=sum(1 for e in a['turn'] if e[0]=='particles');matched+=sum(1 for e in a['turn'] if e[0]=='achievement')
    assert survived and matched and all(hex(x) in old.poison_visits for x in (0x13a2a,0x13a5c,0x13a8e,0x13ab2,0x13ac0,0x13ae4,0x13d88))
    report=dict(status='passed',comparisons=count,survived_labels=survived,race1_achievements=matched,
                ranges=[[hex(LOOP),hex(LOOP_END)],[hex(HEAD),hex(HEAD_END)]],stop=hex(STOP),
                original='Actual EndOfTurn poisoned-enemy loop with original Tile::GetPoison and MatchTile (+tokens/rewards)',
                boundaries=['own UpdateText/AddSimpleLabel/AddParticles/QueueAchievement adapted',
                            'entry state at 0x13a1c (R8=Game) set by the harness; the loop zeroes its own column counter'],
                scope='Full shared board incl. per-tile poison queues and health, combat, match state, tokens and RNG',branch_visits=old.poison_visits)
    (HERE/'turn_poison_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='branch_visits'}))

if __name__=='__main__':main()
