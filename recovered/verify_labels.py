#!/usr/bin/env python3
"""Actual SimpleLabel functions vs native recovered_labels (T040-K6).

The original functions run from their entry to their return on a SimpleLabel object (R0) in the harness's memory:
the constructor, SetColour, Initialise (RegenerateLabel, CreateNumberDefinition, CreateTypeDefinition,
CreateTypeDefinitionLast, SetDefinition, SetVertex and Rand as original code; the digit tables filled by their static
initialiser first; the runtime's __divsi3 / __modsi3 modelled), SetNumber, SetPosition, SetAlpha and Process (Sqr original code). Sequences of 30 random
operations per label run on both sides: every type 0..43, numbers negative, zero and up to 99999, digit sizes, scales,
positions, durations written as Game::Start does (SimpleLabel+0x34c), alpha bases, dt up to past the duration.
Compared after every operation: the whole object (0x358 bytes) and the six random streams.
"""
import ctypes as C
import json
import random
import struct
from verify_skills import Original as SkillsOriginal, case as skills_case
from verify_stroke import HERE

LABEL,POINT,SEEDS=0x170f000,0x170f400,0x1eac20
ENTRIES=dict(construct=0x22194,colour=0x221c4,initialise=0x23078,number=0x2311c,position=0x22d6c,alpha=0x22f64,process=0x22f80)
STATIC_INIT=0x313c   # the digit glyph tables (0x1eac64 / 0x1eacb4)
class Point(C.Structure):_fields_=[('x',C.c_float),('y',C.c_float)]

DIVSI3,MODSI3=0x194d78,0x194d8c   # the runtime's signed division / remainder (symbol stubs): modelled
class Original(SkillsOriginal):
    def hook(self,u,address,size,context):
        if address in (DIVSI3,MODSI3):
            a,b=(C.c_int32(u.reg_read(r)).value for r in self.regs[:2]);q=int(a/b)
            u.reg_write(self.regs[0],(q if address==DIVSI3 else a-q*b)&0xffffffff);u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def run(self,name,args,stack=()):
        u=self.u
        for r,v in zip(self.regs,[LABEL,*args]):u.reg_write(r,v&0xffffffff)
        sp=0x140fe00-0x40;u.mem_write(sp,b''.join(struct.pack('<I',v&0xffffffff) for v in stack));u.reg_write(self.SP,sp)
        u.reg_write(self.LR,self.STOP|1);u.emu_start(ENTRIES[name]|1,self.STOP,timeout=0,count=200000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
    def memory(self):return bytes(self.u.mem_read(LABEL,0x358))
    def seeds(self):return list(struct.unpack('<6I',self.u.mem_read(SEEDS,24)))

def bits(f):return struct.unpack('<I',struct.pack('<f',f))[0]

def main():
    old=Original();old.load(skills_case(random.Random(1)))
    u=old.u;u.reg_write(old.regs[0],1);u.reg_write(old.regs[1],0xffff);u.reg_write(old.SP,0x140fe00);u.reg_write(old.LR,old.STOP|1)
    u.emu_start(STATIC_INIT|1,old.STOP,timeout=0,count=200000)
    lib=C.CDLL(str(HERE/'recovered_labels_native.dylib'));label=(C.c_uint8*0x358)();seeds=(C.c_uint32*6)()
    for n,a in dict(dr_label_construct=[C.c_void_p],dr_label_set_colour=[C.c_void_p,C.c_int32],
                    dr_label_initialise=[C.c_void_p,C.c_int32,Point,C.c_int32,C.c_float,C.c_void_p],dr_label_set_number=[C.c_void_p,C.c_int32],
                    dr_label_set_position=[C.c_void_p,Point],dr_label_set_alpha=[C.c_void_p,C.c_uint8],dr_label_process=[C.c_void_p,C.c_float]).items():
        getattr(lib,n).argtypes=a;getattr(lib,n).restype=None
    rng=random.Random(0x22d7c);ops={};types=set();negative=0;faded=0
    for seq in range(400):
        u.mem_write(LABEL,bytes(0x358));C.memset(label,0,0x358);old.run('construct',[]);lib.dr_label_construct(label)
        for step in range(30):
            op=rng.choice(['initialise','initialise','number','position','alpha','process','process','process','colour','duration'])
            if op=='initialise':
                t=rng.choice([1,3,8,9,10,rng.randrange(44)]);n=rng.choice([0,1,7,10,99,100,1234,99999,-1,-45,-9999,rng.randrange(-99999,100000)])
                x,y=rng.uniform(-1,2),rng.uniform(-1,2);s=rng.choice([0.5,1.0,rng.uniform(0.1,2)])
                u.mem_write(POINT,struct.pack('<ff',x,y))
                for i,v in enumerate(old.seeds()):seeds[i]=v
                old.run('initialise',[t,POINT,n],[bits(s)]);lib.dr_label_initialise(label,t,Point(x,y),n,s,seeds)
                types.add(t);negative+=n<0
            elif op=='number':n=rng.choice([0,5,12,-3,rng.randrange(-99999,100000)]);old.run('number',[n]);lib.dr_label_set_number(label,n)
            elif op=='position':
                x,y=rng.uniform(-1,2),rng.uniform(-1,2);u.mem_write(POINT,struct.pack('<ff',x,y));old.run('position',[POINT]);lib.dr_label_set_position(label,Point(x,y))
            elif op=='alpha':a=rng.choice([0,128,255,rng.randrange(256)]);old.run('alpha',[a]);lib.dr_label_set_alpha(label,a)
            elif op=='colour':c=rng.randrange(56);old.run('colour',[c]);lib.dr_label_set_colour(label,c)
            elif op=='duration':   # Game::Start's 0.2, or the constructor's 1, and the alpha base
                d=rng.choice([0.2,1.0,rng.uniform(0.05,2)]);ab=rng.choice([255,128,rng.randrange(256)])
                u.mem_write(LABEL+0x34c,struct.pack('<f',d));u.mem_write(LABEL+0x354,bytes([ab]))
                C.memmove(C.addressof(label)+0x34c,struct.pack('<f',d),4);label[0x354]=ab
            else:
                dt=rng.choice([1/60,1/30,0.05,rng.uniform(0,0.3)]);old.run('process',[bits(dt)]);lib.dr_label_process(label,dt)
                faded+=label[0]==0 and old.memory()[0]==0
            x,y=[old.memory(),old.seeds()],[bytes(label),old.seeds() if op!='initialise' else list(seeds)]
            if x!=y:
                (HERE/'labels_failure.json').write_text(json.dumps(dict(seq=seq,step=step,op=op,original=[x[0].hex(),x[1]],native=[y[0].hex(),y[1]]),indent=2))
                raise AssertionError('labels_failure.json')
            ops[op]=ops.get(op,0)+1
    assert types>=set(range(44)) and negative>0 and faded>0,(sorted(set(range(44))-types),negative,faded)
    print(json.dumps(dict(status='passed',sequences=400,operations=ops,types=len(types),negative_numbers=negative,
                          functions=list(ENTRIES),native='recovered_labels',original='Actual SimpleLabel functions from their entries',
                          boundaries=['numbers from 100000 not drawn (the original reads past its digit tables)'])))

if __name__=='__main__':main()
