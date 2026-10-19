#!/usr/bin/env python3
"""Whole original Game::CheckEndGame 0x10b18 incl. end-of-game bookkeeping vs native
dr_check_end_game whose game_over callback runs dr_game_over.

GetTotalXP / GetTotalGold / GetTotalUP / GetScore run as original code. Score
entries (ScoreScreen::AddScore, both overloads), ScoreScreen::SetSkills,
Game::SerialiseClasses, GameOverScreen::Initialise and achievements are recorded
in canonical form. The active class profile (Game+0x15564 + index*388) and the
skill objects' id (+0x84) / level (+0x88) are written by the harness.
"""
import ctypes as C
import json
import random
import re
from verify_check_end_game import (Original as CheckOriginal, Native as CheckNative, GAME_OVER, SCREEN, VICTORY, REVIVE2, GUARD, ENTRY, SYMBOLS as CHECK_SYMBOLS)
from verify_attack_all import Original as AllOriginal, scenario
from verify_progression import Profile
from verify_resources import Resource
from verify_path import Path
from verify_turn_burn import Event, EVENT
from verify_stroke import HERE, I32, U8

OVER,END=0x10c04,0x10dd6
CLASS_TABLE,CLASS_STRIDE,CLASS_INDEX=0x15564,388,0x1648c
CLASS_FIELDS=dict(games_played=0x58,enemies_killed=0x5c,normal_score=0x60,hard_score=0x64,harder_score=0x68)
FLAGS=dict(flag_146d0=0x146d0,flag_146d4=0x146d4,flag_15546=0x15546)
SKILLS=0x1700000
SYMBOLS={'__ZN11ScoreScreen8AddScoreEPKciiiii10Difficulty':'score0','__ZN11ScoreScreen8AddScoreEPKciiiii8GameMode':'score1',
         '__ZN11ScoreScreen9SetSkillsEiiii':'skills','__ZN4Game16SerialiseClassesEv':'serialise','__ZN14GameOverScreen10InitialiseEb':'screen',
         '__ZN4Game16QueueAchievementE11Achievementf':'achievement'}
class EndGameState(C.Structure):
    _fields_=[(k,U8) for k in ('game_over_screen','victory','revive_second')]+[('flag_146d0',I32),('flag_146d4',U8),('flag_15546',U8)]
class SkillSlots(C.Structure):_fields_=[('id',I32*4),('level',I32*4)]
class ScoreEntry(C.Structure):_fields_=[(k,I32) for k in ('variant','turn','a','b','c','score','mode')]
SCORE=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(ScoreEntry))
class EndGameHooks(C.Structure):_fields_=[('context',C.c_void_p),('event',EVENT),('game_over',GAME_OVER)]
class GameOverHooks(C.Structure):_fields_=[('context',C.c_void_p),('event',EVENT),('add_score',SCORE)]

class Original(CheckOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.over_calls={};self.over_visits={}
        for symbol,name in SYMBOLS.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol;self.over_calls[int(m[1],16)]=name
    def hook(self,u,address,size,context):
        if self.recording:
            if OVER<=address<END:self.over_visits[hex(address)]=self.over_visits.get(hex(address),0)+1
            lr=u.reg_read(self.LR)&~1;name=self.over_calls.get(address)
            if name and OVER<lr<=END:
                r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value;sp=u.reg_read(self.SP);rd=lambda a:s(self.read(a))
                if name.startswith('score'):
                    assert r[0]==self.GAME+0xef68 and r[1]==self.GAME+0xbe38
                    e=['score',int(name[-1]),s(r[2]),s(r[3]),rd(sp),rd(sp+4),rd(sp+8),rd(sp+12)]
                elif name=='skills':assert r[0]==self.GAME+0xef68;e=['skills',s(r[1]),s(r[2]),s(r[3]),rd(sp)]
                elif name=='serialise':assert r[0]==self.GAME;e=['serialise_classes']
                elif name=='screen':assert r[0]==self.GAME+0xcac0;e=['game_over_screen',r[1]&0xff]
                else:e=['achievement',r[1],s(r[2])]
                self.end_events.append(e);u.reg_write(self.PC,u.reg_read(self.LR));return
            if address==OVER:return   # do not stop: the bookkeeping runs as original code
        return super().hook(u,address,size,context) if address!=OVER else AllOriginal.hook(self,u,address,size,context)
    def load(self,c):
        super().load(c)
        base=self.GAME+CLASS_TABLE+CLASS_STRIDE*self.read(self.GAME+CLASS_INDEX)
        for k,o in CLASS_FIELDS.items():self.write(base+o,c['cls'][k])
        for k,o in FLAGS.items():
            if k=='flag_146d0':self.write(self.GAME+o,c[k])
            else:self.u.mem_write(self.GAME+o,bytes([c[k]]))
        for i in range(4):self.write(SKILLS+0x100*i+0x84,c['skill_id'][i]);self.write(SKILLS+0x100*i+0x88,c['skill_level'][i])
    def check(self):
        result=super().check()
        base=self.GAME+CLASS_TABLE+CLASS_STRIDE*self.read(self.GAME+CLASS_INDEX)
        result['cls']={k:self.read(base+o)&0xffffffff for k,o in CLASS_FIELDS.items()}
        result['end_flags']=[C.c_int32(self.read(self.GAME+FLAGS['flag_146d0'])).value]+[self.u.mem_read(self.GAME+FLAGS[k],1)[0] for k in ('flag_146d4','flag_15546')]
        return result

class Native(CheckNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_turn_native.dylib'))
        self.check_fn.argtypes=[C.POINTER(Resource),C.POINTER(EndGameState),C.POINTER(EndGameHooks)]
        self.over_fn=lib.dr_game_over
        self.over_fn.argtypes=[C.POINTER(Resource),C.POINTER(Path),C.POINTER(Profile),C.POINTER(SkillSlots),C.POINTER(EndGameState),C.c_bool,C.POINTER(GameOverHooks)]
        self.over_fn.restype=None
        def over_event(_,p):
            e=p.contents;k=e.kind
            if k==5:self.end_events.append(['achievement',e.a,e.b])
            elif k==100:self.end_events.append(['skills',e.a,e.b,e.c,e.d])
            elif k==101:self.end_events.append(['serialise_classes'])
            elif k==102:self.end_events.append(['game_over_screen',e.a])
            else:raise AssertionError(k)
        def score(_,p):
            e=p.contents;self.end_events.append(['score',e.variant,e.turn,e.a,e.b,e.c,e.score,e.mode])
        def game_over(_,win):
            self.over_fn(C.byref(self.r),C.byref(self.path_state),C.byref(self.cls),C.byref(self.skills),C.byref(self.flags),win,C.byref(self.over_hooks))
        self.over_cb=(EVENT(over_event),SCORE(score),GAME_OVER(game_over))
        self.over_hooks=GameOverHooks(None,self.over_cb[0],self.over_cb[1])
        self.end_hooks=EndGameHooks(None,self.end_cb[0],self.over_cb[2])
    def load(self,c):
        super().load(c)
        self.flags=EndGameState(c['screen'],c['victory'],c['revive2'],c['flag_146d0'],c['flag_146d4'],c['flag_15546'])
        self.cls=Profile();[setattr(self.cls,k,v) for k,v in c['cls'].items()]
        self.skills=SkillSlots((I32*4)(*c['skill_id']),(I32*4)(*c['skill_level']))
    def check(self):
        result=super().check()
        result['cls']={k:getattr(self.cls,k) for k in CLASS_FIELDS}
        result['end_flags']=[self.flags.flag_146d0,self.flags.flag_146d4,self.flags.flag_15546]
        return result

def main():
    old,new=Original(),Native();rng=random.Random(0x10C04);counts={'boundary':0,'random':0};kinds={}
    def case(**k):
        c,_=scenario(rng)
        c.update(screen=0,victory=k.get('victory',0),revive2=0,guard=0,flag_146d0=rng.randrange(-5,5),flag_146d4=0,flag_15546=0)
        c['record']=k.get('record',0);c['mode']=k.get('mode',0);c['game']['race']=rng.randrange(10)
        c['resources'].update(health=k.get('health',0),ui_health=rng.randrange(0,40),skill_count=k.get('skills',rng.randrange(0,5)))
        for key in ('gold','up','xp','total_gold','total_up','total_xp'):c['resources'][key]=rng.choice([0,rng.randrange(0,5000),rng.randrange(-50,50)])
        c['match']['spawn_enabled_14ae0']=k.get('difficulty',rng.randrange(0,5))
        c['path_state'].update(turn=rng.randrange(0,900),total=rng.randrange(0,100000),crossing_best=rng.randrange(0,50),
                               crossing_average=rng.randrange(0,50),crossing_samples=rng.randrange(0,500))
        c['battle']['kills_a']=rng.randrange(0,400)
        c['cls']=dict(games_played=rng.randrange(0,1000),enemies_killed=rng.randrange(0,10**6),normal_score=rng.choice([0,rng.randrange(0,20000),0xffffff00]),
                      hard_score=rng.randrange(0,20000),harder_score=rng.randrange(0,20000))
        c['skill_id']=[rng.randrange(0,40) for _ in range(4)];c['skill_level']=[rng.randrange(0,6) for _ in range(4)]
        return c
    def compare(c,group):
        a,b=old.check(),new.check()
        if a!=b:
            (HERE/'game_over_failure.json').write_text(json.dumps(dict(case=c,original=a,native=b),indent=2))
            raise AssertionError('game_over_failure.json')
        counts[group]+=1
        key=str([e[1] for e in a['events'] if e[0]=='score'])+'/'+str(a['result']);kinds[key]=kinds.get(key,0)+1
    for record in (0,1):
     for mode in (0,1,2):
      for victory in (0,1):
       for difficulty in (0,1,2,3,4):
        for skills in (0,1,2,3,4):   # valid domain: four skill slots
            c=case(record=record,mode=mode,victory=victory,difficulty=difficulty,skills=skills,health=rng.choice([0,-3]))
            old.load(c);new.load(c);compare(c,'boundary')
    for _ in range(300):
        c=case(record=rng.randrange(2),mode=rng.randrange(3),victory=rng.randrange(2),health=rng.choice([0,-1,-20,5]))
        old.load(c);new.load(c);compare(c,'random')
    assert all(hex(x) in old.over_visits for x in (0x10c32,0x10c88,0x10c96,0x10ca4,0x10cbe,0x10d00,0x10d4a,0x10dc6,0x10d80,0x10d84))
    report=dict(status='passed',comparisons=sum(counts.values()),by_group=counts,score_paths=kinds,
                functions=[dict(symbol='__ZN4Game12CheckEndGameEv',address=hex(ENTRY),native='dr_check_end_game + dr_game_over'),
                           dict(symbol='__ZN4Game8GetScoreEv',address='0x8c18',native='dr_get_score'),
                           dict(symbol='__ZN4Game12GetTotalGoldEv',address='0x18a2c',native='dr_total_gold'),
                           dict(symbol='__ZN4Game10GetTotalUPEv',address='0x18a5c',native='dr_total_up')],
                original='Whole CheckEndGame with original GetTotalXP/Gold/UP, GetScore, GetMortalEnemyType, GetEnemyCount',
                boundaries=['ScoreScreen::AddScore/SetSkills, SerialiseClasses (class persistence), GameOverScreen adapted as canonical events',
                            'class profile and skill id/level written by the harness'],
                scope='Class games/kills/best scores, end flags, health, guards and ordered events',branch_visits=old.over_visits)
    (HERE/'game_over_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='branch_visits'}))

if __name__=='__main__':main()
