#!/usr/bin/env python3
"""Actual EndOfTurn regeneration/poison segment [0x13910,0x13a1c) vs native.

The original runs from 0x13910 (R8=Game, [sp,#0x30]=Interface at Game+0x4cdc,
as the preceding EndOfTurn code leaves them) until 0x13a1c (turn continues) or
0x13e04 (CheckEndGame ended the game). Game::CheckEndGame is NOT recovered yet:
both sides record an ordered check_end event and return the case's value.
Sounds, achievements, health bar, label positions (GetTarget / GetPoisonPosition)
and labels are recorded in canonical form.
"""
import ctypes as C
import json
import random
import re
from verify_attack_all import Original as AllOriginal, Native as AllNative, scenario, ATTACK
from verify_resources import Resource
from verify_turn_burn import Event, EVENT, MATCH
from verify_stroke import HERE, I32

START,CONTINUE,ENDED=0x13910,0x13a1c,0x13e04
REGEN,INTERFACE,HEALTH_QUAD=0xbe70,0x4cdc,0x4d4c
TARGET=0x1400200
SYMBOLS={'__ZN4Game10QueueSoundE5Sound':'sound','__ZN4Game16QueueAchievementE11Achievementf':'achievement',
         '__ZN9Interface15UpdateHealthBarER4Quadi':'bar','__ZN9Interface9GetTargetE8TileType':'target',
         '__ZN9Interface17GetPoisonPositionEv':'poison_position','__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif':'label',
         '__ZN4Game12CheckEndGameEv':'check_end'}
CHECK=C.CFUNCTYPE(C.c_bool,C.c_void_p)
class TurnHooks(C.Structure):
    _fields_=[('context',C.c_void_p),('event',EVENT),('match_tile',MATCH),('attack_skull',ATTACK),('check_end_game',CHECK)]

class Original(AllOriginal):
    ranges,entry,stop_at,extra_stops=[(START,CONTINUE)],START,CONTINUE,(ENDED,)
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.calls={};self.regen_visits={};self.recording=False
        for symbol,name in SYMBOLS.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol;self.calls[int(m[1],16)]=name
    def hook(self,u,address,size,context):
        if self.recording:
            if START<=address<CONTINUE:self.regen_visits[hex(address)]=self.regen_visits.get(hex(address),0)+1
            lr=u.reg_read(self.LR)&~1;name=self.calls.get(address)
            if name and START<lr<=CONTINUE:
                r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value;sp=u.reg_read(self.SP);e=None
                if name=='sound':e=['sound',r[1]]
                elif name=='achievement':e=['achievement',r[1],s(r[2])]
                elif name=='bar':assert r[0]==self.GAME+INTERFACE and r[1]==self.GAME+HEALTH_QUAD;e=['health_bar',s(r[2])]
                elif name=='target':assert r[0]==self.GAME+INTERFACE and r[1]==0;u.reg_write(self.regs[0],TARGET)
                elif name=='poison_position':assert r[1]==self.GAME+INTERFACE;self.poison_out=r[0]
                elif name=='label':
                    tag='target' if r[2]==TARGET else 'poison' if r[2]==getattr(self,'poison_out',None) else hex(r[2])
                    e=['label',tag,r[1],s(r[3]),s(self.read(sp)),s(self.read(sp+4))]
                else:e=['check_end'];u.reg_write(self.regs[0],int(self.ends))
                if e:self.regen_events.append(e)
                u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def regen(self,amount,ends):
        self.regen_events=[];self.ends=ends;self.write(self.GAME+REGEN,amount);self.write(0x140ff00+0x30,self.GAME+INTERFACE);self.recording=True
        try:result=self.run_original()
        finally:self.recording=False
        return dict(**result,regen=self.regen_events[:],exit=self.u.reg_read(self.PC),poison=C.c_int32(self.read(self.GAME+0x15540)).value)

class Native(AllNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_turn_native.dylib'))
        self.regen_fn=lib.dr_end_turn_regen_poison;self.regen_fn.argtypes=[C.POINTER(Resource),I32,C.POINTER(TurnHooks)];self.regen_fn.restype=C.c_bool
        def event(_,p):
            e=p.contents;k=e.kind;ev=self.regen_events.append
            if k==1:ev(['sound',e.a])
            elif k==5:ev(['achievement',e.a,e.b])
            elif k==11:ev(['health_bar',e.a])
            elif k==12:ev(['label','target',e.a,e.b,e.c,e.d])
            elif k==13:ev(['label','poison',e.a,e.b,e.c,e.d])
            else:raise AssertionError(k)
        def check(_):self.regen_events.append(['check_end']);return self.ends
        self.regen_cb=(EVENT(event),CHECK(check));self.regen_hooks=TurnHooks(None,self.regen_cb[0],MATCH(0),self.cb[1],self.regen_cb[1])
    def regen(self,amount,ends):
        self.regen_events=[];self.ends=ends;self.all_events=[];self.match_events=[];self.path_events=[]
        ended=self.regen_fn(C.byref(self.r),amount,C.byref(self.regen_hooks))
        return dict(path=self.path_status(),enc=self.enc_status(),all=self.all_events[:],regen=self.regen_events[:],
                    exit=ENDED if ended else CONTINUE,poison=self.r.poison)

def main():
    old,new=Original(),Native();rng=random.Random(0x13910);counts={'boundary':0,'random':0,'turns':0};ended=0
    def compare(c,amount,ends,group):
        nonlocal ended
        a,b=old.regen(amount,ends),new.regen(amount,ends)
        if a!=b:
            (HERE/'turn_regen_failure.json').write_text(json.dumps(dict(case=c,amount=amount,ends=ends,original=a,native=b),indent=2))
            raise AssertionError('turn_regen_failure.json')
        counts[group]+=1;ended+=a['exit']==ENDED;return a
    def case(health,ui,maximum,bonus,poison):
        c,_=scenario(rng);c['resources'].update(health=health,ui_health=ui,health_max=maximum,health_bonus=bonus,poison=poison);return c
    for health in (-3,0,1,29,30,31,40):
     for regen in (-1,0,1,5,100):
      for poison in (-1,0,1,30,45):
       for ends in (False,True):
        c=case(health,rng.choice([health,0]),30,rng.choice([0,2]),poison);old.load(c);new.load(c);compare(c,regen,ends,'boundary')
    for _ in range(300):
        maximum=rng.randrange(1,200);c=case(rng.randrange(-5,220),rng.randrange(0,220),maximum,rng.randrange(0,20),rng.choice([0,0,rng.randrange(-2,40)]))
        old.load(c);new.load(c);compare(c,rng.choice([0,rng.randrange(-3,30)]),rng.random()<.2,'random')
    for game in range(10):
        c=case(rng.randrange(40,120),0,120,rng.randrange(0,10),rng.randrange(1,6));old.load(c);new.load(c)
        for _ in range(25):compare(dict(game=game),rng.randrange(0,6),False,'turns')
    assert ended and all(hex(x) in old.regen_visits for x in (0x1393a,0x13962,0x1399e,0x139be,0x139e0,0x13a10))
    report=dict(status='passed',comparisons=sum(counts.values()),by_group=counts,ended=ended,
                range=dict(start=hex(START),end_exclusive=hex(CONTINUE),exits=[hex(CONTINUE),hex(ENDED)]),
                original='Actual EndOfTurn regeneration and poison segment',
                boundaries=['Game::CheckEndGame not recovered: ordered callback returning the case value on both sides',
                            'regeneration amount Game+0xbe70 supplied by the harness','sound/achievement/health bar/label positions adapted'],
                scope='Player health, UI health, poison and the shared state',branch_visits=old.regen_visits)
    (HERE/'turn_regen_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='branch_visits'}))

if __name__=='__main__':main()
