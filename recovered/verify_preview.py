#!/usr/bin/env python3
"""Original resource preview instructions, isolated and in continuous gestures."""
import ctypes as C
import hashlib
import json
import math
import random
import struct
from verify_stroke import Native as StrokeNative, Original as StrokeOriginal, State, Hooks, I32, U8, HERE, initial, scenarios

INT_OFFSETS=dict(armour_current=0xbda4,armour_max=0xbda8,shield_value=0xbe10,
    shield_bonus=0xbe14,healing_value=0xbe08,healing_bonus=0xbe0c)
FLOAT_OFFSETS=dict(xp_bonus=0xbdd4,upgrade_bonus=0xbde4,gold_bonus=0xbddc)
BYTE_OFFSETS=dict(double_upgrade=0xbe75,double_healing=0xbe76,double_gold=0xbe77)
class Potion(C.Structure):
    _fields_=[('a',U8),('b',U8),('c',U8)]
class Preview(C.Structure):
    _fields_=[(k,I32) for k in INT_OFFSETS]+[(k,C.c_float) for k in FLOAT_OFFSETS]+[(k,U8) for k in BYTE_OFFSETS]+[('total',I32),('potions',Potion*36)]

def configure(case):
    case['real_shadows']=True
    case['preview']=dict(armour_current=5,armour_max=12,shield_value=3,shield_bonus=0,
        healing_value=2,healing_bonus=1,xp_bonus=.25,upgrade_bonus=.5,gold_bonus=.75,
        double_upgrade=0,double_healing=0,double_gold=0,total=123,potions=[[0,0,0] for _ in range(36)])
    return case

class Native(StrokeNative):
    def __init__(self):
        super().__init__();self.preview_lib=C.CDLL(str(HERE/'recovered_preview_native.dylib'))
        self.fn=self.preview_lib.dr_preview_resources
        self.fn.argtypes=[C.POINTER(State),C.POINTER(Preview),C.POINTER(Hooks)];self.fn.restype=None
    def load(self,case):
        super().load(case);self.p=Preview();p=case['preview']
        for k in (*INT_OFFSETS,*FLOAT_OFFSETS,*BYTE_OFFSETS,'total'):setattr(self.p,k,p[k])
        for i,flags in enumerate(p['potions']):self.p.potions[i]=Potion(*flags)
        self.resource_callback=lambda:self.fn(C.byref(self.state),C.byref(self.p),C.byref(self.hooks))
    def run(self):
        self.events=[];self.resource_callback()
        return dict(counts=list(self.state.counts),total=self.p.total,events=self.events)
    def step(self,phase,touch):
        result=super().step(phase,touch);result['preview_total']=self.p.total;return result

class Original(StrokeOriginal):
    def hook(self,u,address,size,context):
        if address==0x194dec:
            value=struct.unpack('<f',struct.pack('<I',u.reg_read(self.regs[0])))[0]
            result=float(math.ceil(value)) if math.isfinite(value) else value
            u.reg_write(self.regs[0],struct.unpack('<I',struct.pack('<f',result))[0])
            u.reg_write(self.PC,u.reg_read(self.LR));return
        # Direct entry omits the orchestration callback marker on both sides.
        if address==0xefe0 and getattr(self,'direct',False):return
        return super().hook(u,address,size,context)
    def load(self,case):
        super().load(case);p=case['preview'];self.direct=False
        for k,a in INT_OFFSETS.items():self.write(self.GAME+a,p[k])
        for k,a in FLOAT_OFFSETS.items():self.u.mem_write(self.GAME+a,struct.pack('<f',p[k]))
        for k,a in BYTE_OFFSETS.items():self.u.mem_write(self.GAME+a,bytes([p[k]]))
        self.write(self.GAME+0x165d0,p['total'])
        for i,flags in enumerate(p['potions']):self.u.mem_write(self.tile(i)+0x232,bytes(flags))
    def total(self):return C.c_int32(self.read(self.GAME+0x165d0)).value
    def run(self):
        self.direct=True;self.events=[];u=self.u
        u.reg_write(self.regs[0],self.GAME);u.reg_write(self.SP,0x140fff0);u.reg_write(self.LR,self.STOP|1)
        u.emu_start(0xefe1,self.STOP,timeout=0,count=500000)
        assert u.reg_read(self.PC)==self.STOP
        return dict(counts=[C.c_int32(self.read(self.GAME+0x164b0+4*i)).value for i in range(6)],total=self.total(),events=self.events)
    def step(self,phase,touch):
        result=super().step(phase,touch);result['preview_total']=self.total();return result

def cases():
    for kind in range(7):
        for length in [0,1,3,4,6,36]:
            for flaw in [False,True]:
                for flags in range(8):
                    case=configure(initial());case['path']=list(range(length));case['counts']=[0]*6
                    if flaw:case['game']['flaws'][0]=2
                    for t in case['board']:t.update(type=kind,cross_visibility=1)
                    case['preview']['potions']=[[flags&1,(flags>>1)&1,(flags>>2)&1] for _ in range(36)]
                    yield case
    rng=random.Random(0xEFe0)
    for _ in range(500):
        case=configure(initial());p=case['preview'];length=rng.randrange(37)
        case['path']=rng.sample(range(36),length);case['fake']=rng.sample(case['path'],rng.randrange(length+1))
        case['record']=rng.randrange(2);case['mode']=rng.randrange(3)
        case['counts']=[rng.randrange(8) for _ in range(6)]
        case['game']['flaws'][0]=rng.choice([2,255])
        for t in case['board']:t.update(type=rng.randrange(7),broken=rng.randrange(2),cross_visibility=rng.randrange(2))
        for k in INT_OFFSETS:p[k]=rng.randrange(-5,30)
        for k in FLOAT_OFFSETS:p[k]=rng.choice([-.9,0,.1,.5,1.25,3,100])
        for k in BYTE_OFFSETS:p[k]=rng.randrange(2)
        p['potions']=[[rng.randrange(2) for _ in range(3)] for _ in range(36)]
        yield case
    # Division by zero, conversion saturation and wrapped integer arithmetic.
    for current,maximum,shield in [(0,0,0),(0,1,0),(1,0,0),(0,2147483647,1),(-2147483648,2147483647,1)]:
        for count in [0,1,2147483647,-2147483648]:
            case=configure(initial());case['path']=[];case['counts']=[count]*6
            case['record']=1;case['mode']=0
            case['preview'].update(armour_current=current,armour_max=maximum,shield_value=shield,healing_value=2147483647)
            yield case

def main():
    old=Original();new=Native();direct=0;steps=0;gestures=0;samples=[]
    def compare(case,a,b):
        if a!=b:
            (HERE/'preview_failure.json').write_text(json.dumps(dict(case=case,original=a,native=b),indent=2))
            raise AssertionError('See preview_failure.json')
    for case in cases():
        old.load(case);new.load(case);a=old.run();b=new.run();compare(case,a,b);direct+=1
    for case in scenarios():
        if case.get('mutating_shadows'):continue
        configure(case);old.load(case);new.load(case)
        for phase,touch in case['steps']:
            a=old.step(phase,touch);b=new.step(phase,touch);compare(case,a,b);steps+=1
            if len(samples)<6 and any(e[0]==13 for e in a['events']):samples.append(dict(path=a['path'],counts=a['counts'],events=a['events']))
        gestures+=1
    report=dict(status='passed',direct_preview_cases=direct,integrated_gestures=gestures,integrated_steps=steps,
        original='Actual ARMv7 ProcessResourceShadows and original input/selection instructions',
        native='ARM64 C++ stroke + resource preview via callback',
        adapters=['ceilf platform function','old collections','UI/audio/rendering'],
        unresolved_gameplay_callbacks=['ProcessRune','ProcessPretzels'],
        limits='Resource previews only; no reward application, release effects or complete game turn. UI callbacks observed without game-state mutation.',samples=samples)
    (HERE/'preview_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    provenance=dict(original_symbol='Game::ProcessResourceShadows',address='0xefe0',size=0x320,
        sha256=hashlib.sha256(old.old.bytes_at(0xefe0,0x320)).hexdigest(),native_source='recovered_preview.cpp',
        status='function reconstructed; referenced normal-potion predicate inlined; boolean flags required')
    (HERE/'preview_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='samples'}))

if __name__=='__main__':main()
