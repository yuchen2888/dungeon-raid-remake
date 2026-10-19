#!/usr/bin/env python3
"""Actual ProcessAttack phases 2..4 [0x141c6,0x1457c) incl. phase 4 vs native.

The original runs contiguously, so its "flares done this frame" stack flag
([sp,#0x2c]) flows from the shared part into phase 4 exactly as in the game;
native calls dr_process_attack_flares then dr_process_attack_phase4 with its
returned flag. Rand(float) runs as original code on the shared RNG streams.
Quad::SetAlpha runs as original code; SimpleLabel calls, HelpMenu::Initialise
and QueueSound are adapted. Built on verify_attack_flare_phases.py (full
shared state, real DoCounterattack chain).
"""
import ctypes as C
import json
import random
import re
import struct
from verify_attack_flare_phases import (Original as FlareOriginal, Native as FlareNative, AnimEvent, ANIM_EVENT, COUNTER_FN, AnimHooks,
    case, fbits, f32, ENTRY, COUNTER, COUNTER_END, LABELS, VERTEX_ALPHA, HERE)
from verify_attack_absorb import AttackDamage
from verify_stroke import I32, U8

END=0x1457c
QUAD1=0xb8ac
MOTION=dict(bd30=0xbd30,bd34=0xbd34,bd5c=0xbd5c,bd60=0xbd60,bd64=0xbd64,bd68=0xbd68,bd6c=0xbd6c,bd70=0xbd70,bd74=0xbd74,bd78=0xbd78,bd7c=0xbd7c)
RAND_FLOAT=0x1b7a8

class AnimState(C.Structure):
    _fields_=[('label_progress',C.c_float),('label_y',C.c_float),('damage_label_alpha',C.c_float),('poison_label_alpha',C.c_float),
              ('flare_count',I32),('counterattack',U8)]+[(k,C.c_float) for k in MOTION]

class Original(FlareOriginal):
    ranges,anim_end=[(ENTRY,END),(COUNTER,COUNTER_END)],END
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.p4_calls={}
        for symbol,name in [('__ZN11SimpleLabel8SetAlphaEh','label_alpha'),('__ZN8HelpMenu10InitialiseEffff8HelpType','help'),('__ZN4Quad8SetAlphaEh','alpha')]:
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol
            self.p4_calls[int(m[1],16)]=name
        self.phase4_visits={}
    def hook(self,u,address,size,context):
        if self.all_running and 0x143ca<=address<END:self.phase4_visits[hex(address)]=self.phase4_visits.get(hex(address),0)+1
        if self.all_running and self.mode is None:
            lr=u.reg_read(self.LR)&~1;name=self.p4_calls.get(address);r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value
            if address==RAND_FLOAT and ENTRY<lr<=END:
                self.all_events.append(['N',9,s(r[0]),s(r[1]),r[2]]);return super().hook(u,address,size,context)   # original Rand runs
            if name and ENTRY<lr<=END:
                if name=='alpha' and r[0]==self.GAME+QUAD1:
                    self.all_events.append(['N',6,1,r[1]&0xff,0]);return super(FlareOriginal,self).hook(u,address,size,context)   # original store runs
                if name=='label_alpha':
                    self.all_events.append(['N',7,LABELS[r[0]-self.GAME],r[1]&0xff,0]);u.reg_write(self.PC,u.reg_read(self.LR));return
                if name=='help':
                    sp=u.reg_read(self.SP);assert r[0]==self.GAME+0x10298 and r[3]==0 and self.read(sp)==0
                    self.all_events.append(['N',8,s(r[1]),s(r[2]),self.read(sp+4)]);u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def load(self,c):
        super().load(c)
        for k,o in MOTION.items():self.write(self.GAME+o,fbits(c[k]))
        for v in VERTEX_ALPHA:self.u.mem_write(self.GAME+QUAD1+v,bytes([0x5a]))
    def anim_state(self):
        d=super().anim_state();d.update({k:self.read(self.GAME+o)&0xffffffff for k,o in MOTION.items()})
        d['quad1']=self.u.mem_read(self.GAME+QUAD1+0xf,1)[0]
        assert all(self.u.mem_read(self.GAME+QUAD1+v,1)[0]==d['quad1'] for v in VERTEX_ALPHA)
        return d

class Native(FlareNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_attack_shield_native.dylib'))
        self.flare_fn.argtypes=[C.POINTER(AttackDamage),C.POINTER(AnimState),C.c_float,C.POINTER(AnimHooks)];self.flare_fn.restype=C.c_bool
        self.phase4_fn=lib.dr_process_attack_phase4
        self.phase4_fn.argtypes=[C.POINTER(AttackDamage),C.POINTER(AnimState),C.c_bool,C.c_float,C.POINTER(AnimHooks)];self.phase4_fn.restype=None
        base_event=self.anim_cb[0]
        def event(ctx,p):
            e=p.contents
            if e.kind==6 and e.a==1:self.quad1=e.b;self.all_events.append(['N',6,1,e.b,0]);return
            base_event(ctx,p)
        self.anim_cb=(ANIM_EVENT(event),self.anim_cb[1]);self.anim_hooks=AnimHooks(None,*self.anim_cb)
    def load(self,c):
        super().load(c)
        self.anim=AnimState(c['progress'],c['label_y'],c['damage_alpha'],c['poison_alpha'],c['count'],c['alternate'],*[c[k] for k in MOTION])
        self.quad1=0x5a
    def anim_state(self):
        d=super().anim_state();d.update({k:fbits(getattr(self.anim,k)) for k in MOTION});d['quad1']=self.quad1;return d
    def frame(self,dt):
        self.all_events=[];self.enc_events=[];self.gen_events=[];self.refill_events=[];self.path_events=[]
        self.match_events=[];self.token_events=[];self.motion_events=[]
        done=self.flare_fn(C.byref(self.damage),C.byref(self.anim),dt,C.byref(self.anim_hooks))
        self.phase4_fn(C.byref(self.damage),C.byref(self.anim),done,dt,C.byref(self.anim_hooks))
        return dict(path=self.path_status(),enc=self.enc_status(),all=self.all_events[:],anim=self.anim_state())

def p4case(rng,**k):
    c=case(rng);c['preview']['armour_current']=rng.choice([-1,0,0,1,5,rng.randrange(0,30)])
    for key in MOTION:c[key]=f32(rng.uniform(-1,2))
    c.update(k);return c

def main():
    old,new=Original(),Native();rng=random.Random(0x143CA);counts={'boundary':0,'random':0,'frames':0};entered={5:0,6:0};randoms=0
    def compare(c,dt,group):
        nonlocal randoms
        a,b=old.frame(dt),new.frame(dt)
        if a!=b:
            (HERE/'attack_phase4_failure.json').write_text(json.dumps(dict(case=c,dt=dt,original=a,native=b),indent=2))
            raise AssertionError('attack_phase4_failure.json')
        counts[group]+=1;randoms+=sum(1 for e in a['all'] if e[:2]==['N',9]);return a
    for armour in (-1,0,1,7):
     for timer_b in (0.6,f32(0.5+4.5/60),0.02,-0.1):
      for progress in (0.0,f32(1-8/60),0.95,1.0,1.5):
       for dt in (0.0,f32(1/60),f32(1/30),0.25):
        c=p4case(rng,phase=4,timer_b=timer_b,progress=progress);c['preview']['armour_current']=armour
        old.load(c);new.load(c);a=compare(c,dt,'boundary')
        if a['anim']['phase'] in entered:entered[a['anim']['phase']]+=1
    for _ in range(300):
        c=p4case(rng,phase=rng.choice([2,3,4,4,4,5]));old.load(c);new.load(c);compare(c,f32(rng.uniform(0,0.2)),'random')
    for game in range(24):
        c=p4case(rng,phase=2,timer_a=0.0,timer_b=1.0,progress=0.0,alternate=0,count=rng.randrange(0,30))
        c['preview']['armour_current']=[0,3][game%2];old.load(c);new.load(c)
        for _ in range(400):
            a=compare(c,f32(rng.choice([1/60,1/30,rng.uniform(0,0.05)])),'frames')
            if a['anim']['phase'] in (5,6):entered[a['anim']['phase']]+=1;break
        assert a['anim']['phase']==(5 if game%2 else 6),a['anim']['phase']
    assert entered[5] and entered[6] and randoms
    report=dict(status='passed',comparisons=sum(counts.values()),by_group=counts,entered_phase=entered,random_calls=randoms,
                range=dict(start=hex(0x143ca),end_exclusive=hex(END),run_contiguously_from=hex(ENTRY)),
                original='Actual ProcessAttack phases 2..4 incl. phase 4, Rand(float) on stream 0 and Quad::SetAlpha; DoCounterattack chain when reached',
                boundaries=['SimpleLabel::SetAlpha/SetNumber/SetPosition, HelpMenu::Initialise and QueueSound adapted',
                            'bd30..bd7c are phase 5/6 motion parameters named by offset','dt finite >= 0; NEON flush-to-zero not modelled'],
                scope='Phase, timers, label progress/alphas, motion parameters, RNG streams, quads 0xb8ac/0xb98c and flares on the full shared state',
                branch_visits=old.phase4_visits)
    (HERE/'attack_phase4_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='branch_visits'}))

if __name__=='__main__':main()
