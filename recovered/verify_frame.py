#!/usr/bin/env python3
"""Actual Game::Process 0x1717c (the frame schedule) vs native dr_process_frame (recovered_schedule).

The original runs from its entry (R0=Game) to its return. Every step that is a separately verified unit
is skipped at its segment boundary and recorded (native: GameFrameHooks): ProcessInput (call 0x17d10),
board effects [0x17d22..0x173c8), falling tiles / round reset [0x173c8,0x1744c), reward tokens
[0x1744c,0x174dc) (may leave the frame at 0x17da4), particle/label pools [0x174dc,0x17570), flare fade
[0x17570,0x17622), current-damage label [0x17622,0x176fc), damage labels [0x176fc,0x17cda) (may end the
frame) and ProcessAttack. The case decides what the input step opens (menus) and whether tokens leave /
damage labels end the frame, on both sides. Recorded and skipped: UpdateTime, CalculateFPS, the screens'
Process functions, ScoreScreen::Show and Interface::Process. The frame's sound / achievement queue
counters (Game+0x13ea8/0x13eac/0x13ebc/0x13ec0) must be 0 afterwards (native: QueuesReset event).
"""
import ctypes as C
import json
import random
import re
import struct
from verify_input_gate import Original as GateOriginal, Native as GateNative
from verify_attack_all import scenario
from verify_game_over import EndGameState
from verify_selection import Point
from verify_stroke import HERE, I32, U8

ENTRY=0x1717c
QUEUES=(0x13ea8,0x13eac,0x13ebc,0x13ec0)
SCREEN_BYTES=dict(help_102a4=0x102a4,unlock_165a0=0x165a0,main_menu_c400=0xc400,score_ef6c=0xef6c,name_12c09=0x12c09,intro_c3f0=0xc3f0)
MENUS=(0x59f4,0x5b0c,0x5b9c)
ROUTES=dict(Done=0,GameOver=1,Help=2,Unlock=3,MainMenu=4,Name=5,Intro=6,Score=7,Menu=8,MenuAfterInput=9,TokensExit=10,Ended=11)
SCREENS={'__ZN14GameOverScreen7ProcessEf':'GameOver','__ZN8HelpMenu7ProcessEf':'Help','__ZN10UnlockMenu7ProcessEf':'Unlock',
         '__ZN8MainMenu7ProcessEf':'MainMenu','__ZN10NameScreen7ProcessEf':'Name','__ZN11IntroScreen7ProcessEf':'Intro',
         '__ZN11ScoreScreen7ProcessEf':'Score'}
OTHER={'__ZN4Game10UpdateTimeEv':'time','__ZN4Game12CalculateFPSEv':'fps','__ZN11ScoreScreen4ShowE8GameModeb':'show_mode',
       '__ZN11ScoreScreen4ShowE10Difficultyb':'show_difficulty','__ZN9Interface7ProcessEfb':'interface',
       '__ZN4Game12ProcessInputEv':'input','__ZN4Game13ProcessAttackEv':'attack'}
# step segment start -> (step, next pc, exit pc for a step that may leave the frame)
JUMPS={0x17d22:('effects',0x173c8,None),0x173c8:('falling',0x1744c,None),0x1744c:('tokens',0x174dc,0x17da4),
       0x174dc:('pools',0x17570,None),0x17570:('flare_fade',0x17622,None),0x17622:('damage_label',0x176fc,None),
       0x176fc:('damage_labels',0x17cda,0x17da4)}
KINDS=dict(queues=1,time=2,fps=3,screen=4,show=5,interface=6,input=10,effects=11,falling=12,tokens=13,pools=14,flare_fade=15,
           damage_label=16,damage_labels=17,attack=18)
class Screens(C.Structure):_fields_=[(k,U8) for k in SCREEN_BYTES]+[('game_over_state_cc1c',I32),('menus',U8*3)]
class Touch(C.Structure):_fields_=[('phase',I32),('position',Point)]
class Frame(C.Structure):
    _fields_=[('touch',C.POINTER(Touch)),('end',C.POINTER(EndGameState)),('screens',C.POINTER(Screens)),('stroke',C.c_void_p),
              ('match',C.c_void_p),('path',C.c_void_p)]
class Event(C.Structure):_fields_=[(k,I32) for k in ('kind','a','b')]
EVENT=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(Event))
STEP=C.CFUNCTYPE(None,C.c_void_p);FLAG=C.CFUNCTYPE(C.c_bool,C.c_void_p)
class Hooks(C.Structure):
    _fields_=[('context',C.c_void_p),('event',EVENT),('input',STEP),('effects',STEP),('falling',STEP),('tokens',FLAG),('pools',STEP),
              ('flare_fade',STEP),('damage_label',STEP),('damage_labels',FLAG),('attack',STEP)]

class Original(GateOriginal):
    def __init__(self):
        super().__init__();self.framing=False;self.frame_calls={};self.frame_visits={}
        text=(HERE.parent/'armv7-disassembly.txt').read_text()
        for symbol,name in {**SCREENS,**OTHER}.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol;self.frame_calls[int(m[1],16)]=name
        assert re.search(r'^__ZN4Game7ProcessEv:\n\s*1717c:',text,re.M)
    def hook(self,u,address,size,context):
        if not self.framing:return super().hook(u,address,size,context)
        if ENTRY<=address<0x17db8:self.frame_visits[hex(address)]=self.frame_visits.get(hex(address),0)+1
        if address in JUMPS:
            step,next_pc,exit_pc=JUMPS[address];self.events.append([KINDS[step],0,0])
            leave=exit_pc is not None and self.case_frame[step+'_leave']
            u.reg_write(self.PC,(exit_pc if leave else next_pc)|1);return
        name=self.frame_calls.get(address)
        if name is None:return super().hook(u,address,size,context)
        lr=u.reg_read(self.LR);r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value;G=self.GAME
        if name in SCREENS.values():e=[KINDS['screen'],ROUTES[name],0]
        elif name=='time':e=[KINDS['time'],0,0]
        elif name=='fps':e=[KINDS['fps'],0,0]
        elif name in ('show_mode','show_difficulty'):assert r[2]==1;e=[KINDS['show'],s(r[1]),int(name=='show_mode')]
        elif name=='interface':assert r[0]==G+0x4cdc;e=[KINDS['interface'],r[2]&0xff,0]
        elif name=='input':
            assert r[0]==G and (lr&~1)==0x17d14,hex(lr);e=[KINDS['input'],0,0]
            for a,v in zip(MENUS,self.case_frame['menus_after']):self.u.mem_write(G+a,bytes([v]))
        elif name=='attack':assert r[0]==G;e=[KINDS['attack'],0,0]
        self.events.append(e);u.reg_write(self.PC,lr)
    def load(self,c):
        super().load(c);G=self.GAME;f=c['frame'];self.case_frame=f
        self.u.mem_write(G+0xcac4,bytes([f['game_over']]));self.write(G+0xcc1c,f['game_over_state'])
        for k,a in SCREEN_BYTES.items():self.u.mem_write(G+a,bytes([f[k]]))
        for a,v in zip(MENUS,f['menus']):self.u.mem_write(G+a,bytes([v]))
        for a in QUEUES:self.write(G+a,7)
        self.write(G+0x10,f['touch_phase']);self.u.mem_write(G+0x5e14,bytes([f['input_ready']]))
        self.u.mem_write(G+0x14aed,bytes([f['record']]));self.write(G+0x14ae8,f['mode']);self.write(G+0x14ae0,f['difficulty'])
    def run(self):
        u=self.u;self.events=[];self.framing=True
        u.reg_write(self.regs[0],self.GAME);u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1)
        try:u.emu_start(ENTRY|1,self.STOP,timeout=0,count=200000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.framing=False
        assert all(self.read(self.GAME+a)==0 for a in QUEUES)
        events=self.events[:2]+[[KINDS['queues'],0,0]]+self.events[2:]
        return dict(events=events,touch_phase=C.c_int32(self.read(self.GAME+0x10)).value)

class Native(GateNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_schedule_native.dylib'))
        self.frame_fn=lib.dr_process_frame;self.frame_fn.restype=I32;self.frame_fn.argtypes=[C.POINTER(Frame),C.c_float,C.POINTER(Hooks)]
        def event(_,p):
            e=p.contents;k=e.kind
            self.events.append([KINDS['screen'],e.a,0] if k==4 else [KINDS['show'],e.a,e.b] if k==5 else [KINDS['interface'],e.a,0] if k==6 else [k,0,0])
        def step(name):
            def run(_):
                self.events.append([KINDS[name],0,0])
                if name=='input':self.screens.menus=(U8*3)(*self.case_frame['menus_after'])
            return STEP(run)
        def flag(name,leave_value):
            def run(_):self.events.append([KINDS[name],0,0]);return bool(self.case_frame[name+'_leave'])==leave_value
            return FLAG(run)
        self.callbacks=dict(event=EVENT(event),input=step('input'),effects=step('effects'),falling=step('falling'),
                            tokens=flag('tokens',False),pools=step('pools'),flare_fade=step('flare_fade'),damage_label=step('damage_label'),
                            damage_labels=flag('damage_labels',True),attack=step('attack'))
        self.frame_hooks=Hooks(None,*[self.callbacks[k] for k,_ in Hooks._fields_[1:]])
    def load(self,c):
        super().load(c);f=c['frame'];self.case_frame=f
        self.end=EndGameState();self.end.game_over_screen=f['game_over']
        self.screens=Screens(*[f[k] for k in SCREEN_BYTES],f['game_over_state'],(U8*3)(*f['menus']))
        self.touch=Touch(f['touch_phase'],Point(0,0))
        s=self.state;s.record=f['record'];s.mode=f['mode'];self.m.spawn_enabled_14ae0=f['difficulty'];self.path_state.input_ready=f['input_ready']
        self.frame=Frame(C.pointer(self.touch),C.pointer(self.end),C.pointer(self.screens),C.cast(C.pointer(s),C.c_void_p),
                         C.cast(C.pointer(self.m),C.c_void_p),C.cast(C.pointer(self.path_state),C.c_void_p))
    def run(self):
        self.events=[];route=self.frame_fn(C.byref(self.frame),0.0166,C.byref(self.frame_hooks))
        self.route=route;return dict(events=self.events,touch_phase=self.touch.phase)

def case(rng):
    c,_=scenario(rng)
    pick=lambda p:int(rng.random()<p)
    f=dict(game_over=pick(.1),game_over_state=rng.choice([3,3,0,2]),touch_phase=rng.randrange(5),input_ready=rng.randrange(2),
           record=rng.randrange(2),mode=rng.randrange(3),difficulty=rng.randrange(3),
           menus=[pick(.07),pick(.07),pick(.07)],menus_after=[pick(.07),pick(.07),pick(.07)],tokens_leave=pick(.1),damage_labels_leave=pick(.1))
    for k in SCREEN_BYTES:f[k]=pick(.08)
    c['frame']=f;c['moving_list']=[];c['gate']=dict(tokens_pending=0,flare_count=0,phase=0,touch_phase=0,input_target=-1,rune=0)
    return c

def main():
    old,new=Original(),Native();rng=random.Random(0x1717c);routes={};compared=0
    for n in range(1500):
        c=case(rng);old.load(c);new.load(c);a,b=old.run(),new.run()
        if a!=b:
            (HERE/'frame_failure.json').write_text(json.dumps(dict(case=c['frame'],original=a,native=b,route=new.route),indent=2))
            raise AssertionError('frame_failure.json')
        compared+=1;routes[new.route]=routes.get(new.route,0)+1
    names={v:k for k,v in ROUTES.items()}
    assert len(routes)==len(ROUTES),{names[k]:v for k,v in routes.items()}
    report=dict(status='passed',comparisons=compared,routes={names[k]:v for k,v in sorted(routes.items())},
                functions=[dict(symbol='__ZN4Game7ProcessEv',address=hex(ENTRY),native='dr_process_frame')],
                original='Actual Game::Process control flow from its entry to its return',
                boundaries=['verified steps skipped at their segment boundaries and recorded (GameFrameHooks)',
                            'screens, ScoreScreen::Show, Interface::Process, UpdateTime, CalculateFPS recorded'],
                scope='screen gates and touch consumption, in-game menus before/after input, step order, frame exits')
    (HERE/'frame_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
