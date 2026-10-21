#!/usr/bin/env python3
"""Actual Interface::GetSpecialTarget(Token*) 0x20358 vs native dr_special_target (recovered_skills), on the shared
state of verify_skills.py (T040-L1).

A special reward token (Token+0x7c == 1: a mana potion tile, MotionHooks.choose_special) recharges one equipped
skill. The original runs from its entry to its return with R0 = Interface (Interface+0x1030 = Game) and R1 = a
Token object; RandI is original code, std::set<int> is modelled as in verify_menu_level.py and the SjLj stubs are
skipped. Cases vary skill_count 0..4, the skill types (29 often), the cooldowns (full or not) and the token kind.
Compared: the result and the six random streams.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_skills import Original as SkillsOriginal, Native as SkillsNative, SkillState, case as skills_case
from verify_menu_level import SET_OPS, STUBS
from verify_stroke import HERE, I32

ENTRY,END=0x20358,0x204a0
INTERFACE,TOKEN,SET_NODES=0x170b000,0x170d000,0x170e000   # Interface+0x1030 (the Game pointer) is 0x170c030

class Original(SkillsOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text()
        addr=lambda s:int(re.search(r'^'+re.escape(s)+r':\n\s*([0-9a-f]+):',text,re.M)[1],16)
        assert addr('__ZN9Interface16GetSpecialTargetEP5Token')==ENTRY
        self.set_ops={addr(s):n for s,n in SET_OPS.items()};self.sets={}
    def write_set(self,tree):
        values=sorted(self.sets[tree]);header=tree+4;base=SET_NODES+0x400*list(self.sets).index(tree)
        self.write(tree+0x14,len(values));self.write(tree+0xc,base if values else header);self.write(tree+8,base if values else 0)
        for i,v in enumerate(values):node=base+32*i;self.write(node,base+32*(i+1) if i+1<len(values) else header);self.write(node+16,v&0xffffffff)
    def hook(self,u,address,size,context):
        lr=u.reg_read(self.LR)&~1
        if ENTRY<=lr<END:   # calls made by GetSpecialTarget
            r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value;op=self.set_ops.get(address)
            if op:
                if op=='init':self.sets[r[0]]=set();self.write_set(r[0])
                elif op=='insert':self.sets.setdefault(r[1],set()).add(s(self.read(r[2])));self.write_set(r[1])
                elif op=='clear':self.sets[r[0]]=set();self.write_set(r[0])
                else:raise AssertionError(op)
                u.reg_write(self.PC,u.reg_read(self.LR));return
            stub=STUBS.get(address)
            if stub:
                if stub=='increment':u.reg_write(self.regs[0],self.read(r[0]))
                u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def special(self,kind):
        self.sets={};self.write(INTERFACE+0x1030,self.GAME);self.write(TOKEN+0x7c,kind)
        return C.c_int32(self.call(ENTRY,[INTERFACE,TOKEN])).value
    def seeds(self):return list(struct.unpack('<6I',self.u.mem_read(0x1eac20,24)))

class Native(SkillsNative):
    def __init__(self):
        super().__init__();f=self.skills_lib.dr_special_target;f.argtypes=[C.POINTER(SkillState),I32];f.restype=I32
    def special(self,kind):return self.skills_lib.dr_special_target(C.byref(self.state_obj),kind)
    def seeds(self):return list(self.m.random.seeds)

def case(rng):
    c=skills_case(rng);r=c['resources'];k=c['skills']
    r['skill_count']=rng.choice([0,1,2,3,4,4,4])
    k['type']=[29 if rng.random()<.25 else rng.randrange(40) for _ in range(4)]
    r['skill_max']=[rng.randrange(1,9) for _ in range(4)]
    r['skill_current']=[m if rng.random()<.4 else rng.randrange(0,9) for m in r['skill_max']]
    c['token_kind']=1 if rng.random()<.85 else rng.choice([0,2,3])
    return c

def main():
    old,new=Original(),Native();rng=random.Random(0x20358);results={};kinds={}
    for n in range(1500):
        c=case(rng);old.load(c);new.load(c)
        a=[old.special(c['token_kind']),old.seeds()];b=[new.special(c['token_kind']),new.seeds()]
        if a!=b:
            (HERE/'special_target_failure.json').write_text(json.dumps(dict(case=c,original=a,native=b),indent=2))
            raise AssertionError('special_target_failure.json')
        results[a[0]]=results.get(a[0],0)+1;kinds[c['token_kind']]=kinds.get(c['token_kind'],0)+1
    assert {-1,0,1,2,3}<=set(results),results
    report=dict(status='passed',cases=1500,results={str(k):v for k,v in sorted(results.items())},token_kinds={str(k):v for k,v in sorted(kinds.items())},
                function=dict(symbol='__ZN9Interface16GetSpecialTargetEP5Token',address=hex(ENTRY),native='dr_special_target'),
                original='Actual Interface::GetSpecialTarget(Token*) from its entry (RandI original code)',
                boundaries=['std::set<int> modelled; SjLj stubs skipped'])
    print(json.dumps(report))

if __name__=='__main__':main()
