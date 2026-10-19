#!/usr/bin/env python3
"""Actual Tile::SetFlameVisibility 0x3d89c and EndOfTurn burn/freeze loop
[0x13710,0x13910) + loop head [0x13d64,0x13d88) vs native (recovered_turn).

SetFlameVisibility runs whole (its overlay Quad calls run as original code; the
alpha call marks the overlay). The loop runs with its SetFreezeVisibility and
SetFlameVisibility calls executing as original code and its AttackSkull
executing the original function (MatchTile, tokens) via verify_attack_all.py's
subsystem switching; native wires attack_skull to dr_path_attack_skull.
Own UpdateText/AddSimpleLabel/AddFlare/AddParticles/QueueSound/QueueAchievement
calls are recorded in canonical form.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_attack_all import Original as AllOriginal, Native as AllNative, scenario, ATTACK
from verify_path import Path
from verify_stroke import HERE, I32

FLAME,FLAME_END=0x3d89c,0x3d91c
FREEZE,FREEZE_END=0x3d934,0x3d9a4
QUAD_SYMBOLS=('__ZN4Quad5SetUVERK8GLfloat2S2_','__ZN4Quad7SetSizeERK8GLfloat2','__ZN4Quad8SetAlphaEh')
LOOP,LOOP_END,HEAD,HEAD_END=0x13710,0x13910,0x13d64,0x13d88
TILES,STRIDE,RESTING=0x5e58,608,0xb400
SYMBOLS={'__ZN4Game10QueueSoundE5Sound':'sound','__ZN4Tile10UpdateTextEbbb':'text','__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif':'label',
         '__ZN4Game8AddFlareE9FlareType8GLfloat2RK9GLcolour4':'flare','__ZN4Game16QueueAchievementE11Achievementf':'achievement',
         '__ZN4Game12AddParticlesEP4Tile12ParticleType':'particles','__ZN4Tile19SetFreezeVisibilityEb':'freeze','__ZN4Quad8SetAlphaEh':'alpha'}

class Event(C.Structure):_fields_=[(k,I32) for k in ('kind','tile','a','b','c','d')]
EVENT=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(Event))
MATCH=C.CFUNCTYPE(None,C.c_void_p,I32,I32)
class TurnHooks(C.Structure):_fields_=[('context',C.c_void_p),('event',EVENT),('match_tile',MATCH),('attack_skull',ATTACK)]

class Original(AllOriginal):
    ranges,entry,stop_at=[(LOOP,LOOP_END),(HEAD,HEAD_END)],LOOP,LOOP_END
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.calls={};self.burn_visits={};self.recording=False
        for symbol,name in SYMBOLS.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol;self.calls[int(m[1],16)]=name
        self.quads=set()
        for symbol in QUAD_SYMBOLS:
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol;self.quads.add(int(m[1],16))
    def tile_of(self,address,offset=0):
        i,rest=divmod(address-self.GAME-TILES-offset,STRIDE);assert rest==0 and 0<=i<36,hex(address);return i
    def resting_index(self,x,y):
        found=[i for i in range(36) if struct.unpack('<II',self.u.mem_read(self.GAME+RESTING+8*i,8))==(x,y)];assert len(found)==1;return found[0]
    def hook(self,u,address,size,context):
        if self.recording and getattr(self,'mode',None) is None:
            if LOOP<=address<LOOP_END or HEAD<=address<HEAD_END:self.burn_visits[hex(address)]=self.burn_visits.get(hex(address),0)+1
            lr=u.reg_read(self.LR)&~1;name=self.calls.get(address)
            mine=LOOP<lr<=LOOP_END or HEAD<lr<=HEAD_END
            if address in self.quads and (FLAME<lr<=FLAME_END or FREEZE<lr<=FREEZE_END):
                # Overlay quad (Tile+0x140) calls of Set{Flame,Freeze}Visibility: run the original code,
                # bypassing lower harness hooks that expect a tile pointer.
                if name=='alpha' and FLAME<lr<=FLAME_END:self.turn_events.append(['flame_overlay',self.tile_of(u.reg_read(self.regs[0]),0x140)])
                return
            elif name and name!='alpha' and mine:
                r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value;sp=u.reg_read(self.SP)
                if name=='freeze':
                    self.turn_events.append(['freeze',self.tile_of(r[0]),r[1]&0xff]);return super().hook(u,address,size,context)   # original runs
                if name=='sound':e=['sound',r[1]]
                elif name=='text':e=['text',self.tile_of(r[0]),r[1]&0xff,r[2]&0xff,r[3]&0xff]
                elif name=='label':
                    o=r[2]-self.GAME-RESTING;assert o%8==0 and 0<=o//8<36
                    e=['label_rest',o//8,r[1],s(r[3]),s(self.read(sp)),s(self.read(sp+4))]
                elif name=='flare':e=['flare_rest',self.resting_index(r[2],r[3]),r[1],s(self.read(self.read(sp)))]
                elif name=='achievement':e=['achievement',r[1],s(r[2])]
                else:e=['particles',self.tile_of(r[1]),r[2]]
                self.turn_events.append(e);u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def flame_state(self):
        return [[self.u.mem_read(self.tile(i)+0x257,1)[0],C.c_int32(self.read(self.tile(i)+0x258)).value] for i in range(36)]
    def burn(self):
        self.turn_events=[];self.recording=True
        from unicorn.arm_const import UC_ARM_REG_R10
        self.u.reg_write(UC_ARM_REG_R10,0)
        try:result=self.run_original()
        finally:self.recording=False
        return dict(**result,turn=self.turn_events[:],flame=self.flame_state())
    def flame(self,tile,on,damage,self_flame):
        self.turn_events=[];self.recording=True;u=self.u
        for reg,v in zip(self.regs,[self.tile(tile),int(on),damage&0xffffffff,int(self_flame)]):u.reg_write(reg,v)
        u.reg_write(self.SP,0x140ff00);u.reg_write(self.LR,self.STOP|1)
        try:u.emu_start(FLAME|1,self.STOP,timeout=0,count=100000);assert u.reg_read(self.PC)==self.STOP
        finally:self.recording=False
        return dict(path=self.path_status(),turn=self.turn_events[:],flame=self.flame_state())

class Native(AllNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_turn_native.dylib'))
        self.burn_fn=lib.dr_end_turn_burn_freeze;self.burn_fn.argtypes=[C.POINTER(Path),C.POINTER(TurnHooks)];self.burn_fn.restype=None
        self.flame_fn=lib.dr_set_flame_visibility
        self.flame_fn.argtypes=[C.POINTER(Path),C.c_uint32,C.c_bool,I32,C.c_bool,C.POINTER(TurnHooks)];self.flame_fn.restype=None
        def event(_,p):
            e=p.contents;k=e.kind;ev=self.turn_events.append
            if k==1:ev(['sound',e.a])
            elif k==2:ev(['text',e.tile,e.a,e.b,e.c])
            elif k==5:ev(['achievement',e.a,e.b])
            elif k==6:ev(['label_rest',e.tile,e.a,e.b,e.c,e.d])
            elif k==7:ev(['flare_rest',e.tile,e.a,e.b])
            elif k==8:ev(['freeze',e.tile,e.a])
            elif k==9:ev(['flame_overlay',e.tile])
            elif k==10:ev(['particles',e.tile,e.a])
            else:raise AssertionError(k)
        def match(_,tile,reward):self.match_fn(C.byref(self.m),tile,reward,C.byref(self.match_hooks))
        self.turn_cb=(EVENT(event),MATCH(match));self.turn_hooks=TurnHooks(None,self.turn_cb[0],self.turn_cb[1],self.cb[1])
    def flame_state(self):
        return [[t.self_flame,t.flame_damage] for t in self.state.selection.tiles]
    def reset(self):
        self.all_events=[];self.enc_events=[];self.gen_events=[];self.refill_events=[];self.path_events=[]
        self.match_events=[];self.token_events=[];self.motion_events=[];self.turn_events=[]
    def burn(self):
        self.reset();self.burn_fn(C.byref(self.path_state),C.byref(self.turn_hooks))
        return dict(path=self.path_status(),enc=self.enc_status(),all=self.all_events[:],turn=self.turn_events[:],flame=self.flame_state())
    def flame(self,tile,on,damage,self_flame):
        self.reset();self.flame_fn(C.byref(self.path_state),tile,on,damage,self_flame,C.byref(self.turn_hooks))
        return dict(path=self.path_status(),turn=self.turn_events[:],flame=self.flame_state())

def burn_case(rng):
    c,_=scenario(rng)
    for i,t in enumerate(c['board']):
        state=rng.choice(['plain','plain','frozen','burning','both'])
        t['flag255']=int(state in ('frozen','both'));t['flaming']=int(state in ('burning','both'))
        t['self_flame']=rng.randrange(2);t['flame_damage']=rng.choice([0,1,3,rng.randrange(1,25)])
        c['combat'][i]['overlay']=rng.randrange(2);c['combat'][i]['flag256']=t['flaming']
    return c

def main():
    old,new=Original(),Native();rng=random.Random(0x13710);counts={'flame':0,'burn':0};kills=0
    def compare(c,a,b,key):
        if a!=b:
            (HERE/'turn_burn_failure.json').write_text(json.dumps(dict(case=c,key=key,original=a,native=b),indent=2))
            raise AssertionError('turn_burn_failure.json')
        counts[key]+=1
    for _ in range(40):
        c=burn_case(rng);old.load(c);new.load(c)
        for _ in range(6):
            args=(rng.randrange(36),rng.randrange(2),rng.choice([-5,0,1,7,2**31-1]),rng.randrange(2))
            compare(dict(c=c,args=args),old.flame(*args),new.flame(*args),'flame')
    for _ in range(160):
        c=burn_case(rng);c['game']['race']=rng.choice([0,8,8,rng.randrange(10)]);old.load(c);new.load(c)
        a,b=old.burn(),new.burn();compare(c,a,b,'burn');kills+=sum(1 for e in a['all'] if e[1]==9)
    assert kills and all(hex(x) in old.burn_visits for x in (0x1371e,0x13784,0x1379c,0x13804,0x1381a,0x1388a,0x138f4,0x13d64))
    report=dict(status='passed',comparisons=sum(counts.values()),by_group=counts,burn_kills=kills,
                functions=[dict(symbol='__ZN4Tile18SetFlameVisibilityEbib',address=hex(FLAME),native='dr_set_flame_visibility')],
                ranges=[[hex(LOOP),hex(LOOP_END)],[hex(HEAD),hex(HEAD_END)]],
                original='Actual SetFlameVisibility and EndOfTurn burn/freeze loop with original SetFreezeVisibility and AttackSkull chain',
                boundaries=['own UpdateText/AddSimpleLabel/AddFlare/AddParticles/QueueSound/QueueAchievement adapted','overlay quad calls run as original code',
                            'entry state at 0x13710 (R8=Game, R10=0) set by the harness; preceding EndOfTurn code is a later unit'],
                scope='Full shared board incl. frozen/burning/self-flame/flame damage, combat, tokens and RNG',branch_visits=old.burn_visits)
    (HERE/'turn_burn_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='branch_visits'}))

if __name__=='__main__':main()
