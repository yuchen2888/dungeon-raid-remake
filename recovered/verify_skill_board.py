#!/usr/bin/env python3
"""Board skills, batch 1 (T040-H2): actual Game::Upgrade 0x9694, FreezeSkulls 0xa470, ConvertTiles 0xa7f4,
CreateManaPotions 0xa548, CreateExplosivePotions 0xa380, CreateArrows 0xcdac and CreateMagicSword 0xccc0 vs
native dr_skill_upgrade / dr_freeze_skulls / dr_convert_tiles / dr_create_mana_potions /
dr_create_explosive_potions / dr_create_arrows / dr_create_magic_sword (recovered_skills), on the shared
state of verify_attack_all.py.

Each original function runs from its entry to its return with the generation harness on (as in
verify_generation.py: Tile::SetType, RandI, Tile::IsNormalPotion, GetNormalSwordCount, Tile::MakeArrow /
MakeManaPotion / MakeExplosivePotion / MakeMagicSword and Tile::SetFreezeVisibility run as original code;
Quad::SetUV / SetColour, text and the RNG calls are recorded as generation events). Recorded and skipped:
Game::AddFlare (flare type, tile of the resting position, colour) and Interface::ShowMenu. Tile::
SetFreezeVisibility is recorded and runs (its overlay quad's SetUV / SetSize / SetAlpha skipped). Compared: skill events, the board, combat tiles, potions,
generation extras and events, random seeds, the flare timers (Game+0xbd90 / 0xbd94) and Game+0x165b8.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_input_gate import Original as GateOriginal, Native as GateNative
from verify_skills import SkillState, SkillEvent, SkillHooks, EVENT, ACTION, case as skills_case
from verify_turn_begin import SkillSlots, TurnFlags
from verify_turn_finish import TurnFinishFlags
from verify_game_over import EndGameState
from verify_attack_phase4 import AnimState
from verify_stroke import HERE, I32, U8

FUNCTIONS=dict(upgrade=0x9694,freeze=0xa470,convert=0xa7f4,mana=0xa548,explosive=0xa380,arrows=0xcdac,magic=0xccc0)
ADD_FLARE,SHOW_MENU,FREEZE_VISIBILITY=0x9f94,0x1eb20,0x3d934
TIMERS,B165B8=0xbd90,0x165b8

class Original(GateOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text()
        addr=lambda s:int(re.search(r'^'+re.escape(s)+r':\n\s*([0-9a-f]+):',text,re.M)[1],16)
        assert addr('__ZN4Game8AddFlareE9FlareType8GLfloat2RK9GLcolour4')==ADD_FLARE and addr('__ZN9Interface8ShowMenuE8MenuType')==SHOW_MENU
        assert addr('__ZN4Tile19SetFreezeVisibilityEb')==FREEZE_VISIBILITY
        self.match_calls={k:v for k,v in self.match_calls.items() if k!=ADD_FLARE};self.boarding=False
        self.overlay_quad={addr(q) for q in ('__ZN4Quad7SetSizeERK8GLfloat2','__ZN4Quad5SetUVERK8GLfloat2S2_','__ZN4Quad8SetAlphaEh')}
    def resting_tile(self,x,y):
        for i in range(36):
            if struct.unpack('<II',self.u.mem_read(self.GAME+0xb400+8*i,8))==(x,y):return i
        raise AssertionError((hex(x),hex(y)))
    def hook(self,u,address,size,context):
        if self.boarding:
            r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value
            if address==ADD_FLARE:
                self.skill_events.append(['flare',s(r[1]),self.resting_tile(r[2],r[3]),s(self.read(self.read(u.reg_read(self.SP))))])
                u.reg_write(self.PC,u.reg_read(self.LR));return
            if address==SHOW_MENU:
                assert r[0]==self.GAME+0x4cdc;self.skill_events.append(['menu',s(r[1])]);u.reg_write(self.PC,u.reg_read(self.LR));return
            if address==FREEZE_VISIBILITY:assert r[1]&0xff==1;self.skill_events.append(['freeze',self.index(r[0])])   # runs
            if address in self.overlay_quad and FREEZE_VISIBILITY<(u.reg_read(self.LR)&~1)<0x3d98c:   # the freeze overlay quad (presentation)
                u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def run(self,key,args):
        u=self.u;self.skill_events=[];self.gen_events=[];self.pending_gen=None;self.boarding=self.gen_active=True
        for reg,v in zip(self.regs,[self.GAME,*args]):u.reg_write(reg,v&0xffffffff)
        u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1)
        try:u.emu_start(FUNCTIONS[key]|1,self.STOP,timeout=0,count=2000000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.boarding=self.gen_active=False
        G=self.GAME
        return dict(events=self.skill_events,gen=self.gen_status(),timers=[self.read(G+TIMERS),self.read(G+TIMERS+4)],b165b8=u.mem_read(G+B165B8,1)[0])
    def set_extra(self,timers,b):
        self.write(self.GAME+TIMERS,timers[0]);self.write(self.GAME+TIMERS+4,timers[1]);self.u.mem_write(self.GAME+B165B8,bytes([b]))

class Native(GateNative):
    def __init__(self):
        super().__init__();lib=self.skills_lib=C.CDLL(str(HERE/'recovered_skills_native.dylib'))
        P=C.POINTER(SkillState);H=C.POINTER(SkillHooks);G=C.c_void_p
        self.fns=dict(upgrade=(lib.dr_skill_upgrade,[H]),freeze=(lib.dr_freeze_skulls,[P,H]),convert=(lib.dr_convert_tiles,[P,I32,I32,H,G]),
                      mana=(lib.dr_create_mana_potions,[P,H,G]),explosive=(lib.dr_create_explosive_potions,[P,H,G]),
                      arrows=(lib.dr_create_arrows,[P,H,G]),magic=(lib.dr_create_magic_sword,[P,H,G]))
        for f,a in self.fns.values():f.argtypes=a;f.restype=None
        def event(_,p):
            e=p.contents
            self.skill_events.append(['flare',e.a,e.b,e.c] if e.kind==5 else ['freeze',e.b] if e.kind==6 else ['menu',e.a] if e.kind==7 else ['other',e.kind,e.a,e.b,e.c])
        def action(_,kind,a,b):self.skill_events.append(['action',kind,a,b])
        self.board_cb=(EVENT(event),ACTION(action));self.board_hooks=SkillHooks(None,*self.board_cb)
    def load(self,c):
        super().load(c);k=c['skills']
        self.slots=SkillSlots((I32*4)(*k['type']),(I32*4)(*k['level']),(U8*4)(*k['active']))
        self.flags=TurnFlags();self.finish=TurnFinishFlags();self.end=EndGameState();self.anim=AnimState()
        self.state_obj=SkillState(*[C.addressof(x) for x in (self.slots,self.r,self.path_state,self.gen,self.flags,self.finish,self.rune,self.anim,self.end)])
    def run(self,key,args):
        self.skill_events=[];self.gen_events=[];f,types=self.fns[key];h=C.byref(self.board_hooks);g=C.addressof(self.gen_hooks);s=C.byref(self.state_obj)
        if key=='upgrade':f(h)
        elif key=='freeze':f(s,h)
        elif key=='convert':f(s,*args,h,g)
        else:f(s,h,g)
        return dict(events=self.skill_events,gen=self.gen_status(),timers=[self.m.shake_progress_bd90&0xffffffff,self.m.shake_scale_bd94&0xffffffff],
                    b165b8=self.flags.b165b8[0])
    def set_extra(self,timers,b):self.m.shake_progress_bd90,self.m.shake_scale_bd94=timers;self.flags.b165b8[0]=b

def case(rng):
    c=skills_case(rng)
    for t in c['extras']:t['variant']=rng.randrange(0,5)
    c['path_state']['turn']=rng.choice([1,40,120,rng.randrange(0,600)]);c['match']['spawn_enabled_14ae0']=rng.randrange(1,4)
    return c

def main():
    old,new=Original(),Native();rng=random.Random(0xa470);counts={};flares=0
    for n in range(700):
        c=case(rng);old.load(c);new.load(c)
        timers=[rng.choice([0,0x3f000000,0x40000000]),rng.choice([0,0x3e800000])];b=rng.randrange(2);old.set_extra(timers,b);new.set_extra(timers,b)
        key=list(FUNCTIONS)[n%len(FUNCTIONS)]
        args=[rng.choice([(4,2),(4,3),(1,4),(2,4),(2,1),(rng.randrange(6),rng.randrange(6))])][0] if key=='convert' else []
        a,b2=old.run(key,args),new.run(key,args)
        if a!=b2:
            (HERE/'skill_board_failure.json').write_text(json.dumps(dict(case=c,key=key,args=list(args),original=a,native=b2),indent=2))
            raise AssertionError(f'skill_board_failure.json ({key})')
        counts[key]=counts.get(key,0)+1;flares+=sum(1 for e in a['events'] if e[0]=='flare')
    report=dict(status='passed',comparisons=counts,flares=flares,
                functions={k:hex(v) for k,v in FUNCTIONS.items()},
                original='Actual functions with the generation harness on; SetType, RandI, IsNormalPotion, GetNormalSwordCount, Tile::Make* and SetFreezeVisibility as original code',
                boundaries=['AddFlare and Interface::ShowMenu recorded (AddFlare game state: dr_add_flare, wired by the session)'])
    (HERE/'skill_board_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
