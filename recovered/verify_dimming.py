#!/usr/bin/env python3
"""Actual Game::UpdateDimming 0x9c78 vs native dr_update_dimming (recovered_selection), on the shared state of
verify_cross.py (T040-C3).

The original runs from its entry (R0 = Game) with Tile::CanMatchType as original code over the path list
Game+0xb3d8; Tile::Dim / Tile::Undim (quad and label alphas) are recorded per tile and skipped. Compared: the
dimmed flag of each of the 36 tiles. Boards vary tile types, special types (0 / 1 / others), flags 231 / 255.
"""
import ctypes as C
import json
import random
import re
from verify_cross import Original as CrossOriginal, Native as CrossNative, case as cross_case
from verify_stroke import HERE, U8

ENTRY=0x9c78

class Original(CrossOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text()
        addr=lambda s:int(re.search(r'^'+re.escape(s)+r':\n\s*([0-9a-f]+):',text,re.M)[1],16)
        self.dim,self.undim=addr('__ZN4Tile3DimEv'),addr('__ZN4Tile5UndimEv');self.dimming=False
        self.extra={k:v for k,v in self.extra.items() if k!=ENTRY}   # verify_stroke's UpdateDimming boundary
        assert addr('__ZN4Game13UpdateDimmingEv')==ENTRY
    def hook(self,u,address,size,context):
        if self.dimming and address in (self.dim,self.undim):
            self.dimmed[self.index(u.reg_read(self.regs[0]))]=int(address==self.dim);u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def update(self):
        u=self.u;self.dimmed=[-1]*36
        u.reg_write(self.regs[0],self.GAME);u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1);self.dimming=True
        try:u.emu_start(ENTRY|1,self.STOP,timeout=0,count=500000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.dimming=False
        return self.dimmed

class Native(CrossNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_selection_native.dylib'))
        self.dim_fn=lib.dr_update_dimming;self.dim_fn.argtypes=[C.c_void_p,C.POINTER(U8*36)];self.dim_fn.restype=None
    def update(self):
        out=(U8*36)();self.dim_fn(C.addressof(self.state.selection),C.byref(out));return list(out)

def case(rng):
    c=cross_case(rng)
    for t in c['board']:
        t['special']=rng.choice([0,1,3,3,3,rng.randrange(5)]);t['flag231']=int(rng.random()<.2);t['flag255']=int(rng.random()<.15)
        t['type']=rng.choice([t['type'],t['type'],0,1,2,3,4,rng.randrange(7)])
    return c

def main():
    old,new=Original(),Native();rng=random.Random(0x9c78);n=1500;dimmed=0;kinds=set()
    for i in range(n):
        c=case(rng);old.load(c);new.load(c)
        a,b=old.update(),new.update()
        if a!=b:
            (HERE/'dimming_failure.json').write_text(json.dumps(dict(case=i,path=c['path'],board=c['board'],original=a,native=b),indent=2))
            raise AssertionError('dimming_failure.json')
        dimmed+=sum(a);kinds.add(len(c['path'])>0)
    assert kinds=={False,True} and 0<dimmed<36*n,(kinds,dimmed)
    report=dict(status='passed',comparisons=n,dimmed_tiles=dimmed,function=dict(symbol='__ZN4Game13UpdateDimmingEv',address=hex(ENTRY),native='dr_update_dimming'),
                original='Actual UpdateDimming with Tile::CanMatchType as original code',boundaries=['Tile::Dim / Undim recorded per tile'])
    (HERE/'dimming_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
