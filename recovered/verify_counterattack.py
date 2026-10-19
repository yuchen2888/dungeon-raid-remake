#!/usr/bin/env python3
"""Actual Game::DoCounterattack 0x11214 vs native, on the full shared state.

Runs the whole original function; its Tile::GetAttack, Game::AttackSkull
(with MatchTile/tokens) and Game::MoveMatchedTiles (with RandomiseTile,
generation, Stab/JumpDown) execute as original code, using the same subsystem
hook switching as verify_attack_all.py. Only AddSimpleLabel from
DoCounterattack itself is adapted. Native: dr_do_counterattack whose callbacks
call dr_path_attack_skull and dr_move_matched_tiles.
"""
import ctypes as C
import json
import random
from verify_attack_all import Original as AllOriginal, Native as AllNative, scenario
from verify_path import Path
from verify_stroke import HERE

ENTRY,END=0x11214,0x1133c
RESTING=0xb400

class Original(AllOriginal):
    ranges,entry=[(ENTRY,END)],ENTRY
    def __init__(self):super().__init__();self.stop_at=self.STOP
    def label_tile(self,position):
        i,rest=divmod(position-self.GAME-RESTING,8);assert rest==0 and 0<=i<36;return i
    def counterattack(self):return self.run_original()

class Native(AllNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_attack_shield_native.dylib'))
        self.counter_fn=lib.dr_do_counterattack;self.counter_fn.argtypes=[C.POINTER(Path),C.c_void_p];self.counter_fn.restype=None
    def counterattack(self):
        self.all_events=[];self.enc_events=[];self.gen_events=[];self.refill_events=[];self.path_events=[]
        self.match_events=[];self.token_events=[];self.motion_events=[]
        self.counter_fn(C.byref(self.path_state),C.addressof(self.all_hooks))
        return dict(path=self.path_status(),enc=self.enc_status(),all=self.all_events[:])

def main():
    old,new=Original(),Native();rng=random.Random(0x11214);counts={'random':0,'race':0,'repeated':0,'falling_frames':0};kills=attacks=0
    def check(c,a,b,group):
        if a!=b:
            (HERE/'counterattack_failure.json').write_text(json.dumps(dict(case=c,original=a,native=b),indent=2))
            raise AssertionError('counterattack_failure.json')
        counts[group]+=1
    def run(c,group):
        nonlocal kills,attacks
        a,b=old.counterattack(),new.counterattack();check(c,a,b,group)
        hits=[e for e in a['all'] if e[1]==9];attacks+=len(hits);kills+=sum(e[5] for e in hits)
    for _ in range(150):
        c,_=scenario(rng);old.load(c);new.load(c);run(c,'random')
    # Poison + race 1 halves GetAttack; zero/one attack edge values.
    for race in range(10):
        for n in range(3):
            c,_=scenario(rng);c['game']['race']=race
            for k in c['combat']:k['poison'][0]=rng.choice([0,2]);k['attack']=rng.choice([0,1,2,3,rng.randrange(4,30)])
            old.load(c);new.load(c);run(c,'race')
    for game in range(6):
        c,_=scenario(rng);old.load(c);new.load(c)
        for step in range(4):
            run(dict(game=game,step=step),'repeated')
            for frame in range(240):
                a,b=old.falling_frame(1/60),new.falling_frame(1/60);check(dict(game=game,step=step,frame=frame),a,b,'falling_frames')
                if not new.moving_list:break
            else:raise AssertionError('did not settle')
    assert kills and attacks
    report=dict(status='passed',comparisons=sum(counts.values()),by_group=counts,attack_skull_calls=attacks,kills=kills,
                function=dict(symbol='__ZN4Game15DoCounterattackEv',address=hex(ENTRY),size=END-ENTRY,native='dr_do_counterattack'),
                original='Actual DoCounterattack with original GetAttack, AttackSkull (+MatchTile/tokens) and MoveMatchedTiles (+generation/Stab/JumpDown)',
                boundaries=['DoCounterattack label adapted','callee presentation adapted by existing hooks','not yet driven by the phase-3 scheduler'],
                scope='Full shared board, combat, match counts, tokens, refill, generation and RNG state',
                branch_visits=old.all_visits)
    import hashlib
    report['byte_sha256']=hashlib.sha256(old.old.bytes_at(ENTRY,END-ENTRY)).hexdigest()
    (HERE/'counterattack_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='branch_visits'}))

if __name__=='__main__':main()
