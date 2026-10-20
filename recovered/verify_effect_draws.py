#!/usr/bin/env python3
"""Random stream 0 drawn by presentation code (T040-J1): actual Game::AddParticles 0xa914, Game::AddSimpleLabel
0xae2c and Game::AddSimpleLabel(Tile*, TileType) 0xb130 vs native dr_add_particles / dr_add_simple_label
(recovered_attack_shield), on the shared state of verify_attack_all.py.

The original functions run from their entry to their return; the particle / label storage (the std::vector
size, constructors, push_back, destructors), SimpleLabel::RegenerateLabel, the tiles' label positions and the
SjLj stubs are skipped, cosf / sinf answer from the host libm; Particles::InitialiseFromTile /
InitialiseAtPosition and SimpleLabel::Initialise run as original code with their Rand calls. Compared: the six
random seeds after each call (only the number of draws on each stream matters to the game: the values place
the particles and labels).
"""
import ctypes as C
import json
import math
import random
import re
import struct
from verify_input_gate import Original as GateOriginal, Native as GateNative
from verify_attack_all import scenario
from verify_stroke import HERE, I32

SEEDS=0x1eac20
PARTICLES='__ZN4Game12AddParticlesEP4Tile12ParticleType'
LABEL='__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif'
TILE_LABEL='__ZN4Game14AddSimpleLabelEP4Tile8TileType'
SKIP=['__ZNKSt6vectorI9ParticlesSaIS0_EE4sizeEv','__ZN9ParticlesC1Ev','__ZNSt6vectorI9ParticlesSaIS0_EE9push_backERKS0_','__ZN9ParticlesD1Ev',
      '__ZNKSt6vectorI11SimpleLabelSaIS0_EE4sizeEv','__ZN11SimpleLabelC1Ev','__ZNSt6vectorI11SimpleLabelSaIS0_EE9push_backERKS0_','__ZN11SimpleLabelD1Ev',
      '__ZN11SimpleLabel15RegenerateLabelEv','__ZN11SimpleLabel9SetColourEi','__ZN4Tile23GetDefenceLabelPositionEv','__ZN4Tile22GetHealthLabelPositionEv',
      '__ZN4Tile22GetAttackLabelPositionEv']
LIBM={0x194e0c:math.cos,0x194f5c:math.sin}

class Original(GateOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text()
        addr=lambda s:int(re.search(r'^'+re.escape(s)+r':\n\s*([0-9a-f]+):',text,re.M)[1],16)
        self.entries={k:addr(s) for k,s in (('particles',PARTICLES),('label',LABEL),('tile_label',TILE_LABEL))}
        self.effect_skip={addr(s):s for s in SKIP};self.effect_skip.update({a:'stub' for a in (0x194cec,0x194cf0,0x194cf4)})
        self.match_calls={k:v for k,v in self.match_calls.items() if k not in self.entries.values()};self.effecting_rng=False
    def hook(self,u,address,size,context):
        if self.effecting_rng:
            if address in LIBM:
                x=struct.unpack('<f',struct.pack('<I',u.reg_read(self.regs[0])))[0]
                u.reg_write(self.regs[0],struct.unpack('<I',struct.pack('<f',LIBM[address](x)))[0]);u.reg_write(self.PC,u.reg_read(self.LR));return
            name=self.effect_skip.get(address)
            if name:
                if 'size' in name:u.reg_write(self.regs[0],0x7fffffff)   # the pool is never full: no new storage
                u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def call(self,key,args):
        u=self.u;G=self.GAME;self.write(G+0xb530,0x1600000);self.write(G+0xb540,0x1680000);self.write(G+0xb53c,0);self.write(G+0xb54c,0)
        for reg,v in zip(self.regs,[G,*args[:3]]):u.reg_write(reg,v&0xffffffff)
        sp=0x140fe00;u.reg_write(self.SP,sp)
        for k,v in enumerate(args[3:]):self.write(sp+4*k,v)
        u.reg_write(self.LR,self.STOP|1);self.effecting_rng=True
        try:u.emu_start(self.entries[key]|1,self.STOP,timeout=0,count=3000000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.effecting_rng=False
        return list(struct.unpack('<6I',u.mem_read(SEEDS,24)))
    def particles(self,tile,type_):return self.call('particles',[self.tile(tile),type_])
    def label(self,type_):
        pos=0x170f000;self.u.mem_write(pos,struct.pack('<ff',.4,.6));return self.call('label',[type_,pos,7,5,0x3f800000])
    def tile_label(self,tile,tile_type):return self.call('tile_label',[self.tile(tile),tile_type])

class Native(GateNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_attack_shield_native.dylib'))
        self.particles_fn=lib.dr_add_particles;self.label_fn=lib.dr_add_simple_label
        for f in (self.particles_fn,self.label_fn):f.argtypes=[C.c_void_p,I32];f.restype=None
    def particles(self,tile,type_):self.particles_fn(C.addressof(self.m.random),type_);return list(self.m.random.seeds)
    def label(self,type_):self.label_fn(C.addressof(self.m.random),type_);return list(self.m.random.seeds)
    def tile_label(self,tile,tile_type):self.label_fn(C.addressof(self.m.random),0);return list(self.m.random.seeds)   # label type 0

def main():
    old,new=Original(),Native();rng=random.Random(0xa914);counts={'particles':0,'label':0,'tile_label':0}
    for n in range(120):
        c,_=scenario(rng);c['moving_list']=[];c['gate']=dict(tokens_pending=0,flare_count=0,phase=0,touch_phase=0,input_target=-1,rune=0)
        old.load(c);new.load(c)
        for k in range(12):
            what=rng.choice(['particles','particles','label','label','tile_label'])
            if what=='particles':args=(rng.randrange(36),rng.choice([0,1,2,3,4,rng.randrange(6)]))
            elif what=='label':args=(rng.choice([0,1,2,3,4,5,8,9,10,11,19,27,35,rng.randrange(60)]),)
            else:args=(rng.randrange(36),rng.randrange(7))
            a,b=getattr(old,what)(*args),getattr(new,what)(*args)
            if a!=b:
                (HERE/'effect_draws_failure.json').write_text(json.dumps(dict(case=n,call=what,args=args,original=a,native=b),indent=2))
                raise AssertionError('effect_draws_failure.json')
            counts[what]+=1
    report=dict(status='passed',comparisons=counts,
                functions=[dict(symbol=PARTICLES,address='0xa914',native='dr_add_particles'),dict(symbol=LABEL,address='0xae2c',native='dr_add_simple_label'),
                           dict(symbol=TILE_LABEL,address='0xb130',native='dr_add_simple_label (type 0)')],
                original='Actual functions with Particles::Initialise* and SimpleLabel::Initialise as original code',
                boundaries=['particle / label storage, RegenerateLabel, SetColour, tile label positions, SjLj stubs skipped; cosf / sinf from the host libm'])
    (HERE/'effect_draws_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
