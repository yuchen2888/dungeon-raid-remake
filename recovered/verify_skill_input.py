#!/usr/bin/env python3
"""Skill buttons (T040-H5): actual Interface::ProcessInput 0x209e4 (with Skill::CanActivate, Skill::Activate and
Game::FireBreath 0xa274 as original code) vs native dr_skill_input (recovered_skills), on the shared state of
verify_attack_all.py.

The original runs from its entry (R0 = the Interface at Game+0x4cdc; Interface+0x1030 = Game, +0x1034 = the
previous touch phase, +0xbd0 = the pressed slot; the touch phase at Game+0x10). Interface::CursorInButton(slot)
answers whether slot is the case's button under the touch and Quad::ContainsPoint (the game / stats menu buttons,
the renderer's) answers no. Recorded and skipped: QueueSound, Quad::SetColour of a skill button, Tooltip::Show /
Hide and Interface::UpdateSkills; inside Skill::Activate the calls of verify_skills.py (sounds, achievements,
arrow colour, the Game skill functions as actions); inside FireBreath AddFlare and Tile::SetFlameVisibility, its
RandI as original code (a generation Random event). Compared: events, the pressed slot, the previous phase, the
skill slots and cooldowns, every flag Skill::Activate writes, random seeds and the flare timers.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_skills import Original as SkillsOriginal, Native as SkillsNative, case as skills_case, FLAGS, ACTIONS, SKILLS
from verify_skill_board2 import SkillHooks, SkillEvent, EVENT, ACTION
from verify_stroke import HERE, I32, U8

ENTRY,END=0x209e4,0x20c4e
FIRE,FIRE_END,RANDI=0xa274,0xa37e,0x1bca0
INTERFACE=0x4cdc
SYMBOLS={'__ZN9Interface14CursorInButtonEi':'cursor','__ZN4Quad13ContainsPointERK8GLfloat2':'contains','__ZN4Game10QueueSoundE5Sound':'sound',
         '__ZN4Quad9SetColourERK9GLcolour4':'colour','__ZN7Tooltip4ShowE9SkillTypeiiRK8GLfloat2':'tooltip','__ZN7Tooltip4HideEv':'hide',
         '__ZN9Interface12UpdateSkillsEv':'update_skills','__ZN4Game8AddFlareE9FlareType8GLfloat2RK9GLcolour4':'flare',
         '__ZN4Tile18SetFlameVisibilityEbib':'flame'}
class SkillInput(C.Structure):_fields_=[('pressed',I32),('previous_phase',I32)]

class Original(SkillsOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.input_calls={};self.inputting=False;self.pending_rand=None
        for symbol,name in SYMBOLS.items():
            self.input_calls[int(re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M)[1],16)]=name
    def resting_tile(self,x,y):
        for i in range(36):
            if struct.unpack('<II',self.u.mem_read(self.GAME+0xb400+8*i,8))==(x,y):return i
        raise AssertionError((hex(x),hex(y)))
    def hook(self,u,address,size,context):
        if self.inputting:
            lr=u.reg_read(self.LR)&~1;r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value
            if self.pending_rand and address==self.pending_rand[0]:
                self.gen_events.append([1,-1,*self.pending_rand[1:],s(r[0])]);self.pending_rand=None
            if address==RANDI and FIRE<lr<FIRE_END:self.pending_rand=(lr,s(r[0]),s(r[1]),s(r[2]));return
            name=self.input_calls.get(address)
            if name and (ENTRY<lr<END or FIRE<lr<FIRE_END):
                sp=u.reg_read(self.SP);e=None
                if name=='cursor':u.reg_write(self.regs[0],int(s(r[1])==self.button))
                elif name=='contains':u.reg_write(self.regs[0],0)
                elif name=='sound':e=['sound',s(r[1])]
                elif name=='colour':
                    slot=(r[0]-(self.GAME+INTERFACE+0x850))//0x70;assert r[0]==self.GAME+INTERFACE+0x850+0x70*slot
                    e=['colour',slot,s(self.read(r[1]))]
                elif name=='tooltip':e=['tooltip',s(r[1]),s(r[2]),s(r[3]),self.button]
                elif name=='hide':e=['hide']
                elif name=='update_skills':e=['update_skills']
                elif name=='flare':e=['flare',s(r[1]),self.resting_tile(r[2],r[3]),s(self.read(self.read(sp)))]
                else:assert r[1]&0xff==1 and r[3]&0xff==1;e=['flame',s(r[2]),self.index(r[0])]
                if e:self.skill_events.append(e)
                u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def input(self,phase,button,pressed,previous):
        u=self.u;G=self.GAME;I=G+INTERFACE;self.button=button;self.skill_events=[];self.gen_events=[];self.pending_rand=None
        self.write(I+0x1030,G);self.write(I+0x1034,previous);self.write(I+0xbd0,pressed);self.write(G+0x10,phase)
        u.reg_write(self.regs[0],I);u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1);self.inputting=self.skilling=True
        try:u.emu_start(ENTRY|1,self.STOP,timeout=0,count=2000000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.inputting=self.skilling=False
        st=self.status(None);st.pop('spare_active');st['slots']=[x[1:] for x in st['slots']]
        return dict(st,gen_events=self.gen_events,seeds=list(struct.unpack('<6I',u.mem_read(0x1eac20,24))),timers=[self.read(G+0xbd90),self.read(G+0xbd94)],
                    pressed=C.c_int32(self.read(I+0xbd0)).value,previous=C.c_int32(self.read(I+0x1034)).value)

class Native(SkillsNative):
    def __init__(self):
        super().__init__();lib=self.skills_lib
        lib.dr_skill_input.argtypes=[C.c_void_p,C.POINTER(SkillInput),I32,I32,C.POINTER(SkillHooks),C.c_void_p];lib.dr_skill_input.restype=None
        def event(_,p):
            e=p.contents;k=e.kind
            self.skill_events.append(['sound',e.a] if k==1 else ['achievement',e.a,e.b] if k==2 else ['arrow',e.a,e.b,e.c] if k==3 else ['position',e.a] if k==4 else
                                     ['flare',e.a,e.b,e.c] if k==5 else ['flame',e.a,e.b] if k==16 else ['update_skills'] if k==17 else
                                     ['colour',e.a,e.b] if k==18 else ['tooltip',e.a,e.b,e.c,e.d] if k==19 else ['hide'] if k==20 else ['other',k,e.a,e.b,e.c,e.d])
        def action(_,kind,a,b):self.skill_events.append(['action',ACTIONS[kind-1],a,b])
        self.input_cb=(EVENT(event),ACTION(action))
    def load(self,c):
        super().load(c);self.input_hooks=SkillHooks(None,*self.input_cb,None,None)
    def input(self,phase,button,pressed,previous):
        self.skill_events=[];self.gen_events=[];inp=SkillInput(pressed,previous)
        self.skills_lib.dr_skill_input(C.addressof(self.state_obj),C.byref(inp),phase,button,C.byref(self.input_hooks),C.addressof(self.gen_hooks))
        st=self.status();st.pop('spare_active');st['slots']=[x[1:] for x in st['slots']]
        return dict(st,gen_events=self.gen_events,seeds=list(self.m.random.seeds),
                    timers=[self.m.shake_progress_bd90&0xffffffff,self.m.shake_scale_bd94&0xffffffff],pressed=inp.pressed,previous=inp.previous_phase)

def main():
    old,new=Original(),Native();rng=random.Random(0x209e4);kinds={};used=fires=0
    for n in range(1500):
        c=skills_case(rng);count=c['resources']['skill_count']
        if rng.random()<.5 and count:   # ready cooldowns
            for i in range(4):c['resources']['skill_current'][i]=c['resources']['skill_max'][i]
        if rng.random()<.3:c['game']['race']=8
        c['game'].update(base_damage=rng.randrange(1,30),weapon_damage=rng.randrange(1,30))
        if rng.random()<.2:c['resources']['skill_max'][rng.randrange(4)]=-rng.randrange(1,4)
        old.load(c);new.load(c)
        phase=rng.choice([0,1,1,2,2,3,4]);button=rng.choice([-1,0,1,2,3,rng.randrange(-1,4)])
        pressed=rng.choice([-1,-1,button,rng.randrange(-1,4)]) if phase in (2,3) else rng.choice([-1,-1,0])
        previous=rng.choice([0,0,1,2,3])
        a,b=old.input(phase,button,pressed,previous),new.input(phase,button,pressed,previous)
        if a!=b:
            (HERE/'skill_input_failure.json').write_text(json.dumps(dict(case=n,phase=phase,button=button,pressed=pressed,previous=previous,original=a,native=b),indent=2))
            raise AssertionError('skill_input_failure.json')
        k=(phase,'used' if ['update_skills'] in a['events'] else 'pressed' if a['pressed']>=0 and pressed<0 else 'other');kinds[k]=kinds.get(k,0)+1
        used+=['update_skills'] in a['events'];fires+=any(e[0]=='flame' for e in a['events'])
    assert used>50 and fires>5,(used,fires)
    report=dict(status='passed',comparisons=1500,skills_used=used,fire_breaths=fires,kinds={f'{k[0]}:{k[1]}':v for k,v in sorted(kinds.items())},
                functions=[dict(symbol='__ZN9Interface12ProcessInputEv',address=hex(ENTRY),native='dr_skill_input (skill buttons)'),
                           dict(symbol='__ZN4Game10FireBreathEv',address=hex(FIRE),native='dr_fire_breath')],
                original='Actual Interface::ProcessInput, Skill::CanActivate / Activate and FireBreath',
                boundaries=['button layout (CursorInButton / ContainsPoint) from the case; sounds, button colours, tooltips, UpdateSkills, flares, '
                            'SetFlameVisibility and the Game skill functions recorded'])
    (HERE/'skill_input_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
