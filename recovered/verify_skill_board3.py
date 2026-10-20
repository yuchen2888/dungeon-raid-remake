#!/usr/bin/env python3
"""Board skills, batch 3 (T040-H4): actual Game::CheckShockAwe 0xbdf4, CollectBoard 0x11c3c, CollectRandomRow
0x11ea8, CollectRandomBlock 0x11748, CollectEdgeTiles 0x11ac4, ConvertColumnToSwords 0x11da0, Teleport 0x1133c,
Earthquake 0xb780, KillSkullsNextToCoins 0x11908 and CreateChain 0xa618 vs native recovered_skills, on the
shared state of verify_attack_all.py.

As verify_skill_board2.py: each original function runs from its entry to its return; the calls made from these
functions themselves (they call one another: CheckShockAwe, CollectBoard) are recorded and skipped -- AddFlare,
QueueAchievement, MoveMatchedTiles (with filter_enabled at that moment), SwapTiles and Tile::SetSpecialType --
and their own RandI runs as original code, recorded as a generation Random event. MatchTile runs with the match
harness, Tile::SetType with the generation harness. Compared: skill events, the generation / board / combat
state and events, the match and path state, random seeds, the flare timers, Game+0x13ec4 and the turn flags
b15561 / b15562 / b165b8.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_input_gate import Original as GateOriginal, Native as GateNative
from verify_skills import SkillState, case as skills_case
from verify_turn_begin import SkillSlots, TurnFlags
from verify_turn_finish import TurnFinishFlags
from verify_game_over import EndGameState
from verify_attack_phase4 import AnimState
from verify_stroke import HERE, I32, U8

FUNCTIONS=dict(shock=(0xbdf4,0xbe30),board=(0x11c3c,0x11da0),row=(0x11ea8,0x12060),block=(0x11748,0x11908),edge=(0x11ac4,0x11c3c),
               column=(0x11da0,0x11ea8),teleport=(0x1133c,0x11498),earthquake=(0xb780,0xb880),coins=(0x11908,0x11ac4),chain=(0xa618,0xa6f4))
FLAG_BYTES=dict(b15561=0x15561,b15562=0x15562,**{f'b165b8_{k}':0x165b8+k for k in range(5)})
RANDI,TIMERS,SOUND=0x1bca0,0xbd90,0x13ec4
BODY={'__ZN4Game8AddFlareE9FlareType8GLfloat2RK9GLcolour4':'flare','__ZN4Game16QueueAchievementE11Achievementf':'achievement',
      '__ZN4Game16MoveMatchedTilesEv':'move','__ZN4Game9SwapTilesEiiii':'swap','__ZN4Tile14SetSpecialTypeE15SpecialTileType':'special'}

class SkillEvent(C.Structure):_fields_=[('kind',I32),('a',I32),('b',I32),('c',I32),('d',I32)]
EVENT=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(SkillEvent))
ACTION=C.CFUNCTYPE(None,C.c_void_p,I32,I32,I32)
class SkillHooks(C.Structure):_fields_=[('context',C.c_void_p),('event',EVENT),('action',ACTION),('match',C.c_void_p),('path',C.c_void_p)]

class Original(GateOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.body={};self.boarding=False;self.pending_rand=None
        self.set_type=int(re.search(r'^__ZN4Tile7SetTypeE8TileTypeii:\n\s*([0-9a-f]+):',text,re.M)[1],16)
        for symbol,name in BODY.items():
            self.body[int(re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M)[1],16)]=name
    def resting_tile(self,x,y):
        for i in range(36):
            if struct.unpack('<II',self.u.mem_read(self.GAME+0xb400+8*i,8))==(x,y):return i
        raise AssertionError((hex(x),hex(y)))
    def hook(self,u,address,size,context):
        if self.boarding:
            lr=u.reg_read(self.LR)&~1;inside=any(start<lr<end for start,end in FUNCTIONS.values());s=lambda v:C.c_int32(v).value
            r=[u.reg_read(v) for v in self.regs]
            if self.pending_rand and address==self.pending_rand[0]:
                self.gen_events.append([1,-1,*self.pending_rand[1:],s(r[0])]);self.pending_rand=None
            if address==RANDI and inside:self.pending_rand=(lr,s(r[0]),s(r[1]),s(r[2]));return   # runs as original code
            if address==self.set_type and inside:self.gen_active=True;self.set_type_return=lr   # the generation harness for SetType only
            elif address==getattr(self,'set_type_return',None):self.gen_active=False;self.set_type_return=None
            name=self.body.get(address)
            if name and inside:
                sp=u.reg_read(self.SP)
                if name=='flare':e=['flare',s(r[1]),self.resting_tile(r[2],r[3]),s(self.read(self.read(sp)))]
                elif name=='achievement':e=['achievement',s(r[1]),s(r[2])]
                elif name=='move':e=['move',u.mem_read(self.GAME+0xbfb8,1)[0]]
                elif name=='swap':e=['swap',s(r[1]),s(r[2]),s(r[3]),s(self.read(sp))]
                else:e=['special',s(r[1]),self.index(r[0])]
                self.skill_events.append(e);u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def run(self,key,args):
        u=self.u;self.skill_events=[];self.gen_events=[];self.match_events=[];self.path_events=[];self.token_events=[];self.motion_events=[]
        self.pending_gen=self.pending_rand=None;self.int_sets={}
        self.boarding=key;self.gen_active=self.path_active=False
        for reg,v in zip(self.regs,[self.GAME,*args]):u.reg_write(reg,v&0xffffffff)
        u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1)
        try:u.emu_start(FUNCTIONS[key][0]|1,self.STOP,timeout=0,count=5000000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.boarding=self.gen_active=self.path_active=False
        G=self.GAME
        return dict(events=self.skill_events,gen=self.gen_status(),path=self.path_status(),timers=[self.read(G+TIMERS),self.read(G+TIMERS+4)],
                    sound=u.mem_read(G+SOUND,1)[0],flags={k:u.mem_read(G+a,1)[0] for k,a in FLAG_BYTES.items()})
    def set_extra(self,timers,sound,flags):
        self.write(self.GAME+TIMERS,timers[0]);self.write(self.GAME+TIMERS+4,timers[1]);self.u.mem_write(self.GAME+SOUND,bytes([sound]))
        for k,v in flags.items():self.u.mem_write(self.GAME+FLAG_BYTES[k],bytes([v]))

class Native(GateNative):
    def __init__(self):
        super().__init__();lib=self.skills_lib=C.CDLL(str(HERE/'recovered_skills_native.dylib'))
        P=C.POINTER(SkillState);H=C.POINTER(SkillHooks);G=C.c_void_p
        self.fns=dict(shock=(lib.dr_check_shock_awe,[P,H]),board=(lib.dr_collect_board,[P,H]),row=(lib.dr_collect_random_row,[P,H,G]),
                      block=(lib.dr_collect_random_block,[P,H,G]),edge=(lib.dr_collect_edge_tiles,[P,H]),column=(lib.dr_convert_column_to_swords,[P,H,G]),
                      teleport=(lib.dr_teleport,[P,H]),earthquake=(lib.dr_earthquake,[P,H,G]),coins=(lib.dr_kill_skulls_next_to_coins,[P,H]),
                      chain=(lib.dr_create_chain,[P,H,G]))
        for f,a in self.fns.values():f.argtypes=a;f.restype=None
        def event(_,p):
            e=p.contents;k=e.kind
            self.skill_events.append(['flare',e.a,e.b,e.c] if k==5 else ['achievement',e.a,e.b] if k==2 else ['move',self.gen.filter_enabled] if k==12 else
                                     ['swap',e.a,e.b,e.c,e.d] if k==14 else ['special',e.a,e.b] if k==15 else ['other',k,e.a,e.b,e.c,e.d])
        def action(_,kind,a,b):self.skill_events.append(['action',kind,a,b])
        self.board_cb=(EVENT(event),ACTION(action))
    def load(self,c):
        super().load(c);k=c['skills']
        self.slots=SkillSlots((I32*4)(*k['type']),(I32*4)(*k['level']),(U8*4)(*k['active']))
        self.flags=TurnFlags();self.finish=TurnFinishFlags();self.finish.flag_1554c=c['flag_1554c'];self.end=EndGameState();self.anim=AnimState()
        self.state_obj=SkillState(*[C.addressof(x) for x in (self.slots,self.r,self.path_state,self.gen,self.flags,self.finish,self.rune,self.anim,self.end)])
        self.board_hooks=SkillHooks(None,*self.board_cb,C.addressof(self.match_hooks),C.addressof(self.path_hooks))
    def run(self,key,args):
        self.skill_events=[];self.gen_events=[];self.match_events=[];self.path_events=[];self.token_events=[];self.motion_events=[]
        f,_=self.fns[key];h=C.byref(self.board_hooks);g=C.addressof(self.gen_hooks);s=C.byref(self.state_obj)
        if key in ('row','block','column','earthquake','chain'):f(s,h,g)
        else:f(s,h)
        return dict(events=self.skill_events,gen=self.gen_status(),path=self.path_status(),
                    timers=[self.m.shake_progress_bd90&0xffffffff,self.m.shake_scale_bd94&0xffffffff],sound=self.m.sound_13ec4,
                    flags=dict(b15561=self.flags.b15561,b15562=self.flags.b15562,**{f'b165b8_{k}':self.flags.b165b8[k] for k in range(5)}))
    def set_extra(self,timers,sound,flags):
        self.m.shake_progress_bd90,self.m.shake_scale_bd94=timers;self.m.sound_13ec4=sound
        self.flags.b15561,self.flags.b15562=flags['b15561'],flags['b15562']
        for k in range(5):self.flags.b165b8[k]=flags[f'b165b8_{k}']

def case(rng):
    c=skills_case(rng)
    for i,t in enumerate(c['extras']):t['variant']=rng.randrange(0,5)
    for i,k in enumerate(c['combat']):
        k['defence']=rng.choice([0,0,2,rng.randrange(1,9)]);k['attack']=rng.choice([0,1,2,rng.randrange(1,15)]);k['attack_flag']=rng.randrange(2)
        if c['board'][i]['type']==1 and rng.random()<.15:c['board'][i]['enemy']=31
        if c['board'][i]['type']==1:c['board'][i]['enemy_state']=rng.choice([0,1,2,5])
    c['path_state']['turn']=rng.choice([1,40,120,rng.randrange(0,600)]);c['match']['spawn_enabled_14ae0']=rng.randrange(1,4)
    c['flag_1554c']=rng.randrange(2);c['resources'].update(health=5000,ui_health=5000)
    if rng.random()<.2:   # whole rows of plain skulls (CollectRandomRow's six-skull achievement)
        for y in rng.sample(range(6),rng.randrange(2,6)):
            for x in range(6):c['board'][y*6+x].update(type=1,enemy=0)
            if rng.random()<.5:c['board'][y*6+rng.randrange(6)].update(type=rng.choice([0,2,3,4]),enemy=0)   # five skulls
    elif rng.random()<.2:   # nearly all special enemies (CreateChain's ten tries)
        for t in c['board']:
            if rng.random()<.92:t.update(type=1,enemy=rng.choice([2,9,20]))
    return c

def main():
    old,new=Original(),Native();rng=random.Random(0x11c3c);counts={}
    for n in range(1000):
        c=case(rng);old.load(c);new.load(c)
        old.u.mem_write(old.GAME+0x1554c,bytes([c['flag_1554c']]))
        timers=[rng.choice([0,0x3f000000]),rng.choice([0,0x3e800000])];sound=rng.randrange(2)
        flags={k:int(rng.random()<.6) for k in FLAG_BYTES};old.set_extra(timers,sound,flags);new.set_extra(timers,sound,flags)
        key=list(FUNCTIONS)[n%len(FUNCTIONS)];args=()
        a,b=old.run(key,args),new.run(key,args)
        if a!=b:
            (HERE/'skill_board3_failure.json').write_text(json.dumps(dict(case=n,key=key,args=list(args),original=a,native=b),indent=2,default=str))
            raise AssertionError(f'skill_board3_failure.json ({key})')
        counts[key]=counts.get(key,0)+1
    report=dict(status='passed',comparisons=counts,functions={k:hex(v[0]) for k,v in FUNCTIONS.items()},
                original='Actual functions; their RandI, MatchTile (match harness) and Tile::SetType (generation harness) as original code',
                boundaries=['own AddFlare / QueueAchievement / MoveMatchedTiles / SwapTiles / Tile::SetSpecialType recorded'])
    (HERE/'skill_board3_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
