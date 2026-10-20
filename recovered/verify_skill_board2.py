#!/usr/bin/env python3
"""Board skills, batch 2 (T040-H3): actual Game::DemoteSpecialEnemy 0xa6f4, PromoteNormalEnemy 0xb648,
KillSpecialEnemy 0x11498, GrabTiles 0x12060, ShatterDefence 0xcf4c and ExplodeArmour 0x115dc vs native
dr_demote_special_enemy / dr_promote_normal_enemy / dr_kill_special_enemy / dr_grab_tiles /
dr_shatter_defence / dr_explode_armour (recovered_skills), on the shared state of verify_attack_all.py.

Each original function runs from its entry to its return. The calls the function itself makes (the return
address inside it) are recorded and skipped: AddFlare, AddParticles, Tile::UpdateText, AddSimpleLabel,
Tile::UpdateEnemyUV, MoveMatchedTiles and JumpDown; its own RandI runs as original code and is recorded as
a generation Random event. Game::MatchTile runs as original code with the match harness (as in
verify_match.py), Game::AttackSkull with the path harness (verify_path.py), Tile::Promote with the
generation harness (verify_generation.py). Compared: skill events, the generation / board / combat state
and events, the match and path state and events, random seeds, the flare timers and Game+0x13ec4.
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

FUNCTIONS=dict(demote=(0xa6f4,0xa7f4),promote=(0xb648,0xb780),kill=(0x11498,0x115dc),grab=(0x12060,0x12188),shatter=(0xcf4c,0xd03c),
               explode=(0x115dc,0x11748))
RANDI,TIMERS,SOUND=0x1bca0,0xbd90,0x13ec4
BODY={'__ZN4Game8AddFlareE9FlareType8GLfloat2RK9GLcolour4':'flare','__ZN4Game12AddParticlesEP4Tile12ParticleType':'particles',
      '__ZN4Tile10UpdateTextEbbb':'text','__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif':'label',
      '__ZN4Tile13UpdateEnemyUVEv':'enemy_uv','__ZN4Game16MoveMatchedTilesEv':'move','__ZN4Game8JumpDownEP4Tile':'jump'}

class SkillEvent(C.Structure):_fields_=[('kind',I32),('a',I32),('b',I32),('c',I32),('d',I32)]
EVENT=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(SkillEvent))
ACTION=C.CFUNCTYPE(None,C.c_void_p,I32,I32,I32)
class SkillHooks(C.Structure):_fields_=[('context',C.c_void_p),('event',EVENT),('action',ACTION),('match',C.c_void_p),('path',C.c_void_p)]

class Original(GateOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.body={};self.boarding=False;self.pending_rand=None
        for symbol,name in BODY.items():
            self.body[int(re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M)[1],16)]=name
    def resting_tile(self,x,y):
        for i in range(36):
            if struct.unpack('<II',self.u.mem_read(self.GAME+0xb400+8*i,8))==(x,y):return i
        raise AssertionError((hex(x),hex(y)))
    def hook(self,u,address,size,context):
        if self.boarding:
            lr=u.reg_read(self.LR)&~1;start,end=FUNCTIONS[self.boarding];inside=start<lr<end;s=lambda v:C.c_int32(v).value
            r=[u.reg_read(v) for v in self.regs]
            if self.pending_rand and address==self.pending_rand[0]:
                self.gen_events.append([1,-1,*self.pending_rand[1:],s(r[0])]);self.pending_rand=None
            if address==RANDI and inside:self.pending_rand=(lr,s(r[0]),s(r[1]),s(r[2]));return   # runs as original code
            name=self.body.get(address)
            if name and inside:
                sp=u.reg_read(self.SP)
                if name=='flare':e=['flare',s(r[1]),self.resting_tile(r[2],r[3]),s(self.read(self.read(sp)))]
                elif name=='particles':e=['particles',s(r[2]),self.index(r[1])]
                elif name=='text':e=['text',self.index(r[0]),r[1]&0xff,r[2]&0xff,r[3]&0xff]
                elif name=='label':
                    assert self.read(sp+4)==0x3f000000;e=['label',s(r[1]),self.resting_tile(*struct.unpack('<II',u.mem_read(r[2],8))),s(r[3]),s(self.read(sp))]
                elif name=='enemy_uv':e=['enemy_uv',self.index(r[0])]
                elif name=='move':e=['move']
                else:e=['jump',self.index(r[1])]
                self.skill_events.append(e);u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def run(self,key,args):
        u=self.u;self.skill_events=[];self.gen_events=[];self.match_events=[];self.path_events=[];self.token_events=[];self.motion_events=[]
        self.pending_gen=self.pending_rand=None;self.int_sets={}
        self.boarding=key;self.gen_active=key in ('demote','promote');self.path_active=key=='explode'
        for reg,v in zip(self.regs,[self.GAME,*args]):u.reg_write(reg,v&0xffffffff)
        u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1)
        try:u.emu_start(FUNCTIONS[key][0]|1,self.STOP,timeout=0,count=5000000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.boarding=self.gen_active=self.path_active=False
        G=self.GAME
        return dict(events=self.skill_events,gen=self.gen_status(),path=self.path_status(),timers=[self.read(G+TIMERS),self.read(G+TIMERS+4)],
                    sound=u.mem_read(G+SOUND,1)[0])
    def set_extra(self,timers,sound):
        self.write(self.GAME+TIMERS,timers[0]);self.write(self.GAME+TIMERS+4,timers[1]);self.u.mem_write(self.GAME+SOUND,bytes([sound]))

class Native(GateNative):
    def __init__(self):
        super().__init__();lib=self.skills_lib=C.CDLL(str(HERE/'recovered_skills_native.dylib'))
        P=C.POINTER(SkillState);H=C.POINTER(SkillHooks);G=C.c_void_p
        self.fns=dict(demote=(lib.dr_demote_special_enemy,[P,H,G]),promote=(lib.dr_promote_normal_enemy,[P,H,G]),kill=(lib.dr_kill_special_enemy,[P,H,G]),
                      grab=(lib.dr_grab_tiles,[P,I32,I32,H]),shatter=(lib.dr_shatter_defence,[P,H]),explode=(lib.dr_explode_armour,[P,H]))
        for f,a in self.fns.values():f.argtypes=a;f.restype=None
        def event(_,p):
            e=p.contents;k=e.kind
            self.skill_events.append(['flare',e.a,e.b,e.c] if k==5 else ['particles',e.a,e.b] if k==8 else ['text',e.b,e.a,e.c,e.d] if k==9 else
                                     ['label',e.a,e.b,e.c,e.d] if k==10 else ['enemy_uv',e.b] if k==11 else ['move'] if k==12 else ['jump',e.b] if k==13 else ['other',k,e.a,e.b,e.c,e.d])
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
        if key in ('demote','promote','kill'):f(s,h,g)
        elif key=='grab':f(s,*args,h)
        else:f(s,h)
        return dict(events=self.skill_events,gen=self.gen_status(),path=self.path_status(),
                    timers=[self.m.shake_progress_bd90&0xffffffff,self.m.shake_scale_bd94&0xffffffff],sound=self.m.sound_13ec4)
    def set_extra(self,timers,sound):self.m.shake_progress_bd90,self.m.shake_scale_bd94=timers;self.m.sound_13ec4=sound

def case(rng):
    c=skills_case(rng)
    for i,t in enumerate(c['extras']):t['variant']=rng.randrange(0,5)
    for i,k in enumerate(c['combat']):
        k['defence']=rng.choice([0,0,2,rng.randrange(1,9)]);k['attack']=rng.choice([0,1,2,rng.randrange(1,15)]);k['attack_flag']=rng.randrange(2)
        if c['board'][i]['type']==1 and rng.random()<.15:c['board'][i]['enemy']=31
        if c['board'][i]['type']==1:c['board'][i]['enemy_state']=rng.choice([0,1,2,5])
    c['path_state']['turn']=rng.choice([1,40,120,rng.randrange(0,600)]);c['match']['spawn_enabled_14ae0']=rng.randrange(1,4)
    c['flag_1554c']=rng.randrange(2);c['resources'].update(health=5000,ui_health=5000)
    return c

def main():
    old,new=Original(),Native();rng=random.Random(0x11498);counts={}
    for n in range(600):
        c=case(rng);old.load(c);new.load(c)
        old.u.mem_write(old.GAME+0x1554c,bytes([c['flag_1554c']]))
        timers=[rng.choice([0,0x3f000000]),rng.choice([0,0x3e800000])];sound=rng.randrange(2);old.set_extra(timers,sound);new.set_extra(timers,sound)
        key=list(FUNCTIONS)[n%len(FUNCTIONS)]
        args=rng.choice([(0,0),(3,3),(0,1),(2,2),(1,2),(4,4)]) if key=='grab' else ()
        a,b=old.run(key,args),new.run(key,args)
        if a!=b:
            (HERE/'skill_board2_failure.json').write_text(json.dumps(dict(case=n,key=key,args=list(args),original=a,native=b),indent=2,default=str))
            raise AssertionError(f'skill_board2_failure.json ({key})')
        counts[key]=counts.get(key,0)+1
    report=dict(status='passed',comparisons=counts,functions={k:hex(v[0]) for k,v in FUNCTIONS.items()},
                original='Actual functions; their RandI, MatchTile (match harness), AttackSkull (path harness) and Tile::Promote (generation harness) as original code',
                boundaries=['own AddFlare / AddParticles / UpdateText / AddSimpleLabel / UpdateEnemyUV / MoveMatchedTiles / JumpDown recorded'])
    (HERE/'skill_board2_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
