#!/usr/bin/env python3
"""The class screen's rules (T040-M4): actual CharacterClass / Game / ClassScreen functions vs native recovered code.

Each trial builds the ten class records at Game+0x15564 (388 bytes each: type, race, base race, perks, flaws, level and
three std::vector<SkillType> -- base skills, the other skills, the replacement list -- whose memory is laid out as the
original's) from random values, and the same roster as native ClassProfile records. Compared:
- CharacterClass::CanChooseRace, IsPerkUnlocked(slot -1..4), GetReplacementSkillsAllowed for every record;
- Game::IsRaceUnlocked(race 0..10), Game::IsPerkUnlocked(perk 0..10);
- CharacterClass::SetPerk / SetFlaw / SetReplacementSkill with random slots and values (255 included) on the current
  record (Game+0x1648c), the record compared after each;
- ClassScreen::UpdatePerks and UpdateAbilities (ClassScreen at Game+0x12c78) run as original code with their display
  calls skipped and nothing being dragged: the choosable perks / flaws (+0xa84, 20 bytes) and skills (+0xaac, 20 bytes)
  against dr_class_choices (recovered_menu) on the same roster.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_skills import Original as SkillsOriginal, case as skills_case
from verify_stroke import HERE
from verify_progression import Profile

CLASSES,STRIDE,CURRENT,SCREEN=0x15564,388,0x1648c,0x12c78
VEC=0x170a000   # the records' vectors: 10 records x 3 vectors x 0x100 bytes
PANELS=0x3400000   # scratch for the class screen's panel and label vectors (display memory)
TEXT=(HERE.parent/'armv7-disassembly.txt').read_text()
def addr(symbol):return int(re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',TEXT,re.M)[1],16)
FUNCS=dict(choose=addr('__ZN14CharacterClass13CanChooseRaceEv'),slot=addr('__ZN14CharacterClass14IsPerkUnlockedEi'),
           allowed=addr('__ZN14CharacterClass27GetReplacementSkillsAllowedEv'),perk=addr('__ZN14CharacterClass7SetPerkEi8PerkType'),
           flaw=addr('__ZN14CharacterClass7SetFlawEi8FlawType'),skill=addr('__ZN14CharacterClass19SetReplacementSkillEi9SkillType'),
           race_unlocked=addr('__ZN4Game14IsRaceUnlockedE8RaceType'),perk_unlocked=addr('__ZN4Game14IsPerkUnlockedE8PerkType'),
           update_perks=addr('__ZN11ClassScreen11UpdatePerksEv'),update_abilities=addr('__ZN11ClassScreen15UpdateAbilitiesEv'))
RUN={addr(n) for n in ('__ZN14CharacterClass14IsPerkUnlockedEi','__ZN4Game14IsPerkUnlockedE8PerkType','__ZN4Game15IsSkillUnlockedE9SkillType',
                       '__ZN14CharacterClass27GetReplacementSkillsAllowedEv','__ZN14CharacterClass18IsReplacementSkillE9SkillType',
                       '__ZNKSt6vectorI9SkillTypeSaIS0_EE4sizeEv','__ZN14CharacterClass8HavePerkE8PerkType','__ZN14CharacterClass8HaveFlawE8FlawType',
                       '__ZN14CharacterClass24GetReplacementSkillCountEv')}
STARTS={int(a,16) for a in re.findall(r'^[^\s][^\n]*:\n\s+([0-9a-f]+):',TEXT,re.M)}
SCREEN_RANGES=[(FUNCS['update_perks'],FUNCS['update_perks']+2116),(FUNCS['update_abilities'],FUNCS['update_abilities']+872)]

class Original(SkillsOriginal):
    def __init__(self):super().__init__();self.screening=False
    def hook(self,u,address,size,context):
        if self.screening and address in STARTS and address not in RUN:
            lr=u.reg_read(self.LR)&~1
            if any(a<=lr<b for a,b in SCREEN_RANGES):u.reg_write(self.PC,lr|1);return   # display
        return super().hook(u,address,size,context)
    def call(self,entry,args,screening=False):
        u=self.u
        for r,v in zip(self.regs,args):u.reg_write(r,v&0xffffffff)
        u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1);self.screening=screening
        try:u.emu_start(entry|1,self.STOP,timeout=0,count=2000000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.screening=False
        return u.reg_read(self.regs[0])
    def record(self,i):return self.GAME+CLASSES+STRIDE*i
    def write_vector(self,v,base,values):
        for k,x in enumerate(values):self.write(base+4*k,x&0xffffffff)
        self.write(v,base);self.write(v+4,base+4*len(values));self.write(v+8,base+0x100)
    def vector(self,v):
        b,e=self.read(v),self.read(v+4);return [C.c_int32(self.read(a)).value for a in range(b,e,4)]

def main():
    old=Original();old.load(skills_case(random.Random(1)));u=old.u;G=old.GAME;u.mem_map(PANELS,0x40000)
    menu=C.CDLL(str(HERE/'recovered_menu_native.dylib'));prog=C.CDLL(str(HERE/'recovered_progression_native.dylib'))
    base_skills=((C.c_int32*20)*10).in_dll(menu,'dr_class_base_skills')
    for n,a,r in [('dr_class_can_choose_race',[C.POINTER(Profile)],C.c_bool),('dr_class_slot_unlocked',[C.POINTER(Profile),C.c_int32],C.c_bool),
                  ('dr_class_replacements_allowed',[C.POINTER(Profile)],C.c_size_t),('dr_race_unlocked',[C.POINTER(Profile),C.c_int32],C.c_bool),
                  ('dr_perk_unlocked',[C.POINTER(Profile),C.c_int32],C.c_bool)]+[(f,[C.POINTER(Profile),C.c_int32,C.c_int32],None) for f in
                  ('dr_class_set_perk','dr_class_set_flaw','dr_class_set_replacement')]:
        f=getattr(prog,n);f.argtypes=a;f.restype=r
    menu.dr_class_choices.argtypes=[C.POINTER(Profile),C.c_size_t]+[C.POINTER(C.c_uint8)]*3;menu.dr_class_choices.restype=None
    roster=(Profile*10)();lists=[(C.c_int32*20)() for _ in range(10)]
    for i in range(10):roster[i].replacement_skills=lists[i];roster[i].replacement_skill_count=20
    rng=random.Random(0x10ca70);counts=dict(rules=0,sets=0,choices=0,choosable=0)
    def fail(**k):
        (HERE/'class_screen_failure.json').write_text(json.dumps(k,indent=2,default=str));raise AssertionError('class_screen_failure.json')
    for trial in range(300):
        cur=rng.choice([0,rng.randrange(10)])
        for i in range(10):
            rec=old.record(i);t=i;level=rng.choice([0,0,1,2,3,5,7,8,9,10,rng.randrange(11)]) if i else rng.choice([1,3,5,8,10])
            race=rng.randrange(10);base=rng.choice([race,rng.randrange(10)])
            first=rng.choice([255,rng.randrange(10)]);perks=[first]+[rng.choice([255,255,rng.randrange(10)]) for _ in range(3)]
            flaws=[first]+[rng.choice([255,255,rng.randrange(10)]) for _ in range(3)]
            others=[k for k in range(40) if k not in list(base_skills[t])]
            repl=[255]+[rng.choice([255,255,255,rng.choice(others)]) for _ in range(19)]
            u.mem_write(rec,bytes(STRIDE));old.write(rec,G);old.write(rec+4,t);old.write(rec+8,race);old.write(rec+0xc,base)
            for k in range(4):old.write(rec+0x10+4*k,perks[k]);old.write(rec+0x20+4*k,flaws[k])
            u.mem_write(rec+0x54,bytes([level]))
            for j,(off,vals) in enumerate(((0x30,list(base_skills[t])),(0x3c,others),(0x48,repl))):old.write_vector(rec+off,VEC+0x300*i+0x100*j,vals)
            p=roster[i];p.class_type=t;p.race=race;p.base_race=base;p.level=level
            for k in range(4):p.perks[k]=perks[k];p.flaws[k]=flaws[k]
            for k in range(20):p.replacement_skills[k]=repl[k]
            p.replacement_skill_count=20
        old.write(G+CURRENT,cur)
        for i in range(10):   # rules of every record
            rec=old.record(i);p=C.pointer(roster[i])
            a=[old.call(FUNCS['choose'],[rec])&0xff,[old.call(FUNCS['slot'],[rec,s])&0xff for s in range(-1,5)],old.call(FUNCS['allowed'],[rec])]
            b=[int(prog.dr_class_can_choose_race(p)),[int(prog.dr_class_slot_unlocked(p,s)) for s in range(-1,5)],prog.dr_class_replacements_allowed(p)]
            if a!=b:fail(trial=trial,record=i,original=a,native=b)
            counts['rules']+=1
        a=[[old.call(FUNCS['race_unlocked'],[G,r])&0xff for r in range(11)],[old.call(FUNCS['perk_unlocked'],[G,k])&0xff for k in range(11)]]
        b=[[int(prog.dr_race_unlocked(roster,r)) for r in range(11)],[int(prog.dr_perk_unlocked(roster,k)) for k in range(11)]]
        if a!=b:fail(trial=trial,original=a,native=b)
        # the choosable icons (nothing dragged)
        S=G+SCREEN;old.write(S,G);old.write(S+0xa80,0xffffffff);old.write(S+0xaa8,0xffffffff)
        for off,base in ((0xa28,PANELS),(0xa34,PANELS+0x10000),(0x9d4,PANELS+0x20000)):old.write(S+off,base)   # its panel / label vectors
        old.write(S+0xa50,0);old.write(S+0xa54,20)                                                        # the perk and flaw panels' first index
        old.call(FUNCS['update_perks'],[S],True);old.call(FUNCS['update_abilities'],[S],True)
        perks,flaws,skills=(C.c_uint8*10)(),(C.c_uint8*10)(),(C.c_uint8*20)()
        menu.dr_class_choices(roster,cur,perks,flaws,skills)
        a=[list(u.mem_read(S+0xa84,20)),list(u.mem_read(S+0xaac,20))];b=[list(perks)+list(flaws),list(skills)]
        if a!=b:fail(trial=trial,current=cur,original=a,native=b)
        counts['choices']+=1;counts['choosable']+=sum(b[0])+sum(b[1])
        for step in range(12):   # edits of the current record
            rec=old.record(cur);p=C.pointer(roster[cur]);kind=rng.choice(['perk','flaw','skill'])
            slot=rng.choice([-1,0,1,2,3,4,rng.randrange(20)]) if kind=='skill' else rng.choice([-1,0,1,2,3,4])
            value=rng.choice([255,rng.randrange(10)]) if kind!='skill' else rng.choice([255,rng.randrange(40)])
            old.call(FUNCS[kind],[rec,slot,value]);getattr(prog,{'perk':'dr_class_set_perk','flaw':'dr_class_set_flaw','skill':'dr_class_set_replacement'}[kind])(p,slot,value)
            a=[[C.c_int32(old.read(rec+0x10+4*k)).value for k in range(4)],[C.c_int32(old.read(rec+0x20+4*k)).value for k in range(4)],old.vector(rec+0x48)]
            b=[list(roster[cur].perks),list(roster[cur].flaws),list(roster[cur].replacement_skills[:20])]
            if a!=b:fail(trial=trial,step=step,kind=kind,slot=slot,value=value,original=a,native=b)
            counts['sets']+=1
    assert counts['choosable']>0,counts
    print(json.dumps(dict(status='passed',trials=300,**counts,functions=list(FUNCS),native=['recovered_progression','dr_class_choices'],
                          original='Actual functions from their entries',boundaries=['std::vector memory laid out as the original','ClassScreen display calls skipped'])))

if __name__=='__main__':main()
