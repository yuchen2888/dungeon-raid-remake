#!/usr/bin/env python3
"""Actual CharacterClass::Initialise and Game::SetCurrentClass vs native dr_class_initialise / dr_current_class
(recovered_progression, T040-M2).

CharacterClass::Initialise(type, Game*) 0x111e20 runs from its entry on a class record (388 bytes) whose fields hold
random bytes beforehand and whose three std::vector<SkillType> (base skills +0x30, other skills +0x3c, replacement
skills +0x48) are empty, as Game::Start finds them; push_back is modelled (the vector memory kept as the original's
layout, so IsBaseSkill and size run as original code). Compared for each class type 0..9: type, race, base race,
perks, flaws, level, the progress counters (+0x58..+0x6b: untouched on both sides), the replacement list, the base
skills (dr_class_base_skills, recovered_menu) and the other skills (the rest of 0..39 in order).
Game::SetCurrentClass(type) 0x1a390 runs from its entry with the ten records' levels random (NameScreen::SelectClass
recorded and skipped); the current class (Game+0x1648c) is compared with dr_current_class for every type 0..9.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_skills import Original as SkillsOriginal, case as skills_case
from verify_stroke import HERE
from verify_progression import Profile

INIT,SET_CURRENT,REC,VEC=0x111e20,0x1a390,0x170f000,0x170e000
CLASSES,STRIDE,CURRENT=0x15564,388,0x1648c
TEXT=(HERE.parent/'armv7-disassembly.txt').read_text()
def addr(symbol):return int(re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',TEXT,re.M)[1],16)
PUSH,SELECT=addr('__ZNSt6vectorI9SkillTypeSaIS0_EE9push_backERKS0_'),addr('__ZN10NameScreen11SelectClassER14CharacterClass')
assert addr('__ZN14CharacterClass10InitialiseE9ClassTypeP4Game')==INIT and addr('__ZN4Game15SetCurrentClassE9ClassType')==SET_CURRENT

class Original(SkillsOriginal):
    def __init__(self):super().__init__();self.classing=False;self.selected=[]
    def hook(self,u,address,size,context):
        if self.classing and address==PUSH:   # std::vector<SkillType>::push_back: the vector memory as the original's
            v,p=u.reg_read(self.regs[0]),u.reg_read(self.regs[1]);vals=self.vecs.setdefault(v,[]);vals.append(self.read(p))
            base=VEC+0x400*list(self.vecs).index(v)
            for k,x in enumerate(vals):self.write(base+4*k,x&0xffffffff)
            self.write(v,base);self.write(v+4,base+4*len(vals));self.write(v+8,base+0x400)
            u.reg_write(self.PC,u.reg_read(self.LR));return
        if self.classing and address==SELECT:self.selected.append(u.reg_read(self.regs[1]));u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def call(self,entry,args):
        u=self.u
        for r,v in zip(self.regs,args):u.reg_write(r,v&0xffffffff)
        u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1);self.classing=True
        try:u.emu_start(entry|1,self.STOP,timeout=0,count=500000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.classing=False
    def vector(self,v):
        b,e=self.read(v),self.read(v+4)
        return [C.c_int32(self.read(a)).value for a in range(b,e,4)] if b else []

def main():
    old=Original();old.load(skills_case(random.Random(1)));u=old.u
    progression=C.CDLL(str(HERE/'recovered_progression_native.dylib'));menu=C.CDLL(str(HERE/'recovered_menu_native.dylib'))
    init=progression.dr_class_initialise;init.argtypes=[C.POINTER(Profile),C.c_int32,C.POINTER(C.c_int32)];init.restype=C.c_bool
    current=progression.dr_current_class;current.argtypes=[C.POINTER(Profile),C.c_int32];current.restype=C.c_int32
    base_skills=((C.c_int32*20)*10).in_dll(menu,'dr_class_base_skills')
    rng=random.Random(0x111e20);initialised=0;currents=0;fallbacks=0
    rd=lambda a:C.c_int32(old.read(REC+a)).value
    for trial in range(40):
        for t in range(10):
            fill=bytes(rng.randrange(256) for _ in range(388))
            u.mem_write(REC,fill);u.mem_write(REC+0x30,bytes(36));old.vecs={}   # empty vectors (begin, end, capacity)
            old.call(INIT,[REC,t,old.GAME])
            p=Profile();p.class_type,p.race,p.base_race=(rd(o) for o in (4,8,0xc))
            for i in range(4):p.perks[i]=rd(0x10+4*i);p.flaws[i]=rd(0x20+4*i)
            p.level=old.u.mem_read(REC+0x54,1)[0]
            counters=list(struct.unpack('<5I',fill[0x58:0x6c]))
            p.games_played,p.enemies_killed,p.normal_score,p.hard_score,p.harder_score=counters
            q=Profile();q.games_played,q.enemies_killed,q.normal_score,q.hard_score,q.harder_score=counters
            storage=(C.c_int32*20)(*[rng.randrange(-5,300) for _ in range(20)]);assert init(C.byref(q),t,storage)
            base=old.vector(REC+0x30)
            a=dict(fields=[p.class_type,p.race,p.base_race,list(p.perks),list(p.flaws),p.level],counters=list(struct.unpack('<5I',bytes(u.mem_read(REC+0x58,20)))),
                   replacement=old.vector(REC+0x48),base=base,others=old.vector(REC+0x3c),game=old.read(REC))
            b=dict(fields=[q.class_type,q.race,q.base_race,list(q.perks),list(q.flaws),q.level],counters=[q.games_played,q.enemies_killed,q.normal_score,q.hard_score,q.harder_score],
                   replacement=list(q.replacement_skills[:q.replacement_skill_count]),base=list(base_skills[t]),
                   others=[k for k in range(40) if k not in list(base_skills[t])],game=old.GAME)
            assert a['counters']==counters
            if a!=b:
                (HERE/'class_init_failure.json').write_text(json.dumps(dict(type=t,original=a,native=b),indent=2));raise AssertionError('class_init_failure.json')
            initialised+=1
        # Game::SetCurrentClass: random levels, every type
        levels=[rng.choice([0,0,1,5,10,rng.randrange(256)]) for _ in range(10)]
        roster=(Profile*10)()
        for i,l in enumerate(levels):u.mem_write(old.GAME+CLASSES+STRIDE*i+0x54,bytes([l]));roster[i].level=l
        for t in range(10):
            old.write(old.GAME+CURRENT,rng.randrange(10));old.selected=[];old.call(SET_CURRENT,[old.GAME,t])
            a=[C.c_int32(old.read(old.GAME+CURRENT)).value,len(old.selected)];b=[current(roster,t),1]
            if a!=b:
                (HERE/'class_init_failure.json').write_text(json.dumps(dict(type=t,levels=levels,original=a,native=b),indent=2));raise AssertionError('class_init_failure.json')
            currents+=1;fallbacks+=a[0]!=t
    assert fallbacks>0 and fallbacks<currents,(fallbacks,currents)
    print(json.dumps(dict(status='passed',initialised=initialised,set_current_class=currents,locked_fallbacks=fallbacks,
                          functions=['CharacterClass::Initialise 0x111e20','Game::SetCurrentClass 0x1a390'],
                          native=['dr_class_initialise','dr_current_class'],original='Actual functions from their entries',
                          boundaries=['std::vector<SkillType>::push_back modelled','NameScreen::SelectClass recorded and skipped',
                                      'class types 0..9 (the only ones Game::Start initialises)'])))

if __name__=='__main__':main()
