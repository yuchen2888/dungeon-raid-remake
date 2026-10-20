#!/usr/bin/env python3
"""Actual Game::ProcessInput 0x16638 as a whole vs native dr_process_input (recovered_schedule), on the shared
state of verify_attack_all.py.

The original runs from its entry to its return for every touch phase and gate state. It composes units
verified separately (verify_input_gate, verify_stroke, verify_rune / verify_preview through the stroke
callbacks, verify_release); this test checks the dispatch between them and their composition on one state.
As in the chain tests, ProcessRune and ProcessResourceShadows run as original code (native: dr_process_rune /
dr_preview_resources through the stroke callbacks). For a release (phase 2) the calls made by the release
code itself are recorded as in verify_release.py (MatchTiles adds the case counts on both sides); other
boundaries are those of the stroke / selection harnesses. EndOfTurn is recorded.
"""
import copy
import ctypes as C
import json
import random
from verify_release import (Original as ReleaseOriginal, Native as ReleaseNative, case as release_case, Hooks as ReleaseHooks,
                            ReleaseState, Inputs as ReleaseInputs, ScrollState, REVENGE, REVENGE_END)
from verify_input_gate import Original as GateOriginal, Inputs as GateInputs, ScheduleHooks
from verify_selection import INTS, BYTES, TBYTES, snapshot, Hooks as SelectionHooks
from verify_rune import Rune
from verify_path import Path
from verify_stroke import HERE, I32, U8

ENTRY=0x16638
RELEASE_CODE=[(0x16890,0x16e10),(REVENGE,REVENGE_END),(0x111a38,0x111a88),(0xbe30,0xbe58)]
ROUTES=['blocked','attack_started','idle','begin','update','cancel','release','scroll','scroll_ended']
class InputState(C.Structure):
    _fields_=[('path',C.POINTER(Path)),('damage',C.c_void_p),('rune',C.POINTER(Rune)),('gate_inputs',C.POINTER(GateInputs)),
              ('release',C.POINTER(ReleaseState)),('release_inputs',C.POINTER(ReleaseInputs)),('scroll',C.POINTER(ScrollState))]
class InputHooks(C.Structure):
    _fields_=[('schedule',C.POINTER(ScheduleHooks)),('selection',C.POINTER(SelectionHooks)),('release',C.POINTER(ReleaseHooks))]

class Original(ReleaseOriginal):
    def __init__(self):
        super().__init__()
        for a,n in list(self.release_calls.items()):
            if n=='rune':del self.release_calls[a]   # ProcessRune runs as original code (chain rune harness)
    def hook(self,u,address,size,context):
        if self.releasing and address in self.release_calls:
            lr=u.reg_read(self.LR)&~1
            if not any(a<=lr<b for a,b in RELEASE_CODE):return GateOriginal.hook(self,u,address,size,context)
        return super().hook(u,address,size,context)
    def run_input(self,phase,touch,gate):
        G=self.GAME;u=self.u
        self.write(G+0x10,phase);u.mem_write(G+0x14,__import__('struct').pack('<ff',*touch))
        self.write(G+0xb8a8,gate['phase']);u.mem_write(G+0x5e14,bytes([gate['input_ready']]));self.write(G+0x58ac,gate['input_target'])
        self.write(G+0xb52c,gate['tokens_pending']);self.write(G+0xbd8c,gate['flare_count'])
        self.events=[];self.release_events=[];self.gate_events=[];self.run_visits=set();self.int_vectors={};self.route=None
        self.releasing=phase==2;self.gating=True
        u.reg_write(self.regs[0],G);u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1)
        try:u.emu_start(ENTRY|1,self.STOP,timeout=0,count=3000000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.releasing=self.gating=False
        game=dict(self.case['game'])
        for k,a in INTS.items():game[k]=C.c_int32(self.read(G+a)).value
        for k,a in BYTES.items():game[k]=u.mem_read(G+a,1)[0]
        board=copy.deepcopy(self.case['board'])
        for i,t in enumerate(board):
            for k,a in TBYTES.items():t[k]=u.mem_read(self.tile(i)+a,1)[0]
        sel=snapshot(self.case,game,[self.index(p) for p in self.list_values(G+0xb3d8)],[self.index(f) for f in self.fake],board,self.events)
        self.route=self.route or 0;status=self.status();status.pop('events');status.pop('route',None)
        for k in ('path','fake'):status.pop(k)   # the selection snapshot has them (b3f4 is not kept by the set intercepts)
        return dict(selection=sel,release=status,release_events=self.release_events,gate_events=self.gate_events,rune=self.rune_status(),
                    gate=dict(phase=C.c_int32(self.read(G+0xb8a8)).value,input_ready=u.mem_read(G+0x5e14,1)[0],touch_phase=C.c_int32(self.read(G+0x10)).value))
    def rune_status(self):return self.status_rune() if hasattr(self,'status_rune') else None

class Native(ReleaseNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_schedule_native.dylib'))
        self.input_fn=lib.dr_process_input;self.input_fn.restype=I32;self.input_fn.argtypes=[C.POINTER(InputState),C.POINTER(InputHooks)]
    def load(self,c):
        super().load(c)
        # verify_input_gate.Native.load replaces the rune state; restore the chain's (case rune, gate highlight count),
        # matching the original, where the gate loader writes the highlight count last.
        self.rune=Rune(**c['rune']);self.rune.highlights=c['gate']['rune']
    def run_input(self,phase,touch,gate):
        s=self.state.selection;s.touch.x,s.touch.y=touch
        self.gate_inputs=GateInputs(len(self.case['moving_list']),gate['tokens_pending'],gate['flare_count'],phase,gate['input_target'])
        self.damage.phase=gate['phase'];self.path_state.input_ready=gate['input_ready']
        self.events=[];self.release_events=[];self.gate_events=[]
        state=InputState(C.pointer(self.path_state),C.cast(C.pointer(self.damage),C.c_void_p),C.pointer(self.rune),C.pointer(self.gate_inputs),
                         C.pointer(self.release_state),C.pointer(self.inputs),C.pointer(self.scroll_state))
        hooks=InputHooks(C.pointer(self.schedule_hooks),C.pointer(self.hooks),C.pointer(self.release_hooks))
        self.route=ROUTES[self.input_fn(C.byref(state),C.byref(hooks))]
        game=dict(self.case['game'])
        for k in (*INTS,*BYTES):game[k]=getattr(s,k)
        board=copy.deepcopy(self.case['board'])
        for i,t in enumerate(s.tiles):
            for k in TBYTES:board[i][k]=getattr(t,k)
        sel=snapshot(self.case,game,list(s.path[:s.path_length]),[i for i,v in enumerate(s.fake) if v],board,self.events)
        r=self.release_status()
        return dict(selection=sel,release=r,release_events=self.release_events,gate_events=self.gate_events,rune=None,
                    gate=dict(phase=self.damage.phase,input_ready=self.path_state.input_ready,touch_phase=phase))
    def release_status(self):
        s=self.state.selection;f=self.flights;b=self.path_state.battle
        st=dict(selection={k:getattr(s,k) for k in ['current_damage','current_leech','current_flame_damage','current_spike_damage','flame_label_moving','spike_label_moving']},
                flights={k:[__import__('verify_release').f32(x) for x in (getattr(f,k).arc,getattr(f,k).start.x,getattr(f,k).start.y,getattr(f,k).progress,getattr(f,k).speed)] for k in ('flame','spike','leech')},
                counters=dict(kills_b=b.kills_b,killed_attack=b.killed_attack,generated_count=self.gen.generated_count,generated_enemies=self.gen.generated_enemies),
                flag_1554c=self.finish.flag_1554c,health=[self.r.health,self.r.ui_health],attack=[t.attack for t in self.path_state.combat],
                seeds=list(self.m.random.seeds),
                classes=[c.level for c in self.classes],match_view=[self.m.class_level]+list(self.m.unlocked))
        return st

def case(rng,n):
    c=release_case(rng,n,n%7==0)
    phase=rng.choice([0,1,1,2,2,2,3,4])
    if phase in (1,4) and rng.random()<.5:   # begin: empty path, touch on or near a tile
        c['path']=[];c['fake']=[]
        for t in c['board']:t['selected']=0
    t=c['board'][rng.randrange(36)]['center'];touch=[t[0]+rng.uniform(-.05,.05),t[1]+rng.uniform(-.05,.05)]
    blocked=rng.random()<.2
    gate=dict(phase=rng.choice([0,0,0,0,8,8,3]) if blocked else rng.choice([0,0,0,8]),input_ready=rng.choice([1,1,1,0]),
              input_target=rng.choice([-1,-1,-1,-1,0]),tokens_pending=int(blocked and rng.random()<.4),flare_count=int(blocked and rng.random()<.4))
    return c,phase,touch,gate

def main():
    old,new=Original(),Native();rng=random.Random(0x16639);routes={};compared=0
    for n in range(1500):
        c,phase,touch,gate=case(rng,n);old.load(c);new.load(c)
        a,b=old.run_input(phase,touch,gate),new.run_input(phase,touch,gate)
        a['rune']=b['rune']=None
        if a!=b:
            (HERE/'process_input_failure.json').write_text(json.dumps(dict(case=c,phase=phase,touch=touch,gate=gate,route=new.route,original=a,native=b),indent=2))
            raise AssertionError('process_input_failure.json')
        compared+=1;routes[new.route]=routes.get(new.route,0)+1
    assert set(routes)==set(ROUTES),routes
    report=dict(status='passed',comparisons=compared,routes=routes,
                functions=[dict(symbol='__ZN4Game12ProcessInputEv',address=hex(ENTRY),native='dr_process_input')],
                original='Actual ProcessInput from its entry to its return; original ProcessRune / ProcessResourceShadows (native through the stroke callbacks)',
                boundaries=['release calls recorded as in verify_release.py','stroke/selection boundaries as in verify_stroke.py','EndOfTurn recorded'],
                scope='gate outcomes, touch dispatch by phase and path, composition of gate, stroke, rune, release and class scroll on one state')
    (HERE/'process_input_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
