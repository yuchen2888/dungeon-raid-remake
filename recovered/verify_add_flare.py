#!/usr/bin/env python3
"""Actual Game::AddFlare 0x9f94 vs native dr_add_flare (recovered_attack_shield), on the shared state of
verify_attack_all.py (T040-I).

The original runs from its entry (R0=Game, R1=flare type, R2/R3=position, [sp]=colour) to its return with
the flare list (std::vector<Quad> at Game+0xbd80) placed by the harness at a fixed address. Its
presentation calls are skipped: the vector's size (answered "not full", so no Quad is constructed),
Quad::Quad / push_back / ~Quad, Quad::SetUV, Quad::SetColour and the SjLj stubs. Rand(0, 360, stream 0)
runs as original code. Compared: the six random seeds, the flare count (Game+0xbd8c) and the rotation
(quad+0x6c) against dr_add_flare's result; the quad's position (+0x54/+0x58) and size (+0x64/+0x68, 0.08)
are checked on the original side.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_input_gate import Original as GateOriginal, Native as GateNative
from verify_attack_all import scenario
from verify_stroke import HERE, I32

ENTRY,END=0x9f94,0xa118
COUNT,LIST=0xbd8c,0xbd80
QUADS,COLOUR=0x1708000,0x170f800
SEEDS=0x1eac20
STUBS=(0x194cec,0x194cf0,0x194cf4)
SKIP=('__ZNKSt6vectorI4QuadSaIS0_EE4sizeEv','__ZN4QuadC1Ev','__ZNSt6vectorI4QuadSaIS0_EE9push_backERKS0_','__ZN4QuadD1Ev',
      '__ZN4Quad5SetUVERK8GLfloat2S2_','__ZN4Quad9SetColourERK9GLcolour4')
fbits=lambda f:struct.unpack('<I',struct.pack('<f',f))[0]

class Original(GateOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.flare_skip={}
        for symbol in SKIP:
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol;self.flare_skip[int(m[1],16)]=symbol
        for a in STUBS:self.flare_skip[a]='stub'
        self.flaring=False
        self.match_calls={k:v for k,v in self.match_calls.items() if k!=ENTRY}   # the match harness adapts AddFlare; here it runs
    def hook(self,u,address,size,context):
        if self.flaring:
            lr=u.reg_read(self.LR)&~1;name=self.flare_skip.get(address)
            if name and ENTRY<lr<END:
                if 'size' in name:u.reg_write(self.regs[0],self.read(self.GAME+COUNT)+1)   # the list is not full
                u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def add_flare(self,type_,x,y,colour):
        u=self.u;G=self.GAME;self.write(G+LIST,QUADS);u.mem_write(COLOUR,bytes(colour))
        u.reg_write(self.regs[0],G);u.reg_write(self.regs[1],type_);u.reg_write(self.regs[2],fbits(x));u.reg_write(self.regs[3],fbits(y))
        sp=0x140fe00;u.reg_write(self.SP,sp);self.write(sp,COLOUR);u.reg_write(self.LR,self.STOP|1);self.flaring=True
        index=C.c_int32(self.read(G+COUNT)).value;quad=QUADS+0x70*index
        try:u.emu_start(ENTRY|1,self.STOP,timeout=0,count=200000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.flaring=False
        assert struct.unpack('<II',u.mem_read(quad+0x54,8))==(fbits(x),fbits(y))
        assert struct.unpack('<II',u.mem_read(quad+0x64,8))==(fbits(0.08),fbits(0.08))
        return dict(count=C.c_int32(self.read(G+COUNT)).value,rotation=self.read(quad+0x6c),seeds=list(struct.unpack('<6I',u.mem_read(SEEDS,24))))
    def set_count(self,n):self.write(self.GAME+COUNT,n)

class Native(GateNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_attack_shield_native.dylib'))
        self.flare_fn=lib.dr_add_flare;self.flare_fn.argtypes=[C.POINTER(I32),C.c_void_p];self.flare_fn.restype=C.c_float
    def add_flare(self,type_,x,y,colour):
        n=I32(self.count);r=self.flare_fn(C.byref(n),C.addressof(self.m.random));self.count=n.value
        return dict(count=self.count,rotation=fbits(r),seeds=list(self.m.random.seeds))
    def set_count(self,n):self.count=n

def main():
    old,new=Original(),Native();rng=random.Random(0x9f94);compared=0
    for n in range(150):
        c,_=scenario(rng);c['moving_list']=[];c['gate']=dict(tokens_pending=0,flare_count=0,phase=0,touch_phase=0,input_target=-1,rune=0)
        old.load(c);new.load(c);start=rng.choice([0,0,1,5,rng.randrange(0,15)]);old.set_count(start);new.set_count(start)
        for k in range(rng.randrange(1,8)):   # several flares in a row, as the skills and abilities add them
            type_=rng.choice([0,1,2,rng.randrange(0,4)]);x,y=rng.uniform(0,1),rng.uniform(0,1.5);colour=[rng.randrange(256) for _ in range(4)]
            a,b=old.add_flare(type_,x,y,colour),new.add_flare(type_,x,y,colour)
            if a!=b:
                (HERE/'add_flare_failure.json').write_text(json.dumps(dict(case=n,flare=k,original=a,native=b),indent=2))
                raise AssertionError('add_flare_failure.json')
            compared+=1
    report=dict(status='passed',comparisons=compared,function=dict(symbol='__ZN4Game8AddFlareE9FlareType8GLfloat2RK9GLcolour4',address=hex(ENTRY),native='dr_add_flare'),
                original='Actual AddFlare; Rand(0, 360, stream 0) as original code',
                boundaries=['flare list storage, Quad::SetUV / SetColour and the SjLj stubs skipped (presentation)'])
    (HERE/'add_flare_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
