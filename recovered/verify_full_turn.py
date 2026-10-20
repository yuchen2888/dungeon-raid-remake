#!/usr/bin/env python3
"""Whole turns on carried state: original vs native, frame by frame (T040-F2).

Extends verify_turn_loop.py (the enemy half) with the player's move. Each turn the harness picks a path
of at least three adjacent tiles of one type on the current board and touches its tiles one per frame
(touch phase 1), then releases (phase 2). Those frames run the whole ProcessInput (original from its
entry; native dr_process_input) as in verify_process_input.py, except that on release Game::MatchTiles
runs as original code (recorded as in verify_path.py; native: the ReleaseHooks MatchTiles event runs
dr_commit_path) and MoveMatchedTiles runs inside it as original code (recorded as in
verify_encounters.py; native: the path hooks' MoveMatchedTiles event runs dr_move_matched_tiles). Every
frame then runs falling tiles, reward tokens, the flare fade and, while it runs, ProcessAttack; the touch
is consumed at the end of a release frame as Game::Process does. After the move the board settles, the
gate starts the enemy attack, ProcessAttack runs to phase 8 and the gate runs EndOfTurn, as in
verify_turn_loop.py. Native objects for one Game field are shared across the units.
"""
import copy
import ctypes as C
import json
import random
import struct
import verify_original
from verify_process_input import Original as InputOriginal, Native as InputNative, ROUTES, InputState, InputHooks
from verify_turn_loop import Original as LoopOriginal, Native as LoopNative, case as loop_case, GAMES as _G, f32
from verify_input_gate import Inputs as GateInputs, ENTRY as GATE_ENTRY, EPILOGUE, END_OF_TURN
from verify_release import ReleaseState, case as release_case, Hooks as ReleaseHooks, EVENT as RELEASE_EVENT, KINDS as RELEASE_KINDS
from verify_process_attack import Inputs as AttackInputs
from verify_selection import INTS, BYTES, TBYTES, snapshot
from verify_path import EVENT as PATH_EVENT, Hooks as PathHooks
from verify_stroke import HERE, I32, U8
from verify_rune import Rune

MATCH_TILES,MATCH_TILES_END,MOVE=0x12188,0x127a8,0x10ed8
GAMES,TURNS=8,4

class Original(InputOriginal,LoopOriginal):
    def __init__(self):
        super().__init__();self.match_return=None;self.move_return=None
    def hook(self,u,address,size,context):
        lr=u.reg_read(self.LR)&~1
        if self.releasing and address==MATCH_TILES and 0x16638<=lr<0x1717c:
            # Game::MatchTiles from the release: run it as original code (path harness), not the release record
            self.release_events.append([RELEASE_KINDS['match_tiles'],-1,0,0,0,0,0.0,0.0])
            self.path_events=[];self.match_events=[];self.token_events=[];self.motion_events=[];self.int_sets={}
            self.path_active=True;self.match_return=lr
            return LoopOriginal.hook(self,u,address,size,context)
        if self.match_return is not None:
            if address==self.match_return:self.path_active=False;self.match_return=None
            elif address==MOVE and MATCH_TILES<=lr<MATCH_TILES_END and self.path_active:
                self.path_events.append([-1,12,0,0,0,0])   # the path harness's MoveMatchedTiles record
                self.enc_events=[];self.gen_events=[];self.refill_events=[]
                self.path_active=False;self.refill_active=self.gen_active=self.enc_active=True;self.move_return=lr
                return LoopOriginal.hook(self,u,address,size,context)
            elif self.move_return is not None and address==self.move_return:
                self.refill_active=self.gen_active=self.enc_active=False;self.path_active=True;self.move_return=None
        return super().hook(u,address,size,context)
    def player_frame(self,phase,touch):
        G=self.GAME;u=self.u
        self.write(G+0x10,phase);u.mem_write(G+0x14,struct.pack('<ff',*touch))
        self.events=[];self.release_events=[];self.gate_events=[];self.run_visits=set();self.int_vectors={};self.route=None
        self.path_events=[];self.enc_events=[];self.gen_events=[];self.refill_events=[]
        self.releasing=phase==2;self.gating=True;self.eot_ran=False
        u.reg_write(self.regs[0],G);u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1)
        try:u.emu_start(GATE_ENTRY|1,self.STOP,timeout=0,count=60000000);assert u.reg_read(self.PC) in (EPILOGUE,self.STOP),hex(u.reg_read(self.PC))
        finally:self.releasing=self.gating=False
        if phase in (2,3):self.write(G+0x10,0)   # Game::Process consumes a released / cancelled touch
        game=dict(self.case['game'])
        for k,a in INTS.items():game[k]=C.c_int32(self.read(G+a)).value
        for k,a in BYTES.items():game[k]=u.mem_read(G+a,1)[0]
        board=[{k:u.mem_read(self.tile(i)+a,1)[0] for k,a in TBYTES.items()} for i in range(36)]
        sel=snapshot(self.case,game,[self.index(p) for p in self.list_values(G+0xb3d8)],[self.index(f) for f in self.fake],board,self.events)
        self.route=self.route or 0;st=self.status();st.pop('events');st.pop('route',None)
        for k in ('path','fake'):st.pop(k)
        return dict(selection=sel,release=st,release_events=self.release_events,gate_events=self.gate_events,
                    path=self.path_status() if any(e[0]==RELEASE_KINDS['match_tiles'] for e in self.release_events) else None,
                    enc=self.enc_status() if self.enc_events or self.gen_events or self.refill_events else None,
                    end_of_turn=self.end_state() if self.eot_ran else None,common=self.common())
    def set_touch_phase(self,v):self.write(self.GAME+0x10,v)

class Native(InputNative,LoopNative):
    def __init__(self):
        super().__init__()
        def release_event(_,p):
            e=p.contents;self.release_events.append([e.kind,e.tile,e.a,e.b,e.c,e.d,f32(e.x),f32(e.y)])
            if e.kind==RELEASE_KINDS['match_tiles']:self.match_tiles()
        self.full_release_cb=RELEASE_EVENT(release_event)
    def load(self,c):
        super().load(c)
        # one native object per Game field (each unit test's loader made its own)
        self.release_inputs=self.inputs;self.inputs=AttackInputs(c['chance'],c['weaken'],c['damage_all'])
        self.flags=self.eot_state.end.contents;self.finish=self.fin_flags
        self.release_state=ReleaseState(C.pointer(self.path_state),C.pointer(self.gen),C.pointer(self.r),C.pointer(self.turn_flags),
                                        C.pointer(self.fin_flags),C.pointer(self.flights))
        rune=self.eot_state.rune.contents;rune.enabled=c['rune']['enabled'];rune.allocated=c['rune']['allocated'];rune.highlights=c['gate']['rune']
        self.rune=rune
        self.release_hooks=ReleaseHooks(None,self.full_release_cb,self.check_cb)
        original=self.path_event
        def path_event(ctx,p):
            original(ctx,p)
            if p.contents.kind==12:   # MoveMatchedTiles at its place inside MatchTiles
                self.enc_events=[];self.gen_events=[];self.refill_events=[]
                self.refill_lib.dr_move_matched_tiles(C.byref(self.refill),C.byref(self.refill_hooks))
        self.full_path_cb=PATH_EVENT(path_event)
        self.path_hooks=PathHooks(None,self.full_path_cb,C.pointer(self.match_hooks),C.pointer(self.token_hooks))
    def match_tiles(self):
        self.path_events=[];self.match_events=[];self.token_events=[];self.motion_events=[]
        s=self.state.selection;indices=list(s.path[:s.path_length]);fake=[i for i,v in enumerate(s.fake) if v]
        path=(U8*max(1,len(indices)))(*indices);excluded=(U8*max(1,len(fake)))(*fake)
        self.commit_fn(C.byref(self.path_state),path,len(indices),excluded,len(fake),C.byref(self.path_hooks));self.matched=True
    def player_frame(self,phase,touch):
        s=self.state.selection;s.touch.x,s.touch.y=touch
        gi=GateInputs(len(self.moving_list),self.token_counters().pending,self.anim.flare_count,phase,-1)
        self.events=[];self.release_events=[];self.gate_events=[];self.eot_ran=False;self.matched=False
        self.path_events=[];self.enc_events=[];self.gen_events=[];self.refill_events=[]
        state=InputState(C.pointer(self.path_state),C.cast(C.pointer(self.damage),C.c_void_p),C.cast(C.pointer(self.rune),C.POINTER(Rune)),C.pointer(gi),
                         C.pointer(self.release_state),C.pointer(self.release_inputs),C.pointer(self.scroll_state))
        hooks=InputHooks(C.pointer(self.session_schedule),C.pointer(self.hooks),C.pointer(self.release_hooks))
        fn=self.input_fn;fn.argtypes=[C.c_void_p,C.c_void_p];self.route=ROUTES[fn(C.addressof(state),C.addressof(hooks))]
        game=dict(self.case['game'])
        for k in (*INTS,*BYTES):game[k]=getattr(s,k)
        board=[{k:getattr(t,k) for k in TBYTES} for t in s.tiles]
        sel=snapshot(self.case,game,list(s.path[:s.path_length]),[i for i,v in enumerate(s.fake) if v],board,self.events)
        return dict(selection=sel,release=self.release_status(),release_events=self.release_events,gate_events=self.gate_events,
                    path=self.path_status() if self.matched else None,
                    enc=self.enc_status() if self.enc_events or self.gen_events or self.refill_events else None,
                    end_of_turn=self.end_state() if self.eot_ran else None,common=self.common())
    def set_touch_phase(self,v):pass
    def pick_path(self,rng):
        tiles=self.state.selection.tiles;best=[]
        def neighbours(i):
            x,y=i%6,i//6
            return [ny*6+nx for nx in range(x-1,x+2) for ny in range(y-1,y+2) if (nx,ny)!=(x,y) and 0<=nx<6 and 0<=ny<6]
        starts=list(range(36));rng.shuffle(starts)
        for start in starts:
            kind=tiles[start].rule.type
            if tiles[start].rule.flag255:continue
            path=[start]
            while len(path)<rng.choice([3,3,4,5,6]):
                options=[n for n in neighbours(path[-1]) if n not in path and tiles[n].rule.type==kind and not tiles[n].rule.flag255]
                if not options:break
                path.append(rng.choice(options))
            if len(path)>len(best):best=path
            if len(best)>=3:break
        return best

def case(rng):
    c=loop_case(rng)
    r=release_case(rng,0)   # release-specific state (flights, labels, class roster, ...)
    for k in ('release',):c[k]=r[k]
    c['release']['effect']=dict(kills_b=0,killed_attack=0,generated_count=0,generated_enemies=0)
    c['release']['help_flags']=0;c['release']['flag_1554c']=c['finish']['flag_1554c'];c['release']['prev_164a7']=c['flags']['prev_164a7']
    c['release']['b165b8']=c['flags']['b165b8'][0];c['release']['scroll']['current']=0
    for k in ('rune',):c[k]=r.get(k,c.get(k))
    c['rune']['enabled']=c['flags']['arrow_pending_16491']
    c['path']=[];c['fake']=[];c['path_state']['input_ready']=1   # the release loader writes input-ready 1
    for t in c['board']:t['selected']=0
    return c

def main():
    old,new=Original(),Native();rng=random.Random(0x12188);frames=turns=moves=matched=refills=attacks=0;routes={}
    def signed_states(x):
        if isinstance(x,dict):return {k:(C.c_int32(v).value if k=='enemy_state' and isinstance(v,int) else signed_states(v)) for k,v in x.items()}
        if isinstance(x,list):return [signed_states(v) for v in x]
        return x
    def compare(stage,a,b,**info):
        a,b=signed_states(a),signed_states(b)
        if a!=b:
            (HERE/'full_turn_failure.json').write_text(json.dumps(dict(stage=stage,info=info,original=a,native=b),indent=2,default=str))
            raise AssertionError(f'full_turn_failure.json ({stage})')
    def rest_of_frame(dt,info):
        compare('falling',old.falling_frame(dt),new.falling_frame(dt),**info)
        compare('tokens',old.batch(dt,[0,0,0]),new.batch(dt,[0,0,0]),**info)
        compare('fade',old.fade_step(dt),new.fade_step(dt),**info)
        if 1<=new.damage.phase<=7:compare('attack',old.frame(dt),new.frame(dt),**info)
        compare('common',old.common(),new.common(),**info)
    for game in range(GAMES):
        c=case(rng);old.load(c);new.load(c)
        if hasattr(new,'batch_pending'):del new.batch_pending
        compare('load',old.common(),new.common(),game=game)
        for turn in range(TURNS):
            path=new.pick_path(rng)
            if len(path)>=3:
                moves+=1
                for k,i in enumerate(path+[path[-1]]):   # touch each tile, then release on the last one
                    phase=1 if k<len(path) else 2;centre=new.state.selection.tiles[i].geometry.center;touch=[centre.x,centre.y]
                    dt=f32(1/60);info=dict(game=game,turn=turn,move=k,path=path)
                    a,b=old.player_frame(phase,touch),new.player_frame(phase,touch);compare('player',a,b,**info)
                    routes[new.route]=routes.get(new.route,0)+1;matched+=a['path'] is not None;refills+=a['enc'] is not None
                    rest_of_frame(dt,info);frames+=1
            else:
                old.set_ready(0);new.set_ready(0)
            for frame in range(3000):
                dt=f32(rng.choice([1/60,1/30]));info=dict(game=game,turn=turn,frame=frame)
                a,b=old.gate_step(),new.gate_step();compare('gate',a,b,**info);attacks+=a['gate']['result']=='attack_started'
                rest_of_frame(dt,info);frames+=1
                if a['gate']['result'] in ('idle','dispatch'):break
            else:raise AssertionError('turn did not finish')
            turns+=1
    assert moves and matched and refills and attacks,(moves,matched,refills,attacks)
    report=dict(status='passed',games=GAMES,turns=turns,moves=moves,matched_moves=matched,refills=refills,attacks=attacks,frames=frames,input_routes=routes,
                original='Whole ProcessInput with MatchTiles/MoveMatchedTiles as original code, falling, tokens, flare fade, ProcessAttack, gate with EndOfTurn',
                boundaries=['the harness picks the path (adjacent tiles of one type)','per-step boundaries as in the unit tests'],
                scope='complete turns: stroke, release, refill, rewards, enemy attack, EndOfTurn, on one carried state')
    (HERE/'full_turn_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
