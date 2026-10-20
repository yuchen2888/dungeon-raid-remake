#!/usr/bin/env python3
"""Whole frames of play: the original Game::Process vs native dr_process_frame (T040-F3).

Same carried state and turns as verify_full_turn.py, but every frame is one call of the ORIGINAL Game::Process
(from its entry to its return) and one call of the NATIVE frame schedule dr_process_frame, whose
GameFrameHooks are wired to the native units: input -> dr_process_input (with MatchTiles -> dr_commit_path and
MoveMatchedTiles -> dr_move_matched_tiles, EndOfTurn -> dr_end_of_turn), effects -> dr_process_board_effects,
falling -> the falling list (dr_process_falling_list) or dr_reset_round_counters, tokens ->
dr_process_reward_tokens, flare fade, damage label, damage labels and attack -> dr_process_attack.
Inside the original Process each verified step's harness is switched on at its segment boundaries (as in the
unit tests); presentation-only calls of the board-effects and label segments, UpdateTime, CalculateFPS and
Interface::Process are skipped (their events are compared by the unit tests, not here). After every frame
the game state is compared: board, selection, battle, generation/refill, tokens, resources, attack
animation, gate and turn fields. No screen is open.
"""
import ctypes as C
import json
import random
import re
import struct
import verify_original
from unicorn.arm_const import UC_ARM_REG_R4
from verify_full_turn import Original as TurnOriginal, Native as TurnNative, case as turn_case, f32, ROUTES
from verify_process_input import InputState, InputHooks
from verify_input_gate import Inputs as GateInputs
from verify_frame import Frame, Screens, Touch, Hooks as FrameHooks, EVENT as FRAME_EVENT, STEP, FLAG, ROUTES as FRAME_ROUTES
from verify_board_effects import State as EffectsState, Shatter, Hooks as EffectHooks, EVENT as EFFECT_EVENT
from verify_frame_parts import State as PartsState, Hooks as PartsHooks, EVENT as PARTS_EVENT, Animation, Touch as PartsTouch
from verify_damage_labels import State as LabelsState, Hooks as LabelsHooks, EVENT as LABELS_EVENT, CHECK as LABELS_CHECK
from verify_turn_finish import TurnFinishFlags
from verify_new_game import Extra
from verify_selection import Point, INTS, BYTES, TBYTES
from verify_rune import Rune
from verify_stroke import HERE, I32, U8

PROCESS,PROCESS_END=0x1717c,0x17db8
CHECK_END=0x10b18
GAMES,TURNS=6,4
POWF=0x194f40
SKIP={'__ZN4Game10UpdateTimeEv','__ZN4Game12CalculateFPSEv','__ZN9Interface7ProcessEfb','__ZN8HelpMenu10InitialiseEffff8HelpType',
      '__ZN4Game18ProcessShieldChunkER4Quadf8GLfloat2','__ZN11SimpleLabel7ProcessEf','__ZN11SimpleLabel10InitialiseE15SimpleLabelTypeRK8GLfloat2if',
      '__ZN11SimpleLabel11SetPositionERK8GLfloat2','__ZN11SimpleLabel9SetNumberEi','__ZN11SimpleLabel8SetAlphaEh',
      '__ZN9Interface15ShowHelpBaseDmgEv','__ZN9Interface17ShowHelpWeaponDmgEv'}
PRESENT={'__ZN4Quad9SetColourERK9GLcolour4','__ZN4Tile10UpdateTextEbbb','__ZN4Game10QueueSoundE5Sound',
         '__ZN4Game16QueueAchievementE11Achievementf','__ZN9Interface15UpdateHealthBarER4Quadi'}
# Process code ranges whose own presentation calls are skipped (effects incl. ProcessShieldShatter /
# Tile::ProcessEffects, tokens loop sound, damage label, damage labels)
OWN=[(0x1733a,0x173c8),(0x17d22,0x17d56),(0x9784,0x9800),(0x3dcfc,0x3de44),(0x1744c,0x174dc),(0x17570,0x17cda),(0x17d64,0x17da4)]

class Original(TurnOriginal):
    def __init__(self):
        super().__init__();self.processing=False;self.attack_return=None
        text=(HERE.parent/'armv7-disassembly.txt').read_text()
        addr=lambda s:int(re.search(r'^'+re.escape(s)+r':\n\s*([0-9a-f]+):',text,re.M)[1],16)
        self.skip_calls={addr(s) for s in SKIP};self.present_calls={addr(s) for s in PRESENT}
        self.process_input=addr('__ZN4Game12ProcessInputEv');self.process_attack=addr('__ZN4Game13ProcessAttackEv')
        self.set_alpha=addr('__ZN4Quad8SetAlphaEh')
    def hook(self,u,address,size,context):
        if self.processing:
            lr=u.reg_read(self.LR)&~1
            if address in self.skip_calls and (PROCESS<=lr<PROCESS_END or any(a<=lr<b for a,b in OWN)):u.reg_write(self.PC,lr|1);return
            if address in self.present_calls and any(a<=lr<b for a,b in OWN):u.reg_write(self.PC,lr|1);return
            if address==POWF and any(a<=lr<b for a,b in OWN):
                x,y=struct.unpack('<ff',struct.pack('<II',u.reg_read(self.regs[0]),u.reg_read(self.regs[1])))
                from verify_damage_labels import LIBM
                u.reg_write(self.regs[0],struct.unpack('<I',struct.pack('<f',LIBM.powf(x,y)))[0]);u.reg_write(self.PC,lr|1);return
            if address==self.set_alpha and 0x17570<=lr<0x17622:return   # flare quads: Quad::SetAlpha as original code
            if address==self.process_input and lr==0x17d14:
                phase=C.c_int32(self.read(self.GAME+0x10)).value
                self.events=[];self.release_events=[];self.gate_events=[];self.run_visits=set();self.int_vectors={};self.route=None
                self.releasing=phase==2;self.gating=True
            elif address==0x17d14:self.releasing=self.gating=False
            elif address==0x1744c:self.motion_events=[];self.resource_events=[];self.resource_active=True
            elif address in (0x174dc,0x17da4):self.resource_active=False
            if address==0x17cda:self.reached_attack=True   # the frame got as far as ProcessAttack
            if address==CHECK_END and PROCESS<=lr<PROCESS_END:   # CheckEndGame from Process (damage labels): end-of-game harness on
                self.end_events.append(['check_end']);self.recording=True;self.check_return=lr
            elif getattr(self,'check_return',None) is not None and address==self.check_return:self.recording=False;self.check_return=None
            if address==self.process_attack and lr==0x17ce0:
                self.configure(self.attack_config)
                self.all_events=[];self.enc_events=[];self.gen_events=[];self.refill_events=[];self.path_events=[]
                self.match_events=[];self.token_events=[];self.motion_events=[];self.int_sets={};self.mode=None
                self.all_running=True;self.attack_return=lr
            elif self.attack_return is not None and address==self.attack_return:
                self.all_running=False;self.path_active=self.refill_active=self.gen_active=self.enc_active=False;self.attack_return=None
        return super().hook(u,address,size,context)
    def load(self,c):
        super().load(c);G=self.GAME;self.end_events=[]
        for a in (0xcac4,0x102a4,0x165a0,0xc400,0xef6c,0x12c09,0xc3f0,0x59f4,0x5b0c,0x5b9c,0xb550,0xbfc0,0x14afc,0x14e70):self.u.mem_write(G+a,b'\0')
        self.write(G+0xb53c,0);self.write(G+0xb54c,0);self.u.mem_write(G+0xbf88,b'\0')
        self.write(G+0x10,0)   # no touch (the release loader leaves phase 2)
    def play_frame(self,phase,touch,dt):
        G=self.GAME;u=self.u
        self.write(G+0x10,phase);u.mem_write(G+0x14,struct.pack('<ff',*touch));u.mem_write(G+4,struct.pack('<f',dt))
        u.reg_write(self.regs[0],G);u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1);self.processing=True;self.end_events=[];self.reached_attack=False
        try:u.emu_start(PROCESS|1,self.STOP,timeout=0,count=80000000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.processing=self.gating=self.releasing=self.all_running=self.resource_active=self.recording=False
        self.moving_list=[self.index(v) for v in self.list_values(G+0xb3f8)]   # the falling list as Game::Process left it
        return dict(self.game_state(),reached_attack=self.reached_attack)
    def game_state(self):
        G=self.GAME;u=self.u
        game={k:C.c_int32(self.read(G+a)).value for k,a in INTS.items()};game.update({k:u.mem_read(G+a,1)[0] for k,a in BYTES.items()})
        path=self.path_status();path.pop('events');path['match'].pop('events',None);path['tokens'].pop('events',None);path['motion'].pop('events',None)
        enc=self.enc_status();enc.pop('events',None);enc.pop('encounters',None)
        return dict(common=self.common(),game=game,path=[self.index(p) for p in self.list_values(G+0xb3d8)],
                    board=[{k:u.mem_read(self.tile(i)+a,1)[0] for k,a in TBYTES.items()} for i in range(36)],
                    battle=path,enc=enc,anim=self.anim_state(),touch_phase=C.c_int32(self.read(G+0x10)).value,
                    flights={k:list(struct.unpack('<5I',u.mem_read(G+a,20))) for k,a in dict(flame=0x14e5c,spike=0x151d0,leech=0xc31c).items()},
                    shatter=[u.mem_read(G+0xbf88,1)[0],self.read(G+0xbf8c)],end=self.finish_state(),
                    end_events=self.end_events[:])

class Native(TurnNative):
    def __init__(self):
        super().__init__();lib=self.sched
        def noop(*a):return None
        self.cbs=dict(effects=EFFECT_EVENT(noop),parts=PARTS_EVENT(noop),labels=LABELS_EVENT(noop),frame=FRAME_EVENT(noop))
        self.effects_fn=lib.dr_process_board_effects;self.effects_fn.restype=None;self.effects_fn.argtypes=[C.POINTER(EffectsState),C.c_float,C.POINTER(EffectHooks)]
        self.reset_fn=lib.dr_reset_round_counters;self.reset_fn.restype=None;self.reset_fn.argtypes=[C.POINTER(PartsState),C.c_uint32]
        self.label_fn=lib.dr_process_damage_label;self.label_fn.restype=None;self.label_fn.argtypes=[C.POINTER(PartsState),U8,C.c_float,C.POINTER(PartsHooks)]
        self.labels_fn=lib.dr_process_damage_labels;self.labels_fn.restype=C.c_bool;self.labels_fn.argtypes=[C.POINTER(LabelsState),C.c_float,Point,C.POINTER(LabelsHooks)]
        self.frame_fn=lib.dr_process_frame;self.frame_fn.restype=I32;self.frame_fn.argtypes=[C.POINTER(Frame),C.c_float,C.POINTER(FrameHooks)]
        def check(_):self.end_events.append(['check_end']);return self.check_fn(C.byref(self.r),C.byref(self.flags),C.byref(self.end_hooks))
        self.cbs['check']=LABELS_CHECK(check)
        def step(fn):return STEP(lambda _:fn())
        def flag(fn):return FLAG(lambda _:bool(fn()))
        self.frame_hooks=FrameHooks(None,self.cbs['frame'],step(self.step_input),step(self.step_effects),step(self.step_falling),
                                    flag(self.step_tokens),step(lambda:None),step(self.step_fade),step(self.step_label),flag(self.step_labels),
                                    step(self.step_attack))
    def load(self,c):
        super().load(c);self.end_events=[]
        self.touch=Touch(0,Point(0,0));self.dt=0.0
        self.shatter=Shatter(0,0.0);self.label_active=(U8*4)()
        self.effects_state=EffectsState(C.cast(C.pointer(self.path_state),C.c_void_p),C.cast(C.pointer(self.gen),C.c_void_p),
                                        C.cast(C.pointer(self.fin_flags),C.c_void_p),C.pointer(self.shatter))
        self.parts_state=PartsState(C.cast(C.pointer(self.path_state),C.c_void_p),C.cast(C.pointer(self.p),C.c_void_p),C.c_void_p(self.q),
                                    C.pointer(self.extra),C.cast(C.pointer(self.anim),C.POINTER(Animation)),C.cast(C.pointer(self.damage),C.c_void_p),
                                    C.cast(C.pointer(self.fin_flags),C.POINTER(TurnFinishFlags)),C.cast(C.pointer(self.touch),C.POINTER(PartsTouch)))
        self.fade_state=self.parts_state
        self.labels_state=LabelsState(C.cast(C.pointer(self.state.selection),C.c_void_p),C.cast(C.pointer(self.r),C.c_void_p),
                                      C.pointer(self.flights),self.label_active)
        self.labels_hooks=LabelsHooks(None,self.cbs['labels'],self.cbs['check'])
        self.screens=Screens()
        self.frame_struct=Frame(C.pointer(self.touch),C.cast(C.pointer(self.flags),Frame._fields_[1][1]),C.pointer(self.screens),
                         C.cast(C.pointer(self.state),C.c_void_p),C.cast(C.pointer(self.m),C.c_void_p),C.cast(C.pointer(self.path_state),C.c_void_p))
    # GameFrameHooks steps
    def step_input(self):
        s=self.state.selection;s.touch.x,s.touch.y=self.touch.position.x,self.touch.position.y
        gi=GateInputs(len(self.moving_list),self.token_counters().pending,self.anim.flare_count,self.touch.phase,-1)
        self.gi=gi
        state=InputState(C.pointer(self.path_state),C.cast(C.pointer(self.damage),C.c_void_p),C.cast(C.pointer(self.rune),C.POINTER(Rune)),C.pointer(gi),
                         C.pointer(self.release_state),C.pointer(self.release_inputs),C.pointer(self.scroll_state))
        hooks=InputHooks(C.pointer(self.session_schedule),C.pointer(self.hooks),C.pointer(self.release_hooks))
        fn=self.input_fn;fn.argtypes=[C.c_void_p,C.c_void_p];self.route=ROUTES[fn(C.addressof(state),C.addressof(hooks))]
    def step_effects(self):self.effects_fn(C.byref(self.effects_state),self.dt,C.byref(EffectHooks(None,self.cbs['effects'])))
    def step_falling(self):
        if self.moving_list:self.falling_frame(self.dt)
        else:self.reset_fn(C.byref(self.parts_state),0)
    def step_tokens(self):return self.batch(self.dt,[0,0,0])['continued']
    def step_fade(self):self.fade_step(self.dt)
    def step_label(self):self.label_fn(C.byref(self.parts_state),0,self.dt,C.byref(PartsHooks(None,self.cbs['parts'])))
    def step_labels(self):return self.labels_fn(C.byref(self.labels_state),self.dt,self.touch.position,C.byref(self.labels_hooks))
    def step_attack(self):self.reached_attack=True;self.frame(self.dt)   # ProcessAttack every frame, as Game::Process calls it
    def play_frame(self,phase,touch,dt):
        self.touch.phase=phase;self.touch.position=Point(*touch);self.dt=dt
        self.events=[];self.release_events=[];self.gate_events=[];self.eot_ran=False;self.matched=False;self.end_events=[]
        self.route=None;self.reached_attack=False;self.frame_route=self.frame_fn(C.byref(self.frame_struct),dt,C.byref(self.frame_hooks))
        return dict(self.game_state(),reached_attack=self.reached_attack)
    def game_state(self):
        s=self.state.selection;r=self.r
        game={k:getattr(s,k) for k in (*INTS,*BYTES)}
        path=self.path_status();path.pop('events');path['match'].pop('events',None);path['tokens'].pop('events',None);path['motion'].pop('events',None)
        enc=self.enc_status();enc.pop('events',None);enc.pop('encounters',None)
        bits=lambda v:struct.unpack('<I',struct.pack('<f',v))[0]
        return dict(common=self.common(),game=game,path=list(s.path[:s.path_length]),board=[{k:getattr(t,k) for k in TBYTES} for t in s.tiles],
                    battle=path,enc=enc,anim=self.anim_state(),touch_phase=self.touch.phase,
                    flights={k:[bits(getattr(self.flights,k).arc),bits(getattr(self.flights,k).start.x),bits(getattr(self.flights,k).start.y),
                                bits(getattr(self.flights,k).progress),bits(getattr(self.flights,k).speed)] for k in ('flame','spike','leech')},
                    shatter=[self.shatter.active,bits(self.shatter.progress)],end=self.finish_state(),end_events=self.end_events[:])

def main():
    old,new=Original(),Native();rng=random.Random(0x1717c);frames=turns=moves=ended=0;routes={}
    def signed_states(x):
        if isinstance(x,dict):return {k:(C.c_int32(v).value if k=='enemy_state' and isinstance(v,int) else signed_states(v)) for k,v in x.items()}
        if isinstance(x,list):return [signed_states(v) for v in x]
        return x
    def compare(stage,a,b,**info):
        a,b=signed_states(a),signed_states(b)
        if a!=b:
            (HERE/'game_frames_failure.json').write_text(json.dumps(dict(stage=stage,info=info,original=a,native=b),indent=2,default=str))
            raise AssertionError(f'game_frames_failure.json ({stage})')
    for game in range(GAMES):
        c=turn_case(rng);old.load(c);new.load(c)
        if hasattr(new,'batch_pending'):del new.batch_pending
        compare('load',old.game_state(),new.game_state(),game=game)
        for turn in range(TURNS):
            path=new.pick_path(rng);moves+=len(path)>=3
            script=[(1,i) for i in path]+[(2,path[-1])] if len(path)>=3 else []
            for frame in range(3000):
                dt=f32(rng.choice([1/60,1/30]))
                if frame<len(script):
                    phase,i=script[frame];centre=new.state.selection.tiles[i].geometry.center;touch=[centre.x,centre.y]
                else:phase,touch=0,[0.5,0.5]
                if not script and frame==0:old.set_ready(0);new.set_ready(0)
                info=dict(game=game,turn=turn,frame=frame,phase=phase)
                a,b=old.play_frame(phase,touch,dt),new.play_frame(phase,touch,dt);compare('frame',a,b,**info);frames+=1
                routes[new.frame_route]=routes.get(new.frame_route,0)+1
                if new.frame_route==11:ended+=1;break   # CheckEndGame ended the game: next game
                if frame>=len(script) and a['common']['input_ready'] and a['common']['phase']==0 and not new.moving_list and not a['common']['pending']:break
            else:raise AssertionError('turn did not finish')
            turns+=1
            if new.frame_route==11:break
    report=dict(status='passed',games=GAMES,turns=turns,moves=moves,frames=frames,games_ended=ended,frame_routes=routes,
                original='Whole original Game::Process every frame',native='dr_process_frame with the native units wired',
                scope='turns of play through the frame schedule on one carried state; screens closed; presentation not compared here')
    (HERE/'game_frames_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
