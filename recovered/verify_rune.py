#!/usr/bin/env python3
"""Execute original rune scan; compare native C++ and integrated gestures.

Actual MatchTile remains a recorded boundary. Tests may mark its requested tile
as matched on BOTH sides, explicitly testing callback/state wiring, not rewards.
"""
import ctypes as C
import hashlib
import json
import random
import re
import struct
from verify_preview import Native as PreviewNative, Original as PreviewOriginal, configure as preview_configure
from verify_stroke import State, Hooks, I32, U8, HERE, initial, Original as StrokeOriginal

class Rune(C.Structure):
    _fields_=[('enabled',U8),('highlights',C.c_uint32),('allocated',C.c_uint32)]

def configure(case):
    preview_configure(case);case['real_rune']=True
    case['rune']=dict(enabled=1,highlights=0,allocated=0)
    return case

class Native(PreviewNative):
    def __init__(self):
        super().__init__();self.rune_lib=C.CDLL(str(HERE/'recovered_rune_native.dylib'))
        self.rune_fn=self.rune_lib.dr_process_rune
        self.rune_fn.argtypes=[C.POINTER(State),C.POINTER(Rune),C.c_bool,C.POINTER(Hooks)]
        self.rune_fn.restype=None
        self.reset_fn=self.rune_lib.dr_reset_rune_preview
        self.reset_fn.argtypes=[C.POINTER(Rune)];self.reset_fn.restype=None
        self.release_fn=self.lib.dr_prepare_release
        self.release_fn.argtypes=[C.POINTER(State),C.POINTER(Hooks)];self.release_fn.restype=I32
    def load(self,case):
        super().load(case);self.rune=Rune(**case['rune'])
        original_callback=self.callback
        from verify_stroke import EVENT
        def callback(context,kind,index,a,b):
            if kind==18 and case.get('mark_matches'):self.state.selection.tiles[index].rule.matched=1
            original_callback(context,kind,index,a,b)
        self.callback=EVENT(callback);self.hooks=Hooks(None,self.callback)
        self.rune_callback=lambda commit:self.rune_fn(C.byref(self.state),C.byref(self.rune),commit,C.byref(self.hooks))
    def status(self):
        return dict(highlights=self.rune.highlights,allocated=self.rune.allocated,
            counts=list(self.state.counts),matched=[t.rule.matched for t in self.state.selection.tiles])
    def run(self,commit):
        self.events=[];self.rune_callback(commit);return dict(self.status(),events=self.events)
    def step(self,phase,touch):
        self.reset_fn(C.byref(self.rune))
        if phase==2:
            self.events=[];route=self.release_fn(C.byref(self.state),C.byref(self.hooks))
            return dict(route=route,rune=self.status(),selected=[t.selected for t in self.state.selection.tiles],events=self.events)
        result=super().step(phase,touch);result['rune']=self.status();return result

class Original(PreviewOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.rune_calls={}
        symbols={
            '__ZNKSt6vectorI9QuadStripSaIS0_EE4sizeEv':'vector_size',
            '__ZNSt6vectorI9QuadStripSaIS0_EE4backEv':'vector_back',
            '__ZNSt6vectorI9QuadStripSaIS0_EE9push_backERKS0_':'vector_push',
            '__ZN9QuadStripC1Ev':'quad_ctor','__ZN9QuadStripD1Ev':'quad_dtor',
            '__ZN9QuadStrip7AddQuadERK8GLfloat2S2_14QuadSizePolicyf':'quad_add',
            '__ZN9QuadStrip17SetPositionCentreE8GLfloat2':'quad_position',
            '__ZN4Game9MatchTileEP4Tile8TileType':'match',
            '__ZN4Game16QueueAchievementE11Achievementf':'achievement'}
        for symbol,name in symbols.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M)
            assert m,symbol;self.rune_calls[int(m[1],16)]=name
        self.rune_visits={}
    def hook(self,u,address,size,context):
        if address in [0xf814,0xf83e,0xf852,0xf92c,0xf97c,0xf9b2,0xf9ba,0xf9ea,0xfa5c,0xfadc]:
            key=hex(address);self.rune_visits[key]=self.rune_visits.get(key,0)+1
        if address==0xf7bc and getattr(self,'rune_direct',False):return
        name=getattr(self,'rune_calls',{}).get(address)
        if not name:return super().hook(u,address,size,context)
        r=[u.reg_read(v) for v in self.regs]
        if name=='vector_size':u.reg_write(self.regs[0],self.slots)
        elif name=='vector_back':u.reg_write(self.regs[0],0x1510000+(self.slots-1)*76)
        elif name=='vector_push':
            self.events.append([16,-1,self.slots,0]);self.slots+=1
        elif name=='quad_position':
            slot=(r[0]-0x1510000)//76
            point=struct.pack('<II',r[1],r[2]);indices=[i for i in range(36) if bytes(u.mem_read(self.GAME+0xb400+8*i,8))==point]
            assert len(indices)==1
            self.events.append([17,indices[0],slot,0])
        elif name=='match':
            index=self.index(r[1]);self.events.append([18,index,r[2],0])
            if self.case.get('mark_matches'):u.mem_write(r[1]+0x84,b'\1')
        elif name=='achievement':
            amount=struct.unpack('<f',struct.pack('<I',r[2]))[0]
            self.events.append([19,-1,r[1],int(amount)])
        # Quad creation, texture sizing and destruction belong to the renderer.
        u.reg_write(self.PC,u.reg_read(self.LR))
    def load(self,case):
        super().load(case);r=case['rune'];self.rune_direct=False;self.slots=r['allocated']
        self.u.mem_write(self.GAME+0x16491,bytes([r['enabled']]))
        self.write(self.GAME+0x164a0,r['highlights']);self.write(self.GAME+0x16494,0x1510000)
        self.write(self.GAME+0xb3f4,len(self.fake))
    def status(self):
        return dict(highlights=self.read(self.GAME+0x164a0),allocated=self.slots,
            counts=[C.c_int32(self.read(self.GAME+0x164b0+4*i)).value for i in range(6)],
            matched=[self.u.mem_read(self.tile(i)+0x84,1)[0] for i in range(36)])
    def run(self,commit):
        self.rune_direct=True;self.events=[];u=self.u
        u.reg_write(self.regs[0],self.GAME);u.reg_write(self.regs[1],int(commit))
        u.reg_write(self.SP,0x140fff0);u.reg_write(self.LR,self.STOP|1)
        u.emu_start(0xf7bd,self.STOP,timeout=1000000,count=1000000)
        assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        return dict(self.status(),events=self.events)
    def step(self,phase,touch):
        if phase==2:
            self.rune_direct=False;route=StrokeOriginal.step(self,phase,touch)
            return dict(route=route,rune=self.status(),selected=[self.u.mem_read(self.tile(i)+0x85,1)[0] for i in range(36)],events=self.events)
        self.rune_direct=False;result=super().step(phase,touch);result['rune']=self.status();return result

def path_case(path):
    case=configure(initial());case['path']=list(path);case['counts']=[0]*6
    for t in case['board']:t['selected']=0
    for i in path:case['board'][i]['selected']=1
    return case

def rectangles():
    for x0 in range(4):
      for x1 in range(x0+2,6):
       for y0 in range(4):
        for y1 in range(y0+2,6):
            yield ([y0*6+x for x in range(x0,x1)]+
                   [y*6+x1 for y in range(y0,y1)]+
                   [y1*6+x for x in range(x1,x0,-1)]+
                   [y*6+x0 for y in range(y1,y0,-1)])

def cases():
    rng=random.Random(0xf7bc)
    paths=list(rectangles())+[[2,9,16,21,26,19,12,7],[0,7,14,21,28,35],[],[0],[0,1,7],[0,1,7,6]]
    for path in paths:
        for reverse in [False,True]:
            for commit in [False,True]:
                case=path_case(path[::-1] if reverse else path);case['commit']=commit
                for t in case['board']:t.update(type=rng.randrange(7),enemy=rng.choice([0,0,2,8,32]))
                case['rune'].update(highlights=2,allocated=4)
                case['mark_matches']=True
                case['fake']=rng.sample(path,rng.randrange(len(path)+1))
                yield case
    for enabled in [0,1]:
      for count in [0,3]:
       for path in [[],[0,1,7],[0,1,7,6],[0,1,2,3,4,5],[0,6,12,18,24,30]]:
        case=path_case(path);case['rune'].update(enabled=enabled,highlights=count,allocated=count)
        case['commit']=False;yield case
    # Selected flags can be stale: exact original fallback behavior is compared.
    for _ in range(150):
        path=rng.sample(range(36),rng.randrange(4,37));case=path_case(path)
        case['commit']=bool(rng.randrange(2))
        for t in case['board']:t.update(type=rng.randrange(7),selected=rng.randrange(2),enemy=rng.randrange(3))
        case['fake']=rng.sample(path,rng.randrange(len(path)+1));yield case

def main():
    old=Original();new=Native();direct=0;steps=0;events={};samples=[]
    def compare(case,a,b):
        if a!=b:
            (HERE/'rune_failure.json').write_text(json.dumps(dict(case=case,original=a,native=b),indent=2))
            raise AssertionError('See rune_failure.json')
        for event in a['events']:events[str(event[0])]=events.get(str(event[0]),0)+1
    for case in cases():
        old.load(case);new.load(case);a=old.run(case['commit']);b=new.run(case['commit']);compare(case,a,b);direct+=1
        if any(e[0]==19 for e in a['events']) and len(samples)<2:samples.append(dict(path=case['path'],fake=case['fake'],result=a))
    gestures=0
    for path in rectangles():
        case=configure(initial());case['counts']=[0]*6
        # All coins, with a valid contiguous perimeter and normal input gates.
        old.load(case);new.load(case)
        for i in path+[path[-1],path[-2]]:
            touch=case['board'][i]['center'];a=old.step(1,touch);b=new.step(1,touch)
            compare(case,a,b);steps+=1
        a=old.step(2,[.5,.5]);b=new.step(2,[.5,.5]);compare(case,a,b);steps+=1
        a=old.step(3,[.5,.5]);b=new.step(3,[.5,.5]);compare(case,a,b);steps+=1;gestures+=1
    assert all(events.get(str(k),0)>0 for k in [16,17,18,19]),events
    report=dict(status='passed',direct_cases=direct,integrated_gestures=gestures,integrated_steps=steps,
        event_counts=events,branch_visits=old.rune_visits,
        scope='Actual original ProcessRune scan and input/selection/resource-preview instructions versus native ARM64. MatchTile requests and achievement dispatch compared, not their effects.',
        release_prefix_cases=gestures,
        boundaries=['MatchTile (recorded; optional deterministic matched flag adapter)','ProcessPretzels','rendering/audio/UI','old collections','platform ceilf'],
        samples=samples)
    (HERE/'rune_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    provenance=dict(original_symbol='Game::ProcessRune',address='0xf7bc',size=0x3b0,
        sha256=hashlib.sha256(old.old.bytes_at(0xf7bc,0x3b0)).hexdigest(),native_source='recovered_rune.cpp',
        status='board scan, counters and dispatch reconstructed; rendering and actual MatchTile remain external')
    (HERE/'rune_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    release_provenance=dict(original_symbol='Game::ProcessInput',address='0x16638',size=0xb44,
        sha256=hashlib.sha256(old.old.bytes_at(0x16638,0xb44)).hexdigest(),
        native_source='recovered_stroke.cpp + recovered_rune.cpp',
        status='additional partial branches, not a complete ProcessInput',
        branches={'highlight_reset':['0x16748','0x1674c'],
                  'release_undim':['0x17082','0x1675a','0x16798'],
                  'rune_and_deselect':['0x1681a','0x1688e']},
        limits='Tests stop at route destination; path effects/scroll effects/turn scheduling remain unresolved. Release joint cases are 100 valid coin perimeters.')
    (HERE/'release_prefix_provenance.json').write_text(json.dumps(release_provenance,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='samples'}))

if __name__=='__main__':main()
