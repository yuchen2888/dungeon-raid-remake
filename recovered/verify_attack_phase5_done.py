#!/usr/bin/env python3
"""Actual ProcessAttack phases 2..6 animation incl. the completion block
[0x146ce,0x14790) vs native.

Runs the original contiguously from 0x141c6 and stops at 0x14790 (phase 5
completed: absorption follows), 0x14a14 (phase 6 completed: health damage
follows) or 0x14ae4 (otherwise). Native: flares, phase4, label motion, then
dr_process_attack_phase5_done when phase 5 completed. Rand(float) runs as
original code; AddSimpleLabel and HelpMenu from the block are adapted.
Built on verify_attack_label_motion.py.
"""
import ctypes as C
import json
import random
import re
from verify_attack_label_motion import Original as MotionOriginal, Native as MotionNative, mcase, SKIP
from verify_attack_flare_phases import f32, ENTRY, COUNTER, COUNTER_END, HERE, AnimHooks
from verify_attack_phase4 import AnimState, RAND_FLOAT
from verify_attack_absorb import AttackDamage

BLOCK,ABSORB,HEALTH=0x146ce,0x14790,0x14a14

class Original(MotionOriginal):
    ranges,anim_end=[(ENTRY,ABSORB),(COUNTER,COUNTER_END)],ABSORB
    extra_stops=(SKIP,HEALTH)
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.block_calls={};self.block_visits={}
        for symbol,name in [('__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif','label'),('__ZN8HelpMenu10InitialiseEffff8HelpType','help')]:
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol
            self.block_calls[int(m[1],16)]=name
    def hook(self,u,address,size,context):
        if self.all_running and BLOCK<=address<ABSORB:self.block_visits[hex(address)]=self.block_visits.get(hex(address),0)+1
        if self.all_running and self.mode is None:
            lr=u.reg_read(self.LR)&~1
            if BLOCK<lr<=ABSORB:
                r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value;sp=u.reg_read(self.SP)
                if address==RAND_FLOAT:
                    self.all_events.append(['N',9,s(r[0]),s(r[1]),r[2]]);return super().hook(u,address,size,context)   # original Rand runs
                name=self.block_calls.get(address)
                if name=='label':
                    assert r[0]==self.GAME and r[2]==self.GAME+0xbd30 and self.read(sp+4)==0x3f000000
                    self.all_events.append(['N',10,r[1],s(r[3]),self.read(sp)]);u.reg_write(self.PC,u.reg_read(self.LR));return
                if name=='help':
                    assert r[0]==self.GAME+0x10298 and r[3]==0 and self.read(sp)==0x3dcccccd
                    self.all_events.append(['N',8,s(r[1]),s(r[2]),self.read(sp+4)]);u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)

class Native(MotionNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_attack_shield_native.dylib'))
        self.done_fn=lib.dr_process_attack_phase5_done
        self.done_fn.argtypes=[C.POINTER(AttackDamage),C.POINTER(AnimState),C.POINTER(AnimHooks)];self.done_fn.restype=None
    def frame(self,dt):
        self.all_events=[];self.enc_events=[];self.gen_events=[];self.refill_events=[];self.path_events=[]
        self.match_events=[];self.token_events=[];self.motion_events=[]
        done=self.flare_fn(C.byref(self.damage),C.byref(self.anim),dt,C.byref(self.anim_hooks))
        self.phase4_fn(C.byref(self.damage),C.byref(self.anim),done,dt,C.byref(self.anim_hooks))
        exit=SKIP
        if self.motion_fn(C.byref(self.damage),C.byref(self.anim),dt,C.byref(self.anim_hooks)):
            if self.damage.phase==5:self.done_fn(C.byref(self.damage),C.byref(self.anim),C.byref(self.anim_hooks));exit=ABSORB
            else:exit=HEALTH
        return dict(path=self.path_status(),enc=self.enc_status(),all=self.all_events[:],anim=self.anim_state(),exit=exit)

def main():
    old,new=Original(),Native();rng=random.Random(0x146CE);counts={'boundary':0,'random':0,'frames':0};exits={}
    def compare(c,dt,group):
        a,b=old.frame(dt),new.frame(dt)
        if a!=b:
            (HERE/'attack_phase5_done_failure.json').write_text(json.dumps(dict(case=c,dt=dt,original=a,native=b),indent=2))
            raise AssertionError('attack_phase5_done_failure.json')
        counts[group]+=1;exits[hex(a['exit'])]=exits.get(hex(a['exit']),0)+1;return a
    for phase in (5,6):
     for armour in (-1,0,3,40):
      for damage in (0,2,3,50):
       for dt in (f32(1/60),0.25):
        c=mcase(rng,phase=phase,bd6c=0.999,bd70=5.0,damage=damage);c['preview']['armour_current']=armour
        old.load(c);new.load(c);compare(c,dt,'boundary')
    for _ in range(300):
        c=mcase(rng,phase=rng.choice([4,5,5,6]),bd6c=f32(rng.uniform(0.8,1.1)));old.load(c);new.load(c);compare(c,f32(rng.uniform(0,0.2)),'random')
    # From phase 4 until the phase-5 motion completes (exit 0x14790) or phase 6 completes (0x14a14).
    for game in range(24):
        c=mcase(rng,phase=4,progress=f32(rng.uniform(0.5,1.0)),timer_b=f32(rng.uniform(-0.1,0.05)),bd6c=0.0,bd70=1.0,damage=rng.randrange(0,30))
        c['preview']['armour_current']=[0,rng.randrange(1,20)][game%2];old.load(c);new.load(c)
        for _ in range(400):
            a=compare(c,f32(rng.choice([1/60,1/30,rng.uniform(0,0.05)])),'frames')
            if a['exit']!=SKIP:break
        assert a['exit']==(ABSORB if game%2 else HEALTH),hex(a['exit'])
    assert exits.get(hex(ABSORB)) and exits.get(hex(HEALTH)) and exits.get(hex(SKIP))
    report=dict(status='passed',comparisons=sum(counts.values()),by_group=counts,exits=exits,
                range=dict(start=hex(BLOCK),end_exclusive=hex(ABSORB),run_contiguously_from=hex(ENTRY)),
                original='Actual ProcessAttack phases 2..6 animation incl. the phase-5 completion block and its Rand(float)',
                boundaries=['AddSimpleLabel (scale 0.5 asserted) and HelpMenu (0.1, type 17 asserted) adapted','host powf for the platform stub',
                            'absorption/health segments after the exits are covered by T020-B/C and the whole-function test'],
                scope='Phase, motion parameters, label alphas, RNG and the full shared state',branch_visits=old.block_visits)
    (HERE/'attack_phase5_done_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='branch_visits'}))

if __name__=='__main__':main()
