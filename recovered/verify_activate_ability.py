#!/usr/bin/env python3
"""Actual Tile::ActivateAbility 0x3f09c vs native dr_activate_ability (recovered_turn),
on the full shared state of verify_attack_all.py.

The whole original function runs from its entry (R0=Tile). MimicDefence,
Resurrect, GenerateStats and UpdateValues run as original code (generation
hooks active); native wires them to dr_mimic_defence, dr_resurrect,
dr_generate_stats and dr_update_generated_values. The 19 ability functions not
yet recovered are recorded as ['ability', enemy_type, tile] and skipped (native:
TurnHooks.ability). UpdateCountdown / UpdateEnemyUV are generation events;
MimicDefence's and Resurrect's own presentation calls are turn events.
"""
import ctypes as C
import json
import random
import re
from verify_turn_small import Original as SmallOriginal, Native as SmallNative, EVENT, MATCH
from verify_attack_all import scenario, ATTACK, MOVE_FN
from verify_turn_begin import CHECK
from verify_generation import Generation, Hooks as GenerationHooks
from verify_path import Path
from verify_stroke import HERE, I32, U8

ENTRY,END=0x3f09c,0x3f25c
ABILITIES={'__ZN4Game12RunAwayEnemyEP4Tile':3,'__ZN4Game11HealOrBlessEP4Tile':4,'__ZN4Game14MakeAcidPotionEP4Tile':6,
    '__ZN4Game11IgniteTilesEP4Tile':7,'__ZN4Game11FreezeTilesEP4Tile':8,'__ZN4Game12ExplodeEnemyEP4Tile':10,
    '__ZN4Game19ConvertSwordToSkullEP4Tile':11,'__ZN4Game9StealGoldEP4Tile':13,'__ZN4Game9JumpEnemyEP4Tile':14,
    '__ZN4Game10StabAttackEP4Tile':16,'__ZN4Game18ConvertRandomTilesEP4Tile':18,'__ZN4Game13TeleportEnemyEv':19,
    '__ZN4Game22BreakRandomShieldSwordEP4Tile':22,'__ZN4Game11LowerSkullsEP4Tile':23,'__ZN4Game13AttractSkullsEP4Tile':24,
    '__ZN4Game20AttractShieldsSwordsEP4Tile':25,'__ZN4Game10ThrowSkullEP4Tile':26,'__ZN4Game14DestroyUpgradeEP4Tile':28,
    '__ZN4Game6FleeUpEP4Tile':31}
ABILITY=C.CFUNCTYPE(None,C.c_void_p,I32,I32)
class TurnHooks(C.Structure):
    _fields_=[('context',C.c_void_p),('event',EVENT),('match_tile',MATCH),('attack_skull',ATTACK),('check_end_game',CHECK),
              ('move_matched_tiles',MOVE_FN),('ability',ABILITY)]

class Original(SmallOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.abilities={};self.ability_visits={};self.activating=False
        for symbol,kind in ABILITIES.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol;self.abilities[int(m[1],16)]=kind
    def hook(self,u,address,size,context):
        if self.activating:
            if ENTRY<=address<END:self.ability_visits[hex(address)]=self.ability_visits.get(hex(address),0)+1
            kind=self.abilities.get(address)
            if kind and ENTRY<u.reg_read(self.LR)&~1<=END:
                assert u.reg_read(self.regs[0])==self.GAME
                self.ability_events.append(['ability',kind,-1 if kind==19 else self.tile_of(u.reg_read(self.regs[1]))])
                u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def activated(self):return [self.u.mem_read(self.tile(i)+0x254,1)[0] for i in range(36)]
    def load(self,c):
        super().load(c)
        for i in range(36):self.u.mem_write(self.tile(i)+0x254,bytes([c['activated'][i]]))
    def activate(self,tile,current):
        self.turn_events=[];self.ability_events=[];self.match_events=[];self.token_events=[];self.path_events=[];self.gen_events=[];self.pending_gen=None
        self.current=current;self.activating=True;self.gen_active=True;u=self.u
        u.reg_write(self.regs[0],self.tile(tile));u.reg_write(self.SP,0x140ff00);u.reg_write(self.LR,self.STOP|1)
        try:
            u.emu_start(ENTRY|1,self.STOP,timeout=0,count=3000000);assert u.reg_read(self.PC)==self.STOP
        finally:self.current=None;self.activating=False;self.gen_active=False
        path,enc=self.path_status(),self.enc_status()
        for t in path['combat']+enc['refill']['combat']:t['enemy_state']=C.c_int32(t['enemy_state']).value   # status reads it unsigned
        return dict(path=path,enc=enc,turn=self.turn_events[:],ability=self.ability_events[:],activated=self.activated())

class Native(SmallNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_turn_native.dylib'))
        self.activate_fn=lib.dr_activate_ability
        self.activate_fn.argtypes=[C.POINTER(Path),C.POINTER(Generation),C.POINTER(U8),C.c_uint32,C.POINTER(TurnHooks),C.POINTER(GenerationHooks)]
        self.activate_fn.restype=None
        def ability(_,kind,tile):self.ability_events.append(['ability',kind,tile])
        self.ability_cb=ABILITY(ability)
        self.activate_hooks=TurnHooks(None,self.turn_cb[0],self.turn_cb[1],ATTACK(0),CHECK(0),MOVE_FN(0),self.ability_cb)
    def load(self,c):
        super().load(c);self.flags_254=(U8*36)(*c['activated'])
    def activate(self,tile,current):
        self.turn_events=[];self.ability_events=[];self.match_events=[];self.token_events=[];self.path_events=[];self.gen_events=[]
        self.activate_fn(C.byref(self.path_state),C.byref(self.gen),self.flags_254,tile,C.byref(self.activate_hooks),C.byref(self.gen_hooks))
        return dict(path=self.path_status(),enc=self.enc_status(),turn=self.turn_events[:],ability=self.ability_events[:],activated=list(self.flags_254))

def main():
    old,new=Original(),Native();rng=random.Random(0x3F09C);counts={'single':0,'board':0};kinds={}
    def compare(c,tile,group):
        enemy=c['board'][tile]['enemy'];current='mimic' if enemy==17 else 'resurrect' if enemy==32 else None
        a,b=old.activate(tile,current),new.activate(tile,current)
        if a!=b:
            (HERE/'activate_ability_failure.json').write_text(json.dumps(dict(case=c,tile=tile,original=a,native=b),indent=2))
            raise AssertionError('activate_ability_failure.json')
        counts[group]+=1
        key='%d:%s'%(enemy,'skip' if a['activated'][tile] and not (a['ability'] or a['turn'] or a['enc']['events']) else
                     'ability' if a['ability'] else 'turn' if a['turn'] else 'gen' if a['enc']['events'] else 'none')
        kinds[key]=kinds.get(key,0)+1
    def case():
        c,_=scenario(rng);c['path_state']['turn']=rng.choice([1,50,100,499,rng.randrange(1,2000)]);c['match']['spawn_enabled_14ae0']=rng.randrange(5)
        c['activated']=[int(rng.random()<.15) for _ in range(36)]
        for i,t in enumerate(c['board']):
            t['enemy_state']=rng.choice([0,1,1,2,5,-1,rng.randrange(-3,9)]);c['combat'][i]['flag25e']=rng.randrange(2)
        return c
    for enemy in range(35):
        for _ in range(8):
            c=case();tile=rng.randrange(36);c['board'][tile].update(type=1,enemy=enemy);old.load(c);new.load(c);compare(c,tile,'single')
    for _ in range(40):
        c=case()
        for t in c['board']:
            if t['type']==1:t['enemy']=rng.choice([3,4,10,17,19,28,32,32,rng.randrange(0,35)])
        old.load(c);new.load(c)
        for x in range(6):
            for y in range(6):
                i=y*6+x
                if c['board'][i]['type']==1 and c['board'][i]['enemy']!=0:compare(c,i,'board')
    assert all(hex(a) in old.ability_visits for a in (0x3f0be,0x3f118,0x3f15e,0x3f1bc,0x3f202,0x3f210,0x3f22e,0x3f236,0x3f256,0x3f196))
    report=dict(status='passed',comparisons=sum(counts.values()),by_group=counts,outcomes=kinds,
                function=dict(symbol='__ZN4Tile15ActivateAbilityEv',address=hex(ENTRY),native='dr_activate_ability'),
                original='Actual ActivateAbility with original MimicDefence, Resurrect, GenerateStats (+RNG), UpdateValues',
                boundaries=['19 unrecovered ability functions recorded (TurnHooks.ability)','UpdateCountdown/UpdateEnemyUV and MimicDefence/Resurrect presentation adapted'],
                scope='Full shared board incl. enemy types 0..34, enemy_state, flag_25e, Tile+0x254, generation extras and RNG',branch_visits=old.ability_visits)
    (HERE/'activate_ability_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='branch_visits'}))

if __name__=='__main__':main()
