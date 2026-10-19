#!/usr/bin/env python3
"""Actual Game::CheckEndGame 0x10b18, decision part [0x10b18,0x10c04), vs native.

The original runs from its entry (R0=Game) until it returns, or until it
reaches 0x10c04, where the end-of-game bookkeeping starts (still a boundary):
there the harness records game_over(win) with win read from [sp,#0x14], as the
native game_over callback does. GetMortalEnemyType and GetEnemyCount run as
original code; achievements, sound, health bar and the poison-position label
are recorded in canonical form.
"""
import ctypes as C
import json
import random
import re
from verify_attack_all import Original as AllOriginal, Native as AllNative, scenario
from verify_resources import Resource
from verify_turn_burn import Event, EVENT
from verify_stroke import HERE, U8

ENTRY,OVER,END=0x10b18,0x10c04,0x10dd6
SCREEN,VICTORY,REVIVE2,GUARD=0xcac4,0x16611,0x164a5,0x164a4
INTERFACE,HEALTH_QUAD=0x4cdc,0x4d4c
SYMBOLS={'__ZN4Game10QueueSoundE5Sound':'sound','__ZN4Game16QueueAchievementE11Achievementf':'achievement',
         '__ZN9Interface15UpdateHealthBarER4Quadi':'bar','__ZN9Interface17GetPoisonPositionEv':'poison_position',
         '__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif':'label'}
GAME_OVER=C.CFUNCTYPE(None,C.c_void_p,C.c_bool)
class EndGameState(C.Structure):_fields_=[(k,U8) for k in ('game_over_screen','victory','revive_second')]
class EndGameHooks(C.Structure):_fields_=[('context',C.c_void_p),('event',EVENT),('game_over',GAME_OVER)]

class Original(AllOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.calls={};self.end_visits={};self.recording=False
        for symbol,name in SYMBOLS.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol;self.calls[int(m[1],16)]=name
    def hook(self,u,address,size,context):
        if self.recording:
            if ENTRY<=address<OVER:self.end_visits[hex(address)]=self.end_visits.get(hex(address),0)+1
            if address==OVER:
                self.end_events.append(['game_over',self.read(u.reg_read(self.SP)+0x14)&0xff]);u.emu_stop();return
            lr=u.reg_read(self.LR)&~1;name=self.calls.get(address)
            if name and ENTRY<lr<=OVER:
                r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value;sp=u.reg_read(self.SP);e=None
                if name=='sound':e=['sound',r[1]]
                elif name=='achievement':e=['achievement',r[1],s(r[2])]
                elif name=='bar':assert r[0]==self.GAME+INTERFACE and r[1]==self.GAME+HEALTH_QUAD;e=['health_bar',s(r[2])]
                elif name=='poison_position':assert r[1]==self.GAME+INTERFACE;self.poison_out=r[0]
                else:assert r[2]==self.poison_out;e=['label','poison',r[1],s(r[3]),s(self.read(sp)),s(self.read(sp+4))]
                if e:self.end_events.append(e)
                u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def load(self,c):
        super().load(c)
        for o,k in ((SCREEN,'screen'),(VICTORY,'victory'),(REVIVE2,'revive2'),(GUARD,'guard')):self.u.mem_write(self.GAME+o,bytes([c[k]]))
    def check(self):
        self.end_events=[];self.recording=True;u=self.u
        u.reg_write(self.regs[0],self.GAME);u.reg_write(self.SP,0x140ff00);u.reg_write(self.LR,self.STOP|1)
        try:
            u.emu_start(ENTRY|1,self.STOP,timeout=0,count=2000000);pc=u.reg_read(self.PC)
            assert pc in (self.STOP,OVER),hex(pc)
        finally:self.recording=False
        result=1 if pc==OVER else u.reg_read(self.regs[0])&0xff
        flags=[self.u.mem_read(self.GAME+o,1)[0] for o in (SCREEN,VICTORY,REVIVE2,GUARD)]
        return dict(path=self.path_status(),enc=self.enc_status(),events=self.end_events[:],result=result,flags=flags)

class Native(AllNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_turn_native.dylib'))
        self.check_fn=lib.dr_check_end_game;self.check_fn.argtypes=[C.POINTER(Resource),C.POINTER(EndGameState),C.POINTER(EndGameHooks)];self.check_fn.restype=C.c_bool
        def event(_,p):
            e=p.contents;k=e.kind
            if k==1:self.end_events.append(['sound',e.a])
            elif k==5:self.end_events.append(['achievement',e.a,e.b])
            elif k==11:self.end_events.append(['health_bar',e.a])
            elif k==13:self.end_events.append(['label','poison',e.a,e.b,e.c,e.d])
            else:raise AssertionError(k)
        def over(_,win):self.end_events.append(['game_over',int(win)])
        self.end_cb=(EVENT(event),GAME_OVER(over));self.end_hooks=EndGameHooks(None,*self.end_cb)
    def load(self,c):
        super().load(c);self.r.guard_164a4=c['guard'];self.flags=EndGameState(c['screen'],c['victory'],c['revive2'])
    def check(self):
        self.end_events=[];result=int(self.check_fn(C.byref(self.r),C.byref(self.flags),C.byref(self.end_hooks)))
        f=self.flags
        return dict(path=self.path_status(),enc=self.enc_status(),events=self.end_events[:],result=result,
                    flags=[f.game_over_screen,f.victory,f.revive_second,self.r.guard_164a4])

def main():
    old,new=Original(),Native();rng=random.Random(0x10B18);counts={'boundary':0,'random':0};outcomes={}
    def case(**k):
        c,_=scenario(rng)
        c.update(screen=k.get('screen',0),victory=k.get('victory',0),revive2=k.get('revive2',0),guard=k.get('guard',0))
        c['record']=k.get('record',0);c['mode']=k.get('mode',0);c['game']['race']=k.get('race',0)
        c['resources'].update(health=k.get('health',10),ui_health=k.get('ui',0),health_max=k.get('maximum',30),health_bonus=k.get('bonus',2))
        if k.get('mortal'):
            for t in c['board'][:3]:t.update(type=1,enemy=k['mortal'])
        return c
    def compare(c,group):
        a,b=old.check(),new.check()
        if a!=b:
            (HERE/'check_end_game_failure.json').write_text(json.dumps(dict(case=c,original=a,native=b),indent=2))
            raise AssertionError('check_end_game_failure.json')
        counts[group]+=1;key=str([e for e in a['events'] if e[0]=='game_over'] or a['result']);outcomes[key]=outcomes.get(key,0)+1
    mortals={1:9,2:14,3:13,4:16,5:12,6:5,7:20,8:8,9:19}
    for screen in (0,1):
     for victory in (0,1):
      for record in (0,1):
       for mode in (0,1):
        for health in (-5,0,1):
         for guard in (0,1):
          for race in (0,3,7):
            c=case(screen=screen,victory=victory,record=record,mode=mode,health=health,guard=guard,revive2=1,race=race,
                   mortal=mortals.get(race) if rng.random()<.5 else None,ui=rng.choice([0,32]))
            old.load(c);new.load(c);compare(c,'boundary')
    for _ in range(300):
        race=rng.randrange(10)
        c=case(screen=int(rng.random()<.1),victory=rng.randrange(2),record=rng.randrange(2),mode=rng.randrange(3),health=rng.randrange(-20,20),
               guard=rng.randrange(2),revive2=rng.randrange(2),race=race,mortal=mortals.get(race) if rng.random()<.5 else None,
               ui=rng.randrange(0,60),maximum=rng.randrange(1,60),bonus=rng.randrange(0,10))
        old.load(c);new.load(c);compare(c,'random')
    assert all(hex(x) in old.end_visits for x in (0x10b2c,0x10b4c,0x10b50,0x10b86,0x10b98,0x10c02))
    report=dict(status='passed',comparisons=sum(counts.values()),by_group=counts,outcomes=outcomes,
                function=dict(symbol='__ZN4Game12CheckEndGameEv',address=hex(ENTRY),decision_part=[hex(ENTRY),hex(OVER)],native='dr_check_end_game'),
                original='Actual CheckEndGame decision/revive part with original GetMortalEnemyType and GetEnemyCount',
                boundaries=['end-of-game bookkeeping from 0x10c04 (scores, class stats, screens, SerialiseClasses) is the game_over callback (next unit)',
                            'achievement/sound/health bar/label adapted'],
                scope='Health, UI health, revive guards, flags, record mode, race and board',branch_visits=old.end_visits)
    (HERE/'check_end_game_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='branch_visits'}))

if __name__=='__main__':main()
