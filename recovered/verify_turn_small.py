#!/usr/bin/env python3
"""Actual Game::MimicDefence 0xbd20, Game::Resurrect 0xaf68 and
Game::ProcessCripples 0xcae0 vs native (recovered_turn), on the full shared
state of verify_attack_all.py.

Each whole original function runs from its entry. ProcessCripples' MatchTile
calls execute the original MatchTile with the existing match/token hooks; native
wires the match_tile callback to dr_match_tile with the same match hooks.
Only the three functions' own UpdateText / AddSimpleLabel / AddFlare /
QueueSound / QueueAchievement calls are adapted (recorded).
"""
import ctypes as C
import json
import random
import re
import struct
from verify_attack_all import Original as AllOriginal, Native as AllNative, scenario
from verify_path import Path
from verify_match import Match
from verify_stroke import HERE, I32

FUNCTIONS={'mimic':(0xbd20,0xbd68),'resurrect':(0xaf68,0xafdc),'cripples':(0xcae0,0xcbbc)}
TILES,STRIDE=0x5e58,608
SYMBOLS={'__ZN4Game10QueueSoundE5Sound':'sound','__ZN4Tile10UpdateTextEbbb':'text',
         '__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif':'label','__ZN4Game8AddFlareE9FlareType8GLfloat2RK9GLcolour4':'flare',
         '__ZN4Game16QueueAchievementE11Achievementf':'achievement'}

class Event(C.Structure):_fields_=[(k,I32) for k in ('kind','tile','a','b','c','d')]
EVENT=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(Event))
MATCH=C.CFUNCTYPE(None,C.c_void_p,I32,I32)
class TurnHooks(C.Structure):_fields_=[('context',C.c_void_p),('event',EVENT),('match_tile',MATCH)]

class Original(AllOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.turn_calls={};self.turn_visits={}
        for symbol,name in SYMBOLS.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol;self.turn_calls[int(m[1],16)]=name
        self.current=None
    def tile_of(self,address,offset=0):
        i,rest=divmod(address-self.GAME-TILES-offset,STRIDE);assert rest==0 and 0<=i<36,hex(address);return i
    def hook(self,u,address,size,context):
        if self.current:
            start,end=FUNCTIONS[self.current]
            if start<=address<end:self.turn_visits[hex(address)]=self.turn_visits.get(hex(address),0)+1
            lr=u.reg_read(self.LR)&~1;name=self.turn_calls.get(address)
            if name and start<lr<=end:
                r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value;sp=u.reg_read(self.SP)
                if name=='sound':e=['sound',r[1]]
                elif name=='text':e=['text',self.tile_of(r[0]),r[1]&0xff,r[2]&0xff,r[3]&0xff]
                elif name=='label':assert r[0]==self.GAME;e=['label',self.tile_of(r[2],0x54),r[1],s(r[3]),s(self.read(sp)),s(self.read(sp+4))]
                elif name=='flare':
                    x,y=struct.unpack('<II',struct.pack('<II',r[2],r[3]));tile=[i for i in range(36) if struct.unpack('<II',self.u.mem_read(self.tile(i)+0x54,8))==(x,y)]
                    e=['flare',tile[0] if len(tile)==1 else tile,r[1],s(struct.unpack('<I',self.u.mem_read(self.read(sp),4))[0])]
                else:e=['achievement',r[1],s(r[2])]
                self.turn_events.append(e);u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def run_turn(self,key,tile=0):
        self.turn_events=[];self.match_events=[];self.token_events=[];self.path_events=[];self.current=key
        u=self.u;u.reg_write(self.regs[0],self.GAME);u.reg_write(self.regs[1],self.tile(tile));u.reg_write(self.SP,0x140ff00);u.reg_write(self.LR,self.STOP|1)
        try:
            u.emu_start(FUNCTIONS[key][0]|1,self.STOP,timeout=0,count=3000000);assert u.reg_read(self.PC)==self.STOP
        finally:self.current=None
        return dict(path=self.path_status(),enc=self.enc_status(),turn=self.turn_events[:])

class Native(AllNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_turn_native.dylib'))
        self.fns=dict(mimic=lib.dr_mimic_defence,resurrect=lib.dr_resurrect,cripples=lib.dr_process_cripples)
        self.fns['mimic'].argtypes=[C.POINTER(Path),C.c_uint32,C.POINTER(TurnHooks)]
        self.fns['resurrect'].argtypes=[C.POINTER(Match),C.c_uint32,C.POINTER(TurnHooks)]
        self.fns['cripples'].argtypes=[C.POINTER(Path),C.POINTER(TurnHooks)]
        for f in self.fns.values():f.restype=None
        def event(_,p):
            e=p.contents;k=e.kind
            if k==1:self.turn_events.append(['sound',e.a])
            elif k==2:self.turn_events.append(['text',e.tile,e.a,e.b,e.c])
            elif k==3:self.turn_events.append(['label',e.tile,e.a,e.b,e.c,e.d])
            elif k==4:self.turn_events.append(['flare',e.tile,e.a,e.b])
            else:self.turn_events.append(['achievement',e.a,e.b])
        def match(_,tile,reward):self.match_fn(C.byref(self.m),tile,reward,C.byref(self.match_hooks))
        self.turn_cb=(EVENT(event),MATCH(match));self.turn_hooks=TurnHooks(None,*self.turn_cb)
    def run_turn(self,key,tile=0):
        self.turn_events=[];self.match_events=[];self.token_events=[];self.path_events=[]
        if key=='mimic':self.fns[key](C.byref(self.path_state),tile,C.byref(self.turn_hooks))
        elif key=='resurrect':self.fns[key](C.byref(self.m),tile,C.byref(self.turn_hooks))
        else:self.fns[key](C.byref(self.path_state),C.byref(self.turn_hooks))
        return dict(path=self.path_status(),enc=self.enc_status(),turn=self.turn_events[:])

def main():
    old,new=Original(),Native();rng=random.Random(0xCAE0);counts={'mimic':0,'resurrect':0,'cripples':0};crippled=0
    def compare(c,key,tile):
        nonlocal crippled
        a,b=old.run_turn(key,tile),new.run_turn(key,tile)
        if a!=b:
            (HERE/'turn_small_failure.json').write_text(json.dumps(dict(case=c,key=key,tile=tile,original=a,native=b),indent=2))
            raise AssertionError('turn_small_failure.json')
        counts[key]+=1;crippled+=sum(1 for e in a['turn'] if e[0]=='achievement')
    for _ in range(60):
        c,_=scenario(rng);c['preview']['armour_current']=rng.choice([-3,0,7,99])
        old.load(c);new.load(c)
        for tile in rng.sample(range(36),4):compare(c,'mimic',tile)
        compare(c,'resurrect',rng.randrange(36))
    for race in range(10):
        for n in range(12):
            c,_=scenario(rng);c['game']['race']=race
            for i,t in enumerate(c['board']):
                if t['type']==1 and rng.random()<.5:t['enemy']=0
                c['combat'][i]['health']=rng.randrange(-1,15);c['combat'][i]['defence']=rng.randrange(0,15)
                t['matched']=int(rng.random()<.1)
            old.load(c);new.load(c);compare(c,'cripples',0)
    assert crippled and all(hex(a) in old.turn_visits for a in (0xcb04,0xcb46,0xcb86,0xcbb0))
    report=dict(status='passed',comparisons=sum(counts.values()),by_function=counts,cripples_matched=crippled,
                functions=[dict(symbol=s,address=hex(FUNCTIONS[k][0]),native=n) for k,s,n in (
                    ('mimic','__ZN4Game12MimicDefenceEP4Tile','dr_mimic_defence'),('resurrect','__ZN4Game9ResurrectEP4Tile','dr_resurrect'),
                    ('cripples','__ZN4Game15ProcessCripplesEv','dr_process_cripples'))],
                original='Actual MimicDefence, Resurrect, ProcessCripples; MatchTile and its rewards as original code',
                boundaries=['own UpdateText/AddSimpleLabel/AddFlare/QueueSound/QueueAchievement adapted'],
                scope='Full shared board, combat, match state, tokens and RNG')
    (HERE/'turn_small_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
