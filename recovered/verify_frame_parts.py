#!/usr/bin/env python3
"""Actual Game::Process segments vs native (recovered_schedule), on the shared state of verify_attack_all.py:

* [0x173c8,0x1744c): falling list (original Tile::Process, as in verify_refill_integration.py) and the
  round-counter reset -> dr_reset_round_counters (native gets the falling count);
* [0x17570,0x176fc)+[0x17d64,0x17d74): attack flare fade and the current-damage label -> dr_process_flare_fade
  and dr_process_damage_label.

Segments start with R4=Game (as Game::Process sets it). Recorded and skipped (native: FrameHooks events):
Quad::SetAlpha on flares, SimpleLabel Process / Initialise / SetPosition / SetNumber on Game+0xb550,
HelpMenu::Initialise, Interface::ShowHelpBaseDmg / ShowHelpWeaponDmg (the case decides whether the latter
clears help flag 0x400, applied on both sides) and the nested Game::ProcessInput. Several frames per case.
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
from verify_new_game import Extra
from verify_turn_finish import TurnFinishFlags
from verify_selection import Point
from verify_stroke import HERE, I32, U8

FALL,FALL_END,FADE,FADE_END=0x173c8,0x1744c,0x17570,0x176fc
LABEL,FLARES,FLARE_COUNT,PHASE,HELP_FLAGS=0xb550,0xbd80,0xbd8c,0xb8a8,0x10298
SYMBOLS={'__ZN4Quad8SetAlphaEh':'alpha','__ZN11SimpleLabel7ProcessEf':'process',
         '__ZN11SimpleLabel10InitialiseE15SimpleLabelTypeRK8GLfloat2if':'init','__ZN11SimpleLabel11SetPositionERK8GLfloat2':'position',
         '__ZN11SimpleLabel9SetNumberEi':'number','__ZN8HelpMenu10InitialiseEffff8HelpType':'help',
         '__ZN9Interface15ShowHelpBaseDmgEv':'base','__ZN9Interface17ShowHelpWeaponDmgEv':'weapon','__ZN4Game12ProcessInputEv':'input'}
KINDS=dict(alpha=1,process=2,init=3,position=4,number=5,help=6,base=7,weapon=8,input=9)
class Animation(C.Structure):
    _fields_=[(k,C.c_float) for k in ('label_progress','label_y','damage_label_alpha','poison_label_alpha')]+[('flare_count',I32),('counterattack',U8)]+\
             [(k,C.c_float) for k in ('bd30','bd34','bd5c','bd60','bd64','bd68','bd6c','bd70','bd74','bd78','bd7c')]
class Touch(C.Structure):_fields_=[('phase',I32),('position',Point)]
class State(C.Structure):
    _fields_=[('path',C.c_void_p),('preview',C.c_void_p),('tokens',C.c_void_p),('extra',C.POINTER(Extra)),('animation',C.POINTER(Animation)),
              ('attack',C.c_void_p),('finish',C.POINTER(TurnFinishFlags)),('touch',C.POINTER(Touch))]
class Event(C.Structure):_fields_=[(k,I32) for k in ('kind','a','b','c')]+[('x',C.c_float),('y',C.c_float)]
EVENT=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(Event))
class Hooks(C.Structure):_fields_=[('context',C.c_void_p),('event',EVENT)]
def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
def fbits(u):return struct.unpack('<f',struct.pack('<I',u&0xffffffff))[0]
def ibits(v):return struct.unpack('<i',struct.pack('<f',v))[0]

class Original(GateOriginal):
    def __init__(self):
        super().__init__();self.framing=False;self.frame_calls={};self.frame_visits={}
        text=(HERE.parent/'armv7-disassembly.txt').read_text()
        for symbol,name in SYMBOLS.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol;self.frame_calls[int(m[1],16)]=name
    def hook(self,u,address,size,context):
        if not self.framing:return super().hook(u,address,size,context)
        if FALL<=address<FALL_END or FADE<=address<FADE_END or 0x17d64<=address<0x17d74:self.frame_visits[hex(address)]=self.frame_visits.get(hex(address),0)+1
        name=self.frame_calls.get(address);lr=u.reg_read(self.LR)
        if name is None or not (FADE<=(lr&~1)<=FADE_END or 0x17d64<=(lr&~1)<0x17d74):return super().hook(u,address,size,context)
        r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value;sp=u.reg_read(self.SP);G=self.GAME;e=None
        if name=='alpha':
            i,rest=divmod(r[0]-self.read(G+FLARES),0x70);assert rest==0
            e=[i,r[1]&0xff,s(self.read(G+0xbd90)),0.0,0.0];self.alpha_pending=True
        elif name=='process':assert r[0]==G+LABEL;e=[s(r[1]),0,0,0.0,0.0]
        elif name=='init':
            assert r[0]==G+LABEL and self.read(sp)==0x3f800000;x,y=struct.unpack('<ff',u.mem_read(r[2],8));e=[s(r[1]),s(r[3]),0,f32(x),f32(y)]
        elif name=='position':assert r[0]==G+LABEL;x,y=struct.unpack('<ff',u.mem_read(r[1],8));e=[0,0,0,f32(x),f32(y)]
        elif name=='number':assert r[0]==G+LABEL;e=[s(r[1]),0,0,0.0,0.0]
        elif name=='help':
            assert r[0]==G+HELP_FLAGS and fbits(r[3])==f32(0.05) and self.read(sp)==0;e=[s(self.read(sp+4)),0,0,f32(fbits(r[1])),f32(fbits(r[2]))]
        elif name in ('base','weapon'):
            assert r[0]==G+0x4cdc;e=[0,0,0,0.0,0.0]
            if name=='weapon' and self.clear_help:self.write(G+0x102d0,self.read(G+0x102d0)&~0x400)
        elif name=='input':assert r[0]==G and self.read(G+0x10)==3;e=[0,0,0,0.0,0.0]
        self.frame_events.append([KINDS[name],*e]);u.reg_write(self.PC,lr)
    def load(self,c):
        super().load(c);G=self.GAME;f=c['frame']
        self.write(G+FLARE_COUNT,f['flare_count']);self.write(G+PHASE,f['phase'])
        self.write(G+0xbd90,f['bd90']);self.write(G+0xbd94,f['bd94'])
        self.write(G+FLARES,0x1516000)   # flare quad storage (stride 0x70)
        self.u.mem_write(0x1516000,bytes(0x70*4))
        self.u.mem_write(G+LABEL,bytes([f['label_active']]));self.write(G+0x102d0,f['help_flags'])
        self.write(G+0x10,f['touch_phase']);self.u.mem_write(G+0x14,struct.pack('<ff',*f['touch']))
        for k,a in dict(current_damage=0xbe7c,skull_counted=0xbe80).items():
            if k=='current_damage':self.write(G+a,c['game'][k])
            else:self.u.mem_write(G+a,bytes([c['game'][k]]))
        for a,v in zip((0x165d8,0x165e8,0x165ec,0x165fc),f['ends']):self.write(G+a,v)
        self.clear_help=f['clear_help']
    def run(self,start,stop):
        u=self.u;self.frame_events=[];self.framing=True
        u.reg_write(UC_ARM_REG_R4,self.GAME);u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1)
        try:u.emu_start(start|1,stop,timeout=0,count=400000);assert u.reg_read(self.PC)==stop,hex(u.reg_read(self.PC))
        finally:self.framing=False
        G=self.GAME;s=lambda a:C.c_int32(self.read(a)).value
        return dict(events=self.frame_events,counters=[s(G+0x165d0),s(G+0x165d4)]+[s(G+0x165d8+4*i) for i in range(10)],
                    flares=[s(G+FLARE_COUNT),self.read(G+0xbd90),self.read(G+0xbd94)],
                    sizes=[[self.read(0x1516000+0x70*i+0x64),self.read(0x1516000+0x70*i+0x68)] for i in range(4)],
                    damage=s(G+0xbe7c),touch_phase=s(G+0x10),help=self.read(G+0x102d0))
    def frame(self,dt):
        self.u.mem_write(self.GAME+4,struct.pack('<f',dt))
        a=self.run(FALL,FALL_END);b=self.run(FADE,FADE_END);return [a,b]

class Native(GateNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_schedule_native.dylib'))
        self.reset_fn=lib.dr_reset_round_counters;self.reset_fn.restype=None;self.reset_fn.argtypes=[C.POINTER(State),C.c_uint32]
        self.fade_fn=lib.dr_process_flare_fade;self.fade_fn.restype=None;self.fade_fn.argtypes=[C.POINTER(State),C.c_float,C.POINTER(Hooks)]
        self.label_fn=lib.dr_process_damage_label;self.label_fn.restype=None;self.label_fn.argtypes=[C.POINTER(State),U8,C.c_float,C.POINTER(Hooks)]
        def event(_,p):
            e=p.contents;self.frame_events.append([e.kind,e.a,e.b,e.c,f32(e.x),f32(e.y)])
            if e.kind==KINDS['alpha']:self.sizes[e.a]=[e.c&0xffffffff]*2
            if e.kind==KINDS['weapon'] and self.clear_help:self.finish.help_flags_102d0&=~0x400
        self.frame_cb=EVENT(event);self.frame_hooks=Hooks(None,self.frame_cb)
    def load(self,c):
        super().load(c);f=c['frame']
        self.extra=Extra();x=self.extra;x.tokens_type0_165d8,x.tokens_type4_165e8,x.bonus_type0_165ec,x.bonus_type4_165fc=f['ends'];self.animation=Animation();self.animation.flare_count=f['flare_count'];self.damage.phase=f['phase']
        self.m.shake_progress_bd90=f['bd90'];self.m.shake_scale_bd94=f['bd94']
        self.finish=TurnFinishFlags();self.finish.help_flags_102d0=f['help_flags']
        self.touch=Touch(f['touch_phase'],Point(*f['touch']));self.label_active=f['label_active'];self.clear_help=f['clear_help']
        self.falling=len(c['moving_list']);self.sizes=[[0,0] for _ in range(4)]
        self.frame_state=State(C.cast(C.pointer(self.path_state),C.c_void_p),C.cast(C.pointer(self.p),C.c_void_p),C.c_void_p(self.q),
                               C.pointer(self.extra),C.pointer(self.animation),C.cast(C.pointer(self.damage),C.c_void_p),
                               C.pointer(self.finish),C.pointer(self.touch))
    def status(self):
        from verify_tokens import Counters
        fn=self.tokens_lib.dr_token_queue_counters;fn.restype=C.POINTER(Counters);fn.argtypes=[C.c_void_p];t=fn(C.c_void_p(self.q)).contents
        x=self.extra;s=self.state.selection
        return dict(events=self.frame_events,counters=[self.p.total,t.bonus_total,x.tokens_type0_165d8,*t.normal,x.tokens_type4_165e8,x.bonus_type0_165ec,*t.bonus,x.bonus_type4_165fc],
                    flares=[self.animation.flare_count,self.m.shake_progress_bd90,self.m.shake_scale_bd94],sizes=[list(x) for x in self.sizes],
                    damage=s.current_damage,touch_phase=self.touch.phase,help=self.finish.help_flags_102d0)
    def frame(self,dt):
        self.frame_events=[];self.reset_fn(C.byref(self.frame_state),self.falling);a=self.status()
        self.frame_events=[];self.fade_fn(C.byref(self.frame_state),dt,C.byref(self.frame_hooks))
        self.label_fn(C.byref(self.frame_state),self.label_active,dt,C.byref(self.frame_hooks));return [a,self.status()]

def case(rng):
    c,_=scenario(rng);g=c['game']
    g['current_damage']=rng.choice([0,0,4,17,-3]);g['skull_counted']=int(rng.random()<.5)
    c['path_state'].update(base_attack=g['current_damage'],direction_bonus=g['weapon_damage'])   # same Game fields (verify_path)
    if rng.random()<.5:c['path']=[];c['fake']=[]
    c['moving_list']=rng.choice([[],[],[],[rng.randrange(36)]])
    for f in c['falling']:f.update(moving=0,speed=1)
    c['preview']['total']=rng.choice([0,0,3,-1]);t=c['tokens'];t.update(bonus_total=rng.choice([0,0,2,-2]),normal=[rng.randrange(4) for _ in range(3)],bonus=[rng.randrange(4) for _ in range(3)])
    c['frame']=dict(flare_count=rng.choice([0,1,3,-1]),phase=rng.choice([0,1,2,3,4,5,8]),bd90=ibits(rng.uniform(0,1)),
                    bd94=ibits(rng.choice([1.0,0.5,0.05,0.01,0.0])),label_active=rng.randrange(2),
                    help_flags=rng.choice([0,0x400,0x400,0xffffffff,0x3ff]),touch_phase=rng.randrange(4),
                    touch=[round(rng.uniform(0,1),4),round(rng.uniform(0,1.5),4)],clear_help=int(rng.random()<.6),
                    ends=[rng.randrange(4) for _ in range(4)])   # unmodelled ends of the 5-wide token counters
    c['gate']=dict(tokens_pending=0,flare_count=0,phase=0,touch_phase=0,input_target=-1,rune=0)
    return c

def main():
    old,new=Original(),Native();rng=random.Random(0x17570);frames=0;kinds={};resets=0;cancels=0
    for n in range(300):
        c=case(rng);old.load(c);new.load(c)
        for step in range(rng.choice([1,2,4])):
            dt=rng.choice([0.0,0.0166,0.033,rng.uniform(0,0.3)])
            a,b=old.frame(dt),new.frame(dt)
            if a!=b:
                (HERE/'frame_parts_failure.json').write_text(json.dumps(dict(case=c,step=step,dt=dt,original=a,native=b),indent=2))
                raise AssertionError('frame_parts_failure.json')
            frames+=1;cancels+=any(e[0]==KINDS['input'] for e in a[1]['events'])
            for e in a[1]['events']:kinds[e[0]]=kinds.get(e[0],0)+1
            if old.frame_visits.get('0x17422'):resets=old.frame_visits['0x17422']
            new.falling=len(old.list_values(old.GAME+0xb3f8))   # falling tiles that finished were erased by Tile::Process
    names={v:k for k,v in KINDS.items()}
    assert all(kinds.get(v) for v in KINDS.values()) and resets and cancels,(kinds,resets,cancels)
    assert all(hex(x) in old.frame_visits for x in (0x175ce,0x175d6,0x17622,0x173dc,0x1740e)),'flare end / continue, phase skip, falling, path empty'
    report=dict(status='passed',frames=frames,cases=300,round_resets=resets,stroke_cancels=cancels,events={names[k]:v for k,v in sorted(kinds.items())},
                functions=[dict(symbol='__ZN4Game7ProcessEv',address='0x1717c',segments=[[hex(FALL),hex(FALL_END)],[hex(FADE),hex(FADE_END)],['0x17d64','0x17d74']],
                                native=['dr_reset_round_counters','dr_process_flare_fade','dr_process_damage_label'])],
                original='Actual Game::Process segments; original Tile::Process on falling tiles',
                boundaries=['flare SetAlpha, damage SimpleLabel calls, help 8, ShowHelpBaseDmg/WeaponDmg (case decides the 0x400 clear), nested ProcessInput recorded'],
                scope='round counters, flare fade over frames, current-damage label and the help-8 stroke cancel')
    (HERE/'frame_parts_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
