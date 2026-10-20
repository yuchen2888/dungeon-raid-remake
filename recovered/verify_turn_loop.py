#!/usr/bin/env python3
"""The enemy half of the turn loop on carried state: original vs native, frame by frame (T040-F1).

Each frame runs, in Game::Process order: the ProcessInput gate (original from the ProcessInput entry,
with Game::EndOfTurn executing as original code inside it when the gate calls it, recorded as in
verify_end_of_turn.py; native dr_input_gate with ScheduleHooks.end_of_turn wired to dr_end_of_turn), the
falling tiles and reward tokens (as in verify_refill_integration.py / verify_motion.py), the attack flare
fade (original Process segment [0x17570,0x17622) with Quad::SetAlpha as original code; native
dr_process_flare_fade) and ProcessAttack (as in verify_process_attack.py). One board, RNG and resource
state is carried through several turns. A turn starts as if the player had just finished a move
(input not ready); the gate then starts the enemy attack, ProcessAttack runs to phase 8, the flares fade,
the gate runs EndOfTurn and makes input ready. Shared native objects are unified where the separate tests
each made their own copy of one Game field (attack phase, rune state, counterattack byte).
"""
import ctypes as C
import json
import random
import struct
import verify_original
from unicorn.arm_const import UC_ARM_REG_R4
from verify_input_gate import (Original as GateOriginal, Native as GateNative, Inputs as GateInputs, ScheduleHooks, END_FN,
                               END_OF_TURN, END_OF_TURN_SITE, ENTRY as GATE_ENTRY, DISPATCH, EPILOGUE, RESULTS)
from verify_end_of_turn import Original as EotOriginal, Native as EotNative, FLAG_BYTES
from verify_process_attack import Original as AttackOriginal, Native as AttackNative, AttackDamage, AnimState, Inputs as AttackInputs, MOTION, f32
from verify_new_game import Extra
from verify_turn_finish import TurnFinishFlags
from verify_frame_parts import Animation, Touch, State as FrameState, Hooks as FrameHooks, EVENT as FRAME_EVENT
from verify_selection import Point
from verify_stroke import HERE, I32, U8

FADE,FADE_END=0x17570,0x17622
GAMES,TURNS=8,4

class Original(GateOriginal,EotOriginal,AttackOriginal):
    def __init__(self):
        super().__init__();self.eot_return=None;self.fading=False
        # AllOriginal's attack/move mode switching is configured per function under test
        self.eot_config=dict(entry=EotOriginal.entry,ranges=list(self.ranges),stop_at=-1,extra_stops=())
        self.attack_config=dict(entry=AttackOriginal.entry,ranges=list(AttackOriginal.ranges),stop_at=self.STOP,extra_stops=())
        import re
        text=(HERE.parent/'armv7-disassembly.txt').read_text()
        self.set_alpha=int(re.search(r'^__ZN4Quad8SetAlphaEh:\n\s*([0-9a-f]+):',text,re.M)[1],16)
    def hook(self,u,address,size,context):
        if self.gating and address==EPILOGUE and not getattr(self,'processing',False):u.emu_stop();return   # ProcessInput returns after the gate
        lr=u.reg_read(self.LR)&~1
        if self.gating and address==END_OF_TURN and lr==END_OF_TURN_SITE+4:
            self.gate_events.append(['end_of_turn']);self.eot_ran=True
            self.all_events=[];self.enc_events=[];self.gen_events=[];self.refill_events=[];self.path_events=[]
            self.match_events=[];self.token_events=[];self.motion_events=[];self.end_events=[];self.int_sets={};self.mode=None;self.pending_gen=None
            self.ability_stack=[];self.configure(self.eot_config);self.eot_running=self.all_running=self.recording=True;self.eot_return=lr
            return EotOriginal.hook(self,u,address,size,context)   # EndOfTurn runs as original code (bypassing the gate's skip)
        if self.eot_return is not None and address==self.eot_return:
            self.eot_running=self.all_running=self.recording=self.gen_active=False
            self.path_active=self.refill_active=self.enc_active=False;self.eot_return=None
        if self.fading:
            if address==FADE_END:u.emu_stop();return
            if address==self.set_alpha:return   # flare quads: Quad::SetAlpha as original code
        return super().hook(u,address,size,context)
    def configure(self,config):
        for k,v in config.items():setattr(self,k,v)
    def frame(self,dt):
        self.configure(self.attack_config);return AttackOriginal.frame(self,dt)
    def gate_step(self):
        self.eot_ran=False;self.gate_events=[];self.gate_visits={};self.gating=True;u=self.u
        u.reg_write(self.regs[0],self.GAME);u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1)
        try:
            u.emu_start(GATE_ENTRY|1,DISPATCH,timeout=0,count=60000000);pc=u.reg_read(self.PC)
            assert pc in (DISPATCH,EPILOGUE),hex(pc)
        finally:self.gating=False
        visits=self.gate_visits
        result=dict(result='dispatch' if pc==DISPATCH else 'attack_started' if '0x166fc' in visits else 'idle' if '0x16722' in visits else 'blocked',
                    events=self.gate_events[:],**self.state())
        out=dict(gate=result,end_of_turn=None)
        if self.eot_ran:out['end_of_turn']=self.end_state()
        return out
    def end_state(self):
        from verify_end_of_turn import BeginOriginal
        path,enc=self.path_status(),self.enc_status()
        for t in path['combat']+enc['refill']['combat']:t['enemy_state']=C.c_int32(t['enemy_state']).value
        base=self.GAME+0x15564+388*self.read(self.GAME+0x1648c)
        return dict(path=path,enc=enc,all=self.all_events[:],events=self.end_events[:],begin=BeginOriginal.begin_state(self),fin=self.finish_state(),
                    activated=[self.u.mem_read(self.tile(i)+0x254,1)[0] for i in range(36)],
                    flame=[[self.u.mem_read(self.tile(i)+0x257,1)[0],C.c_int32(self.read(self.tile(i)+0x258)).value] for i in range(36)],
                    poison=C.c_int32(self.read(self.GAME+0x15540)).value,
                    cls={k:self.read(base+o)&0xffffffff for k,o in dict(games_played=0x58,enemies_killed=0x5c).items()})
    def fade_step(self,dt):
        u=self.u;self.write(self.GAME+4,struct.unpack('<I',struct.pack('<f',dt))[0])
        u.reg_write(UC_ARM_REG_R4,self.GAME);u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1);self.fading=True
        try:u.emu_start(FADE|1,FADE_END,timeout=0,count=200000);assert u.reg_read(self.PC)==FADE_END,hex(u.reg_read(self.PC))
        finally:self.fading=False
        return self.anim_state()
    def set_ready(self,v):self.u.mem_write(self.GAME+0x5e14,bytes([v]))
    def common(self):
        G=self.GAME;s=lambda a:C.c_int32(self.read(G+a)).value
        return dict(phase=s(0xb8a8),input_ready=self.u.mem_read(G+0x5e14,1)[0],pending=s(0xb52c),flares=s(0xbd8c),
                    shake=[self.read(G+0xbd90),self.read(G+0xbd94)],rune=self.read(G+0x164a0),
                    rune_enabled=self.u.mem_read(G+0x16491,1)[0],counter=self.u.mem_read(G+0xbfba,1)[0],turn=s(0xc))

class Native(GateNative,EotNative,AttackNative):
    def __init__(self):
        super().__init__();self.sched=C.CDLL(str(HERE/'recovered_schedule_native.dylib'))
        self.fade_fn=self.sched.dr_process_flare_fade;self.fade_fn.restype=None;self.fade_fn.argtypes=[C.POINTER(FrameState),C.c_float,C.POINTER(FrameHooks)]
        def end_of_turn(_):
            self.gate_events.append(['end_of_turn']);self.eot_ran=True
            self.all_events=[];self.enc_events=[];self.gen_events=[];self.refill_events=[];self.path_events=[]
            self.match_events=[];self.token_events=[];self.motion_events=[];self.end_events=[]
            self.eot_fn(C.byref(self.r),C.byref(self.path_state),C.byref(self.gen),C.byref(self.eot_state),C.byref(self.eot_hooks),C.byref(self.gen_hooks))
        self.session_eot_cb=END_FN(end_of_turn);self.session_schedule=ScheduleHooks(None,self.session_eot_cb)
        def fade_event(_,p):
            e=p.contents
            if e.kind==1:self.flare_mirror[e.a]=[e.b&0xff,e.c&0xffffffff]
        self.fade_cb=FRAME_EVENT(fade_event);self.fade_hooks=FrameHooks(None,self.fade_cb)
    def load(self,c):
        super().load(c)
        # one object per Game field across the three tests' loaders
        self.damage=AttackDamage(C.pointer(self.r),c['phase'],c['damage'],c['enemy9'])
        self.anim=AnimState(c['progress'],c['label_y'],c['damage_alpha'],c['poison_alpha'],c['count'],c['counter'],*[c[k] for k in MOTION])
        self.inputs=AttackInputs(c['chance'],c['weaken'],c['damage_all'])
        self.quads['overlay']=c['overlay']   # the overlay quad's alpha byte is OVERLAY_ALPHA (Game+0xb92b) itself
        self.rune=self.eot_state.rune.contents;self.rune.highlights=c['gate']['rune']
        self.counter=U8.from_buffer(self.anim,AnimState.counterattack.offset)   # Game+0xbfba: one byte for EndOfTurn and ProcessAttack
        self.eot_state.counterattack=C.pointer(self.counter)
        self.extra=Extra();self.fade_finish=TurnFinishFlags();self.touch=Touch(0,Point(0,0))
        self.fade_state=FrameState(C.cast(C.pointer(self.path_state),C.c_void_p),C.cast(C.pointer(self.p),C.c_void_p),C.c_void_p(self.q),
                                   C.pointer(self.extra),C.cast(C.pointer(self.anim),C.POINTER(Animation)),C.cast(C.pointer(self.damage),C.c_void_p),
                                   C.pointer(self.fade_finish),C.pointer(self.touch))
    def gate_step(self):
        self.gate_events=[];self.eot_ran=False
        pending=self.token_counters().pending
        gi=GateInputs(len(self.moving_list),pending,self.anim.flare_count,0,-1)
        fn=self.sched.dr_input_gate;fn.restype=I32;fn.argtypes=[C.c_void_p]*5
        r=fn(C.addressof(self.path_state),C.addressof(self.damage),C.addressof(self.rune),C.addressof(gi),C.addressof(self.session_schedule))
        return dict(gate=dict(result=RESULTS[r],events=self.gate_events[:],phase=self.damage.phase,input_ready=self.path_state.input_ready,
                              rune=self.rune.highlights),end_of_turn=self.end_state() if self.eot_ran else None)
    def end_state(self):
        from verify_end_of_turn import BeginNative
        return dict(path=self.path_status(),enc=self.enc_status(),all=self.all_events[:],events=self.end_events[:],begin=BeginNative.begin_state(self),
                    fin=self.finish_state(),activated=list(self.flags_254),
                    flame=[[t.self_flame,t.flame_damage] for t in self.state.selection.tiles],poison=self.r.poison,
                    cls={k:getattr(self.cls,k) for k in ('games_played','enemies_killed')})
    def token_counters(self):
        from verify_tokens import Counters
        fn=self.tokens_lib.dr_token_queue_counters;fn.restype=C.POINTER(Counters);fn.argtypes=[C.c_void_p]
        return fn(C.c_void_p(self.q)).contents
    def batch(self,dt,menus):
        # one pending count: the token queue's (Game+0xb52c), used by AddToken and by the Process token loop
        counters=self.token_counters();self.batch_pending=counters.pending
        out=super().batch(dt,menus)
        from verify_tokens import Counters
        new=Counters();C.pointer(new)[0]=counters;new.pending=self.batch_pending
        fn=self.tokens_lib.dr_token_queue_restore;fn.restype=None;fn.argtypes=[C.c_void_p,C.POINTER(Counters)];fn(C.c_void_p(self.q),C.byref(new))
        return out
    def fade_step(self,dt):
        self.fade_fn(C.byref(self.fade_state),dt,C.byref(self.fade_hooks));return self.anim_state()
    def set_ready(self,v):self.path_state.input_ready=v
    def common(self):
        return dict(phase=self.damage.phase,input_ready=self.path_state.input_ready,pending=self.token_counters().pending,
                    flares=self.anim.flare_count,shake=[self.m.shake_progress_bd90,self.m.shake_scale_bd94],rune=self.rune.highlights,
                    rune_enabled=self.rune.enabled,counter=self.anim.counterattack,turn=self.path_state.turn)

def case(rng):
    from verify_attack_all import scenario
    c,_=scenario(rng)
    c.update(screen=0,victory=0,revive2=0,guard=0,flag_146d0=0,flag_146d4=0,flag_15546=0)
    c['record']=0;c['mode']=0;c['game']['race']=rng.choice([1,7,8,rng.randrange(10)])
    c['path_state']['turn']=rng.randrange(5,60);c['match']['spawn_enabled_14ae0']=rng.randrange(1,4)
    c['resources'].update(health=rng.randrange(150,400),ui_health=0,poison=rng.choice([0,0,1]),skill_count=rng.randrange(0,5),
                          skill_max=[rng.randrange(1,8) for _ in range(4)],skill_current=[rng.randrange(0,9) for _ in range(4)])
    c['regen']=rng.choice([0,0,1,3])
    c['cls']=dict(games_played=1,enemies_killed=2,normal_score=0,hard_score=0,harder_score=0)
    c['skill_id']=[1,2,3,4];c['skill_level']=[0,1,2,3];c['skill_active']=[rng.randrange(2) for _ in range(4)]
    c['flags']={k:rng.randrange(2) for k in FLAG_BYTES};c['flags'].update(b165b8=[0]*5,prev_be74=[0]*4,next_be78=[0]*4)
    c['battle']['coin_on_attack']=c['flags']['coin']
    c['generation'].update(time_to_promotion=rng.choice([1,2,7]),one_health=0,force_coins=0,filter_enabled=0,filter_swords=0)
    c['finish']=dict(guard_164a6=0,next_one_health_14af7=0,next_force_coins_14af8=0,flag_1554c=0,help_flags_102d0=0)
    c['activated']=[0]*36
    for i,t in enumerate(c['board']):
        t['flag255']=0;t['flaming']=0;t['self_flame']=0;t['flame_damage']=0;c['combat'][i]['overlay']=0;c['combat'][i]['flag256']=0
        if t['type']==1:t['enemy']=rng.choice([0,0,0,2,3,9,20,rng.randrange(0,35)])
        if rng.random()<.2:c['combat'][i]['poison']=[rng.choice([1,2]),0,0,0,0,0]   # poisoned enemies: EndOfTurn poison damage and kills
        t['enemy_state']=0;c['combat'][i]['flag25e']=0;c['combat'][i]['attack_flag']=0;t['matched']=0
    c.update(phase=0,damage=0,enemy9=0,count=0,chance=rng.randrange(0,101),weaken=rng.choice([0,0,1]),damage_all=rng.choice([0,0,1]),
             progress=0.0,label_y=f32(rng.uniform(0.2,0.8)),damage_alpha=0.0,poison_alpha=0.0,counter=c['flags']['counterattack'],overlay=0)
    for k in MOTION:c[k]=f32(rng.uniform(0,1))
    c['gate']=dict(tokens_pending=0,flare_count=0,phase=0,touch_phase=0,input_target=-1,rune=0)
    c['moving_list']=[];c['flags']['arrow_pending_16491']=0
    for f in c['falling']:f.update(moving=0,speed=1)
    return c

def main():
    old,new=Original(),Native();rng=random.Random(0x13575);frames=turns=attacks=eots=0;routes={}
    def signed_states(x):   # enemy_state is an int32; the status helpers format it differently
        if isinstance(x,dict):return {k:(C.c_int32(v).value if k=='enemy_state' and isinstance(v,int) else signed_states(v)) for k,v in x.items()}
        if isinstance(x,list):return [signed_states(v) for v in x]
        return x
    def compare(stage,a,b,**info):
        a,b=signed_states(a),signed_states(b)
        if a!=b:
            (HERE/'turn_loop_failure.json').write_text(json.dumps(dict(stage=stage,info=info,original=a,native=b),indent=2,default=str))
            raise AssertionError(f'turn_loop_failure.json ({stage})')
    for game in range(GAMES):
        c=case(rng);old.load(c);new.load(c)
        if hasattr(new,'batch_pending'):del new.batch_pending
        compare('load',old.common(),new.common(),game=game)
        for turn in range(TURNS):
            old.set_ready(0);new.set_ready(0)   # the player has just finished a move
            for frame in range(3000):
                dt=f32(rng.choice([1/60,1/30]));info=dict(game=game,turn=turn,frame=frame)
                a,b=old.gate_step(),new.gate_step();compare('gate',a,b,**info)
                routes[a['gate']['result']]=routes.get(a['gate']['result'],0)+1;eots+=a['end_of_turn'] is not None
                if a['gate']['result']=='attack_started':attacks+=1
                compare('falling',old.falling_frame(dt),new.falling_frame(dt),**info)
                compare('tokens',old.batch(dt,[0,0,0]),new.batch(dt,[0,0,0]),**info)
                compare('fade',old.fade_step(dt),new.fade_step(dt),**info)
                if 1<=new.damage.phase<=7:compare('attack',old.frame(dt),new.frame(dt),**info)
                compare('common',old.common(),new.common(),**info);frames+=1
                if a['gate']['result'] in ('idle','dispatch'):break   # input ready: the next move is the player's
            else:raise AssertionError('turn did not finish')
            turns+=1
    assert attacks and eots and turns==GAMES*TURNS,(attacks,eots,turns)
    report=dict(status='passed',games=GAMES,turns=turns,frames=frames,attacks=attacks,end_of_turns=eots,gate_routes=routes,
                original='ProcessInput gate with EndOfTurn as original code, falling tiles, reward tokens, Process flare fade, ProcessAttack',
                boundaries=['the player move is simulated by clearing input-ready at the start of each turn',
                            'per-step boundaries as in verify_end_of_turn / verify_process_attack / verify_refill_integration / verify_motion'],
                scope='enemy attack -> flare fade -> EndOfTurn -> input ready, on one carried state over several turns')
    (HERE/'turn_loop_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
