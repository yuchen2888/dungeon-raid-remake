#!/usr/bin/env python3
"""Real ProcessInput branches versus native stroke controller.

Starts the ORIGINAL ProcessInput entry with its input gates already satisfied.
Runs its actual GetTileAtPosition/Select/ProcessTileSelection and rule helpers.
Rune/resource-shadow/special-mode handlers are explicit unresolved boundaries.
For release, stops at the observed route BEFORE applying gameplay effects.
"""
import copy
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import random
import re
import struct
os.environ['RAID_UNICORN_TCI']='1'
from verify_selection import (Original as SelectionOriginal,State as SelectionState,
    Tile,Point,Geometry,Character,Rule,Hooks,EVENT,INTS,BYTES,TBYTES,RULE_INTS,
    RULE_BYTES,base_case,I32,U8,snapshot)

HERE=Path(__file__).resolve().parent
class State(C.Structure):
    _fields_=[('selection',SelectionState),('counts',I32*6),('record',U8),('mode',I32)]

class Native:
    def __init__(self):
        self.lib=C.CDLL(str(HERE/'recovered_stroke_native.dylib'))
        for name in ['dr_begin_stroke','dr_update_stroke','dr_cancel_stroke']:
            fn=getattr(self.lib,name);fn.argtypes=[C.POINTER(State),C.POINTER(Hooks)];fn.restype=None
        self.lib.dr_release_route.argtypes=[C.POINTER(SelectionState)]
        self.lib.dr_release_route.restype=I32
    def load(self,case):
        self.case=copy.deepcopy(case);self.state=State();state=self.state.selection;g=case['game']
        state.geometry.offset=g['offset'];state.geometry.pitch=g['pitch']
        state.half_spacing=g['half_spacing'];state.touch=Point(*case['touch'])
        state.character=Character(g['race'],(I32*4)(*g['flaws']))
        for k in (*INTS,*BYTES):setattr(state,k,g[k])
        for i,b in enumerate(case['board']):
            t=state.tiles[i];t.rule=Rule(**{k:b[k] for k in (*RULE_INTS,*RULE_BYTES)})
            t.geometry=Geometry(Point(*b['center']),b['half_size']);t.resting=Point(*b['resting']);t.size=b['size']
            state.geometry.tiles[i]=t.geometry
            for k in TBYTES:setattr(t,k,b[k])
            t.flame_damage=b['flame_damage']
        state.path_length=len(case['path'])
        for i,v in enumerate(case['path']):state.path[i]=v
        for v in case['fake']:state.fake[v]=1
        self.state.counts=(I32*6)(*case['counts']);self.state.record=case['record'];self.state.mode=case['mode']
        def receive(_,kind,index,a,b):
            event=[kind,index,a,b]
            if kind==10:event.append(list(state.path[:state.path_length]))
            self.events.append(event)
            if kind==13 and hasattr(self,'resource_callback'):
                self.resource_callback()
            if kind==14 and hasattr(self,'rune_callback'):
                self.rune_callback(bool(a))
            # Chosen deterministic callback side effect, used on both machines.
            if kind==13 and case.get('mutating_shadows'):
                state.current_damage+=2;state.leech=40
        self.callback=EVENT(receive);self.hooks=Hooks(None,self.callback)
    def step(self,phase,touch):
        s=self.state.selection;s.touch=Point(*touch);self.events=[]
        if phase==2:return self.lib.dr_release_route(C.byref(s))
        fn=self.lib.dr_cancel_stroke if phase==3 else self.lib.dr_update_stroke
        fn(C.byref(self.state),C.byref(self.hooks))
        game=dict(self.case['game'])
        for k in (*INTS,*BYTES):game[k]=getattr(s,k)
        board=copy.deepcopy(self.case['board'])
        for i,t in enumerate(s.tiles):
            for k in TBYTES:board[i][k]=getattr(t,k)
        result=snapshot(self.case,game,list(s.path[:s.path_length]),
            [i for i,v in enumerate(s.fake) if v],board,self.events)
        result['counts']=list(self.state.counts)
        return result

class Original(SelectionOriginal):
    def __init__(self):
        super().__init__()
        text=(HERE.parent/'armv7-disassembly.txt').read_text()
        names={'__ZN7Tooltip4ShowE9EnemyTypeRK8GLfloat2':'enemy_tip',
               '__ZN4Game13UpdateDimmingEv':'dimming',
               '__ZN4Game22ProcessResourceShadowsEv':'shadows',
               '__ZN4Game11ProcessRuneEb':'rune',
               '__ZN4Game15ProcessPretzelsEv':'pretzels'}
        self.extra={}
        for symbol,name in names.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M)
            assert m,symbol;self.extra[int(m[1],16)]=name
        self.visits={}
    def hook(self,u,address,size,context):
        if self.release and address in (0x168a6,0x16c1c,0x16d88):
            self.route={0x168a6:1,0x16c1c:2,0x16d88:0}[address]
            u.emu_stop();return
        if address in (0x16e28,0x16f82,0x170ca,0x170d2,0x16ff4,0x17018,0x17042,0x1679a):
            key=hex(address);self.visits[key]=self.visits.get(key,0)+1
        name=self.extra.get(address)
        if not name:return super().hook(u,address,size,context)
        r=[u.reg_read(v) for v in self.regs]
        if name=='enemy_tip':event=[11,self.index(r[2]-0x54),r[1],0]
        else:event=[{'dimming':12,'shadows':13,'rune':14,'pretzels':15}[name],-1,r[1] if name=='rune' else 0,0]
        self.events.append(event)
        if name=='shadows' and self.case.get('real_shadows'):
            return # Execute actual original resource calculation.
        if name=='rune' and self.case.get('real_rune'):
            return # Execute actual original rune scan.
        if name=='shadows' and self.case.get('mutating_shadows'):
            self.write(self.GAME+INTS['current_damage'],self.read(self.GAME+INTS['current_damage'])+2)
            self.write(self.GAME+INTS['leech'],40)
        u.reg_write(self.PC,u.reg_read(self.LR))
    def load(self,case):
        self.case=copy.deepcopy(case)
        u=self.u;G=self.GAME;g=case['game'];self.events=[];self.next_node=0x1500100
        self.fake={self.tile(i) for i in case['fake']};self.release=False
        u.mem_write(G,b'\0'*0x16614)
        for k,offset in INTS.items():self.write(G+offset,g[k])
        for k,offset in BYTES.items():u.mem_write(G+offset,bytes([g[k]]))
        self.write(G+0x15564+8,g['race'])
        for i,v in enumerate(g['flaws']):self.write(G+0x15564+0x20+4*i,v)
        for a,key in [(0x165c8,'offset'),(0x5e50,'pitch'),(0x5e54,'half_spacing')]:u.mem_write(G+a,struct.pack('<f',g[key]))
        for i,t in enumerate(case['board']):
            base=self.tile(i)
            for k,a in RULE_INTS.items():self.write(base+a,t[k])
            for k,a in {**RULE_BYTES,**TBYTES}.items():u.mem_write(base+a,bytes([t[k]]))
            self.write(base+0x70,G);self.write(base+0x258,t['flame_damage'])
            u.mem_write(base+0x54,struct.pack('<ff',*t['center']))
            u.mem_write(base+0x7c,struct.pack('<ff',t['size'],t['half_size']))
            u.mem_write(G+0xb400+8*i,struct.pack('<ff',*t['resting']))
        for offset in [0xb3d8,0xb3f8]:
            sentinel=G+offset;u.mem_write(sentinel,struct.pack('<II',sentinel,sentinel))
        for index in case['path']:self.push(G+0xb3d8,self.tile(index))
        for i,v in enumerate(case['counts']):self.write(G+0x164b0+4*i,v)
        u.mem_write(G+0x14aed,bytes([case['record']]))
        self.write(G+0x14ae8,case['mode'])
        u.mem_write(G+0x5e14,b'\1') # Original input-ready gate satisfied.
        self.write(G+0x58ac,-1) # No active skill/menu input target.
    def step(self,phase,touch):
        u=self.u;G=self.GAME;self.events=[];self.release=phase==2;self.route=None
        self.write(G+0x10,phase);u.mem_write(G+0x14,struct.pack('<ff',*touch))
        self.write(G+0xb3f4,len(self.fake))
        u.reg_write(self.regs[0],G);u.reg_write(self.SP,0x140fff0);u.reg_write(self.LR,self.STOP|1)
        u.emu_start(0x16639,self.STOP,timeout=0,count=500000)
        if self.release:
            assert self.route is not None,hex(u.reg_read(self.PC))
            return self.route
        assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        game=dict(self.case['game'])
        for k,a in INTS.items():game[k]=C.c_int32(self.read(G+a)).value
        for k,a in BYTES.items():game[k]=u.mem_read(G+a,1)[0]
        board=copy.deepcopy(self.case['board'])
        for i,t in enumerate(board):
            for k,a in TBYTES.items():t[k]=u.mem_read(self.tile(i)+a,1)[0]
        result=snapshot(self.case,game,[self.index(p) for p in self.list_values(G+0xb3d8)],
            [self.index(p) for p in self.fake],board,self.events)
        result['counts']=[C.c_int32(self.read(G+0x164b0+4*i)).value for i in range(6)]
        return result

def initial():
    case=base_case();case.update(path=[],counts=[3,1,4,1,5,9],record=0,mode=0)
    case['board'][0]['selected']=0
    case['game'].update(current_damage=99,current_leech=77,current_flame_damage=11,
                        current_spike_damage=13,skull_counted=1,spiky_enemy_attacked=1)
    return case

def scenarios():
    for index in range(36):
        for kind in [0,1,2,3,4,5,6]:
            case=initial();case['board'][index]['type']=kind
            case['steps']=[(1,case['board'][index]['center'])];yield case
    for race in range(10):
        for enemy in [0,2,8,32]:
            for active in [0,1]:
                for frozen in [0,1]:
                    case=initial();case['game']['race']=race
                    case['board'][0].update(type=1,enemy=enemy,enemy_state=active,flag255=frozen)
                    case['board'][1].update(type=1,enemy=8)
                    case['steps']=[(1,case['board'][0]['center'])];yield case
    for frozen in [0,1]:
        for magic in [0,1]:
            for broken in [0,1]:
                for double in [0,1]:
                    for flaming,self_flame in [(0,0),(1,0),(1,1)]:
                        case=initial();case['game']['double_damage']=double
                        case['board'][0].update(type=4,flag255=frozen,magic_sword=magic,broken=broken,
                                               flaming=flaming,self_flame=self_flame,flame_damage=7)
                        case['steps']=[(1,case['board'][0]['center'])];yield case
    for touch in [[-.2,.5],[1.2,.5],[.5,.1],[.5,1.4],[0,.246875],[1,1.246875]]:
        case=initial();case['steps']=[(1,touch)];yield case
    for moving in [0,1]:
        for mode in [0,1,2]:
            for mutate in [False,True]:
                case=initial();case['record']=1;case['mode']=mode;case['mutating_shadows']=mutate
                case['game'].update(flame_label_moving=moving,spike_label_moving=moving)
                case['steps']=[(1,case['board'][i]['center']) for i in [0,0,1,2,1,7,14]]
                case['steps'] += [(3,[.5,.5]),(1,case['board'][18]['center'])]
                yield case
    # Original special sword bridge, then physical backtracking and cancellation.
    case=initial()
    for tile in case['board']:tile.update(type=4)
    case['board'][1]['flag231']=1
    case['board'][2]['type']=3
    case['steps']=[(1,case['board'][i]['center']) for i in [0,1,2,3,2,1]]+[(3,[.5,.5])]
    yield case
    rng=random.Random(0xD13457)
    for _ in range(150):
        case=initial();case['game'].update(race=rng.randrange(10),base_damage=rng.randrange(-20,100),
            bonus_base_damage=rng.randrange(-10,50),weapon_damage=rng.randrange(0,50),leech=rng.randrange(101))
        for tile in case['board']:
            tile.update(type=rng.choice([1,2,3,4,5]),enemy=rng.choice([0,2,8,32]),enemy_state=rng.randrange(2),
                        flag255=rng.randrange(2),flag231=rng.randrange(2),magic_sword=rng.randrange(2),
                        broken=rng.randrange(2),flaming=rng.randrange(2),self_flame=rng.randrange(2),flame_damage=rng.randrange(10))
        case['steps']=[(1,case['board'][rng.randrange(36)]['center']) for _ in range(7)]
        case['steps'] += [(3,[.5,.5])];yield case

def release_cases():
    for length in range(0,9):
        for fake_count in range(length+1):
            for first_type,special in [(1,0),(2,0),(4,0),(6,0),(6,1),(6,2)]:
                case=initial();case['path']=list(range(length));case['fake']=list(range(fake_count))
                case['board'][0].update(type=first_type,special=special)
                yield case

def main():
    old=Original();new=Native();steps=0;cases=0;samples=[]
    for case in scenarios():
        old.load(case);new.load(case);trace=[]
        for phase,touch in case['steps']:
            original=old.step(phase,touch);native=new.step(phase,touch)
            if original!=native:
                failure=dict(case=case,phase=phase,touch=touch,original=original,native=native)
                (HERE/'stroke_failure.json').write_text(json.dumps(failure,indent=2))
                raise AssertionError(f'Case {cases} step {steps}; see stroke_failure.json')
            trace.append(dict(phase=phase,touch=touch,path=original['path'],
                              damage=original['game']['current_damage'],events=original['events']))
            steps+=1
        if len(case['steps'])>1 and len(samples)<4:samples.append(trace)
        cases+=1
    routes={0:0,1:0,2:0}
    for case in release_cases():
        old.load(case);new.load(case)
        original=old.step(2,[.5,.5]);native=new.step(2,[.5,.5])
        assert original==native,(case['path'],case['fake'],original,native)
        routes[original]+=1
    report=dict(status='passed',mode='original ProcessInput ARMv7 entry versus native ARM64 stroke branches',
        gesture_scenarios=cases,gesture_steps=steps,release_routes=routes,branch_visits=old.visits,
        scope='Input gates pre-satisfied; begin/continue/cancel plus release route decision ONLY; not release effects or a playable turn',
        unresolved_gameplay_callbacks=['ProcessRune','ProcessResourceShadows','ProcessPretzels'],
        adapted_interfaces=['old collection storage','rendering/audio/UI'],sample_traces=samples)
    (HERE/'stroke_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    raw=old.old.bytes_at(0x16638,0xb44)
    provenance=dict(original_symbol='Game::ProcessInput',address='0x16638',size=0xb44,
        sha256=hashlib.sha256(raw).hexdigest(),native_source='recovered_stroke.cpp',
        status='partial function reconstruction; do not count as complete ProcessInput',
        branches={'begin':['0x16e28','0x16ff2','0x170ca','0x170dc'],
                  'continue':['0x16ff4','0x17072'],
                  'cancel':['0x17082','0x1675a','0x16818','0x16d88','0x16e0e'],
                  'release_route':['0x16890','0x168a2','0x16bf4','0x16c18']})
    (HERE/'stroke_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['sample_traces','adapted_interfaces','unresolved_gameplay_callbacks']}))

if __name__=='__main__':main()
