#!/usr/bin/env python3
"""Actual Game::Process damage-label segment [0x176fc,0x17cda) (with its branch block [0x17d74,0x17da4))
vs native dr_process_damage_labels (recovered_schedule), on the shared state of verify_attack_all.py.

The original segment runs from 0x176fc (R4=Game, as Game::Process sets it) until the ProcessAttack call
0x17cda or the epilogue 0x17da4 (CheckEndGame ended the game). Interpolate and Sqr run as original code;
the powf stub is answered by the host C library's powf (the function the native build calls). Recorded
and skipped (native: LabelHooks events): SimpleLabel::Process / Initialise / SetPosition / SetNumber /
SetAlpha, QueueSound, QueueAchievement, Interface::UpdateHealthBar and CheckEndGame (returns the case's
result). The label scale stores (SimpleLabel+0x33c, the str at 0x17874 / 0x17a76 / 0x17c7a) are recorded
by code hooks (a memory-write hook leaves Unicorn's IT state stale after a skipped conditional store). Each
case runs several frames on carried state.
"""
import ctypes as C
import ctypes.util
import json
import random
import re
import struct
import verify_original
from unicorn.arm_const import UC_ARM_REG_R4
from verify_input_gate import Original as GateOriginal, Native as GateNative
from verify_attack_all import scenario
from verify_release import Flights, Flight, FLIGHTS
from verify_selection import Point
from verify_stroke import HERE, I32, U8

ENTRY,ATTACK,EPILOGUE=0x176fc,0x17cda,0x17da4
POWF=0x194f40
LABELS=[0xbfc0,0x14afc,0x14e70]   # leech, flame, spike SimpleLabel
SCALE=0x33c
SCALE_STORES={0x17874:0,0x17a76:1,0x17c7a:2}
SYMBOLS={'__ZN11SimpleLabel7ProcessEf':'process','__ZN11SimpleLabel10InitialiseE15SimpleLabelTypeRK8GLfloat2if':'init',
         '__ZN11SimpleLabel11SetPositionERK8GLfloat2':'position','__ZN11SimpleLabel9SetNumberEi':'number',
         '__ZN11SimpleLabel8SetAlphaEh':'alpha','__ZN4Game10QueueSoundE5Sound':'sound',
         '__ZN4Game16QueueAchievementE11Achievementf':'achievement','__ZN9Interface15UpdateHealthBarER4Quadi':'health_bar',
         '__ZN4Game12CheckEndGameEv':'check_end'}
KINDS=dict(process=1,init=2,position=3,number=4,alpha=5,scale=6,health_bar=7,sound=8,achievement=9,check_end=10)
SEL_INTS=dict(current_damage=0xbe7c,current_leech=0xc318,current_flame_damage=0x14e54,current_spike_damage=0x151c8)
SEL_BYTES=dict(skull_counted=0xbe80,flame_label_moving=0x14e58,spike_label_moving=0x151cd)
LIBM=C.CDLL(ctypes.util.find_library('m'));LIBM.powf.restype=C.c_float;LIBM.powf.argtypes=[C.c_float,C.c_float]
class State(C.Structure):
    _fields_=[('selection',C.c_void_p),('resources',C.c_void_p),('flights',C.POINTER(Flights)),('active',C.POINTER(U8))]
class Event(C.Structure):_fields_=[(k,I32) for k in ('kind','label','a','b')]+[('x',C.c_float),('y',C.c_float)]
EVENT=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(Event))
CHECK=C.CFUNCTYPE(C.c_bool,C.c_void_p)
class Hooks(C.Structure):_fields_=[('context',C.c_void_p),('event',EVENT),('check_end_game',CHECK)]
def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
def fbits(u):return struct.unpack('<f',struct.pack('<I',u&0xffffffff))[0]

class Original(GateOriginal):
    def __init__(self):
        super().__init__();self.labelling=False;self.label_calls={};self.label_visits={}
        text=(HERE.parent/'armv7-disassembly.txt').read_text()
        for symbol,name in SYMBOLS.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol;self.label_calls[int(m[1],16)]=name
    def label(self,p):
        i=LABELS.index(p-self.GAME);return i
    def hook(self,u,address,size,context):
        if not self.labelling:return super().hook(u,address,size,context)
        if ENTRY<=address<ATTACK or 0x17d74<=address<0x17da4:self.label_visits[hex(address)]=self.label_visits.get(hex(address),0)+1
        if address==EPILOGUE:u.emu_stop();return   # CheckEndGame ended the game: Process returns
        if address in SCALE_STORES:   # str r0,[r3]: label scale (SimpleLabel+0x33c)
            assert u.reg_read(self.regs[3])==self.GAME+LABELS[SCALE_STORES[address]]+SCALE
            self.label_events.append([KINDS['scale'],SCALE_STORES[address],u.reg_read(self.regs[0]),0,0.0,0.0])
        lr=u.reg_read(self.LR);r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value
        if address==POWF:
            u.reg_write(self.regs[0],struct.unpack('<I',struct.pack('<f',LIBM.powf(fbits(r[0]),fbits(r[1]))))[0]);u.reg_write(self.PC,lr);return
        name=self.label_calls.get(address)
        if name is None:return super().hook(u,address,size,context)
        sp=u.reg_read(self.SP);e=None
        if name=='process':e=[self.label(r[0]),r[1] if r[1]<1<<31 else r[1]-(1<<32),0,0.0,0.0]
        elif name=='init':
            assert self.read(sp)==0x3f800000
            x,y=struct.unpack('<ff',u.mem_read(r[2],8));e=[self.label(r[0]),s(r[1]),s(r[3]),f32(x),f32(y)]
        elif name=='position':x,y=struct.unpack('<ff',u.mem_read(r[1],8));e=[self.label(r[0]),0,0,f32(x),f32(y)]
        elif name=='number':e=[self.label(r[0]),s(r[1]),0,0.0,0.0]
        elif name=='alpha':e=[self.label(r[0]),r[1]&0xff,0,0.0,0.0]
        elif name=='sound':assert r[0]==self.GAME;e=[-1,s(r[1]),0,0.0,0.0]
        elif name=='achievement':assert r[0]==self.GAME;e=[-1,s(r[1]),s(r[2]),0.0,0.0]
        elif name=='health_bar':assert r[0]==self.GAME+0x4cdc and r[1]==self.GAME+0x4d4c;e=[-1,s(r[2]),0,0.0,0.0]
        elif name=='check_end':
            assert r[0]==self.GAME;self.label_events.append([KINDS['check_end'],-1,0,0,0.0,0.0])
            u.reg_write(self.regs[0],self.case_end_game);u.reg_write(self.PC,lr);return
        self.label_events.append([KINDS[name],*e]);u.reg_write(self.PC,lr)
    def load(self,c):
        super().load(c);G=self.GAME;l=c['labels']
        for k,a in SEL_INTS.items():self.write(G+a,c['game'][k])
        for k,a in SEL_BYTES.items():self.u.mem_write(G+a,bytes([c['game'][k]]))
        for k,a in FLIGHTS.items():self.u.mem_write(G+a,struct.pack('<5f',*l['flights'][k]))
        for i,a in enumerate(LABELS):self.u.mem_write(G+a,bytes([l['active'][i]]));self.u.mem_write(G+a+SCALE,struct.pack('<f',1.0))
        self.u.mem_write(G+0x14,struct.pack('<ff',*l['touch']))
    def frame(self,dt,end_game):
        G=self.GAME;u=self.u;self.label_events=[];self.case_end_game=end_game
        u.mem_write(G+4,struct.pack('<f',dt))
        u.reg_write(UC_ARM_REG_R4,G);u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1)
        self.labelling=True
        try:u.emu_start(ENTRY|1,ATTACK,timeout=0,count=200000);pc=u.reg_read(self.PC)
        finally:self.labelling=False
        assert pc in (ATTACK,EPILOGUE),hex(pc)
        s=lambda a:C.c_int32(self.read(a)).value
        return dict(ended=pc!=ATTACK,events=self.label_events,selection={**{k:s(G+a) for k,a in SEL_INTS.items()},**{k:u.mem_read(G+a,1)[0] for k,a in SEL_BYTES.items()}},
                    flights={k:[f32(v) for v in struct.unpack('<5f',u.mem_read(G+a,20))] for k,a in FLIGHTS.items()},
                    health=[s(G+0xbd98),s(G+0x5994)])

class Native(GateNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_schedule_native.dylib'))
        self.label_fn=lib.dr_process_damage_labels;self.label_fn.restype=C.c_bool
        self.label_fn.argtypes=[C.POINTER(State),C.c_float,Point,C.POINTER(Hooks)]
        def event(_,p):
            e=p.contents;self.label_events.append([e.kind,e.label,e.a,e.b,f32(e.x),f32(e.y)] if e.kind!=KINDS['scale'] else [e.kind,e.label,e.a&0xffffffff,0,0.0,0.0])
        def check(_):self.label_events.append([KINDS['check_end'],-1,0,0,0.0,0.0]);return bool(self.case_end_game)
        self.label_cb=EVENT(event);self.check_cb=CHECK(check);self.label_hooks=Hooks(None,self.label_cb,self.check_cb)
    def load(self,c):
        super().load(c);l=c['labels'];s=self.state.selection
        for k in list(SEL_INTS)+list(SEL_BYTES):setattr(s,k,c['game'][k])
        self.flights=Flights(*[Flight(v[0],Point(v[1],v[2]),v[3],v[4]) for v in (l['flights'][k] for k in FLIGHTS)])
        self.active=(U8*4)(*l['active'],0);self.touch=Point(*l['touch'])
        self.label_state=State(C.cast(C.pointer(s),C.c_void_p),C.cast(C.pointer(self.r),C.c_void_p),C.pointer(self.flights),self.active)
    def frame(self,dt,end_game):
        self.label_events=[];self.case_end_game=end_game
        ended=self.label_fn(C.byref(self.label_state),dt,self.touch,C.byref(self.label_hooks))
        s=self.state.selection;f=self.flights
        return dict(ended=ended,events=self.label_events,selection={k:getattr(s,k) for k in list(SEL_INTS)+list(SEL_BYTES)},
                    flights={k:[f32(x) for x in (getattr(f,k).arc,getattr(f,k).start.x,getattr(f,k).start.y,getattr(f,k).progress,getattr(f,k).speed)] for k in FLIGHTS},
                    health=[self.r.health,self.r.ui_health])

def case(rng):
    c,_=scenario(rng);g=c['game']
    for k in SEL_INTS:g[k]=rng.choice([0,0,3,12,-2,rng.randrange(1,60)])
    for k in SEL_BYTES:g[k]=int(rng.random()<.5)
    c['path_state'].update(base_attack=g['current_damage'],direction_bonus=g['weapon_damage'])   # same Game fields (verify_path)
    res=c['resources'];res.update(health_max=rng.choice([20,60]),health_bonus=rng.choice([0,5]))
    res['health']=rng.randrange(0,res['health_max']+8);res['ui_health']=rng.choice([res['health'],res['health']+1])
    c['labels']=dict(active=[rng.randrange(2) for _ in range(3)],touch=[round(rng.uniform(0,1),4),round(rng.uniform(0,1.5),4)],
                     flights={k:[rng.uniform(0.4,0.8),rng.uniform(0,1),rng.uniform(0,1.5),rng.choice([0.0,rng.uniform(0,1),0.95,1.0]),rng.choice([1.0,rng.uniform(0,6)])] for k in FLIGHTS})
    c['moving_list']=[];c['gate']=dict(tokens_pending=0,flare_count=0,phase=0,touch_phase=0,input_target=-1,rune=0)
    return c

def main():
    old,new=Original(),Native();rng=random.Random(0x176fc);frames=0;kinds={};ended=0
    for n in range(300):
        c=case(rng);old.load(c);new.load(c)
        for step in range(rng.choice([1,3,8])):
            dt=rng.choice([0.0166,0.033,rng.uniform(0,0.2)]);end=int(rng.random()<.3)
            a,b=old.frame(dt,end),new.frame(dt,end)
            if a!=b:
                (HERE/'damage_labels_failure.json').write_text(json.dumps(dict(case=c,step=step,dt=dt,end=end,original=a,native=b),indent=2))
                raise AssertionError('damage_labels_failure.json')
            frames+=1;ended+=a['ended']
            for e in a['events']:kinds[e[0]]=kinds.get(e[0],0)+1
            if a['ended']:break
    names={v:k for k,v in KINDS.items()}
    assert all(kinds.get(v) for v in KINDS.values()) and ended,(kinds,ended)
    report=dict(status='passed',frames=frames,cases=300,ended=ended,events={names[k]:v for k,v in sorted(kinds.items())},
                functions=[dict(symbol='__ZN4Game7ProcessEv',address='0x1717c',segment=[hex(ENTRY),hex(ATTACK)],extra=['0x17d74','0x17da4'],
                                native='dr_process_damage_labels')],
                original='Actual Game::Process damage-label segment with original Interpolate and Sqr; host powf for the powf stub',
                boundaries=['SimpleLabel Process/Initialise/SetPosition/SetNumber/SetAlpha, sounds, achievements, health bar recorded',
                            'CheckEndGame returns the case result'],
                scope='leech/flame/spike labels: fade, display at the touch, flight, arrival heal/damage, carried over frames')
    (HERE/'damage_labels_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
