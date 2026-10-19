#!/usr/bin/env python3
"""Actual EndOfTurn tail [0x13b3c,0x13cda) + [0x13d12,0x13d64) + [0x13dc8,0x13e04)
vs native dr_end_turn_finish (recovered_turn).

The original runs from 0x13b3c (after the ability loop; R8=Game) until the
epilogue 0x13e04. Both CheckEndGame calls run the whole original function
(GetScore etc., as in verify_game_over.py); MoveMatchedTiles runs the original
function (RandomiseTile/generation/encounters) via verify_attack_all.py's
subsystem switching. native wires check_end_game to dr_check_end_game (+
dr_game_over) and move_matched_tiles to dr_move_matched_tiles.
HelpMenu::Initialise and Game::SerialiseState are recorded in canonical form.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_game_over import Original as OverOriginal, Native as OverNative
from verify_attack_all import scenario, ATTACK, MOVE, MOVE_FN
from verify_resources import Resource
from verify_path import Path
from verify_generation import Generation
from verify_turn_burn import EVENT, MATCH, TILES, STRIDE
from verify_turn_begin import CHECK
from verify_game_over import EndGameState
from verify_stroke import HERE, I32, U8

ENTRY,EPILOGUE=0x13b3c,0x13e04
RANGES=[(0x13b3c,0x13cda),(0x13d12,0x13d64),(0x13dc8,0x13e04)]
HELP_MENU=0x10298
FIN_BYTES=dict(guard_164a6=0x164a6,next_one_health_14af7=0x14af7,next_force_coins_14af8=0x14af8,flag_1554c=0x1554c)
HELP_FLAGS=0x102d0
SYMBOLS={'__ZN4Game12CheckEndGameEv':'check_end','__ZN8HelpMenu10InitialiseEffff8HelpType':'help','__ZN4Game14SerialiseStateEv':'serialise'}
class TurnFinishFlags(C.Structure):
    _fields_=[('next_one_health_14af7',U8),('next_force_coins_14af8',U8),('flag_1554c',U8),('help_flags_102d0',C.c_uint32)]
class TurnHooks(C.Structure):
    _fields_=[('context',C.c_void_p),('event',EVENT),('match_tile',MATCH),('attack_skull',ATTACK),('check_end_game',CHECK),('move_matched_tiles',MOVE_FN)]

class Original(OverOriginal):
    ranges,entry,stop_at=RANGES,ENTRY,EPILOGUE
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.fin_calls={};self.fin_visits={}
        for symbol,name in SYMBOLS.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol;self.fin_calls[int(m[1],16)]=name
    def hook(self,u,address,size,context):
        if self.recording and self.all_running and self.mode is None:
            if self.in_range(address):self.fin_visits[hex(address)]=self.fin_visits.get(hex(address),0)+1
            lr=u.reg_read(self.LR)&~1;name=self.fin_calls.get(address)
            if address==MOVE and self.in_range(lr):self.end_events.append(['move'])
            if name and self.in_range(lr):
                if name=='check_end':self.end_events.append(['check_end']);return super().hook(u,address,size,context)   # whole original runs
                r=[u.reg_read(v) for v in self.regs];sp=u.reg_read(self.SP)
                if name=='help':
                    assert r[0]==self.GAME+HELP_MENU
                    tile=[i for i in range(36) if struct.unpack('<II',u.mem_read(self.tile(i)+0x54,8))==(r[1],r[2])]
                    e=['help',tile[0] if len(tile)==1 else tile,self.read(sp+4),r[3],self.read(sp)]
                else:assert r[0]==self.GAME;e=['serialise_state']
                self.end_events.append(e);u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def load(self,c):
        super().load(c)
        for k,o in FIN_BYTES.items():self.u.mem_write(self.GAME+o,bytes([c['finish'][k]]))
        self.write(self.GAME+HELP_FLAGS,c['finish']['help_flags_102d0'])
    def finish_state(self):
        rb=lambda o:self.u.mem_read(self.GAME+o,1)[0]
        return dict(**{k:rb(o) for k,o in FIN_BYTES.items()},guard_164a4=rb(0x164a4),revive2=rb(0x164a5),victory=rb(0x16611),screen=rb(0xcac4),
                    help_flags=self.read(self.GAME+HELP_FLAGS))
    def finish(self):
        self.end_events=[];self.recording=True
        try:result=self.run_original()
        finally:self.recording=False
        base=self.GAME+0x15564+388*self.read(self.GAME+0x1648c)
        return dict(**result,events=self.end_events[:],ended=int(['serialise_state'] not in self.end_events),fin=self.finish_state(),
                    cls={k:self.read(base+o)&0xffffffff for k,o in dict(games_played=0x58,enemies_killed=0x5c).items()})

class Native(OverNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_turn_native.dylib'))
        self.finish_fn=lib.dr_end_turn_finish
        self.finish_fn.argtypes=[C.POINTER(Resource),C.POINTER(Path),C.POINTER(Generation),C.POINTER(EndGameState),C.POINTER(TurnFinishFlags),C.POINTER(TurnHooks)]
        self.finish_fn.restype=C.c_bool
        def event(_,p):
            e=p.contents;k=e.kind
            if k==16:self.end_events.append(['help',e.tile,e.a,e.b&0xffffffff,e.c&0xffffffff])
            elif k==17:self.end_events.append(['serialise_state'])
            else:raise AssertionError(k)
        def check(_):
            self.end_events.append(['check_end']);return self.check_fn(C.byref(self.r),C.byref(self.flags),C.byref(self.end_hooks))
        def move(_):
            self.end_events.append(['move']);self.refill_lib.dr_move_matched_tiles(C.byref(self.refill),C.byref(self.refill_hooks))
        self.fin_cb=(EVENT(event),CHECK(check),MOVE_FN(move))
        self.fin_hooks=TurnHooks(None,self.fin_cb[0],MATCH(0),ATTACK(0),self.fin_cb[1],self.fin_cb[2])
    def load(self,c):
        super().load(c);f=c['finish'];self.r.guard_164a6=f['guard_164a6']
        self.fin_flags=TurnFinishFlags(f['next_one_health_14af7'],f['next_force_coins_14af8'],f['flag_1554c'],f['help_flags_102d0'])
    def finish_state(self):
        f=self.fin_flags
        return dict(guard_164a6=self.r.guard_164a6,next_one_health_14af7=f.next_one_health_14af7,next_force_coins_14af8=f.next_force_coins_14af8,
                    flag_1554c=f.flag_1554c,guard_164a4=self.r.guard_164a4,revive2=self.flags.revive_second,victory=self.flags.victory,
                    screen=self.flags.game_over_screen,help_flags=f.help_flags_102d0)
    def finish(self):
        self.all_events=[];self.enc_events=[];self.gen_events=[];self.refill_events=[];self.path_events=[]
        self.match_events=[];self.token_events=[];self.motion_events=[];self.end_events=[]
        ended=self.finish_fn(C.byref(self.r),C.byref(self.path_state),C.byref(self.gen),C.byref(self.flags),C.byref(self.fin_flags),C.byref(self.fin_hooks))
        return dict(path=self.path_status(),enc=self.enc_status(),all=self.all_events[:],events=self.end_events[:],ended=int(ended),
                    fin=self.finish_state(),cls={k:getattr(self.cls,k) for k in ('games_played','enemies_killed')})

def main():
    old,new=Original(),Native();rng=random.Random(0x13B3C);counts={'boundary':0,'random':0,'turns':0};kinds={};refilled=0
    def case(health=10,**k):
        c,_=scenario(rng)
        c.update(screen=0,victory=k.get('victory',rng.randrange(2)),revive2=rng.randrange(2),guard=rng.randrange(2),flag_146d0=0,flag_146d4=0,flag_15546=0)
        c['record']=k.get('record',rng.randrange(2));c['mode']=k.get('mode',rng.randrange(3))
        c['path_state']['turn']=k.get('turn',rng.choice([99,100,101,rng.randrange(0,300)]))
        c['resources'].update(health=health,skill_count=rng.randrange(0,5))
        c['cls']=dict(games_played=1,enemies_killed=2,normal_score=0,hard_score=0,harder_score=0)
        c['skill_id']=[1,2,3,4];c['skill_level']=[0,1,2,3]
        c['generation'].update(time_to_promotion=rng.choice([0,1,2,7,-3,-2**31,2**31-1]),one_health=rng.randrange(2),force_coins=rng.randrange(2),
                               filter_enabled=rng.randrange(2),filter_swords=rng.randrange(2))
        c['finish']=dict(guard_164a6=rng.randrange(2),next_one_health_14af7=rng.randrange(2),next_force_coins_14af8=rng.randrange(2),flag_1554c=rng.randrange(2),
                         help_flags_102d0=k.get('help',rng.choice([0,0x8000,0x200000,0x208000,rng.randrange(2**32)])))
        for i,t in enumerate(c['board']):
            c['combat'][i]['attack_flag']=rng.randrange(2);t['matched']=int(rng.random()<.15)
        return c
    def compare(c,group):
        a,b=old.finish(),new.finish()
        if a!=b:
            (HERE/'turn_finish_failure.json').write_text(json.dumps(dict(case=c,original=a,native=b),indent=2))
            raise AssertionError('turn_finish_failure.json')
        nonlocal refilled
        counts[group]+=1;checks=a['events'].count(['check_end']);refilled+=bool(a['enc']['events'])
        key=('saved' if not a['ended'] else 'ended_first' if checks==1 else 'ended_victory' if a['fin']['victory'] else 'ended_second')
        key+='/help%d'%sum(1 for e in a['events'] if e[0]=='help');kinds[key]=kinds.get(key,0)+1
    for help in (0,0x8000,0x200000,0x208000):
     for record in (0,1):
      for mode in (0,1):
       for turn in (99,100):
        for health in (5,0):
            c=case(health=health,help=help,record=record,mode=mode,turn=turn,victory=0);old.load(c);new.load(c);compare(c,'boundary')
    for _ in range(150):
        c=case(health=rng.choice([1,5,0,-2,30]));old.load(c);new.load(c);compare(c,'random')
    for game in range(6):
        c=case(health=60,victory=0);old.load(c);new.load(c)
        for _ in range(8):compare(dict(game=game),'turns')
    # ended_second: health lost inside MoveMatchedTiles (encounters) ends the game at the second CheckEndGame.
    assert refilled and all(any(k.startswith(s+'/') for k in kinds) for s in ('saved','ended_first','ended_second','ended_victory'))
    assert all(hex(x) in old.fin_visits for x in (0x13b68,0x13bae,0x13bd0,0x13c16,0x13c4c,0x13d56,0x13cba,0x13cbe,0x13cd2))
    report=dict(status='passed',comparisons=sum(counts.values()),by_group=counts,outcomes=kinds,with_generation_events=refilled,ranges=[[hex(a),hex(b)] for a,b in RANGES],
                original='Actual EndOfTurn tail with the whole original CheckEndGame (twice) and MoveMatchedTiles (+RandomiseTile/generation/encounters)',
                boundaries=['HelpMenu::Initialise and Game::SerialiseState recorded (persistence not yet recovered)',
                            'entry state at 0x13b3c (R8=Game) set by the harness; preceding ability loop is a later unit',
                            'flag meanings not yet confirmed (named by offset)'],
                scope='Revive guards, end flags/victory, generation flags/filter/promotion timer, attack flags, refill/generation/encounter state, class stats',
                branch_visits=old.fin_visits)
    (HERE/'turn_finish_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='branch_visits'}))

if __name__=='__main__':main()
