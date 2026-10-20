#!/usr/bin/env python3
"""Actual Game::UpdateCrossVisibility 0xaa24 vs native dr_update_cross_visibility (recovered_schedule), on the shared
state of verify_attack_all.py (T040-J2).

The original runs from its entry (R0=Game) to its return over the path list Game+0xb3d8, with Tile::GetDamageType
(and CharacterClass::HaveFlaw / GetMortalEnemyType, Game::GetEnemyCount) and SimpleLabel::Initialise as original
code; the cross-label storage (the std::vector size, constructor, push_back, destructor), SimpleLabel::SetColour
(recorded: the label colour), SimpleLabel::RegenerateLabel and the SjLj stubs are skipped. Compared: every tile's
cross visibility (Tile+0x13c), the random seeds and the cross labels (type, tile, colour).
"""
import ctypes as C
import json
import random
import re
import struct
from verify_input_gate import Original as GateOriginal, Native as GateNative
from verify_attack_all import scenario
from verify_stroke import HERE, I32
from verify_pretzels import walk

ENTRY,SEEDS=0xaa24,0x1eac20
SKIP=['__ZNKSt6vectorI11SimpleLabelSaIS0_EE4sizeEv','__ZN11SimpleLabelC1Ev','__ZNSt6vectorI11SimpleLabelSaIS0_EE9push_backERKS0_',
      '__ZN11SimpleLabelD1Ev','__ZN11SimpleLabel15RegenerateLabelEv']
EVENT=C.CFUNCTYPE(None,C.c_void_p,C.c_void_p)
class CrossHooks(C.Structure):_fields_=[('context',C.c_void_p),('event',EVENT)]

class Original(GateOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text()
        addr=lambda s:int(re.search(r'^'+re.escape(s)+r':\n\s*([0-9a-f]+):',text,re.M)[1],16)
        self.cross_skip={addr(s):s for s in SKIP};self.cross_skip.update({a:'stub' for a in (0x194cec,0x194cf0,0x194cf4)})
        self.set_colour=addr('__ZN11SimpleLabel9SetColourEi');self.initialise=addr('__ZN11SimpleLabel10InitialiseE15SimpleLabelTypeRK8GLfloat2if')
        self.boundaries={k:v for k,v in self.boundaries.items() if v!='cross'};self.crossing=False
    def hook(self,u,address,size,context):
        if self.crossing:
            lr=u.reg_read(self.LR)&~1
            if ENTRY<lr<0xae2c:
                if address==self.set_colour:self.colour=C.c_int32(u.reg_read(self.regs[1])).value;u.reg_write(self.PC,u.reg_read(self.LR));return
                if address==self.initialise:
                    x,y=struct.unpack('<ff',u.mem_read(u.reg_read(self.regs[2]),8))
                    self.cross_events.append([C.c_int32(u.reg_read(self.regs[1])).value,self.colour])   # runs: its Rand draw
                name=self.cross_skip.get(address)
                if name:
                    if 'size' in name:u.reg_write(self.regs[0],0x7fffffff)   # the pool is never full
                    u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def cross(self):
        u=self.u;G=self.GAME;self.cross_events=[];self.colour=None
        self.write(G+0x164c8,0x1600000);u.reg_write(self.regs[0],G);u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1);self.crossing=True
        try:u.emu_start(ENTRY|1,self.STOP,timeout=0,count=3000000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.crossing=False
        return dict(visibility=[u.mem_read(self.tile(i)+0x13c,1)[0] for i in range(36)],seeds=list(struct.unpack('<6I',u.mem_read(SEEDS,24))),
                    labels=[e for e in self.cross_events])

class Native(GateNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_schedule_native.dylib'))
        self.cross_fn=lib.dr_update_cross_visibility;self.cross_fn.argtypes=[C.c_void_p,C.POINTER(CrossHooks)];self.cross_fn.restype=None
        def event(_,p):e=C.cast(p,C.POINTER(I32*4)).contents;self.cross_events.append([e[1],e[3]])
        self.cross_cb=EVENT(event);self.cross_hooks=CrossHooks(None,self.cross_cb)
    def cross(self):
        self.cross_events=[];self.cross_fn(C.addressof(self.path_state),C.byref(self.cross_hooks))
        return dict(visibility=[t.cross_visibility for t in self.state.selection.tiles],seeds=list(self.m.random.seeds),labels=self.cross_events)

def case(rng):
    c,_=scenario(rng)
    for i,t in enumerate(c['board']):
        if t['type']==1:
            t['enemy']=rng.choice([0,0,9,14,20,27,30,32,rng.randrange(33)]);t['enemy_state']=rng.choice([0,0,1])
        t['cross_visibility']=rng.randrange(2);t['selected']=0
        c['combat'][i].update(health=rng.choice([1,2,5,rng.randrange(-2,25)]),defence=rng.choice([0,0,2,rng.randrange(0,10)]))
    c['path']=walk(rng,rng.choice([0,0,1,2,3,4,6,9,14]));c['fake']=[]
    if rng.random()<.3:   # straight up a column (race 2: damage type 3 in the middle of it)
        x,top=rng.randrange(6),rng.randrange(0,3);c['path']=[y*6+x for y in range(5,top-1,-1)]
        for i in c['path']:
            if rng.random()<.7:c['board'][i].update(type=1,enemy=0)
    if rng.random()<.1:c['path']=[]   # no path: every tile's cross visibility cleared
    for i in c['path']:c['board'][i]['selected']=1
    g=c['game'];g.update(race=rng.choice([2,2,0,4,5,7,rng.randrange(10)]),current_damage=rng.choice([0,3,8,rng.randrange(-3,30)]),
                         weapon_damage=rng.choice([0,2,rng.randrange(0,15)]),flaws=[rng.choice([0,0,255,3]),255,255,255])
    c['path_state'].update(turn=rng.choice([1,3,4,5,rng.randrange(0,60)]),base_attack=g['current_damage'],direction_bonus=g['weapon_damage'])
    c['moving_list']=[];c['gate']=dict(tokens_pending=0,flare_count=0,phase=0,touch_phase=0,input_target=-1,rune=0)
    return c

def main():
    old,new=Original(),Native();rng=random.Random(0xaa24);labels=empty=cleared=0;kinds=set()
    for n in range(1500):
        c=case(rng);old.load(c);new.load(c)
        a,b=old.cross(),new.cross()
        if a!=b:
            (HERE/'cross_failure.json').write_text(json.dumps(dict(case=n,path=c['path'],original=a,native=b),indent=2))
            raise AssertionError('cross_failure.json')
        labels+=len(a['labels']);kinds|={e[0] for e in a['labels']}
        if not c['path']:empty+=1;cleared+=any(t['cross_visibility'] for t in c['board'])
    assert kinds=={30,35},kinds
    assert empty>50 and cleared>50,(empty,cleared)
    report=dict(status='passed',comparisons=1500,cross_labels=labels,empty_paths=empty,function=dict(symbol='__ZN4Game21UpdateCrossVisibilityEv',address=hex(ENTRY),native='dr_update_cross_visibility'),
                original='Actual function with Tile::GetDamageType and SimpleLabel::Initialise as original code',
                boundaries=['cross-label storage, SetColour (recorded), RegenerateLabel and SjLj stubs skipped'])
    (HERE/'cross_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
