#!/usr/bin/env python3
"""Actual ProcessAttack phases 2..6 animation [0x141c6,0x146ce) vs native.

Runs contiguously from 0x141c6 so every phase of a frame flows as in the game:
shared timers/flares (T020-K), phase 4 (T020-L) and the phase 5/6 label motion
[0x1457c,0x146ce) recovered here. The original stops at 0x146ce (motion
completed) or 0x14ae4 (otherwise); native calls dr_process_attack_flares,
dr_process_attack_phase4 and dr_process_attack_label_motion, whose result
selects the same exit. Interpolate (both overloads) and Sqr execute as original
code; the platform powf stub is answered with the host C library powf, which
native code also uses. Built on verify_attack_phase4.py.
"""
import ctypes as C
import ctypes.util
import json
import random
import struct
from verify_attack_phase4 import Original as P4Original, Native as P4Native, AnimState, p4case, MOTION
from verify_attack_flare_phases import fbits, f32, ENTRY, COUNTER, COUNTER_END, HERE
from verify_attack_absorb import AttackDamage
from verify_attack_flare_phases import AnimHooks

END,SKIP=0x146ce,0x14ae4
POWF_STUB=0x194f40
LIBM=C.CDLL(ctypes.util.find_library('m'))
LIBM.powf.argtypes=[C.c_float,C.c_float];LIBM.powf.restype=C.c_float

class Original(P4Original):
    ranges,anim_end=[(ENTRY,END),(COUNTER,COUNTER_END)],END
    extra_stops=(SKIP,)
    def __init__(self):super().__init__();self.motion_visits={}
    def hook(self,u,address,size,context):
        if self.all_running and 0x1457c<=address<END:self.motion_visits[hex(address)]=self.motion_visits.get(hex(address),0)+1
        if self.all_running and self.mode is None and address==POWF_STUB:
            r0,r1=(u.reg_read(v) for v in self.regs[:2])
            x,y=struct.unpack('<ff',struct.pack('<II',r0,r1))
            u.reg_write(self.regs[0],fbits(LIBM.powf(x,y)));u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def frame(self,dt):
        result=super().frame(dt);result['exit']=self.u.reg_read(self.PC);return result

class Native(P4Native):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_attack_shield_native.dylib'))
        self.motion_fn=lib.dr_process_attack_label_motion
        self.motion_fn.argtypes=[C.POINTER(AttackDamage),C.POINTER(AnimState),C.c_float,C.POINTER(AnimHooks)];self.motion_fn.restype=C.c_bool
    def frame(self,dt):
        self.all_events=[];self.enc_events=[];self.gen_events=[];self.refill_events=[];self.path_events=[]
        self.match_events=[];self.token_events=[];self.motion_events=[]
        done=self.flare_fn(C.byref(self.damage),C.byref(self.anim),dt,C.byref(self.anim_hooks))
        self.phase4_fn(C.byref(self.damage),C.byref(self.anim),done,dt,C.byref(self.anim_hooks))
        finished=self.motion_fn(C.byref(self.damage),C.byref(self.anim),dt,C.byref(self.anim_hooks))
        return dict(path=self.path_status(),enc=self.enc_status(),all=self.all_events[:],anim=self.anim_state(),exit=END if finished else SKIP)

def mcase(rng,**k):
    c=p4case(rng,phase=rng.choice([5,6]))
    c.update(bd6c=f32(rng.uniform(0,1.1)),bd70=f32(rng.uniform(0,10)),bd7c=f32(rng.uniform(0.4,1.0)),
             bd64=f32(rng.uniform(0,1)),bd68=f32(rng.uniform(0,1)),bd5c=f32(rng.uniform(0,1)),bd60=f32(rng.uniform(0,1.3)),
             bd74=f32(rng.uniform(0,1)),bd78=f32(rng.uniform(0,1)))
    c.update(k);return c

def main():
    old,new=Original(),Native();rng=random.Random(0x1457C);counts={'boundary':0,'random':0,'frames':0};finished=0
    def compare(c,dt,group):
        nonlocal finished
        a,b=old.frame(dt),new.frame(dt)
        if a!=b:
            (HERE/'attack_label_motion_failure.json').write_text(json.dumps(dict(case=c,dt=dt,original=a,native=b),indent=2))
            raise AssertionError('attack_label_motion_failure.json')
        counts[group]+=1;finished+=a['exit']==END;return a
    for phase in (4,5,6,7):
     for progress in (0.0,0.5,0.99,1.0,1.2):
      for speed in (0.0,1.0,f32(1/60),5.0):
       for dt in (0.0,f32(1/60),f32(1/30),0.25):
        c=mcase(rng,phase=phase,bd6c=progress,bd70=speed);old.load(c);new.load(c);compare(c,dt,'boundary')
    for _ in range(400):
        c=mcase(rng,phase=rng.choice([2,3,4,5,5,6,6]));old.load(c);new.load(c);compare(c,f32(rng.uniform(0,0.2)),'random')
    # Phase 4 entry through the whole phase 5/6 motion, as phase 4 leaves it (bd6c=0, bd70=1).
    for game in range(24):
        c=mcase(rng,phase=4,progress=f32(rng.uniform(0.5,1.0)),timer_b=f32(rng.uniform(-0.1,0.05)),bd6c=0.0,bd70=1.0)
        c['preview']['armour_current']=[0,3][game%2];old.load(c);new.load(c)
        for _ in range(400):
            a=compare(c,f32(rng.choice([1/60,1/30,rng.uniform(0,0.05)])),'frames')
            if a['exit']==END:break
        assert a['exit']==END and a['anim']['phase'] in (5,6)
    assert finished and all(hex(x) in old.motion_visits for x in (0x145da,0x145d4,0x1463e,0x1464c,0x146c6))
    report=dict(status='passed',comparisons=sum(counts.values()),by_group=counts,motions_completed=finished,
                range=dict(start=hex(0x1457c),end_exclusive=hex(END),run_contiguously_from=hex(ENTRY),exits=[hex(END),hex(SKIP)]),
                original='Actual ProcessAttack phases 2..6 animation incl. Interpolate (vector and scalar) and Sqr; DoCounterattack/Rand/SetAlpha as before',
                boundaries=['platform powf answered by the host C library powf (native uses the same)','SimpleLabel calls, HelpMenu, QueueSound adapted',
                            'dt finite >= 0; NEON flush-to-zero not modelled','completion block at 0x146ce (phase 5 -> 6 setup) is the next unit'],
                scope='Phase, timers, label motion parameters and alphas, label positions, RNG and the full shared state',
                branch_visits=old.motion_visits)
    (HERE/'attack_label_motion_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='branch_visits'}))

if __name__=='__main__':main()
