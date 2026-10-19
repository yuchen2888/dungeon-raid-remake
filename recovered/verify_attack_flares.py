#!/usr/bin/env python3
"""Actual Game::InitialiseFlares 0xd9b0 and ProcessAttack phase 1 [0x14126,0x141c6).

InitialiseFlares runs whole, including Tile::GetAttack; phase 1 runs with its
InitialiseFlares call executing the original function too. Quad::SetAlpha runs
as original code. Tile::GetEyePosition, Game::AddFlare, Game::QueueSound and the
four Interface::Set*Shadow calls are adapted presentation calls (recorded).
"""
import ctypes as C
import hashlib
import json
import random
import re
import struct
from verify_attack_shield import Original as ShieldOriginal, GAME, TILE, STOP, HERE
from verify_attack_absorb import AttackDamage
from verify_match import Match
from verify_path import Path
from verify_stroke import State as Stroke
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R8,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC

FLARES,FLARES_END=0xd9b0,0xdaf4
START,END=0x14126,0x141c6
PHASE,DT,DAMAGE,ENEMY9,COUNT,SHAKE,SCALE,ALPHA=0xb8a8,0x4,0xbe84,0x1553c,0xbd8c,0xbd90,0xbd94,0xb92b
TILES,STRIDE,RACE=0x5e58,608,0x1556c
OVERLAY=0xb91c;VERTEX_ALPHA=(0xf,0x23,0x37,0x4b)

class Event(C.Structure):
    _fields_=[(k,C.c_int32) for k in ('kind','tile','a','b','c')]
CALLBACK=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(Event))
class Hooks(C.Structure):
    _fields_=[('context',C.c_void_p),('event',CALLBACK)]
def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]

class Original(ShieldOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.calls={};self.flare_visits={};self.stop_at=None
        for symbol,name in [('__ZN4Game10QueueSoundE5Sound','sound'),('__ZN4Tile14GetEyePositionEi','eye'),
                            ('__ZN4Game8AddFlareE9FlareType8GLfloat2RK9GLcolour4','flare'),('__ZN4Quad8SetAlphaEh','alpha'),
                            ('__ZN9Interface15SetHealthShadowEi','shadow0'),('__ZN9Interface11SetXPshadowEi','shadow1'),
                            ('__ZN9Interface11SetUPshadowEi','shadow2'),('__ZN9Interface13SetGoldShadowEi','shadow3')]:
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol
            self.calls[int(m[1],16)]=name
    def index(self,address):
        i,rest=divmod(address-GAME-TILES,STRIDE);assert rest==0 and 0<=i<36;return i
    def hook(self,u,address,size,_):
        if FLARES<=address<FLARES_END or START<=address<END:self.flare_visits[hex(address)]=self.flare_visits.get(hex(address),0)+1
        if address==self.stop_at:u.emu_stop();return
        name=self.calls.get(address)
        if not name:return
        r=[u.reg_read(x) for x in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)];s=lambda v:C.c_int32(v).value
        if name=='alpha':
            assert r[0]==GAME+OVERLAY;self.events.append([3,-1,0,r[1]&0xff,0]);return   # original store runs
        if name=='eye':self.eye=(self.index(r[1]),r[2])
        elif name=='sound':assert r[0]==GAME;self.events.append([1,-1,r[1],0,0])
        elif name=='flare':
            colour=struct.unpack('<i',u.mem_read(struct.unpack('<I',u.mem_read(u.reg_read(UC_ARM_REG_SP),4))[0],4))[0]
            assert r[0]==GAME;self.events.append([2,self.eye[0],self.eye[1],r[1],colour])
        else:assert r[0]==GAME+0x4cdc;self.events.append([4,-1,int(name[-1]),s(r[1]),0])
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def load(self,c):
        self.u.mem_write(GAME,b'\0'*0x20000)
        for offset,key in ((PHASE,'phase'),(DAMAGE,'damage'),(ENEMY9,'enemy9'),(COUNT,'count'),(SHAKE,'shake'),(SCALE,'scale'),(RACE,'race')):self.write(offset,c[key])
        for v in VERTEX_ALPHA:self.u.mem_write(GAME+OVERLAY+v,bytes([0x5a]))
        self.u.mem_write(GAME+ALPHA,bytes([c['alpha']]))
        for i,t in enumerate(c['tiles']):
            base=TILES+STRIDE*i;self.write(base+0x70,GAME)
            for o,k in ((0x9c,'type'),(0x24c,'enemy'),(0x250,'enemy_state'),(0xa4,'attack'),(0x238,'poison')):self.write(base+o,t[k])
            for o,k in ((0x86,'attack_flag'),(0x255,'frozen')):self.u.mem_write(GAME+base+o,bytes([t[k]]))
    def state(self):
        return dict(**{k:self.read(o) for k,o in (('phase',PHASE),('damage',DAMAGE),('enemy9',ENEMY9),('count',COUNT),('shake',SHAKE),('scale',SCALE))},
                    alpha=self.u.mem_read(GAME+ALPHA,1)[0])
    def run(self,key,dt=0.0):
        self.events=[];self.u.mem_write(GAME+DT,struct.pack('<f',dt));before=bytearray(self.u.mem_read(GAME,0x20000))
        start,self.stop_at=(FLARES,STOP) if key=='flares' else (START,END)
        for reg,value in [(UC_ARM_REG_R0,GAME),(UC_ARM_REG_SP,TILE+0xf00),(UC_ARM_REG_LR,STOP|1)]:self.u.reg_write(reg,value)
        self.u.emu_start(start|1,STOP,timeout=0,count=100000)
        assert self.u.reg_read(UC_ARM_REG_PC)==self.stop_at
        for e in self.events:
            if e[0]==3:assert all(self.u.mem_read(GAME+OVERLAY+v,1)[0]==e[3] for v in VERTEX_ALPHA)
        for offset in (PHASE,DAMAGE,ENEMY9,COUNT,SHAKE,SCALE):before[offset:offset+4]=self.u.mem_read(GAME+offset,4)
        for v in VERTEX_ALPHA:before[OVERLAY+v]=self.u.mem_read(GAME+OVERLAY+v,1)[0]
        assert bytes(before)==bytes(self.u.mem_read(GAME,0x20000)),'unexpected gameplay write'
        return dict(**self.state(),events=self.events[:])

class Native:
    def __init__(self):
        lib=C.CDLL(str(HERE/'recovered_attack_shield_native.dylib'))
        self.flares=lib.dr_initialise_flares;self.flares.argtypes=[C.POINTER(AttackDamage),C.POINTER(Path),C.POINTER(C.c_int32),C.POINTER(Hooks)];self.flares.restype=None
        self.fade_in=lib.dr_process_attack_fade_in
        self.fade_in.argtypes=[C.POINTER(AttackDamage),C.POINTER(Path),C.POINTER(C.c_int32),C.POINTER(C.c_uint8),C.c_float,C.POINTER(Hooks)];self.fade_in.restype=None
        self.callback=CALLBACK(lambda _,p:self.events.append([getattr(p.contents,k) for k in ('kind','tile','a','b','c')]));self.hooks=Hooks(None,self.callback)
    def load(self,c):
        self.stroke=Stroke();self.match=Match();self.match.stroke=C.pointer(self.stroke);self.path=Path();self.path.match=C.pointer(self.match)
        self.match.shake_progress_bd90=c['shake']&0xffffffff;self.match.shake_scale_bd94=c['scale']&0xffffffff
        self.stroke.selection.character.race=c['race']
        self.damage=AttackDamage(None,c['phase'],c['damage'],c['enemy9']);self.count=C.c_int32(c['count']);self.alpha=C.c_uint8(c['alpha'])
        for i,t in enumerate(c['tiles']):
            r=self.stroke.selection.tiles[i].rule;r.type,r.enemy,r.enemy_state,r.flag255=t['type'],t['enemy'],t['enemy_state'],t['frozen']
            k=self.path.combat[i];k.attack,k.attack_flag,k.poison.current=t['attack'],t['attack_flag'],t['poison']
    def state(self):
        m=self.match;d=self.damage
        return dict(phase=d.phase,damage=d.incoming_damage,enemy9=d.enemy9_damage,count=self.count.value,
                    shake=C.c_int32(m.shake_progress_bd90).value,scale=C.c_int32(m.shake_scale_bd94).value,alpha=self.alpha.value)
    def run(self,key,dt=0.0):
        self.events=[];board=bytes(self.stroke);combat=bytes(self.path.combat)
        if key=='flares':self.flares(C.byref(self.damage),C.byref(self.path),C.byref(self.count),C.byref(self.hooks))
        else:self.fade_in(C.byref(self.damage),C.byref(self.path),C.byref(self.count),C.byref(self.alpha),dt,C.byref(self.hooks))
        assert bytes(self.stroke)==board and bytes(self.path.combat)==combat
        return dict(**self.state(),events=self.events[:])

def board(rng,enemy_bias=.6):
    tiles=[]
    for _ in range(36):
        enemy=rng.choice([9,32,20,rng.randrange(33)])
        tiles.append(dict(type=1 if rng.random()<enemy_bias else rng.randrange(5),enemy=enemy,enemy_state=rng.choice([0,0,rng.randrange(1,6)]),
                          attack=rng.randrange(-2,40),poison=rng.choice([0,0,rng.randrange(1,5)]),attack_flag=int(rng.random()<.15),frozen=int(rng.random()<.15)))
    return tiles

def main():
    old,new=Original(),Native();rng=random.Random(0xD9B0);counts={'flares_boundary':0,'flares_random':0,'fade_in_boundary':0,'fade_in_random':0,'fade_in_frames':0};to2=0;flare_events=0
    def compare(c,key,dt,group):
        nonlocal to2,flare_events
        a,b=old.run(key,dt),new.run(key,dt)
        if a!=b:
            (HERE/'attack_flares_failure.json').write_text(json.dumps(dict(case=c,key=key,dt=dt,original=a,native=b),indent=2))
            raise AssertionError('attack_flares_failure.json')
        counts[group]+=1;to2+=key=='fade_in' and a['phase']==2 and c.get('phase')==1;flare_events+=sum(e[0]==2 for e in a['events'])
        return a
    def case(tiles,**k):
        c=dict(tiles=tiles,phase=1,damage=77,enemy9=5,count=9,shake=123,scale=456,race=0,alpha=0);c.update(k);return c
    plain=lambda **k:dict(dict(type=2,enemy=0,enemy_state=0,attack=5,poison=0,attack_flag=0,frozen=0),**k)
    # InitialiseFlares: each filter and poison/race halving on a single tile among non-enemies.
    for race in (0,1,2):
     for enemy in (0,9,32):
      for state in (0,1):
       for attack in (-1,0,1,2,7):
        for poison in (0,2):
         for flag,frozen in ((0,0),(1,0),(0,1)):
            tiles=[plain() for _ in range(36)];tiles[13]=plain(type=1,enemy=enemy,enemy_state=state,attack=attack,poison=poison,attack_flag=flag,frozen=frozen)
            tiles[34]=plain(type=1,enemy=9,attack=3);c=case(tiles,race=race);old.load(c);new.load(c);compare(c,'flares',0.0,'flares_boundary')
    for _ in range(500):
        c=case(board(rng),race=rng.randrange(10),damage=rng.randrange(-5,50),enemy9=rng.randrange(-5,20),count=rng.randrange(0,40))
        old.load(c);new.load(c);compare(c,'flares',0.0,'flares_random')
    # Phase 1 segment (calls the original InitialiseFlares when it crosses 200).
    dts=[0.0,1e-45,f32(1/800),f32(1/240),f32(1/60),f32(1/30),f32(200/800),f32(201/800),0.5,10.0]
    for phase in (0,1,2):
     for alpha in (0,1,199,200,201,255):
      for dt in dts:
        c=case(board(rng),phase=phase,alpha=alpha,race=rng.randrange(10));old.load(c);new.load(c);compare(c,'fade_in',dt,'fade_in_boundary')
    for _ in range(800):
        c=case(board(rng),phase=rng.choice([1,1,1,rng.randrange(0,9)]),alpha=rng.randrange(256),race=rng.randrange(10),
               damage=rng.randrange(0,30),enemy9=rng.randrange(0,9),count=rng.randrange(0,30),shake=rng.getrandbits(31),scale=rng.getrandbits(31))
        old.load(c);new.load(c);compare(c,'fade_in',f32(rng.uniform(0,0.5)),'fade_in_random')
    for game in range(30):
        c=case(board(rng),phase=1,alpha=0,race=game%10);old.load(c);new.load(c)
        for _ in range(200):
            a=compare(c,'fade_in',f32(rng.choice([1/60,1/30,rng.uniform(0,0.02)])),'fade_in_frames')
            if a['phase']==2:break
        assert a['phase']==2
    assert all(hex(a) in old.flare_visits for a in (0xd9e6,0xda12,0xda28,0xda6c,0xdac6,0x1415c,0x14188,0x1418a))
    report=dict(status='passed',comparisons=sum(counts.values()),by_group=counts,phase2_transitions=to2,flare_events=flare_events,
                functions=[dict(symbol='__ZN4Game16InitialiseFlaresEv',address=hex(FLARES),native='dr_initialise_flares')],
                range=dict(start=hex(START),end_exclusive=hex(END)),
                original='Actual InitialiseFlares (incl. Tile::GetAttack) and ProcessAttack phase 1 incl. Quad::SetAlpha',
                boundaries=['GetEyePosition/AddFlare/QueueSound/Interface shadows adapted; AddFlare flare-list append and count increment belong to the caller',
                            'frame time written to Game+4 by the harness; valid domain finite 0<=dt<=10','phase 2..4 not covered'],
                scope='Incoming damage, enemy-9 damage, flare count, phase, shake fields and overlay alpha; board/combat must stay unchanged',
                byte_sha256=hashlib.sha256(old.machine.bytes_at(FLARES,FLARES_END-FLARES)).hexdigest(),
                phase1_byte_sha256=hashlib.sha256(old.machine.bytes_at(START,END-START)).hexdigest(),branch_visits=old.flare_visits)
    (HERE/'attack_flares_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='branch_visits'}))

if __name__=='__main__':main()
