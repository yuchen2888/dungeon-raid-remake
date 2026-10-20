#!/usr/bin/env python3
"""Original path selection versus native 64-bit reconstruction.

Actual original geometry, type matching, normalization and Tile::Select execute.
Rendering/audio/UI and old std::list/set allocation are explicit adapters.
No desktop game is launched. Replay mode never constructs an emulator.
"""
from __future__ import annotations
import copy
import ctypes as C
import hashlib
import json
from pathlib import Path
import platform
import random
import re
import struct
import sys
from verify_input import Point, Tile as Geometry, Board, bits, f32
from verify_rules import Tile as Rule, Character
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
I32=C.c_int32
U8=C.c_uint8
INTS={'weapon_damage':0xbdbc,'base_damage':0xbdc0,'bonus_base_damage':0xbdc4,
      'leech':0xbe60,'current_damage':0xbe7c,'current_leech':0xc318,
      'current_flame_damage':0x14e54,'current_spike_damage':0x151c8}
BYTES={'double_damage':0xbe74,'skull_counted':0xbe80,'spiky_enemy_attacked':0x151cc,
       'flame_label_moving':0x14e58,'spike_label_moving':0x151cd}
TBYTES={'selected':0x85,'cross_visibility':0x13c,'magic_sword':0x230,
        'broken':0x25c,'flaming':0x256,'self_flame':0x257}
RULE_INTS={'type':0x9c,'special':0xa0,'enemy':0x24c,'enemy_state':0x250,'x':0x74,'y':0x78}
RULE_BYTES={'flag231':0x231,'flag255':0x255,'matched':0x84}
class Tile(C.Structure):
    _fields_=[('rule',Rule),('geometry',Geometry),('resting',Point),('size',C.c_float)]+[(k,U8) for k in TBYTES]+[('flame_damage',I32)]
class State(C.Structure):
    _fields_=[('geometry',Board),('touch',Point),('half_spacing',C.c_float),('character',Character),
        ('tiles',Tile*36),('path',U8*36),('fake',U8*36),('path_length',C.c_size_t)]+[(k,I32) for k in INTS]+[(k,U8) for k in BYTES]
EVENT=C.CFUNCTYPE(None,C.c_void_p,I32,I32,I32,I32)
class Hooks(C.Structure):
    _fields_=[('context',C.c_void_p),('event',EVENT)]

def snapshot(case,g,path,fake,board,events):
    return {'game':g,'path':path,'fake':sorted(fake),'board':board,'events':events}
class Native:
    def __init__(self):
        self.lib=C.CDLL(str(HERE/'recovered_selection_native.dylib'))
        self.lib.dr_process_tile_selection.argtypes=[C.POINTER(State),C.POINTER(Hooks)]
        self.lib.dr_process_tile_selection.restype=None
    def run(self,case):
        state=State();g=case['game'];state.geometry.offset=g['offset'];state.geometry.pitch=g['pitch']
        state.touch=Point(*case['touch']);state.half_spacing=g['half_spacing']
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
        events=[]
        def receive(_,kind,index,a,b):
            value=[kind,index,a,b]
            if kind==10:value.append(list(state.path[:state.path_length]))
            events.append(value)
        event=EVENT(receive)
        hooks=Hooks(None,event)
        self.lib.dr_process_tile_selection(C.byref(state),C.byref(hooks))
        game=dict(g)
        for k in (*INTS,*BYTES):game[k]=getattr(state,k)
        board=copy.deepcopy(case['board'])
        for i,t in enumerate(state.tiles):
            for k in TBYTES:board[i][k]=getattr(t,k)
        return snapshot(case,game,list(state.path[:state.path_length]),[i for i,v in enumerate(state.fake) if v],board,events)

class Original:
    def __init__(self):
        from verify_original import Original as Machine,GAME,STOP
        from unicorn import UC_HOOK_CODE
        from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_PC,UC_ARM_REG_LR,UC_ARM_REG_C1_C0_2,UC_ARM_REG_FPEXC,UC_ARM_REG_FPSCR
        self.old=Machine();self.u=self.old.uc;self.GAME=GAME;self.STOP=STOP
        self.regs=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
        self.SP=UC_ARM_REG_SP;self.PC=UC_ARM_REG_PC;self.LR=UC_ARM_REG_LR
        self.u.mem_map(0x1400000,0x20000)
        self.u.mem_map(0x1500000,0x20000)
        self.u.reg_write(UC_ARM_REG_C1_C0_2,self.u.reg_read(UC_ARM_REG_C1_C0_2)|(15<<20))
        self.u.reg_write(UC_ARM_REG_FPEXC,0x40000000);self.u.reg_write(UC_ARM_REG_FPSCR,0)
        text=(ROOT/'armv7-disassembly.txt').read_text()
        def address(symbol):
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol
            return int(m[1],16)
        self.boundaries={0x194cec:'unwind',0x194cf4:'unwind'}
        names={
          '__ZN4Quad7SetSizeERK8GLfloat2':'size',
          '__ZN4Tile5UndimEv':'undim',
          '__ZN4Game14QueueTileSoundEP4Tile':'sound',
          '__ZN7Tooltip4HideEv':'tooltip',
          '__ZN4Game21UpdateCrossVisibilityEv':'cross',
          '__ZN5Arrow6UpdateESt4listIP4TileSaIS2_EE':'arrow',
          '__ZN9Interface15SetHealthShadowEi':'health',
          '__ZN9Interface11SetXPshadowEi':'xp',
          '__ZN9Interface11SetUPshadowEi':'up',
          '__ZN9Interface13SetGoldShadowEi':'gold',
          '__ZNSt4listIP4TileSaIS1_EE9push_backERKS1_':'push',
          '__ZNSt4listIP4TileSaIS1_EE5eraseESt14_List_iteratorIS1_E':'erase',
          '__ZNSt10_List_baseIP4TileSaIS1_EE8_M_clearEv':'clear',
          '__ZNSt4listIP4TileSaIS1_EEC2ERKS3_':'copy',
          '__ZNSt3setIP4TileSt4lessIS1_ESaIS1_EE6insertERKS1_':'set_insert',
          '__ZNSt3setIP4TileSt4lessIS1_ESaIS1_EE4findERKS1_':'set_find',
          '__ZNSt8_Rb_treeIP4TileS1_St9_IdentityIS1_ESt4lessIS1_ESaIS1_EE5eraseERKS1_':'set_erase',
          '__ZNSt8_Rb_treeIP4TileS1_St9_IdentityIS1_ESt4lessIS1_ESaIS1_EE8_M_eraseEPSt13_Rb_tree_nodeIS1_E':'set_clear'}
        for symbol,name in names.items():self.boundaries[address(symbol)]=name
        self.u.hook_add(UC_HOOK_CODE,self.hook)
        self.coverage={}
        self.markers={0xfb6c:'process_entry',0xfd44:'within_board_band',0x10334:'cancel',
            0xfdb6:'clamp_long_move',0xfedc:'path_search',0xfee0:'remove_suffix',
            0xff4a:'new_tile_type_check',0xff66:'frozen_rejection',0xff9c:'fake_bridge',
            0xffa8:'append_tile',0x100d6:'backtrack_recompute_check',0x1010e:'recompute',
            0x10382:'halve_skull_damage',0x10396:'halve_recomputed_skull_damage'}
    def read(self,a):return struct.unpack('<I',self.u.mem_read(a,4))[0]
    def write(self,a,v):self.old.write_i32(a,v)
    def tile(self,index):return self.GAME+0x5e58+608*index
    def index(self,p):
        d=p-self.tile(0);assert d>=0 and d%608==0 and d//608<36,hex(p)
        return d//608
    def list_values(self,sentinel):
        result=[];p=self.read(sentinel)
        while p!=sentinel:
            assert len(result)<40
            result.append(self.read(p+8));p=self.read(p)
        return result
    def push(self,sentinel,tile):
        node=self.next_node;self.next_node+=16;prev=self.read(sentinel+4)
        self.u.mem_write(node,struct.pack('<III',sentinel,prev,tile))
        self.write(prev,node);self.write(sentinel+4,node)
    def hook(self,u,address,size,context):
        marker=self.markers.get(address)
        if marker:self.coverage[marker]=self.coverage.get(marker,0)+1
        name=self.boundaries.get(address)
        if not name:return
        r=[u.reg_read(v) for v in self.regs];event=None
        if name=='size':
            a,b=struct.unpack('<ii',u.mem_read(r[1],8));event=[3,self.index(r[0]),a,b]
        elif name=='undim':event=[2,self.index(r[0]),0,0]
        elif name=='sound':event=[4,self.index(r[1]),0,0]
        elif name=='tooltip':event=[1,-1,0,0]
        elif name=='cross':event=[9,-1,0,0]
        elif name=='arrow':
            assert self.list_values(r[1])==self.list_values(self.GAME+0xb3d8)
            event=[10,-1,0,0,[self.index(v) for v in self.list_values(r[1])]]
        elif name in ('health','xp','up','gold'):
            event=[{'health':5,'xp':6,'up':7,'gold':8}[name],-1,C.c_int32(r[1]).value,0]
        elif name=='push':self.push(r[0],self.read(r[1]))
        elif name=='erase':
            nxt,prev=struct.unpack('<II',u.mem_read(r[1],8));self.write(nxt+4,prev);self.write(prev,nxt)
            u.reg_write(self.regs[0],nxt)
        elif name=='clear':pass
        elif name=='copy':
            values=self.list_values(r[1]);self.u.mem_write(r[0],struct.pack('<II',r[0],r[0]))
            for value in values:self.push(r[0],value)
        elif name=='set_insert':self.fake.add(self.read(r[2]))
        elif name=='set_find':u.reg_write(self.regs[0],r[0]+8 if self.read(r[1]) in self.fake else r[0]+4)
        elif name=='set_erase':self.fake.discard(self.read(r[1]))
        elif name=='set_clear':self.fake.clear()
        elif name=='unwind':pass
        else:raise AssertionError(name)
        if event:self.events.append(event)
        u.reg_write(self.PC,u.reg_read(self.LR))
    def run(self,case):
        u=self.u;G=self.GAME;g=case['game'];self.events=[];self.next_node=0x1500100
        self.fake={self.tile(i) for i in case['fake']}
        u.mem_write(G,b'\0'*0x16614)
        for k,offset in INTS.items():self.write(G+offset,g[k])
        for k,offset in BYTES.items():u.mem_write(G+offset,bytes([g[k]]))
        self.write(G+0x15564+8,g['race'])
        for i,v in enumerate(g['flaws']):self.write(G+0x15564+0x20+4*i,v)
        u.mem_write(G+0x14,struct.pack('<ff',*case['touch']))
        for a,key in [(0x165c8,'offset'),(0x5e50,'pitch'),(0x5e54,'half_spacing')]:u.mem_write(G+a,struct.pack('<f',g[key]))
        for i,t in enumerate(case['board']):
            base=self.tile(i)
            for k,a in RULE_INTS.items():self.write(base+a,t[k])
            for k,a in {**RULE_BYTES,**TBYTES}.items():u.mem_write(base+a,bytes([t[k]]))
            self.write(base+0x70,G);self.write(base+0x258,t['flame_damage'])
            u.mem_write(base+0x54,struct.pack('<ff',*t['center']))
            u.mem_write(base+0x7c,struct.pack('<ff',t['size'],t['half_size']))
            u.mem_write(G+0xb400+8*i,struct.pack('<ff',*t['resting']))
        sentinel=G+0xb3d8;u.mem_write(sentinel,struct.pack('<II',sentinel,sentinel))
        for index in case['path']:self.push(sentinel,self.tile(index))
        u.reg_write(self.regs[0],G);u.reg_write(self.SP,0x140fff0);u.reg_write(self.LR,self.STOP|1)
        u.emu_start(0xfb6d,self.STOP,timeout=0,count=500000)
        assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        game=dict(g)
        for k,a in INTS.items():game[k]=C.c_int32(self.read(G+a)).value
        for k,a in BYTES.items():game[k]=u.mem_read(G+a,1)[0]
        board=copy.deepcopy(case['board'])
        for i,t in enumerate(board):
            for k,a in TBYTES.items():t[k]=u.mem_read(self.tile(i)+a,1)[0]
        return snapshot(case,game,[self.index(p) for p in self.list_values(sentinel)],
                        [self.index(p) for p in self.fake],board,self.events)

def base_case():
    pitch=f32(1/6);size=f32(.15)
    game=dict(offset=0.,pitch=pitch,half_spacing=f32(pitch/2),race=0,flaws=[255]*4,
        weapon_damage=8,base_damage=10,bonus_base_damage=3,leech=25,current_damage=10,
        current_leech=2,current_flame_damage=0,current_spike_damage=0,double_damage=0,
        skull_counted=0,spiky_enemy_attacked=0,flame_label_moving=0,spike_label_moving=0)
    board=[]
    for i in range(36):
        x,y=i%6,i//6;center=[f32((x+.5)*pitch),f32(.246875+(y+.5)*pitch)]
        board.append(dict(type=2,special=3,enemy=0,enemy_state=0,x=x,y=y,flag231=0,flag255=0,
          matched=0,center=center,resting=center,size=size,half_size=f32(size/2),selected=0,
          cross_visibility=0,magic_sword=0,broken=0,flaming=0,self_flame=0,flame_damage=0))
    board[0]['selected']=1
    return dict(game=game,board=board,path=[0],fake=[],touch=board[1]['center'])

def cases():
    # Physical straight/diagonal strokes, long moves, retracing and outside bands.
    for start in range(36):
      for target in range(36):
        c=base_case();c['path']=[start];c['board'][0]['selected']=0;c['board'][start]['selected']=1
        c['touch']=c['board'][target]['center'];yield c
    for path in ([0,1,2,3,4,5],[0,7,14,21,28,35],[12,13,14,15,16,17],[0,6,12,18,24,30]):
      for target in path:
        c=base_case();c['path']=list(path)
        for i in path:c['board'][i]['selected']=1;c['board'][i]['cross_visibility']=1
        c['touch']=c['board'][target]['center'];yield c
    for y in [-.1,.1468749,.146875,.2,.246875,1.246875,1.30,1.346875,1.346876,1.5]:
      for moving in (0,1):
        c=base_case();c['touch']=[.5,f32(y)];c['game'].update(current_flame_damage=9,current_spike_damage=7,flame_label_moving=moving,spike_label_moving=moving)
        yield c
    # Explicit sword bridges, frozen tiles, phylacteries, mortal-enemy damage,
    # magic/broken swords, and damage recalculation when retracing the stroke.
    for race in range(9):
      for frozen in (0,1):
       for special in (0,1):
        for broken in (0,1):
         c=base_case();c['game'].update(race=race,skull_counted=0)
         for i in range(36):c['board'][i].update(type=4,flag231=special,flag255=frozen,magic_sword=1,broken=broken)
         c['board'][2].update(type=1,enemy=8,flag255=0)
         c['board'][3].update(type=3,flaming=1,flame_damage=7)
         c['touch']=c['board'][5]['center'];yield c
         c=copy.deepcopy(c);c['path']=[0,1,2,3,4,5];c['touch']=c['board'][2]['center']
         for i in c['path']:c['board'][i]['selected']=1
         yield c
    c=base_case();c['path']=[];yield c
    rng=random.Random(0xd1345e1)
    for n in range(1000):
        c=base_case();g=c['game'];path=[rng.randrange(36)]
        # Valid adjacent, nonrepeating shape; types may deliberately be varied
        # to isolate the original selection branch from initial stroke setup.
        for _ in range(rng.randrange(1,15)):
            a=path[-1];choices=[i for i in range(36) if i not in path and abs(i%6-a%6)<=1 and abs(i//6-a//6)<=1]
            if not choices:break
            path.append(rng.choice(choices))
        c['path']=path
        for i,t in enumerate(c['board']):
            t.update(type=rng.choice([1,2,3,4,5]),special=rng.randrange(8),enemy=rng.choice([0,2,8,32]),enemy_state=rng.randrange(2),
                flag231=rng.randrange(2),flag255=int(rng.random()<.2),selected=int(i in path),
                cross_visibility=int(i in path),magic_sword=rng.randrange(2),broken=int(rng.random()<.2),
                flaming=rng.randrange(2),self_flame=rng.randrange(2),flame_damage=rng.randrange(-5,15))
        c['fake']=[i for i in path if rng.random()<.2]
        g.update(race=rng.randrange(9),current_damage=rng.randrange(-5,50),current_flame_damage=rng.randrange(-5,20),
            double_damage=rng.randrange(2),skull_counted=rng.randrange(2),spiky_enemy_attacked=rng.randrange(2),
            leech=rng.choice([0,1,25,100,150]),weapon_damage=rng.randrange(1,20),base_damage=rng.randrange(1,30),
            bonus_base_damage=rng.randrange(-5,10))
        target=rng.choice(path) if n%3==0 else rng.randrange(36)
        c['touch']=[f32(v+rng.uniform(-.03,.03)) for v in c['board'][target]['center']]
        yield c

def main():
    native=Native();fixtures=[];events=set();changed=0
    if '--replay' in sys.argv:
        source=json.loads((HERE/'selection_original_results.json').read_text());machine=None
    else:source=cases();machine=Original()
    for n,item in enumerate(source):
        case=item['case'] if machine is None else item
        expected=item['expected'] if machine is None else machine.run(case)
        got=native.run(case)
        if got!=expected:
            (HERE/'selection_mismatch.json').write_text(json.dumps(dict(index=n,case=case,expected=expected,got=got),indent=2))
            raise AssertionError(('selection differential mismatch',n))
        events.update(v[0] for v in got['events']);changed+=got['path']!=case['path']
        if machine is not None:fixtures.append(dict(case=case,expected=expected))
    if machine is not None:
        (HERE/'selection_original_results.json').write_text(json.dumps(fixtures,separators=(',',':'))+'\n')
        data=machine.old.bytes_at(0xfb6c,0x103d8-0xfb6c)
        (HERE/'original_selection.bin').write_bytes(data)
        p={'original_symbol':'Game::ProcessTileSelection','original_address':'0xfb6c',
           'bytes_including_literal_pool':len(data),'sha256':hashlib.sha256(data).hexdigest(),
           'native_source':'recovered_selection.cpp','native_pointer_bytes':C.sizeof(C.c_void_p),
           'adapters':['old list/set allocation','rendering, tooltip, arrow, shadows and audio'],
           'actual_original_helpers':['GetTileAtPosition','IsBeingSelected','CanMatchType','GetMortalEnemyType','GetEnemyCount','GLfloat2::Normalise','Tile::Select']}
        select_bytes=machine.old.bytes_at(0x1aa3c,0x34)
        p['recovered_flows']=2
        p['additional_recovered_flow']={'original_symbol':'Tile::Select','address':'0x1aa3c',
            'bytes_including_literal_pool':len(select_bytes),'sha256':hashlib.sha256(select_bytes).hexdigest(),
            'native_function':'dr_select_tile'}
        (HERE/'selection_provenance.json').write_text(json.dumps(p,indent=2)+'\n')
    result={'status':'passed','native_architecture':platform.machine(),'native_pointer_bytes':C.sizeof(C.c_void_p),
       'scenarios':n+1,'path_changes':changed,'event_kinds':sorted(events),
       'mode':'native fixture replay' if machine is None else 'original ARMv7 differential execution',
       'scope':'nonempty stroke continuation, backtracking, cancellation and damage preview; UI/render/audio remain adapters'}
    if machine is not None:result['original_branch_visits']=machine.coverage
    (HERE/('selection_verification_arm64.json' if machine is None else 'selection_verification.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
