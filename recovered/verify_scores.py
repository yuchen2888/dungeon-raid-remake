#!/usr/bin/env python3
"""Actual ScoreScreen high-score functions vs native recovered_scores (T030-N5d).

The original functions run from their entry to their return on the ScoreScreen object at Game+0xef68 (R0), set up
as its constructor leaves the tables (no scores, no latest score, nothing changed): ScoreScreen::AddScore(name, turn,
a, b, c, score, ScoreType / GameMode / Difficulty), SetSkills, SerialiseState, SerialiseChangedState and
DeserialiseState (ClampI original code; strcpy modelled). Sequences of 40 random operations (scores often equal to
or below the table's, so that full tables and ties occur; skills out of range; names of 0..16 characters; serialised
tables restored, corrupted or with a latest place) run on both sides; after every operation the whole table memory
(ScoreScreen+0x1e0..+0x132e: scores, counts, latest score, serialised bytes, length, serialised type, changed flags) and
the results of GetScoreCount / HaveScoresChanged / SerialiseChangedState are compared.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_skills import Original as SkillsOriginal, case as skills_case
from verify_stroke import HERE

SCREEN=0xef68
TABLES,SIZE=0x1e0,0x1328+6-0x1e0
NAME=0x170e000
NAMES=['__ZN11ScoreScreen8AddScoreEPKciiiii9ScoreType','__ZN11ScoreScreen8AddScoreEPKciiiii8GameMode',
       '__ZN11ScoreScreen8AddScoreEPKciiiii10Difficulty','__ZN11ScoreScreen9SetSkillsEiiii','__ZN11ScoreScreen13GetScoreCountEv',
       '__ZN11ScoreScreen17HaveScoresChangedEv','__ZN11ScoreScreen14SerialiseStateE9ScoreType',
       '__ZN11ScoreScreen21SerialiseChangedStateEv','__ZN11ScoreScreen16DeserialiseStateEi9ScoreType']
STRCPY=0x194fb0

class Original(SkillsOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text()
        addr=lambda s:int(re.search(r'^'+re.escape(s)+r':\n\s*([0-9a-f]+):',text,re.M)[1],16)
        self.fn={n:addr(n) for n in NAMES};self.scoring=False
    def reset(self):   # ScoreScreen's constructor (its tables)
        S=self.GAME+SCREEN;self.u.mem_write(S+TABLES,bytes(SIZE));self.write(S+0xf18,0xffffffff);self.write(S+0xf1c,0xffffffff)
    def hook(self,u,address,size,context):
        if self.scoring and address==STRCPY:
            d,s=u.reg_read(self.regs[0]),u.reg_read(self.regs[1])
            while True:
                b=u.mem_read(s,1);u.mem_write(d,bytes(b));s+=1;d+=1
                if not b[0]:break
            u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def run(self,name,args,stack=()):
        u=self.u;regs=[self.GAME+SCREEN,*args]
        for r,v in zip(self.regs,regs):u.reg_write(r,v&0xffffffff)
        sp=0x140fe00-0x40;u.mem_write(sp,b''.join(struct.pack('<I',v&0xffffffff) for v in stack));u.reg_write(self.SP,sp)
        u.reg_write(self.LR,self.STOP|1);self.scoring=True
        try:u.emu_start(self.fn[name]|1,self.STOP,timeout=0,count=200000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.scoring=False
        return C.c_int32(u.reg_read(self.regs[0])).value
    def memory(self):return bytes(self.u.mem_read(self.GAME+SCREEN+TABLES,SIZE))

class Native:
    def __init__(self):
        self.lib=lib=C.CDLL(str(HERE/'recovered_scores_native.dylib'));self.board=(C.c_uint8*0x1200)()
        for n,a,r in [('dr_scores_init',[C.c_void_p],None),('dr_score_add',[C.c_void_p,C.c_char_p]+[C.c_int32]*6,None),
                      ('dr_score_set_skills',[C.c_void_p]+[C.c_int32]*4,None),('dr_score_count',[C.c_void_p],C.c_int32),
                      ('dr_scores_changed',[C.c_void_p],C.c_bool),('dr_score_serialise',[C.c_void_p,C.c_int32],None),
                      ('dr_score_serialise_changed',[C.c_void_p],C.c_int32),('dr_score_deserialise',[C.c_void_p,C.c_int32],None)]:
            f=getattr(lib,n);f.argtypes=a;f.restype=r
    def reset(self):C.memset(self.board,0,0x1200);self.lib.dr_scores_init(self.board)
    def memory(self):return bytes(self.board[:SIZE])

def main():
    old,new=Original(),Native();rng=random.Random(0x347c0);ops={};full=0
    old.load(skills_case(random.Random(1)))   # the harness's game memory (the tables are reset per sequence)
    for seq in range(300):
        old.reset();new.reset()
        for step in range(40):
            op=rng.choice(['add','add','add','skills','serialise','changed','deserialise','count'])
            n=rng.choice([0,1,5,16]);name=bytes(rng.randrange(32,127) for _ in range(n))
            if op=='add':
                score=rng.choice([0,5,100,1000,rng.randrange(0,5000),-3]);vals=[rng.randrange(-5,2000) for _ in range(4)]
                kind=rng.choice(['type','mode','difficulty']);v=rng.randrange(6) if kind=='type' else rng.randrange(2) if kind=='mode' else rng.randrange(4)
                old.u.mem_write(NAME,name+b'\0')
                fn={'type':NAMES[0],'mode':NAMES[1],'difficulty':NAMES[2]}[kind]
                a=old.run(fn,[NAME,vals[0],vals[1]],[vals[2],vals[3],score,v])
                new.lib.dr_score_add(new.board,name,vals[0],vals[1],vals[2],vals[3],score,v+4 if kind=='mode' else v);b=a
            elif op=='skills':
                if C.c_int32.from_buffer(new.board,0xf18-TABLES).value<0:continue   # SetSkills follows AddScore
                s=[rng.choice([-1,0,5,39,rng.randrange(-3,60)]) for _ in range(4)]
                a=old.run(NAMES[3],s[:3],[s[3]]);new.lib.dr_score_set_skills(new.board,*s);b=a
            elif op=='serialise':t=rng.randrange(6);a=old.run(NAMES[6],[t]);new.lib.dr_score_serialise(new.board,t);b=a
            elif op=='changed':
                flags=old.u.mem_read(old.GAME+SCREEN+0x1328,6);a=next((t for t in range(6) if flags[t]),-1)   # the type it serialises
                old.run(NAMES[7],[]);b=new.lib.dr_score_serialise_changed(new.board)
            elif op=='count':
                a=[old.run(NAMES[4],[]),old.run(NAMES[5],[])&0xff];b=[new.lib.dr_score_count(new.board),int(new.lib.dr_scores_changed(new.board))]
            else:
                t=rng.randrange(6);kind=rng.choice(['as is','corrupt','random'])
                if kind=='random':
                    blob=bytes([rng.randrange(14),rng.choice([0xff,rng.randrange(10)])])
                    for i in range(blob[0]):
                        blob+=b''.join(struct.pack('<i',rng.randrange(-100,10**6)) for _ in range(5))+bytes(rng.choice([255,0,39,rng.randrange(256)]) for _ in range(4))
                        k=rng.randrange(18);blob+=bytes(rng.randrange(32,127) for _ in range(k))+(b'\0' if k<17 else b'')
                    blob=blob[:0x400]
                    old.u.mem_write(old.GAME+SCREEN+0xf20,blob);C.memmove(C.addressof(new.board)+0xf20-TABLES,blob,len(blob))
                elif kind=='corrupt':
                    i=rng.randrange(0x40);v=rng.randrange(256);old.u.mem_write(old.GAME+SCREEN+0xf20+i,bytes([v]));new.board[0xf20-TABLES+i]=v
                a=old.run(NAMES[8],[0,t]);new.lib.dr_score_deserialise(new.board,t);b=a
            if op in ('serialise','deserialise','add','skills'):a=b=None
            x,y=[old.memory(),a],[new.memory(),b]
            if x!=y:
                (HERE/'scores_failure.json').write_text(json.dumps(dict(seq=seq,step=step,op=op,original=[x[0].hex(),a],native=[y[0].hex(),b]),indent=2))
                raise AssertionError('scores_failure.json')
            ops[op]=ops.get(op,0)+1
        full+=sum(C.c_int32.from_buffer(new.board,0xf00-TABLES+4*t).value==10 for t in range(6))
    assert full>0,full
    print(json.dumps(dict(status='passed',sequences=300,operations=ops,full_tables=full,
                          functions=NAMES,native='recovered_scores',original='Actual ScoreScreen functions from their entries',
                          boundaries=['strcpy modelled'])))

if __name__=='__main__':main()
