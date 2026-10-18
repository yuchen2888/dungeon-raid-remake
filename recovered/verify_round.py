#!/usr/bin/env python3
"""Execute original MatchTiles + AttackSkull and compare native orchestration.

MatchTile/MoveMatchedTiles, graphics/audio, randomness and std::set storage are
explicit adapters. This validates orchestration through those boundaries, not
reward application, falling animation, refill, or a complete playable turn.
"""
from __future__ import annotations
import ctypes as C
import hashlib
import itertools
import json
from pathlib import Path
import platform
import random
import re
import struct
import sys

from verify_battle import BattleGame,BattleTile,ClassState,Context,CombatTile,Poison,Point,OriginalBattle,initial
from verify_rules import Tile as RuleTile,Character
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
GAME_KEYS=('kills_a','kills_b','killed_attack','break_chance','poison_amount','coin_on_attack',
           'poison_sound','lich_progress','lich_transition')
TILE_KEYS=('attack','poison','type','enemy','enemy_state','defence','health','center','frozen','overlay','flag256','flag25e')
ROUND_KEYS=('turn','base_attack','direction_bonus','flag_5e14','sound_13ec4','record_14aed',
            'mode_14ae8','round_kills_165d0','crossing_best','crossing_average','crossing_samples',
            'total_165cc','pending_165d4')

class RoundTile(C.Structure):
    _fields_=[('battle',BattleTile),('rule',RuleTile),('attack_flag',C.c_uint8)]
class RoundState(C.Structure):
    _fields_=[('battle',BattleGame),('character',Character),('turn',C.c_int32),
        ('base_attack',C.c_int32),('direction_bonus',C.c_int32),('tiles',RoundTile*36),
        ('matched_counts',C.c_int32*5),('flag_5e14',C.c_uint8),('sound_13ec4',C.c_uint8),
        ('record_14aed',C.c_uint8)] + [(k,C.c_int32) for k in ROUND_KEYS[6:]]
class RoundEvent(C.Structure):
    _fields_=[(k,C.c_int32) for k in ('tile','kind','a','b','c','d')]
RANDOM=C.CFUNCTYPE(C.c_int32,C.c_void_p,C.c_int32,C.c_int32,C.c_int32,C.c_int32)
EVENT=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(RoundEvent))
class Hooks(C.Structure):
    _fields_=[('context',C.c_void_p),('random',RANDOM),('event',EVENT)]

class Adapter:
    def __init__(self,case):self.events=[];self.rolls=case['rolls'];self.cursor=0;self.target=-1
    def random_at(self,target,low,high,stream):
        lo,hi=min(low,high),max(low,high)
        value=lo+self.rolls[self.cursor%len(self.rolls)]%(hi-lo+1);self.cursor+=1
        self.events.append([target,0,low,high,stream,value]);return value
    def random(self,low,high,stream):return self.random_at(self.target,low,high,stream)
    def event(self,kind,a=0,b=0,c=0,d=0):
        self.events.append([-1 if kind in (10,12) else self.target,kind,a,b,c,d])

class Native:
    def __init__(self):
        self.lib=C.CDLL(str(HERE/'recovered_round_native.dylib'))
        self.lib.dr_match_path.argtypes=[C.POINTER(RoundState),C.POINTER(C.c_uint8),C.c_size_t,
                                         C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(Hooks)]
        self.lib.dr_match_path.restype=None
    def run(self,case):
        g=case['game'];state=RoundState();character=ClassState(g['race'])
        state.battle.context=Context(C.pointer(character))
        state.character=Character(g['race'],(C.c_int32*4)(*g['flaws']))
        for k in GAME_KEYS:setattr(state.battle,k,g[k])
        for k in ROUND_KEYS:setattr(state,k,g[k])
        state.matched_counts=(C.c_int32*5)(*g['matched_counts'])
        for i,s in enumerate(case['board']):
            t=state.tiles[i];b=t.battle
            b.combat=CombatTile(s['attack'],Poison(*s['poison']),C.pointer(state.battle.context))
            for k in ('type','enemy','enemy_state','defence','health','frozen','overlay','flag256','flag25e'):setattr(b,k,s[k])
            b.center=Point(*s['center']);t.attack_flag=s['attack_flag']
            t.rule=RuleTile(s['type'],s['special'],s['enemy'],s['enemy_state'],s['x'],s['y'],s['flag231'],s['frozen'],s['matched'])
        adapter=Adapter(case)
        random_callback=RANDOM(lambda _,target,lo,hi,stream:adapter.random_at(target,lo,hi,stream))
        def receive(_,ptr):
            event=ptr.contents
            adapter.events.append([event.tile,event.kind,event.a,event.b,event.c,event.d])
        event_callback=EVENT(receive);hooks=Hooks(None,random_callback,event_callback)
        path=(C.c_uint8*len(case['path']))(*case['path']);excluded=(C.c_uint8*len(case['excluded']))(*case['excluded'])
        self.lib.dr_match_path(C.byref(state),path,len(path),excluded,len(excluded),C.byref(hooks))
        game=dict(g)
        for k in GAME_KEYS:game[k]=getattr(state.battle,k)
        for k in ROUND_KEYS:game[k]=getattr(state,k)
        game['matched_counts']=list(state.matched_counts)
        board=[]
        for i,s in enumerate(case['board']):
            item=dict(s);t=state.tiles[i];b=t.battle
            for k in ('type','enemy','enemy_state','defence','health','frozen','overlay','flag256','flag25e'):item[k]=getattr(b,k)
            item['attack']=b.combat.base_attack;p=b.combat.poison
            item['poison']=[p.current,p.next,p.following,p.active,p.clearing,p.progress]
            item['attack_flag']=t.attack_flag;board.append(item)
        return dict(game=game,board=board,events=adapter.events)

class Original(OriginalBattle):
    def __init__(self):
        super().__init__()
        from unicorn.arm_const import UC_ARM_REG_C1_C0_2,UC_ARM_REG_FPEXC,UC_ARM_REG_FPSCR
        self.u.reg_write(UC_ARM_REG_C1_C0_2,self.u.reg_read(UC_ARM_REG_C1_C0_2)|(15<<20))
        self.u.reg_write(UC_ARM_REG_FPEXC,0x40000000);self.u.reg_write(UC_ARM_REG_FPSCR,0)
        text=(ROOT/'armv7-disassembly.txt').read_text()
        def addr(symbol):
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M)
            assert m,symbol
            return int(m[1],16)
        self.round_boundaries={
            addr('__ZNSt3setIiSt4lessIiESaIiEE4findERKi'):'int_find',
            addr('__ZNSt3setIiSt4lessIiESaIiEE6insertERKi'):'int_insert',
            addr('__ZNSt3setIP4TileSt4lessIS1_ESaIS1_EE4findERKS1_'):'tile_find',
            addr('__ZN4Game16MoveMatchedTilesEv'):'move',
            0x194cec:'unwind',0x194cf4:'unwind',0x194d78:'divide',
            0x194d6c:'guard_acquire',0x194d70:'guard_release'}
        self.round_ints=dict(turn=0xc,base_attack=0xbe7c,direction_bonus=0xbdbc,mode_14ae8=0x14ae8,
            round_kills_165d0=0x165d0,crossing_best=0x16608,crossing_average=0x16604,
            crossing_samples=0x16600,total_165cc=0x165cc,pending_165d4=0x165d4)
        self.round_bytes=dict(flag_5e14=0x5e14,sound_13ec4=0x13ec4,record_14aed=0x14aed)
    def index(self,pointer):
        delta=pointer-self.GAME-0x5e58
        assert delta>=0 and delta%608==0 and delta//608<36,pointer
        return delta//608
    def hook(self,u,address,size,context):
        r=[u.reg_read(reg) for reg in self.regs]
        if address==0xd788:self.current_target=self.index(r[1])
        name=getattr(self,'round_boundaries',{}).get(address)
        if name:
            if name=='int_find':
                key=self.i32(r[1]);values=self.int_sets.setdefault(r[0],set())
                u.reg_write(self.regs[0],r[0]+8 if key in values else r[0]+4)
            elif name=='int_insert':
                self.int_sets.setdefault(r[1],set()).add(self.i32(r[2]))
            elif name=='tile_find':
                key=self.u32(r[1]);u.reg_write(self.regs[0],r[0]+8 if key in self.excluded else r[0]+4)
            elif name=='move':self.adapter.event(12)
            elif name=='divide':u.reg_write(self.regs[0],int(C.c_int32(r[0]).value/C.c_int32(r[1]).value)&0xffffffff)
            elif name=='guard_acquire':u.reg_write(self.regs[0],1)
            elif name=='guard_release':u.mem_write(r[0],b'\1')
            u.reg_write(self.PC,u.reg_read(self.LR));return
        boundary=self.boundaries.get(address)
        if boundary is None:return
        if boundary in ('token','particles','match'):self.current_target=self.index(r[1])
        elif boundary in ('text','uv','freeze'):self.current_target=self.index(r[0])
        if boundary=='label':
            point=r[2];target=-1
            for i in range(36):
                if point==self.GAME+0x5e58+608*i+0x54:target=i;break
            if target<0:assert struct.unpack('<ff',u.mem_read(point,8))==(.5,.5)
            self.adapter.target=target;sp=u.reg_read(self.SP)
            self.adapter.event(8,r[1],C.c_int32(r[3]).value,self.i32(sp),self.i32(sp+4))
            u.reg_write(self.PC,u.reg_read(self.LR));return
        self.adapter.target=self.current_target
        if self.current_target>=0:self.TILE=self.GAME+0x5e58+608*self.current_target
        super().hook(u,address,size,context)
    def run(self,case):
        g=case['game'];u=self.u;old=self.old;self.current_target=-1;self.adapter=Adapter(case)
        self.int_sets={};self.excluded={self.GAME+0x5e58+608*i for i in case['excluded']}
        for k,offset in self.game_ints.items():old.write_i32(self.GAME+offset,g[k])
        for k,offset in self.game_bytes.items():u.mem_write(self.GAME+offset,bytes([g[k]]))
        for k,offset in self.round_ints.items():old.write_i32(self.GAME+offset,g[k])
        for k,offset in self.round_bytes.items():u.mem_write(self.GAME+offset,bytes([g[k]]))
        old.write_i32(self.GAME+self.selected_class,g['class_index'])
        cp=self.GAME+self.class_table+g['class_index']*self.class_stride
        old.write_i32(cp+8,g['race'])
        for i,value in enumerate(g['flaws']):old.write_i32(cp+0x20+4*i,value)
        for i,value in enumerate(g['matched_counts']):old.write_i32(self.GAME+0xbfa4+4*i,value)
        for i,s in enumerate(case['board']):
            base=self.GAME+0x5e58+i*608;block=bytearray(608)
            def wi(offset,value):struct.pack_into('<I',block,offset,value&0xffffffff)
            wi(0x70,self.GAME)
            for k,offset in self.tile_ints.items():wi(offset,s[k])
            for k,offset in self.tile_bytes.items():block[offset]=s[k]
            for offset,value in zip((0x238,0x23c,0x240),s['poison'][:3]):wi(offset,value)
            block[0x244:0x246]=bytes(s['poison'][3:5]);wi(0x248,s['poison'][5])
            struct.pack_into('<ff',block,0x54,*s['center'])
            for k,offset in (('special',0xa0),('x',0x74),('y',0x78)):wi(offset,s[k])
            for k,offset in (('flag231',0x231),('matched',0x84),('attack_flag',0x86)):block[offset]=s[k]
            u.mem_write(base,bytes(block))
        sentinel=self.GAME+0xb3d8;nodes=0x1500100;n=len(case['path'])
        u.mem_write(sentinel,struct.pack('<II',nodes if n else sentinel,nodes+16*(n-1) if n else sentinel))
        for i,index in enumerate(case['path']):
            u.mem_write(nodes+16*i,struct.pack('<III',nodes+16*(i+1) if i+1<n else sentinel,
                nodes+16*(i-1) if i else sentinel,self.GAME+0x5e58+608*index))
        u.reg_write(self.regs[0],self.GAME);u.reg_write(self.SP,0x140fff0);u.reg_write(self.LR,self.STOP|1)
        u.emu_start(0x12189,self.STOP,timeout=300000,count=200000)
        assert u.reg_read(self.PC)==self.STOP
        game=dict(g)
        for k,offset in self.game_ints.items():game[k]=self.i32(self.GAME+offset)
        for k,offset in self.game_bytes.items():game[k]=u.mem_read(self.GAME+offset,1)[0]
        for k,offset in self.round_ints.items():game[k]=self.i32(self.GAME+offset)
        for k,offset in self.round_bytes.items():game[k]=u.mem_read(self.GAME+offset,1)[0]
        game['matched_counts']=[self.i32(self.GAME+0xbfa4+4*i) for i in range(5)]
        board=[]
        for i,s in enumerate(case['board']):
            item=dict(s);base=self.GAME+0x5e58+608*i
            for k,offset in self.tile_ints.items():item[k]=self.i32(base+offset)
            for k,offset in self.tile_bytes.items():item[k]=u.mem_read(base+offset,1)[0]
            p=u.mem_read(base+0x238,20)
            item['poison']=[*struct.unpack_from('<iii',p),p[12],p[13],struct.unpack_from('<I',p,16)[0]]
            item['attack_flag']=u.mem_read(base+0x86,1)[0];board.append(item)
        return dict(game=game,board=board,events=self.adapter.events)

def base_case():
    defaults=initial();game={k:defaults[k] for k in GAME_KEYS}
    game.update(race=0,class_index=0,flaws=[255]*4,turn=6,base_attack=10,direction_bonus=10,
        flag_5e14=1,sound_13ec4=1,record_14aed=0,mode_14ae8=1,round_kills_165d0=0,
        crossing_best=0,crossing_average=0,crossing_samples=0,total_165cc=0,pending_165d4=0,
        matched_counts=[9]*5)
    board=[]
    for i in range(36):
        item={k:defaults[k] for k in TILE_KEYS}
        item.update(type=2,enemy=0,special=3,x=i%6,y=i//6,flag231=0,matched=0,attack_flag=1,
                    center=[(i%6+.5)/6,(i//6+.5)/6])
        board.append(item)
    return dict(game=game,board=board,path=[0,1,2],excluded=[],rolls=[0,9,10,11,50,99,100])

def cases():
    rng=random.Random(0xD1347011)
    for enemy,race,flaw,turn in itertools.product([0,9,14,27,30,32],[0,1,2,5],[0,2,255],[4,5]):
        case=base_case();case['game'].update(race=race,flaws=[flaw,255,255,255],turn=turn,
            poison_amount=2,break_chance=50,coin_on_attack=1)
        case['path']=[14,8,2]
        for i in case['path']:case['board'][i].update(type=1,enemy=enemy,health=15,defence=3)
        yield case
    # Coin-only full board, perimeter, crossing and excluded/chain variants.
    for path in [list(range(36)),[i for i in range(36) if i%6 in (0,5) or i//6 in (0,5)],
                 [0,7,1,6,12,19,13,18,24,31,25,30,32,27,33,28,34,29,35]]:
        for record,kills,average in itertools.product([0,1],[0,3],[0,17]):
            case=base_case();case['path']=path;case['game'].update(record_14aed=record,
                round_kills_165d0=kills,crossing_average=average,crossing_samples=3)
            yield case
    # Synthetic paths isolate each scoring threshold; input adjacency belongs
    # to ProcessTileSelection and is intentionally outside this function test.
    thresholds=json.loads((HERE/'crossing_boundary_paths.json').read_text())
    for path,average,kills in itertools.product(thresholds.values(),[0,17],[0,3]):
        case=base_case();case['path']=path;case['game'].update(record_14aed=1,
            crossing_average=average,crossing_samples=3,round_kills_165d0=kills)
        yield case
    # Special sword chain ending in a distant special-enemy kill.
    case=base_case();case['path']=[0,1,35];case['excluded']=[1]
    case['board'][0].update(type=4,flag231=1)
    case['board'][35].update(type=1,enemy=9,health=1,defence=0)
    yield case
    # Guardians outside the path must resolve in column-first order.
    for chance in [0,50,101]:
        case=base_case();case['game'].update(break_chance=chance,poison_amount=3)
        for index in [5,30]:case['board'][index].update(type=1,enemy=30,health=5,defence=2)
        yield case
    case=base_case();case['game']['flaws']=[2,255,255,255];yield case
    for _ in range(300):
        case=base_case();case['path']=rng.sample(range(36),rng.randrange(3,37))
        case['excluded']=rng.sample(case['path'],rng.randrange(min(4,len(case['path']))+1))
        case['game'].update(race=rng.randrange(10),class_index=rng.randrange(10),
            flaws=[rng.choice([0,2,255]),255,255,255],turn=rng.randrange(1,10),
            base_attack=rng.randrange(30),direction_bonus=rng.randrange(20),
            poison_amount=rng.randrange(5),break_chance=rng.randrange(102),coin_on_attack=rng.randrange(2),
            record_14aed=rng.randrange(2),mode_14ae8=rng.randrange(3),round_kills_165d0=rng.randrange(5),
            crossing_average=rng.randrange(20),crossing_samples=rng.randrange(1,100))
        for item in case['board']:
            item.update(type=rng.randrange(5),enemy=rng.choice([0,9,14,27,30,32]),
                health=rng.randrange(1,40),defence=rng.randrange(10),attack=rng.randrange(20),
                enemy_state=rng.randrange(2),special=rng.choice([0,2,3]),flag231=rng.randrange(2),
                attack_flag=rng.randrange(2),frozen=rng.randrange(2),overlay=rng.randrange(2))
        case['rolls']=[rng.randrange(101) for _ in range(31)];yield case

def main():
    replay='--replay' in sys.argv;native=Native();fixtures=[]
    if replay:
        source=json.loads((HERE/'round_original_results.json').read_text())
        for i,case in enumerate(source):
            got=native.run(case)
            if got!=case['expected']:
                (HERE/'round_failure.json').write_text(json.dumps(dict(index=i,case=case,got=got),indent=2))
                raise AssertionError(f'Round replay mismatch {i}; see round_failure.json')
        count=len(source)
    else:
        original=Original()
        for i,case in enumerate(cases()):
            expected=original.run(case);got=native.run(case)
            if got!=expected:
                (HERE/'round_failure.json').write_text(json.dumps(dict(index=i,case=case,expected=expected,got=got),indent=2))
                raise AssertionError(f'Round mismatch {i}; see round_failure.json')
            fixtures.append({**case,'expected':expected})
        count=len(fixtures)
        (HERE/'round_original_results.json').write_text(json.dumps(fixtures,separators=(',',':'))+'\n')
        data=original.old.bytes_at(0x12188,0x620)
        (HERE/'original_match_tiles.bin').write_bytes(data)
        (HERE/'round_provenance.json').write_text(json.dumps(dict(address='0x12188',size=len(data),
            sha256=hashlib.sha256(data).hexdigest()),indent=2)+'\n')
    result=dict(status='passed',machine=platform.machine(),native_pointer_bytes=C.sizeof(C.c_void_p),
        mode='native fixture replay' if replay else 'original MatchTiles + AttackSkull differential execution',
        path_scenarios=count,scope='Path orchestration through MatchTile/MoveMatchedTiles boundaries; not a complete playable turn',
        adapters=['MatchTile','MoveMatchedTiles','RandI','rendering/audio','std::set storage','exception registration'])
    (HERE/('round_verification_arm64.json' if replay else 'round_verification.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
