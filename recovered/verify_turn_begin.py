#!/usr/bin/env python3
"""Actual EndOfTurn opening [0x13574,0x13710) vs native dr_end_turn_begin.

The original runs from EndOfTurn's entry (R0=Game) until 0x13710 (the burn/
freeze loop starts) or until it returns early because CheckEndGame ended the
game. CheckEndGame runs as the whole original function (with GetScore etc.,
via verify_game_over.py); native wires check_end_game to dr_check_end_game,
whose game_over runs dr_game_over. GetEnemyCount and Skill::Deactivate run as
original code; Interface::UpdateSkills and Arrow::SetColour are recorded.
"""
import ctypes as C
import json
import random
import re
from verify_game_over import Original as OverOriginal, Native as OverNative
from verify_attack_all import scenario
from verify_resources import Resource
from verify_path import Path
from verify_turn_burn import Event, EVENT, MATCH
from verify_attack_all import ATTACK
from verify_stroke import HERE, I32, U8

ENTRY,LOOP=0x13574,0x13710
SKILLS=0x1700000
FLAG_BYTES=dict(b15561=0x15561,b15562=0x15562,arrow_pending_16491=0x16491,arrow_hold_16492=0x16492,prev_164a7=0x164a7,next_164a8=0x164a8,
                next_coin_bfbc=0xbfbc,counterattack=0xbfba,coin=0xbfbb)
SYMBOLS={'__ZN4Game10QueueSoundE5Sound':'sound','__ZN9Interface12UpdateSkillsEv':'update_skills','__ZN5Arrow9SetColourEjjj':'arrow',
         '__ZN4Game12CheckEndGameEv':'check_end'}
class SkillSlots(C.Structure):_fields_=[('id',I32*4),('level',I32*4),('active',U8*4)]
class TurnFlags(C.Structure):
    _fields_=[('b15561',U8),('b15562',U8),('b165b8',U8*5),('arrow_pending_16491',U8),('arrow_hold_16492',U8),('prev_164a7',U8),('next_164a8',U8),
              ('prev_be74',U8*4),('next_be78',U8*4),('next_coin_bfbc',U8)]
CHECK=C.CFUNCTYPE(C.c_bool,C.c_void_p)
class TurnHooks(C.Structure):
    _fields_=[('context',C.c_void_p),('event',EVENT),('match_tile',MATCH),('attack_skull',ATTACK),('check_end_game',CHECK)]

class Original(OverOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.begin_calls={};self.begin_visits={}
        for symbol,name in SYMBOLS.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol;self.begin_calls[int(m[1],16)]=name
    def hook(self,u,address,size,context):
        if self.recording:
            if ENTRY<=address<LOOP:self.begin_visits[hex(address)]=self.begin_visits.get(hex(address),0)+1
            if address==LOOP:u.emu_stop();return
            lr=u.reg_read(self.LR)&~1;name=self.begin_calls.get(address)
            if name and ENTRY<lr<=LOOP:
                r=[u.reg_read(v) for v in self.regs]
                if name=='check_end':self.end_events.append(['check_end']);return super().hook(u,address,size,context)   # whole original runs
                if name=='sound':self.end_events.append(['sound',r[1]])
                elif name=='update_skills':assert r[0]==self.GAME+0x4cdc;self.end_events.append(['update_skills'])
                else:assert r[0]==self.GAME+0x3658;self.end_events.append(['arrow',r[1],r[2],r[3]])
                u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def load(self,c):
        super().load(c)
        for k,o in FLAG_BYTES.items():self.u.mem_write(self.GAME+o,bytes([c['flags'][k]]))
        self.u.mem_write(self.GAME+0x165b8,bytes(c['flags']['b165b8']));self.u.mem_write(self.GAME+0xbe74,bytes(c['flags']['prev_be74']))
        self.u.mem_write(self.GAME+0xbe78,bytes(c['flags']['next_be78']))
        for i in range(4):self.u.mem_write(SKILLS+0x100*i+0x80,bytes([c['skill_active'][i]]))
    def begin_state(self):
        rb=lambda o,n=1:list(self.u.mem_read(self.GAME+o,n))
        flags={k:rb(o)[0] for k,o in FLAG_BYTES.items()};flags.update(b165b8=rb(0x165b8,5),prev_be74=rb(0xbe74,4),next_be78=rb(0xbe78,4))
        skills=[[C.c_int32(self.read(SKILLS+0x100*i+0x90)).value,self.u.mem_read(SKILLS+0x100*i+0x80,1)[0]] for i in range(4)]
        return dict(flags=flags,skills=skills,turn=C.c_int32(self.read(self.GAME+0xc)).value)
    def begin(self):
        self.end_events=[];self.recording=True;u=self.u
        u.reg_write(self.regs[0],self.GAME);u.reg_write(self.SP,0x140ff00);u.reg_write(self.LR,self.STOP|1)
        try:
            u.emu_start(ENTRY|1,self.STOP,timeout=0,count=3000000);pc=u.reg_read(self.PC);assert pc in (self.STOP,LOOP),hex(pc)
        finally:self.recording=False
        base=self.GAME+0x15564+388*self.read(self.GAME+0x1648c)
        return dict(path=self.path_status(),enc=self.enc_status(),events=self.end_events[:],ended=int(pc==self.STOP),begin=self.begin_state(),
                    cls={k:self.read(base+o)&0xffffffff for k,o in dict(games_played=0x58,enemies_killed=0x5c).items()})

class Native(OverNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_turn_native.dylib'))
        self.begin_fn=lib.dr_end_turn_begin
        self.begin_fn.argtypes=[C.POINTER(Resource),C.POINTER(Path),C.POINTER(SkillSlots),C.POINTER(TurnFlags),C.POINTER(U8),C.POINTER(TurnHooks)]
        self.begin_fn.restype=C.c_bool
        def event(_,p):
            e=p.contents;k=e.kind
            if k==1:self.end_events.append(['sound',e.a])
            elif k==14:self.end_events.append(['update_skills'])
            elif k==15:self.end_events.append(['arrow',e.a,e.b,e.c])
            else:raise AssertionError(k)
        def check(_):
            self.end_events.append(['check_end']);return self.check_fn(C.byref(self.r),C.byref(self.flags),C.byref(self.end_hooks))
        self.begin_cb=(EVENT(event),CHECK(check));self.begin_hooks=TurnHooks(None,self.begin_cb[0],MATCH(0),ATTACK(0),self.begin_cb[1])
        types=list(self.over_fn.argtypes);types[3]=C.POINTER(SkillSlots);self.over_fn.argtypes=types   # skill slots incl. active flags
    def load(self,c):
        super().load(c)
        self.skills=SkillSlots((I32*4)(*c['skill_id']),(I32*4)(*c['skill_level']),(U8*4)(*c['skill_active']))
        f=c['flags'];self.turn_flags=TurnFlags(f['b15561'],f['b15562'],(U8*5)(*f['b165b8']),f['arrow_pending_16491'],f['arrow_hold_16492'],
            f['prev_164a7'],f['next_164a8'],(U8*4)(*f['prev_be74']),(U8*4)(*f['next_be78']),f['next_coin_bfbc'])
        self.counter=U8(f['counterattack'])
    def begin_state(self):
        t=self.turn_flags
        flags=dict(b15561=t.b15561,b15562=t.b15562,arrow_pending_16491=t.arrow_pending_16491,arrow_hold_16492=t.arrow_hold_16492,
                   prev_164a7=t.prev_164a7,next_164a8=t.next_164a8,next_coin_bfbc=t.next_coin_bfbc,counterattack=self.counter.value,
                   coin=self.path_state.battle.coin_on_attack,b165b8=list(t.b165b8),prev_be74=list(t.prev_be74),next_be78=list(t.next_be78))
        skills=[[self.r.skill_current[i],self.skills.active[i]] for i in range(4)]
        return dict(flags=flags,skills=skills,turn=self.path_state.turn)
    def begin(self):
        self.end_events=[]
        ended=self.begin_fn(C.byref(self.r),C.byref(self.path_state),C.byref(self.skills),C.byref(self.turn_flags),C.byref(self.counter),C.byref(self.begin_hooks))
        return dict(path=self.path_status(),enc=self.enc_status(),events=self.end_events[:],ended=int(ended),begin=self.begin_state(),
                    cls={k:getattr(self.cls,k) for k in ('games_played','enemies_killed')})

def main():
    old,new=Original(),Native();rng=random.Random(0x13574);counts={'boundary':0,'random':0,'turns':0};ended=readied=0
    def case(health=10,**k):
        c,_=scenario(rng)
        c.update(screen=0,victory=0,revive2=0,guard=0,flag_146d0=0,flag_146d4=0,flag_15546=0)
        c['resources'].update(health=health,skill_count=k.get('skills',rng.randrange(0,5)),
            skill_max=[rng.randrange(1,8) for _ in range(4)],skill_current=[rng.randrange(0,9) for _ in range(4)])
        c['cls']=dict(games_played=1,enemies_killed=2,normal_score=0,hard_score=0,harder_score=0)
        c['skill_id']=[1,2,3,4];c['skill_level']=[0,1,2,3];c['skill_active']=[rng.randrange(2) for _ in range(4)]
        c['flags']={k:rng.randrange(2) for k in FLAG_BYTES};c['flags'].update(b165b8=[rng.randrange(2) for _ in range(5)],
            prev_be74=[rng.randrange(2) for _ in range(4)],next_be78=[rng.randrange(2) for _ in range(4)])
        c['battle']['coin_on_attack']=c['flags']['coin']
        if k.get('enemy15'):c['board'][7].update(type=1,enemy=15)
        else:
            for t in c['board']:
                if t['enemy']==15:t['enemy']=0
        return c
    def compare(c,group):
        nonlocal ended,readied
        a,b=old.begin(),new.begin()
        if a!=b:
            (HERE/'turn_begin_failure.json').write_text(json.dumps(dict(case=c,original=a,native=b),indent=2))
            raise AssertionError('turn_begin_failure.json')
        counts[group]+=1;ended+=a['ended'];readied+=a['events'].count(['sound',10])
    for health in (5,0):
     for enemy15 in (False,True):
      for skills in range(5):
       for _ in range(6):
        c=case(health=health,enemy15=enemy15,skills=skills);old.load(c);new.load(c);compare(c,'boundary')
    for _ in range(200):
        c=case(health=rng.choice([1,5,0,-2]),enemy15=rng.random()<.3);old.load(c);new.load(c);compare(c,'random')
    for game in range(8):
        c=case(health=50,skills=4);old.load(c);new.load(c)
        for _ in range(10):compare(dict(game=game),'turns')
    assert ended and readied and all(hex(x) in old.begin_visits for x in (0x135b6,0x135dc,0x13642,0x13656,0x13710-2))
    report=dict(status='passed',comparisons=sum(counts.values()),by_group=counts,ended_by_check_end_game=ended,skills_readied=readied,
                range=dict(start=hex(ENTRY),end_exclusive=hex(LOOP)),
                original='Actual EndOfTurn opening with the whole original CheckEndGame (GetScore etc.), GetEnemyCount and Skill::Deactivate',
                boundaries=['Interface::UpdateSkills and Arrow::SetColour recorded','per-turn flag meanings not yet confirmed (named by offset)'],
                scope='Turn, skill cooldowns/active flags, per-turn flags, counterattack/coin flags, matched counts, timers, CheckEndGame effects',
                branch_visits=old.begin_visits)
    (HERE/'turn_begin_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='branch_visits'}))

if __name__=='__main__':main()
