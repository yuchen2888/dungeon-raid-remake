#!/usr/bin/env python3
"""Actual Game::ProcessInput gate [0x16638,0x16748) and Game::CountAttackers 0x8fb0 vs native
dr_input_gate / dr_count_attackers (recovered_schedule), on the shared state of verify_attack_all.py.

The original runs ProcessInput from its entry (R0=Game) until the touch dispatch (0x1674e, after
the rune preview reset) or the epilogue 0x170e6. CharacterClass::HavePerk, CountAttackers and
Tile::GetAttack run as original code, as does std::list::size on the falling list (Game+0xb3f8,
filled from the case's moving list by verify_refill.py). Game::EndOfTurn is recorded and skipped
(native: ScheduleHooks end_of_turn, which an embedding wires to dr_end_of_turn).
"""
import ctypes as C
import json
import random
import re
from verify_attack_all import Original as AllOriginal, Native as AllNative, scenario
from verify_rune import Rune
from verify_resources import Resource
from verify_path import Path
from verify_stroke import HERE, I32, U8

ENTRY,DISPATCH,EPILOGUE=0x16638,0x1674e,0x170e6
COUNT,COUNT_END=0x8fb0,0x903c
END_OF_TURN,END_OF_TURN_SITE=0x13574,0x1671e
PHASE,FLARES,TOKENS,TOUCH,TARGET,RUNE,CLASS_INDEX=0xb8a8,0xbd8c,0xb52c,0x10,0x58ac,0x164a0,0x1648c
class Inputs(C.Structure):_fields_=[('falling_count',C.c_uint32),('tokens_pending',I32),('flare_count',I32),('touch_phase',I32),('input_target',I32)]
class DamageState(C.Structure):_fields_=[('resources',C.POINTER(Resource)),('phase',I32),('incoming_damage',I32),('enemy9_damage',I32)]
END_FN=C.CFUNCTYPE(None,C.c_void_p)
class ScheduleHooks(C.Structure):_fields_=[('context',C.c_void_p),('end_of_turn',END_FN)]
RESULTS=['blocked','attack_started','idle','dispatch']

class Original(AllOriginal):
    def __init__(self):
        super().__init__();self.gating=False;self.gate_visits={};self.all_visits={}
        text=(HERE.parent/'armv7-disassembly.txt').read_text()
        assert re.search(r'^__ZN4Game12ProcessInputEv:\n\s*16638:',text,re.M) and re.search(r'^__ZN4Game14CountAttackersEv:\n\s*8fb0:',text,re.M)
    def hook(self,u,address,size,context):
        if self.gating:
            if ENTRY<=address<0x16750 or 0x17074<=address<0x17082 or address==EPILOGUE:self.gate_visits[hex(address)]=self.gate_visits.get(hex(address),0)+1
            lr=u.reg_read(self.LR)&~1
            if address in (0x194cec,0x194cf4) and ENTRY<lr<=0x16750:u.reg_write(self.PC,u.reg_read(self.LR));return   # SjLj (un)register
            if address==END_OF_TURN and lr==END_OF_TURN_SITE+4:self.gate_events.append(['end_of_turn']);u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def load(self,c):
        super().load(c);g=c['gate']
        for k,o in (('phase',PHASE),('flare_count',FLARES),('tokens_pending',TOKENS),('touch_phase',TOUCH),('input_target',TARGET),('rune',RUNE)):self.write(self.GAME+o,g[k])
        self.write(self.GAME+CLASS_INDEX,0)
    def state(self):
        return dict(phase=C.c_int32(self.read(self.GAME+PHASE)).value,input_ready=self.u.mem_read(self.GAME+0x5e14,1)[0],rune=self.read(self.GAME+RUNE))
    def gate(self):
        self.gate_events=[];self.gate_visits={};self.gating=True;u=self.u
        u.reg_write(self.regs[0],self.GAME);u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1)
        try:
            u.emu_start(ENTRY|1,DISPATCH,timeout=0,count=200000);pc=u.reg_read(self.PC)
            if pc!=DISPATCH:assert pc in (EPILOGUE,self.STOP),hex(pc)   # epilogue reached (and returned)
        except Exception:raise
        finally:self.gating=False
        visits=self.gate_visits
        for k in visits:self.all_visits[k]=self.all_visits.get(k,0)+visits[k]
        result='dispatch' if pc==DISPATCH else 'attack_started' if '0x166fc' in visits else 'idle' if '0x16722' in visits else 'blocked'
        return dict(result=result,events=self.gate_events[:],**self.state())
    def count(self):
        u=self.u;u.reg_write(self.regs[0],self.GAME);u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1)
        u.emu_start(COUNT|1,self.STOP,timeout=0,count=200000);assert u.reg_read(self.PC)==self.STOP
        return C.c_int32(u.reg_read(self.regs[0])).value

class Native(AllNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_schedule_native.dylib'))
        self.gate_fn=lib.dr_input_gate;self.gate_fn.restype=I32
        self.gate_fn.argtypes=[C.POINTER(Path),C.POINTER(DamageState),C.POINTER(Rune),C.POINTER(Inputs),C.POINTER(ScheduleHooks)]
        self.count_fn=lib.dr_count_attackers;self.count_fn.argtypes=[C.POINTER(Path)];self.count_fn.restype=I32
        def end_of_turn(_):self.gate_events.append(['end_of_turn'])
        self.gate_cb=END_FN(end_of_turn);self.schedule_hooks=ScheduleHooks(None,self.gate_cb)
    def load(self,c):
        super().load(c);g=c['gate']
        self.inputs=Inputs(len(c['moving_list']),g['tokens_pending'],g['flare_count'],g['touch_phase'],g['input_target'])
        self.damage=DamageState(C.pointer(self.r),g['phase'],0,0);self.rune=Rune();self.rune.highlights=g['rune']
    def gate(self):
        self.gate_events=[]
        r=self.gate_fn(C.byref(self.path_state),C.byref(self.damage),C.byref(self.rune),C.byref(self.inputs),C.byref(self.schedule_hooks))
        return dict(result=RESULTS[r],events=self.gate_events[:],phase=self.damage.phase,input_ready=self.path_state.input_ready,rune=self.rune.highlights)
    def count(self):return self.count_fn(C.byref(self.path_state))

def main():
    old,new=Original(),Native();rng=random.Random(0x16638);counts={};compared=0;attackers=set()
    for n in range(600):
        c,_=scenario(rng)
        c['path_state']['input_ready']=rng.randrange(2);c['path_state']['turn']=rng.choice([0,3,4,5,rng.randrange(0,60)])
        c['match']['perks']=[rng.choice([0,0,3,255]),255,255,255]
        for i,t in enumerate(c['board']):
            t['flag255']=int(rng.random()<.1);c['combat'][i]['attack_flag']=int(rng.random()<.2)
            c['combat'][i]['attack']=rng.choice([0,0,1,3,-1])
        if rng.random()<.3:
            for t in c['board']:
                if t['type']==1:t['type']=rng.choice([0,2,3])
        c['moving_list']=rng.choice([[],[],[],[],[rng.randrange(36)],rng.sample(range(36),3)])
        c['gate']=dict(tokens_pending=rng.choice([0,0,0,0,1,-1]),flare_count=rng.choice([0,0,0,0,2,-1]),
                       phase=rng.choice([0,0,0,1,4,7,8,8,9,-1]),touch_phase=rng.choice([0,1,2,3,4]),input_target=rng.choice([-1,-1,-1,0,2]),rune=rng.randrange(0,9))
        old.load(c);new.load(c)
        ca,cb=old.count(),new.count()
        a,b=old.gate(),new.gate()
        if (ca,a)!=(cb,b):
            (HERE/'input_gate_failure.json').write_text(json.dumps(dict(case=c,original=[ca,a],native=[cb,b]),indent=2))
            raise AssertionError('input_gate_failure.json')
        compared+=1;counts[a['result']]=counts.get(a['result'],0)+1;attackers.add(min(ca,3))
        if a['events']:counts['end_of_turn']=counts.get('end_of_turn',0)+1
    assert all(counts.get(k) for k in ('blocked','attack_started','idle','dispatch','end_of_turn')) and attackers=={0,1,2,3},(counts,attackers)
    # early-turn perk check, perk skip -> phase 8, attack start, EndOfTurn, phases 1..7 blocked, touch dispatch
    assert all(hex(x) in old.all_visits for x in (0x166d8,0x166de,0x17074,0x166fc,0x1671e,0x1670e,0x16748)),sorted(old.all_visits)
    report=dict(status='passed',comparisons=compared,outcomes=counts,
                functions=[dict(symbol='__ZN4Game14CountAttackersEv',address=hex(COUNT),native='dr_count_attackers'),
                           dict(symbol='__ZN4Game12ProcessInputEv',address=hex(ENTRY),gate=[hex(ENTRY),hex(DISPATCH)],native='dr_input_gate')],
                original='Actual ProcessInput gate with original HavePerk, CountAttackers, GetAttack',
                boundaries=['EndOfTurn recorded (native callback; dr_end_of_turn in an embedding)',
                            'touch dispatch after the gate is a later unit'],
                scope='Path input_ready/turn, attack phase, rune preview, perks, board attackers')
    (HERE/'input_gate_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
