#!/usr/bin/env python3
"""Actual ProcessAttack phases 2..4 shared part [0x141c6,0x143ca) vs native.

Covers the two phase timers (MatchState shake fields at Game+0xbd90/+0xbd94),
the flare animation over the list at Game+0xbd80 (stride 0x70, count +0xbd8c),
the phase-2 exit and phase 3. When phase 3 finishes, the original calls
Game::DoCounterattack, which executes as original code with its AttackSkull and
MoveMatchedTiles on the full shared state (hooks of verify_counterattack.py);
native calls dr_do_counterattack. Quad::SetAlpha executes as original code on a
flare array placed in emulator memory; SimpleLabel/QueueSound are adapted.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_counterattack import Original as CounterOriginal, Native as CounterNative
from verify_attack_absorb import AttackDamage
from verify_attack_all import scenario
from verify_resources import Resource
from verify_stroke import HERE, I32, U8

ENTRY,END=0x141c6,0x143ca
COUNTER,COUNTER_END=0x11214,0x1133c
PHASE,DT,DAMAGE,ENEMY9=0xb8a8,0x4,0xbe84,0x1553c
TIMER_A,TIMER_B=0xbd90,0xbd94
PROGRESS,LABEL_Y,DAMAGE_ALPHA,POISON_ALPHA,COUNT,LIST,ALTERNATE=0xbd58,0xbd54,0xbd38,0x15520,0xbd8c,0xbd80,0xbfba
FLARES,STRIDE=0x1518000,0x70
QUAD2=0xb98c
LABELS={0xb9fc:0,0x151e4:1}
VERTEX_ALPHA=(0xf,0x23,0x37,0x4b)

class AnimState(C.Structure):
    _fields_=[('label_progress',C.c_float),('label_y',C.c_float),('damage_label_alpha',C.c_float),('poison_label_alpha',C.c_float),
              ('flare_count',I32),('counterattack',U8)]
class AnimEvent(C.Structure):
    _fields_=[(k,I32) for k in ('kind','a','b','c')]
ANIM_EVENT=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(AnimEvent))
COUNTER_FN=C.CFUNCTYPE(None,C.c_void_p)
class AnimHooks(C.Structure):
    _fields_=[('context',C.c_void_p),('event',ANIM_EVENT),('counterattack',COUNTER_FN)]

def fbits(x):return struct.unpack('<I',struct.pack('<f',x))[0]
def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]

class Original(CounterOriginal):
    ranges,entry,anim_end=[(ENTRY,END),(COUNTER,COUNTER_END)],ENTRY,END
    def __init__(self):
        super().__init__();self.stop_at=self.anim_end;text=(HERE.parent/'armv7-disassembly.txt').read_text();self.anim_calls={}
        for symbol,name in [('__ZN11SimpleLabel9SetNumberEi','number'),('__ZN11SimpleLabel11SetPositionERK8GLfloat2','position'),
                            ('__ZN4Game10QueueSoundE5Sound','sound'),('__ZN4Quad8SetAlphaEh','alpha')]:
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol
            self.anim_calls[int(m[1],16)]=name
    def hook(self,u,address,size,context):
        if self.all_running and self.mode is None:
            lr=u.reg_read(self.LR)&~1;name=self.anim_calls.get(address)
            # A call's return address is after the bl, so the last call returns to END itself.
            if address==COUNTER and ENTRY<lr<=self.anim_end:self.all_events.append(['C'])
            if name and ENTRY<lr<=self.anim_end:
                r=[u.reg_read(v) for v in self.regs]
                if name=='alpha':
                    if r[0]==self.GAME+QUAD2:self.all_events.append(['N',6,2,r[1]&0xff,0])
                    else:
                        i,rest=divmod(r[0]-FLARES,STRIDE);assert rest==0;self.all_events.append(['N',4,i,r[1]&0xff,0])
                    return super().hook(u,address,size,context)   # original store runs
                if name=='sound':e=['N',1,r[1],0,0]
                elif name=='number':e=['N',2,LABELS[r[0]-self.GAME],C.c_int32(r[1]).value,0]
                else:x,y=struct.unpack('<ii',u.mem_read(r[1],8));e=['N',3,LABELS[r[0]-self.GAME],x,y]
                self.all_events.append(e);u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def load(self,c):
        super().load(c);w=lambda o,v:self.write(self.GAME+o,v)
        for o,k in ((PHASE,'phase'),(DAMAGE,'damage'),(ENEMY9,'enemy9'),(COUNT,'count')):w(o,c[k])
        for o,k in ((TIMER_A,'timer_a'),(TIMER_B,'timer_b'),(PROGRESS,'progress'),(LABEL_Y,'label_y'),(DAMAGE_ALPHA,'damage_alpha'),(POISON_ALPHA,'poison_alpha')):w(o,fbits(c[k]))
        w(LIST,FLARES);self.u.mem_write(self.GAME+ALTERNATE,bytes([c['alternate']]))
        self.u.mem_write(FLARES,bytes([0x5a])*(STRIDE*72))
        for v in VERTEX_ALPHA:self.u.mem_write(self.GAME+QUAD2+v,bytes([0x5a]))
        self.flare_slots=c['count']
    def anim_state(self):
        rd=lambda o:self.read(self.GAME+o)&0xffffffff
        flares=[]
        for i in range(self.flare_slots):
            base=FLARES+STRIDE*i;alpha=self.u.mem_read(base+0xf,1)[0]
            assert all(self.u.mem_read(base+v,1)[0]==alpha for v in VERTEX_ALPHA)
            flares.append([alpha,struct.unpack('<I',self.u.mem_read(base+0x64,4))[0],struct.unpack('<I',self.u.mem_read(base+0x68,4))[0]])
        return dict(phase=C.c_int32(rd(PHASE)).value,timers=[rd(TIMER_A),rd(TIMER_B)],progress=rd(PROGRESS),label_y=rd(LABEL_Y),
                    alphas=[rd(DAMAGE_ALPHA),rd(POISON_ALPHA)],count=C.c_int32(rd(COUNT)).value,flares=flares,quad2=self.u.mem_read(self.GAME+QUAD2+0xf,1)[0])
    def frame(self,dt):
        self.write(self.GAME+DT,fbits(dt));result=self.run_original();result['anim']=self.anim_state();return result

class Native(CounterNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_attack_shield_native.dylib'))
        self.flare_fn=lib.dr_process_attack_flares
        self.flare_fn.argtypes=[C.POINTER(AttackDamage),C.POINTER(AnimState),C.c_float,C.POINTER(AnimHooks)];self.flare_fn.restype=None
        def event(_,p):
            e=p.contents
            if e.kind!=5:self.all_events.append(['N',e.kind,e.a,e.b,e.c])   # flare+0x64/+0x68 are plain stores: compared via memory
            if e.kind==4:self.flare_mirror[e.a][0]=e.b
            elif e.kind==5:self.flare_mirror[e.a][1]=self.flare_mirror[e.a][2]=e.b&0xffffffff
            elif e.kind==6:self.quad2=e.b
        def counter(_):
            self.all_events.append(['C']);self.counter_fn(C.byref(self.path_state),C.addressof(self.all_hooks))
        self.anim_cb=(ANIM_EVENT(event),COUNTER_FN(counter));self.anim_hooks=AnimHooks(None,*self.anim_cb)
    def load(self,c):
        super().load(c)
        self.damage=AttackDamage(C.pointer(self.r),c['phase'],c['damage'],c['enemy9'])
        self.m.shake_progress_bd90=fbits(c['timer_a']);self.m.shake_scale_bd94=fbits(c['timer_b'])
        self.anim=AnimState(c['progress'],c['label_y'],c['damage_alpha'],c['poison_alpha'],c['count'],c['alternate'])
        self.flare_mirror=[[0x5a,0x5a5a5a5a,0x5a5a5a5a] for _ in range(c['count'])];self.quad2=0x5a
    def anim_state(self):
        a=self.anim
        return dict(phase=self.damage.phase,timers=[self.m.shake_progress_bd90,self.m.shake_scale_bd94],progress=fbits(a.label_progress),
                    label_y=fbits(a.label_y),alphas=[fbits(a.damage_label_alpha),fbits(a.poison_label_alpha)],count=a.flare_count,
                    flares=[list(f) for f in self.flare_mirror],quad2=self.quad2)
    def frame(self,dt):
        self.all_events=[];self.enc_events=[];self.gen_events=[];self.refill_events=[];self.path_events=[]
        self.match_events=[];self.token_events=[];self.motion_events=[]
        self.flare_fn(C.byref(self.damage),C.byref(self.anim),dt,C.byref(self.anim_hooks))
        return dict(path=self.path_status(),enc=self.enc_status(),all=self.all_events[:],anim=self.anim_state())

def case(rng,**k):
    c,_=scenario(rng)
    c.update(phase=rng.choice([2,3,4]),damage=rng.randrange(0,40),enemy9=rng.randrange(0,8),count=rng.randrange(0,20),
             timer_a=f32(rng.uniform(0,2)),timer_b=f32(rng.choice([1.0,rng.uniform(-0.2,1.0)])),progress=f32(rng.uniform(0,1.2)),
             label_y=f32(rng.uniform(0,1)),damage_alpha=f32(rng.uniform(0,1)),poison_alpha=f32(rng.uniform(0,1)),alternate=rng.randrange(2))
    c.update(k);return c

def main():
    old,new=Original(),Native();rng=random.Random(0x141C6);counts={'boundary':0,'random':0,'frames':0};transitions={};counters=0
    def compare(c,dt,group):
        nonlocal counters
        before=c.get('phase')
        a,b=old.frame(dt),new.frame(dt)
        if a!=b:
            (HERE/'attack_flare_phases_failure.json').write_text(json.dumps(dict(case=c,dt=dt,original=a,native=b),indent=2))
            raise AssertionError('attack_flare_phases_failure.json')
        counts[group]+=1;counters+=a['all'].count(['C'])
        return a
    dts=[0.0,f32(1/60),f32(1/30),f32(0.1),f32(0.5/4.5),f32(1/3),0.5]
    for phase in (1,2,3,4,5):
     for timer_b in (1.0,0.5,f32(0.5+4.5/60),0.01,0.0,-0.1):
      for alternate in (0,1):
       for dt in dts:
        c=case(rng,phase=phase,timer_b=timer_b,alternate=alternate,progress=rng.choice([0.0,0.99,1.0]));old.load(c);new.load(c);compare(c,dt,'boundary')
    for _ in range(300):
        c=case(rng);old.load(c);new.load(c);compare(c,f32(rng.uniform(0,0.2)),'random')
    # Whole animations from phase 2 (timers as left by phase 1) until phase 7 or 4.
    for game in range(24):
        c=case(rng,phase=2,timer_a=0.0,timer_b=1.0,progress=0.0,alternate=game%2,count=rng.randrange(0,30))
        old.load(c);new.load(c)
        for _ in range(400):
            a=compare(c,f32(rng.choice([1/60,1/30,rng.uniform(0,0.05)])),'frames')
            transitions[a['anim']['phase']]=transitions.get(a['anim']['phase'],0)+1
            if a['anim']['phase'] in (4,7):break
        assert a['anim']['phase']==(7 if game%2 else 4),a['anim']['phase']
    assert counters
    report=dict(status='passed',comparisons=sum(counts.values()),by_group=counts,counterattacks=counters,
                range=dict(start=hex(ENTRY),end_exclusive=hex(END)),
                original='Actual ProcessAttack phases 2..4 shared part; Quad::SetAlpha and the whole DoCounterattack chain execute as original code',
                boundaries=['SimpleLabel::SetNumber/SetPosition and QueueSound adapted','flare list placed by the harness at a fixed address (AddFlare not recovered)',
                            'NEON flush-to-zero for subnormal timer values not modelled; dt finite >= 0','phase 4 work after 0x143ca is the next unit'],
                scope='Phase, both timers, label progress/position/alphas, flare count and flare quads, quad 0xb98c, and the full counterattack state',
                branch_visits={k:v for k,v in old.all_visits.items() if ENTRY<=int(k,16)<END})
    (HERE/'attack_flare_phases_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='branch_visits'}))

if __name__=='__main__':main()
