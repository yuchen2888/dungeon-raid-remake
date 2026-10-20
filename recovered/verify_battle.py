#!/usr/bin/env python3
"""Differential combat verification with explicit subsystem boundaries.

Original attack, poison, freeze, phylactery and reward algorithm instructions run.
Graphics/audio calls, MatchTile, RandI and list output storage are adapters. They
are not verified here. We compare state, return value and ordered adapter calls.
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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
from verify_original import Poison, ClassState, Context, Tile as CombatTile

class Point(C.Structure): _fields_ = [('x', C.c_float), ('y', C.c_float)]
class BattleTile(C.Structure):
    _fields_ = [('combat', CombatTile)] + [(k, C.c_int32) for k in
        ('type', 'enemy', 'enemy_state', 'defence', 'health')] + [('center', Point)] + [
        (k, C.c_uint8) for k in ('frozen', 'overlay', 'flag256', 'flag25e')]
class BattleGame(C.Structure):
    _fields_ = [('context', Context)] + [(k, C.c_int32) for k in
        ('kills_a', 'kills_b', 'killed_attack', 'break_chance', 'poison_amount')] + [
        ('coin_on_attack', C.c_uint8), ('poison_sound', C.c_uint8),
        ('lich_progress', C.c_int32), ('lich_transition', C.c_int32)]
RANDOM = C.CFUNCTYPE(C.c_int32, C.c_void_p, C.c_int32, C.c_int32, C.c_int32)
EVENT = C.CFUNCTYPE(None, C.c_void_p, C.c_int32, C.c_int32, C.c_int32, C.c_int32, C.c_int32)
class Hooks(C.Structure):
    _fields_ = [('context', C.c_void_p), ('random', RANDOM), ('event', EVENT)]

def initial(**overrides):
    state = dict(attack=11, poison=[0,0,0,0,1,0x3f000000], type=1, enemy=0,
        enemy_state=0, defence=2, health=20, center=[0.25,0.75], frozen=0,
        overlay=0, flag256=1, flag25e=0, race=0, class_index=0,
        kills_a=4, kills_b=7, killed_attack=15, break_chance=0,
        poison_amount=0, coin_on_attack=0, poison_sound=0,
        lich_progress=0x3f000000, lich_transition=0)
    state.update(overrides)
    return state

class Adapter:
    def __init__(self, case):
        self.events = []; self.rolls = case.get('rolls', [0,100,9,10,11,50]); self.cursor = 0
    def random(self, low, high, stream):
        lo, hi = min(low,high), max(low,high)
        value = lo + self.rolls[self.cursor % len(self.rolls)] % (hi-lo+1)
        self.cursor += 1
        self.events.append([0,low,high,stream,value])
        return value
    def event(self, kind, a=0,b=0,c=0,d=0): self.events.append([kind,a,b,c,d])

class Native:
    def __init__(self):
        self.lib = C.CDLL(str(HERE / 'recovered_battle_native.dylib'))
        self.lib.dr_attack_skull.argtypes, self.lib.dr_attack_skull.restype = [C.POINTER(BattleGame),C.POINTER(BattleTile),C.c_int32,C.c_bool,C.POINTER(Hooks)],C.c_bool
        self.lib.dr_make_phylactery.argtypes, self.lib.dr_make_phylactery.restype = [C.POINTER(BattleTile),C.POINTER(Hooks)],None
        self.lib.dr_set_freeze.argtypes, self.lib.dr_set_freeze.restype = [C.POINTER(BattleTile),C.c_bool,C.POINTER(Hooks)],None
        self.lib.dr_get_rewards.argtypes, self.lib.dr_get_rewards.restype = [C.c_int32,C.POINTER(Hooks)],None
    def run(self, case):
        s = case['before']; adapter = Adapter(case)
        character = ClassState(s['race']); game = BattleGame()
        game.context = Context(C.pointer(character))
        for key in ('kills_a','kills_b','killed_attack','break_chance','poison_amount',
                    'coin_on_attack','poison_sound','lich_progress','lich_transition'):
            setattr(game,key,s[key])
        tile = BattleTile(); tile.combat = CombatTile(s['attack'],Poison(*s['poison']),C.pointer(game.context))
        for key in ('type','enemy','enemy_state','defence','health','frozen','overlay','flag256','flag25e'):
            setattr(tile,key,s[key])
        tile.center = Point(*s['center'])
        random_callback = RANDOM(lambda _,lo,hi,stream: adapter.random(lo,hi,stream))
        event_callback = EVENT(lambda _,kind,a,b,c,d: adapter.event(kind,a,b,c,d))
        hooks = Hooks(None,random_callback,event_callback)
        op = case['op']; result = None
        if op == 'attack': result = int(self.lib.dr_attack_skull(C.byref(game),C.byref(tile),case['incoming'],case['effects'],C.byref(hooks)))
        elif op == 'phylactery': self.lib.dr_make_phylactery(C.byref(tile),C.byref(hooks))
        elif op == 'freeze': self.lib.dr_set_freeze(C.byref(tile),case['visible'],C.byref(hooks))
        elif op == 'rewards': self.lib.dr_get_rewards(s['enemy'],C.byref(hooks))
        else: raise ValueError(op)
        after = dict(s)
        for key in ('kills_a','kills_b','killed_attack','break_chance','poison_amount',
                    'coin_on_attack','poison_sound','lich_progress','lich_transition'):
            after[key] = getattr(game,key)
        for key in ('type','enemy','enemy_state','defence','health','frozen','overlay','flag256','flag25e'):
            after[key] = getattr(tile,key)
        p = tile.combat.poison
        after['attack'] = tile.combat.base_attack
        after['poison'] = [p.current,p.next,p.following,p.active,p.clearing,p.progress]
        return dict(result=result,after=after,events=adapter.events)

class OriginalBattle:
    def __init__(self):
        from verify_original import Original,TILE,GAME,STOP,CLASS_TABLE,CLASS_STRIDE,SELECTED_CLASS
        from unicorn import UC_HOOK_CODE
        from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_LR,UC_ARM_REG_PC,UC_ARM_REG_SP
        self.old = Original(); self.u = self.old.uc
        self.TILE,self.GAME,self.STOP = TILE,GAME,STOP
        self.class_table,self.class_stride,self.selected_class = CLASS_TABLE,CLASS_STRIDE,SELECTED_CLASS
        self.regs = (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)
        self.LR,self.PC,self.SP = UC_ARM_REG_LR,UC_ARM_REG_PC,UC_ARM_REG_SP
        self.u.mem_map(0x1400000,0x10000)
        self.u.mem_map(0x1500000,0x1000)
        text = (ROOT/'armv7-disassembly.txt').read_text()
        def address(symbol):
            match = re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M)
            assert match,symbol
            return int(match[1],16)
        symbols = {
            'token':'__ZN4Game8AddTokenEP4Tile8TileTypebPK8GLfloat2',
            'particles':'__ZN4Game12AddParticlesEP4Tile12ParticleType',
            'text':'__ZN4Tile10UpdateTextEbbb','match':'__ZN4Game9MatchTileEP4Tile8TileType',
            'uv':'__ZN4Tile13UpdateEnemyUVEv',
            'flare':'__ZN4Game8AddFlareE9FlareType8GLfloat2RK9GLcolour4',
            'sound':'__ZN4Game10QueueSoundE5Sound',
            'label':'__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif',
            'freeze':'__ZN4Tile19SetFreezeVisibilityEb',
            'achievement':'__ZN4Game16QueueAchievementE11Achievementf',
            'random':'__Z5RandIii8RandType',
            'reward':'__ZNSt4listI8TileTypeSaIS0_EE9push_backERKS0_',
            'quad_uv':'__ZN4Quad5SetUVERK8GLfloat2S2_',
            'quad_size':'__ZN4Quad7SetSizeERK8GLfloat2',
            'quad_alpha':'__ZN4Quad8SetAlphaEh',
        }
        self.addresses = {op:address(symbol) for op,symbol in symbols.items()}
        self.addresses.update(attack=0xd788,phylactery=0x1a110,rewards=0x3d4d0)
        self.boundaries = {self.addresses[name]:name for name in symbols}
        self.u.hook_add(UC_HOOK_CODE,self.hook)
        self.game_ints = dict(kills_a=0x165b4,kills_b=0x15548,killed_attack=0x164ac,
            break_chance=0xbdcc,poison_amount=0xbe5c,lich_progress=0xbd90,lich_transition=0xbd94)
        self.game_bytes = dict(coin_on_attack=0xbfbb,poison_sound=0x13ec5)
        self.tile_ints = dict(attack=0xa4,type=0x9c,enemy=0x24c,enemy_state=0x250,defence=0xa8,health=0xac)
        self.tile_bytes = dict(frozen=0x255,overlay=0x1b0,flag256=0x256,flag25e=0x25e)
    def i32(self,address): return struct.unpack('<i',self.u.mem_read(address,4))[0]
    def u32(self,address): return struct.unpack('<I',self.u.mem_read(address,4))[0]
    def hook(self,u,address,_size,_context):
        name = self.boundaries.get(address)
        if name is None:return
        r = [u.reg_read(reg) for reg in self.regs]; sp = u.reg_read(self.SP)
        signed = lambda value:C.c_int32(value).value
        e = self.adapter.event
        if name == 'freeze':
            e(9,r[1]);return # Execute original state updates; intercept Quad rendering only.
        if name == 'random':
            value = self.adapter.random(*map(signed,r[:3]))
            u.reg_write(self.regs[0],value&0xffffffff)
        elif name == 'token': e(1,r[2],r[3],self.u32(sp))
        elif name == 'particles':e(2,r[2])
        elif name == 'text':e(3,r[1],r[2],r[3])
        elif name == 'match':e(4,r[2])
        elif name == 'uv':e(5)
        elif name == 'flare':
            assert struct.pack('<II',r[2],r[3]) == bytes(u.mem_read(self.TILE+0x54,8))
            e(6,r[1],self.i32(self.u32(sp)))
        elif name == 'sound':e(7,r[1])
        elif name == 'label':
            assert bytes(u.mem_read(r[2],8)) == bytes(u.mem_read(self.TILE+0x54,8))
            e(8,r[1],signed(r[3]),self.i32(sp),self.i32(sp+4))
        elif name == 'achievement':e(10,r[1],signed(r[2]))
        elif name == 'reward':e(11,self.i32(r[1]))
        elif name.startswith('quad_'): pass
        else:raise ValueError(name)
        u.reg_write(self.PC,u.reg_read(self.LR))
    def run(self,case):
        s=case['before'];self.adapter=Adapter(case);u=self.u;old=self.old
        u.mem_write(self.TILE,bytes(608))
        old.write_i32(self.TILE+0x70,self.GAME)
        old.write_i32(self.GAME+self.selected_class,s['class_index'])
        old.write_i32(self.GAME+self.class_table+s['class_index']*self.class_stride+8,s['race'])
        for key,offset in self.game_ints.items():old.write_i32(self.GAME+offset,s[key])
        for key,offset in self.game_bytes.items():u.mem_write(self.GAME+offset,bytes([s[key]]))
        for key,offset in self.tile_ints.items():old.write_i32(self.TILE+offset,s[key])
        for key,offset in self.tile_bytes.items():u.mem_write(self.TILE+offset,bytes([s[key]]))
        for offset,value in zip((0x238,0x23c,0x240),s['poison'][:3]):old.write_i32(self.TILE+offset,value)
        u.mem_write(self.TILE+0x244,bytes(s['poison'][3:5]))
        old.write_i32(self.TILE+0x248,s['poison'][5])
        u.mem_write(self.TILE+0x54,struct.pack('<ff',*s['center']))
        op=case['op']
        if op=='attack':args=(self.GAME,self.TILE,case['incoming'],int(case['effects']))
        elif op=='phylactery':args=(self.TILE,0,0,0)
        elif op=='freeze':args=(self.TILE,int(case['visible']),0,0)
        elif op=='rewards':args=(self.TILE,0x1500000,0,0)
        else:raise ValueError(op)
        for reg,value in zip(self.regs,args):u.reg_write(reg,value&0xffffffff)
        u.reg_write(self.SP,0x140fff0);u.reg_write(self.LR,self.STOP|1)
        u.emu_start(self.addresses[op]|1,self.STOP,timeout=0,count=10000)
        assert u.reg_read(self.PC)==self.STOP
        result=u.reg_read(self.regs[0]) if op=='attack' else None
        after=dict(s)
        for key,offset in self.game_ints.items():after[key]=self.i32(self.GAME+offset)
        for key,offset in self.game_bytes.items():after[key]=u.mem_read(self.GAME+offset,1)[0]
        for key,offset in self.tile_ints.items():after[key]=self.i32(self.TILE+offset)
        for key,offset in self.tile_bytes.items():after[key]=u.mem_read(self.TILE+offset,1)[0]
        after['poison']=list(old.state())
        return dict(result=result,after=after,events=self.adapter.events)

def cases():
    rng=random.Random(0xD134BA77)
    for health,defence,incoming,enemy,effects,race,poison,chance in itertools.product(
        [1,5,20],[0,2,7],[0,1,5,12],[0,9,32],[False,True],[1,5],[0,3],[0,50,101]):
        yield dict(op='attack',incoming=incoming,effects=effects,
                   before=initial(health=health,defence=defence,enemy=enemy,race=race,
                       poison_amount=poison,break_chance=chance,coin_on_attack=1,
                       class_index=rng.randrange(10)))
    for _ in range(2000):
        state=initial(attack=rng.randrange(40),health=rng.randrange(1,100),defence=rng.randrange(20),
            enemy=rng.randrange(36),enemy_state=rng.randrange(2),race=rng.randrange(10),
            class_index=rng.randrange(10),break_chance=rng.randrange(102),poison_amount=rng.randrange(6),
            coin_on_attack=rng.randrange(2),poison_sound=rng.randrange(2),frozen=rng.randrange(2),
            overlay=rng.randrange(2),flag256=rng.randrange(2),flag25e=rng.randrange(2),
            poison=[rng.randrange(8),rng.randrange(8),rng.randrange(8),rng.randrange(2),rng.randrange(2),0x3f000000])
        yield dict(op='attack',before=state,incoming=rng.randrange(-2,80),effects=bool(rng.randrange(2)),rolls=[rng.randrange(101) for _ in range(17)])
    for race in range(10):
        for effects in (False,True):
            yield dict(op='attack',before=initial(enemy=32,enemy_state=1,race=race,poison_amount=5,coin_on_attack=1),incoming=99,effects=effects)
    for visible,flag256,overlay in itertools.product([False,True],[0,1],[0,1]):
        yield dict(op='freeze',before=initial(flag256=flag256,overlay=overlay),visible=visible)
    for _ in range(60):
        yield dict(op='phylactery',before=initial(attack=rng.randrange(40),defence=rng.randrange(20),
            health=rng.randrange(1,100),enemy=32,enemy_state=rng.randrange(2),
            poison=[rng.randrange(20),rng.randrange(20),rng.randrange(20),rng.randrange(2),rng.randrange(2),rng.getrandbits(32)]))
    for enemy,seed in itertools.product(range(40),range(32)):
        yield dict(op='rewards',before=initial(enemy=enemy),rolls=[seed,seed*7,seed*13])

def main():
    replay='--replay' in sys.argv;native=Native();fixtures=[];counts={}
    if replay:
        source=json.loads((HERE/'battle_original_results.json').read_text())
        for i,case in enumerate(source):
            got=native.run(case)
            assert got==case['expected'],(i,case,got)
            counts[case['op']]=counts.get(case['op'],0)+1
    else:
        original=OriginalBattle()
        def verify(case):
            expected,got=original.run(case),native.run(case)
            assert got==expected,(len(fixtures),case,'original',expected,'recovered',got)
            counts[case['op']]=counts.get(case['op'],0)+1
            fixtures.append({**case,'expected':expected})
            return expected
        for case in cases():verify(case)
        # Repeated attacks carry forward poison, armour, sound flags, counters and
        # freeze state. Replace the target after a kill or phylactery transition.
        rng=random.Random(0xD1345E0)
        for _ in range(100):
            state=initial(race=rng.choice([0,1,5]),poison_amount=2,break_chance=50,
                          health=100,defence=8,coin_on_attack=1)
            for step in range(12):
                case=dict(op='attack',before=state,incoming=rng.randrange(1,20),effects=True,
                          rolls=[rng.randrange(101) for _ in range(9)])
                result=verify(case);state=result['after']
                if result['result'] or state['enemy_state']:
                    state={**state,'health':100,'defence':8,'enemy_state':0,'enemy':rng.choice([0,9,32])}
        (HERE/'battle_original_results.json').write_text(json.dumps(fixtures,separators=(',',':'))+'\n')
        sizes=dict(attack=0x228,phylactery=0x30,freeze=0x70,rewards=0x244)
        provenance=[]
        for name in sizes:
            address=original.addresses[name];data=original.old.bytes_at(address,sizes[name])
            (HERE/('original_battle_'+name+'.bin')).write_bytes(data)
            provenance.append(dict(name=name,address=hex(address),size=len(data),sha256=hashlib.sha256(data).hexdigest()))
        (HERE/'battle_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    result=dict(status='passed',machine=platform.machine(),native_pointer_bytes=C.sizeof(C.c_void_p),
        mode='native fixture replay' if replay else 'original ARMv7 differential execution with explicit adapters',
        checks=counts,total_checks=sum(counts.values()),continuous_attack_steps=1200,
        scope='AttackSkull, MakePhylactery, SetFreezeVisibility state, GetRewards algorithm. MatchTile, RandI, rendering/audio and list output storage are adapter boundaries, not verified implementations.')
    (HERE/('battle_verification_arm64.json' if replay else 'battle_verification.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
