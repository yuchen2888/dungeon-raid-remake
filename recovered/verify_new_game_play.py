#!/usr/bin/env python3
"""New games played to the end: original vs native, frame by frame (T040-F4).

Each game starts with Game::InitNewGame (original as in verify_new_game.py; native dr_init_new_game whose
NewGameState points at the same shared native objects the frame schedule uses) and is then played as in
verify_game_frames.py: every frame one original Game::Process and one native dr_process_frame with the
native units wired, until the game ends or the turn budget is used. Boundaries of the start: time()
returns the case seed; item construction and UpdateStats are recorded on both sides (items keep the
harness's zero stats); the class roster is the case's.
"""
import ctypes as C
import json
import random
import verify_original
from verify_game_frames import Original as FramesOriginal, Native as FramesNative
from verify_new_game import Original as NewOriginal, Native as NewNative, State as NewState, case as new_case, Hooks as NewHooks
from verify_full_turn import case as turn_case, f32
from verify_stroke import HERE, I32, U8
from verify_selection import Hooks as SelectionHooks

GAMES,TURNS=6,10

class Original(FramesOriginal,NewOriginal):
    pass

class Native(FramesNative,NewNative):
    def load(self,c):
        super().load(c)
        self.new_hooks=self.hooks;self.hooks=SelectionHooks(None,self.callback)   # the new-game loader took the stroke's name
        # dr_init_new_game resets the same objects the frame schedule and the units use
        self.state_obj=NewState(C.cast(C.pointer(self.m),C.c_void_p),C.cast(C.pointer(self.p),C.c_void_p),C.cast(C.pointer(self.r),C.c_void_p),
                                C.cast(C.pointer(self.path_state),C.c_void_p),C.cast(C.pointer(self.gen),C.c_void_p),C.c_void_p(self.q),
                                C.cast(C.pointer(self.turn_flags),NewState._fields_[6][1]),C.cast(C.pointer(self.fin_flags),NewState._fields_[7][1]),
                                C.cast(C.pointer(self.rune),C.c_void_p),C.cast(C.pointer(self.flags),NewState._fields_[9][1]),
                                C.cast(C.pointer(self.counter),C.POINTER(U8)),C.cast(C.pointer(self.damage),C.c_void_p),
                                C.cast(C.pointer(self.player),NewState._fields_[12][1]),self.classes,1,
                                C.cast(C.pointer(self.shatter),NewState._fields_[15][1]),C.cast(C.pointer(self.extra),NewState._fields_[16][1]))

def case(rng):
    c=turn_case(rng)
    n=new_case(rng)
    c['new_game']=n['new_game'];c['tokens']=n['tokens']
    c['new_game']['classes'][0][2]=max(1,c['new_game']['classes'][0][2])
    return c

def main():
    old,new=Original(),Native();rng=random.Random(0x15c51);frames=turns=moves=ended=0;routes={}
    def signed_states(x):
        if isinstance(x,dict):return {k:(C.c_int32(v).value if k=='enemy_state' and isinstance(v,int) else signed_states(v)) for k,v in x.items()}
        if isinstance(x,list):return [signed_states(v) for v in x]
        return x
    def compare(stage,a,b,**info):
        a,b=signed_states(a),signed_states(b)
        if a!=b:
            (HERE/'new_game_play_failure.json').write_text(json.dumps(dict(stage=stage,info=info,original=a,native=b),indent=2,default=str))
            raise AssertionError(f'new_game_play_failure.json ({stage})')
    for game in range(GAMES):
        c=case(rng);old.load(c);new.load(c)
        if hasattr(new,'batch_pending'):del new.batch_pending
        a=NewOriginal.run(old);new.new_events=[];new.gen_events=[]
        new.init_fn(C.byref(new.state_obj),c['new_game']['time'],C.byref(new.new_hooks))
        compare('init events',[a['new_events'],a['events']],[new.new_events,new.gen_events],game=game)
        old.moving_list=[old.index(v) for v in old.list_values(old.GAME+0xb3f8)]
        compare('after init',old.game_state(),new.game_state(),game=game)
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
                if new.frame_route==11:ended+=1;break
                if frame>=len(script) and a['common']['input_ready'] and a['common']['phase']==0 and not new.moving_list and not a['common']['pending']:break
            else:raise AssertionError('turn did not finish')
            turns+=1
            if new.frame_route==11:break
    report=dict(status='passed',games=GAMES,turns=turns,moves=moves,frames=frames,games_ended=ended,frame_routes=routes,
                original='Original InitNewGame, then the whole original Game::Process every frame',
                native='dr_init_new_game, then dr_process_frame with the native units wired, on shared native objects',
                boundaries=['time() returns the case seed; item construction and UpdateStats recorded (zero item stats)',
                            'the harness picks the paths; screens closed; presentation compared by the unit tests'],
                scope='games from their start through several turns, up to the end of the game')
    (HERE/'new_game_play_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
