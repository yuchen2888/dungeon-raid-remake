#!/usr/bin/env python3
"""Actual Game::Process board-effects segment (0x17d22 -> 0x1733a/0x17386 -> 0x173c8, with the effect loop
block [0x17d32,0x17d56)) including Game::ProcessShieldShatter 0x9784 and Tile::ProcessEffects 0x3dcfc vs
native dr_process_board_effects (recovered_schedule), on the shared state of verify_attack_all.py.

The original runs from 0x17d22 (R4=Game, as Game::Process sets it) until 0x173c8 (the falling list).
RandI, Interpolate and the poison-effect arithmetic run as original code. Recorded and skipped (native:
BoardEffectHooks events): HelpMenu::Initialise, Game::ProcessShieldChunk (chunk quads), Quad::SetColour
and Tile::UpdateText. The spin update (Tile+0x220 += dt * Tile+0x228, only when flag_224 is set, which the
game never does) is recorded by a code hook at 0x3dd12. Each case runs several frames on carried state.
Also compares Game::InialiseShieldShatter 0x9810 with dr_initialise_shield_shatter.
"""
import ctypes as C
import json
import random
import re
import struct
import verify_original
from unicorn.arm_const import UC_ARM_REG_R4
from verify_input_gate import Original as GateOriginal, Native as GateNative
from verify_attack_all import scenario
from verify_stroke import HERE, I32, U8

ENTRY,END=0x17d22,0x173c8
INIT=0x9810
SPIN=0x3dd12
HELP_FLAGS,SHATTER_ACTIVE,SHATTER_PROGRESS=0x102d0,0xbf88,0xbf8c
CHUNKS={0xbea8:(0,-1.0),0xbf18:(1,1.0)}
SYMBOLS={'__ZN8HelpMenu10InitialiseEffff8HelpType':'help','__ZN4Game18ProcessShieldChunkER4Quadf8GLfloat2':'chunk',
         '__ZN4Quad9SetColourERK9GLcolour4':'colour','__ZN4Tile10UpdateTextEbbb':'text','__ZN4Quad8SetAlphaEh':'alpha'}
KINDS=dict(help=1,init=2,chunk=3,spin=4,colour=5,text=6)
class Shatter(C.Structure):_fields_=[('active',U8),('progress',C.c_float)]
class State(C.Structure):_fields_=[('path',C.c_void_p),('generation',C.c_void_p),('finish',C.c_void_p),('shatter',C.POINTER(Shatter))]
class Event(C.Structure):_fields_=[(k,I32) for k in ('kind','tile','a','b','c')]+[('x',C.c_float),('y',C.c_float)]
EVENT=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(Event))
class Hooks(C.Structure):_fields_=[('context',C.c_void_p),('event',EVENT)]
from verify_turn_finish import TurnFinishFlags
def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
def fbits(u):return struct.unpack('<f',struct.pack('<I',u&0xffffffff))[0]
def ibits(v):return struct.unpack('<i',struct.pack('<f',v))[0]

class Original(GateOriginal):
    def __init__(self):
        super().__init__();self.effecting=False;self.effect_calls={};self.effect_visits={}
        text=(HERE.parent/'armv7-disassembly.txt').read_text()
        for symbol,name in SYMBOLS.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol;self.effect_calls[int(m[1],16)]=name
        assert re.search(r'^__ZN4Tile14ProcessEffectsEf:\n\s*3dcfc:',text,re.M) and re.search(r'^__ZN4Game20ProcessShieldShatterEv:\n\s*9784:',text,re.M)
    def hook(self,u,address,size,context):
        if not self.effecting:return super().hook(u,address,size,context)
        if 0x17322<=address<END or 0x17d22<=address<0x17d56 or 0x9784<=address<0x9800 or 0x3dcfc<=address<0x3de44 or INIT<=address<0x9882:
            self.effect_visits[hex(address)]=self.effect_visits.get(hex(address),0)+1
        lr=u.reg_read(self.LR);r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value
        if address==SPIN:self.effect_events.append([KINDS['spin'],self.index(r[0]),ibits(fbits(r[1])),0,0,0.0,0.0])
        name=self.effect_calls.get(address)
        if name is None:return super().hook(u,address,size,context)
        sp=u.reg_read(self.SP);e=None
        if name=='help':
            assert r[0]==self.GAME+0x10298 and r[3]==0 and self.read(sp)==0
            x,y=fbits(r[1]),fbits(r[2]);e=[KINDS['help'],self.help_tile(x,y),s(self.read(sp+4)),0,0,f32(x),f32(y)]
        elif name=='chunk':
            chunk,direction=CHUNKS[r[1]-self.GAME];assert r[0]==self.GAME and fbits(r[2])==direction;e=[KINDS['chunk'],-1,chunk,0,0,0.0,0.0]
        elif name=='colour':
            rgba=u.mem_read(r[1],4);assert rgba[3]==self.u.mem_read(r[0]+0xf,1)[0];e=[KINDS['colour'],self.index(r[0]),*rgba[:3],0.0,0.0]
        elif name=='text':e=[KINDS['text'],self.index(r[0]),r[1],r[2],r[3],0.0,0.0]
        elif name=='alpha':
            if INIT<(lr&~1)<0x9882:assert r[1]==0xff;u.reg_write(self.PC,lr);return   # chunk quads (presentation)
            return super().hook(u,address,size,context)
        self.effect_events.append(e);u.reg_write(self.PC,lr)
    def help_tile(self,x,y):
        for i in range(36):
            if struct.unpack('<ff',self.u.mem_read(self.GAME+0xb400+8*i,8))==(x,y):return i
        raise AssertionError((x,y))
    def load(self,c):
        super().load(c);G=self.GAME;e=c['effects']
        self.write(G+HELP_FLAGS,e['help_flags']);self.u.mem_write(G+SHATTER_ACTIVE,bytes([e['shatter_active']]))
        self.u.mem_write(G+SHATTER_PROGRESS,struct.pack('<f',e['shatter_progress']))
        for i in range(36):self.u.mem_write(self.tile(i)+0xf,bytes([0xc8]))   # quad colour alpha (kept by SetColour)
    def status(self):
        G=self.GAME;u=self.u
        poison=[list(u.mem_read(self.tile(i)+0x244,2))+[self.read(self.tile(i)+0x248)] for i in range(36)]
        return dict(events=self.effect_events,shatter=[u.mem_read(G+SHATTER_ACTIVE,1)[0],self.read(G+SHATTER_PROGRESS)],poison=poison,
                    seeds=list(struct.unpack('<6I',u.mem_read(0x1eac20,24))))
    def run(self,start,stop,regs):
        u=self.u;self.effect_events=[];self.effecting=True
        for reg,v in regs.items():u.reg_write(reg,v)
        u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1)
        try:u.emu_start(start|1,stop,timeout=0,count=300000);assert u.reg_read(self.PC)==stop,hex(u.reg_read(self.PC))
        finally:self.effecting=False
        return self.status()
    def frame(self,dt):
        self.u.mem_write(self.GAME+4,struct.pack('<f',dt));return self.run(ENTRY,END,{UC_ARM_REG_R4:self.GAME})
    def initialise(self):return self.run(INIT,self.STOP,{self.regs[0]:self.GAME})

class Native(GateNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_schedule_native.dylib'))
        self.effects_fn=lib.dr_process_board_effects;self.effects_fn.restype=None
        self.effects_fn.argtypes=[C.POINTER(State),C.c_float,C.POINTER(Hooks)]
        self.init_fn=lib.dr_initialise_shield_shatter;self.init_fn.restype=None;self.init_fn.argtypes=[C.POINTER(Shatter),C.POINTER(Hooks)]
        def event(_,p):e=p.contents;self.effect_events.append([e.kind,e.tile,e.a,e.b,e.c,f32(e.x),f32(e.y)])
        self.effect_cb=EVENT(event);self.effect_hooks=Hooks(None,self.effect_cb)
    def load(self,c):
        super().load(c);e=c['effects']
        self.finish=TurnFinishFlags();self.finish.help_flags_102d0=e['help_flags']
        self.shatter=Shatter(e['shatter_active'],e['shatter_progress'])
        self.effect_state=State(C.cast(C.pointer(self.path_state),C.c_void_p),C.cast(C.pointer(self.gen),C.c_void_p),
                                C.cast(C.pointer(self.finish),C.c_void_p),C.pointer(self.shatter))
    def status(self):
        poison=[[t.poison.active,t.poison.clearing,t.poison.progress] for t in self.path_state.combat]
        return dict(events=self.effect_events,shatter=[self.shatter.active,struct.unpack('<I',struct.pack('<f',self.shatter.progress))[0]],
                    poison=poison,seeds=list(self.m.random.seeds))
    def frame(self,dt):
        self.effect_events=[];self.effects_fn(C.byref(self.effect_state),dt,C.byref(self.effect_hooks));return self.status()
    def initialise(self):
        self.effect_events=[];self.init_fn(C.byref(self.shatter),C.byref(self.effect_hooks))
        self.effect_events=[e for e in self.effect_events if e[0]!=KINDS['init']];return self.status()

def case(rng):
    c,_=scenario(rng)
    for i,k in enumerate(c['combat']):
        p=k['poison'];active=int(rng.random()<.3);clearing=int(rng.random()<.2)
        k['poison']=p[:3]+[active,clearing,struct.unpack('<I',struct.pack('<f',rng.choice([0.0,0.5,0.9,0.99,rng.random()])))[0]]
    c['effects']=dict(help_flags=rng.choice([0,0,1,0x11,0xfffe,0xffffffff]),shatter_active=int(rng.random()<.5),
                      shatter_progress=rng.choice([0.0,0.4,0.95,0.995,1.0,rng.random()]))   # 1.0 with dt 0 stays active (> 1 ends)
    c['moving_list']=[];c['gate']=dict(tokens_pending=0,flare_count=0,phase=0,touch_phase=0,input_target=-1,rune=0)
    return c

def main():
    old,new=Original(),Native();rng=random.Random(0x3dcfc);frames=0;kinds={}
    for n in range(250):
        c=case(rng)
        spin=rng.random()<.2
        old.load(c);new.load(c)
        if spin:   # flag_224 and its floats: never set by the game, exercised here
            for i in rng.sample(range(36),3):
                old.u.mem_write(old.tile(i)+0x224,b'\1');old.u.mem_write(old.tile(i)+0x220,struct.pack('<f',0.5));old.u.mem_write(old.tile(i)+0x228,struct.pack('<f',2.0));new.gen.tiles[i].flag224=1
        if n%10==0:
            a,b=old.initialise(),new.initialise()
            assert a==b,('initialise',a['shatter'],b['shatter'])
        for step in range(rng.choice([1,2,5])):
            dt=rng.choice([0.0,0.0166,0.033,rng.uniform(0,0.4)])
            a,b=old.frame(dt),new.frame(dt)
            if a!=b:
                (HERE/'board_effects_failure.json').write_text(json.dumps(dict(case=c,step=step,dt=dt,original=a,native=b),indent=2))
                raise AssertionError('board_effects_failure.json')
            frames+=1
            for e in a['events']:kinds[e[0]]=kinds.get(e[0],0)+1
    names={v:k for k,v in KINDS.items()}
    assert all(kinds.get(KINDS[k]) for k in ('help','chunk','spin','colour','text')),kinds
    assert all(hex(x) in old.effect_visits for x in (0x97ba,0x97c4,0x3dd38,0x3de20)),'shatter end/continue, effect, effect end'
    report=dict(status='passed',frames=frames,cases=250,events={names[k]:v for k,v in sorted(kinds.items())},
                functions=[dict(symbol='__ZN4Game7ProcessEv',address='0x1717c',segment=[hex(ENTRY),hex(END)],native='dr_process_board_effects'),
                           dict(symbol='__ZN4Game20ProcessShieldShatterEv',address='0x9784',native='in dr_process_board_effects'),
                           dict(symbol='__ZN4Tile14ProcessEffectsEf',address='0x3dcfc',native='in dr_process_board_effects'),
                           dict(symbol='__ZN4Game21InialiseShieldShatterEv',address=hex(INIT),native='dr_initialise_shield_shatter')],
                original='Actual segment with original RandI, Interpolate and effect arithmetic',
                boundaries=['HelpMenu::Initialise, ProcessShieldChunk, Quad::SetColour/SetAlpha, Tile::UpdateText recorded',
                            'spin floats Tile+0x220/0x228 are renderer-owned (flag_224 is never set by the game)'],
                scope='first-game help RNG, shield shatter progress, poison effect fade over carried frames')
    (HERE/'board_effects_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
