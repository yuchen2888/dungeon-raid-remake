#!/usr/bin/env python3
"""Actual Game::ProcessPretzels 0xd03c vs native dr_process_pretzels (recovered_schedule), on the shared state
of verify_attack_all.py. ProcessPretzels was a boundary of the stroke update (SelectionEvent::ProcessPretzels).

The original runs from its entry (R0=Game) to its return over the path list Game+0xb3d8; std::set<int>
find/insert are modelled by the path harness (as in verify_path.py); the empty set's erase and the SjLj
calls run or are skipped as there. Paths are random walks over the board (eight directions, no repeats),
many of them weaving so that diagonal steps cross. The preview total (Game+0x165d0) and the level
(Game+0x165d4) are compared.
"""
import ctypes as C
import json
import random
from verify_input_gate import Original as GateOriginal, Native as GateNative
from verify_attack_all import scenario
from verify_stroke import HERE, I32, U8

ENTRY=0xd03c

class Original(GateOriginal):
    def __init__(self):
        super().__init__()
        self.extra={k:v for k,v in self.extra.items() if k!=ENTRY}   # the stroke harness models ProcessPretzels as a boundary; here it runs
    def pretzels(self):
        u=self.u;self.int_sets={};self.path_events=[];self.path_active=True
        u.reg_write(self.regs[0],self.GAME);u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1)
        try:u.emu_start(ENTRY|1,self.STOP,timeout=0,count=500000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.path_active=False
        s=lambda a:C.c_int32(self.read(self.GAME+a)).value
        return dict(total=s(0x165d0),level=s(0x165d4))

class Native(GateNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_schedule_native.dylib'))
        self.pretzel_fn=lib.dr_process_pretzels;self.pretzel_fn.restype=None;self.pretzel_fn.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p]
    def pretzels(self):
        self.pretzel_fn(C.addressof(self.state.selection),C.addressof(self.p),C.c_void_p(self.q))
        from verify_tokens import Counters
        fn=self.tokens_lib.dr_token_queue_counters;fn.restype=C.POINTER(Counters);fn.argtypes=[C.c_void_p]
        return dict(total=self.p.total,level=fn(C.c_void_p(self.q)).contents.bonus_total)

def walk(rng,length):
    start=rng.randrange(36);path=[start]
    while len(path)<length:
        x,y=path[-1]%6,path[-1]//6
        options=[ny*6+nx for nx in range(x-1,x+2) for ny in range(y-1,y+2) if 0<=nx<6 and 0<=ny<6 and ny*6+nx not in path]
        diagonal=[o for o in options if o%6!=x and o//6!=y]
        if not options:break
        path.append(rng.choice(diagonal if diagonal and rng.random()<.8 else options))
    return path

def braid(rng):
    """Three two-column strips, each two crossed zigzags (five crossings a strip, fifteen in all), under a
    random symmetry of the board and cut at a random length so that every level threshold is crossed."""
    cells=[]
    for strip in range(3):
        x=2*strip
        cells+=[(x+y%2,y) for y in range(6)]+[(x+1-y%2,y) for y in range(5,-1,-1)]
    flip,mirror,turn=rng.random()<.5,rng.random()<.5,rng.random()<.5
    def place(x,y):
        if turn:x,y=y,x
        if flip:x=5-x
        if mirror:y=5-y
        return y*6+x
    path=[place(x,y) for x,y in cells]
    if rng.random()<.5:path.reverse()
    return path[:rng.randrange(2,37)]

def main():
    old,new=Original(),Native();rng=random.Random(0xd03c);levels={};compared=0
    for n in range(1500):
        c,_=scenario(rng);c['path']=braid(rng) if n%3==0 else walk(rng,rng.choice([1,2,3,6,10,15,20,28,36]));c['fake']=[]
        c['preview']['total']=rng.choice([0,7,-1]);c['tokens']['bonus_total']=rng.choice([0,2,5])
        c['moving_list']=[];c['gate']=dict(tokens_pending=0,flare_count=0,phase=0,touch_phase=0,input_target=-1,rune=0)
        old.load(c);new.load(c);a,b=old.pretzels(),new.pretzels()
        if a!=b:
            (HERE/'pretzels_failure.json').write_text(json.dumps(dict(path=c['path'],original=a,native=b),indent=2))
            raise AssertionError('pretzels_failure.json')
        compared+=1;levels[a['level']]=levels.get(a['level'],0)+1
    assert set(levels)=={0,1,2,3},levels
    report=dict(status='passed',comparisons=compared,levels=levels,
                function=dict(symbol='__ZN4Game15ProcessPretzelsEv',address=hex(ENTRY),native='dr_process_pretzels'),
                original='Actual ProcessPretzels over the path list; std::set<int> modelled as in verify_path.py')
    (HERE/'pretzels_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
