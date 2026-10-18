#!/usr/bin/env python3
"""Actual ProcessAttack enemy-weakening instructions vs native source.

Range: entry 0x1487e (right after shield wear on the phase-5 completion path)
until 0x14938 (the Game+0xbe68 check), including the out-of-line loop blocks
0x14b56..0x14b5c and 0x14b9c..0x14bbc that the code branches through.
Tile::UpdateText, Tile::GetAttackLabelPosition, Game::AddSimpleLabel,
Game::AddParticles and Game::QueueSound are adapted presentation calls.
"""
import ctypes as C
import hashlib
import json
import random
import re
import struct
from verify_attack_shield import Original as ShieldOriginal, GAME, TILE, STOP, HERE
from verify_match import Match
from verify_path import Path
from verify_stroke import State as Stroke
from unicorn.arm_const import (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,
    UC_ARM_REG_R8,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC)

START,END=0x1487e,0x14938
BLOCKS=[(0x14b56,0x14b5e),(0x14b9c,0x14bbe)]
WEAKEN,TILES,STRIDE=0xbe6c,0x5e58,608

class Event(C.Structure):
    _fields_=[(k,C.c_int32) for k in ('kind','tile','a','b','c','d')]
CALLBACK=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(Event))
class Hooks(C.Structure):
    _fields_=[('context',C.c_void_p),('event',CALLBACK)]

def inside(address):return START<=address<END or any(a<=address<b for a,b in BLOCKS)

class Original(ShieldOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.calls={};self.weaken_visits={}
        for symbol,name in [('__ZN4Game10QueueSoundE5Sound','sound'),('__ZN4Tile10UpdateTextEbbb','text'),
                            ('__ZN4Tile22GetAttackLabelPositionEv','position'),
                            ('__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif','label'),
                            ('__ZN4Game12AddParticlesEP4Tile12ParticleType','particles')]:
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol
            self.calls[int(m[1],16)]=name
    def index(self,address):
        i,rest=divmod(address-GAME-TILES,STRIDE);assert rest==0 and 0<=i<36;return i
    def hook(self,u,address,size,_):
        if inside(address):self.weaken_visits[hex(address)]=self.weaken_visits.get(hex(address),0)+1
        if address==END:u.emu_stop();return
        name=self.calls.get(address)
        if not name:return
        r=[u.reg_read(x) for x in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)];s=lambda v:C.c_int32(v).value
        if name=='position':self.label_tile=self.index(r[1]);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        if name=='sound':assert r[0]==GAME;e=[1,-1,r[1],0,0,0]
        elif name=='text':e=[2,self.index(r[0]),r[1]&0xff,r[2]&0xff,r[3]&0xff,0]
        elif name=='label':
            colour,scale=struct.unpack('<ii',u.mem_read(u.reg_read(UC_ARM_REG_SP),8))
            assert r[0]==GAME;e=[3,self.label_tile,r[1],s(r[3]),colour,scale]
        else:assert r[0]==GAME;e=[4,self.index(r[1]),r[2],0,0,0]
        self.events.append(e);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def load(self,c):
        self.u.mem_write(GAME,b'\0'*0x20000);self.write(WEAKEN,c['weaken'])
        for i,t in enumerate(c['tiles']):
            base=TILES+STRIDE*i;self.write(base+0x9c,t['type']);self.write(base+0xa4,t['attack'])
            self.u.mem_write(GAME+base+0x86,bytes([t['attack_flag']]))
    def attacks(self):return [self.read(TILES+STRIDE*i+0xa4) for i in range(36)]
    def run(self):
        self.events=[];before=bytearray(self.u.mem_read(GAME,0x20000))
        for reg,value in [(UC_ARM_REG_R8,GAME),(UC_ARM_REG_SP,TILE+0xf00),(UC_ARM_REG_LR,STOP|1)]:self.u.reg_write(reg,value)
        self.u.emu_start(START|1,STOP,timeout=1000000,count=100000)
        assert self.u.reg_read(UC_ARM_REG_PC)==END
        for i in range(36):o=TILES+STRIDE*i+0xa4;before[o:o+4]=self.u.mem_read(GAME+o,4)
        assert bytes(before)==bytes(self.u.mem_read(GAME,0x20000)),'unexpected gameplay write'
        return dict(attacks=self.attacks(),events=self.events[:])

class Native:
    def __init__(self):
        lib=C.CDLL(str(HERE/'recovered_attack_shield_native.dylib'));self.fn=lib.dr_process_attack_weaken
        self.fn.argtypes=[C.POINTER(Path),C.c_int32,C.POINTER(Hooks)];self.fn.restype=None
        self.callback=CALLBACK(lambda _,p:self.events.append([getattr(p.contents,k) for k in ('kind','tile','a','b','c','d')]))
        self.hooks=Hooks(None,self.callback)
    def load(self,c):
        self.stroke=Stroke();self.match=Match();self.match.stroke=C.pointer(self.stroke);self.path=Path();self.path.match=C.pointer(self.match)
        self.weaken=c['weaken']
        for i,t in enumerate(c['tiles']):
            self.stroke.selection.tiles[i].rule.type=t['type'];self.path.combat[i].attack=t['attack'];self.path.combat[i].attack_flag=t['attack_flag']
    def run(self):
        self.events=[];board=bytes(self.stroke);combat=[(k.defence,k.health,bytes(k.poison),k.overlay,k.flag25e,k.attack_flag) for k in self.path.combat]
        self.fn(C.byref(self.path),self.weaken,C.byref(self.hooks))
        assert bytes(self.stroke)==board and combat==[(k.defence,k.health,bytes(k.poison),k.overlay,k.flag25e,k.attack_flag) for k in self.path.combat]
        return dict(attacks=[k.attack for k in self.path.combat],events=self.events[:])

def main():
    old,new=Original(),Native();rng=random.Random(0x1487E);counts={'boundary':0,'random':0,'repeated':0};reduced=floored=0
    def compare(c,group):
        nonlocal reduced,floored
        a,b=old.run(),new.run()
        if a!=b:
            (HERE/'attack_weaken_failure.json').write_text(json.dumps(dict(case=c,original=a,native=b),indent=2))
            raise AssertionError('attack_weaken_failure.json')
        counts[group]+=1;reduced+=sum(e[0]==3 for e in a['events']);floored+=sum(v==1 for v in a['attacks'])
    def tile(type=1,attack=5,flag=0):return dict(type=type,attack=attack,attack_flag=flag)
    for weaken in (-1,0,1,2,4,100):
     for attack in (-3,0,1,2,3,5,101):
      for kind in (0,1,2,4):
       for flag in (0,1):
        tiles=[tile(2,7) for _ in range(36)];tiles[9]=tile(kind,attack,flag);tiles[27]=tile(1,attack+1,0);tiles[0]=tile(1,1,0)
        c=dict(weaken=weaken,tiles=tiles);old.load(c);new.load(c);compare(c,'boundary')
    for _ in range(600):
        c=dict(weaken=rng.choice([rng.randrange(-2,4),rng.randrange(0,40)]),
               tiles=[tile(1 if rng.random()<.5 else rng.randrange(5),rng.randrange(-2,60),int(rng.random()<.2)) for _ in range(36)])
        old.load(c);new.load(c);compare(c,'random')
    for game in range(5):
        c=dict(weaken=rng.randrange(1,6),tiles=[tile(1 if rng.random()<.6 else 2,rng.randrange(1,40),int(rng.random()<.1)) for _ in range(36)])
        old.load(c);new.load(c)
        for _ in range(15):compare(dict(game=game),'repeated')
    assert all(hex(a) in old.weaken_visits for a in (0x148aa,0x148b6,0x14b5c,0x14b9c,0x14926,0x14930)) and floored and reduced
    report=dict(status='passed',comparisons=sum(counts.values()),by_group=counts,weakened_tiles=reduced,attack_one_results=floored,
                range=dict(start=hex(START),end_exclusive=hex(END),blocks=[[hex(a),hex(b)] for a,b in BLOCKS]),
                original='Actual ProcessAttack weakening loop (Game+0xbe6c) with its out-of-line loop blocks',
                boundaries=['UpdateText/GetAttackLabelPosition/AddSimpleLabel/AddParticles/QueueSound adapted',
                            'weaken value supplied as Game+0xbe6c; its producer is not recovered','no phase scheduler'],
                scope='Shared board tile types and combat attack/attack_flag; no complete enemy phase claim',
                byte_sha256=hashlib.sha256(b''.join(old.machine.bytes_at(a,b-a) for a,b in [(START,END)]+BLOCKS)).hexdigest(),
                branch_visits=old.weaken_visits)
    (HERE/'attack_weaken_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='branch_visits'}))

if __name__=='__main__':main()
