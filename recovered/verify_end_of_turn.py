#!/usr/bin/env python3
"""Whole original Game::EndOfTurn 0x13574 vs native dr_end_of_turn (recovered_turn).

The original runs from its entry (R0=Game) until it returns. Everything it
calls runs as original code except presentation and the boundaries below:
CheckEndGame (incl. GetScore and the end-of-game bookkeeping, as in
verify_game_over.py), GetEnemyCount, Skill::Deactivate, SetFreeze/
SetFlameVisibility, AttackSkull (+MatchTile/tokens), GetPoison, MatchTile,
ProcessCripples, ActivateAbility (+MimicDefence/Resurrect/GenerateStats/
UpdateValues) and MoveMatchedTiles (+RandomiseTile/generation/encounters).
Recorded instead: the 19 ability functions not yet recovered
(['ability', enemy_type, tile]), Game::SerialiseState, HelpMenu, Interface,
Arrow, labels/flares/particles/sounds/achievements/text and score screens.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_turn_finish import Original as FinishOriginal, Native as FinishNative, TurnFinishFlags
from verify_turn_begin import (Original as BeginOriginal, Native as BeginNative, SkillSlots, TurnFlags, FLAG_BYTES)
from verify_activate_ability import ABILITIES, ABILITY, TurnHooks, EVENT, MATCH
from verify_abilities import AbilityMixin, SWAP_FN, canonical, follow_swaps, push_token_hook
from verify_turn_burn import FLAME, FLAME_END, FREEZE, FREEZE_END, QUAD_SYMBOLS, TILES, STRIDE, RESTING
from verify_turn_regen import TARGET, INTERFACE, HEALTH_QUAD
from verify_turn_small import FUNCTIONS as SMALL
from verify_attack_all import scenario, ATTACK, MOVE_FN
from verify_turn_begin import CHECK
from verify_resources import Resource
from verify_path import Path
from verify_generation import Generation, Hooks as GenerationHooks
from verify_game_over import EndGameState
from verify_rune import Rune
from verify_stroke import HERE, I32, U8

ENTRY,EPILOGUE=0x13574,0x13e04
REGEN=0xbe70
ACTIVATE,ACTIVATE_END,AFTER_ACTIVATE=0x3f09c,0x3f25c,0x13b2a
SEGMENTS=dict(begin=[(0x13574,0x13710)],burn=[(0x13710,0x13910),(0x13d64,0x13d88)],regen=[(0x13910,0x13a1c)],
              poison=[(0x13a1c,0x13af2),(0x13d88,0x13daa)],abilities=[(0x13cda,0x13d12),(0x13af2,0x13b3c),(0x13daa,0x13dc8)],
              finish=[(0x13b3c,0x13cda),(0x13d12,0x13d64),(0x13dc8,0x13e04)])
SYMBOLS={'__ZN4Game10QueueSoundE5Sound':'sound','__ZN4Tile10UpdateTextEbbb':'text','__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif':'label',
         '__ZN4Game8AddFlareE9FlareType8GLfloat2RK9GLcolour4':'flare','__ZN4Game16QueueAchievementE11Achievementf':'achievement',
         '__ZN4Game12AddParticlesEP4Tile12ParticleType':'particles','__ZN4Tile19SetFreezeVisibilityEb':'freeze',
         '__ZN9Interface15UpdateHealthBarER4Quadi':'bar','__ZN9Interface9GetTargetE8TileType':'target',
         '__ZN9Interface17GetPoisonPositionEv':'poison_position','__ZN9Interface12UpdateSkillsEv':'update_skills',
         '__ZN5Arrow9SetColourEjjj':'arrow','__ZN4Game12CheckEndGameEv':'check_end','__ZN8HelpMenu10InitialiseEffff8HelpType':'help',
         '__ZN4Game14SerialiseStateEv':'serialise','__ZN4Game16MoveMatchedTilesEv':'move'}
class EndOfTurnState(C.Structure):
    _fields_=[('skills',C.POINTER(SkillSlots)),('flags',C.POINTER(TurnFlags)),('rune',C.POINTER(Rune)),('counterattack',C.POINTER(U8)),('end',C.POINTER(EndGameState)),
              ('finish',C.POINTER(TurnFinishFlags)),('activated',C.POINTER(U8)),('regen',I32)]

def segment_of(lr):
    for name,ranges in SEGMENTS.items():
        if any(a<lr<=b for a,b in ranges):return name
    return None

class Original(AbilityMixin,FinishOriginal):
    ranges,entry,stop_at,extra_stops=[(ENTRY,EPILOGUE)],ENTRY,-1,()   # attack/move switching for any EndOfTurn call site; run to return
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.eot_calls={};self.abilities={};self.quads=set()
        self.eot_visits={};self.eot_running=False;self.small=None;self.ability_setup()
        self.ranges=[(ENTRY,EPILOGUE)]+self.ability_ranges()   # attack/move switching also inside recovered abilities
        address=lambda s:int(re.search(r'^'+re.escape(s)+r':\n\s*([0-9a-f]+):',text,re.M)[1],16)
        for symbol,name in SYMBOLS.items():self.eot_calls[address(symbol)]=name
        for symbol,kind in ABILITIES.items():self.abilities[address(symbol)]=kind
        for symbol in QUAD_SYMBOLS:self.quads.add(address(symbol))
        self.alpha=address('__ZN4Quad8SetAlphaEh')
    def tile_of(self,address,offset=0):
        i,rest=divmod(address-self.GAME-TILES-offset,STRIDE);assert rest==0 and 0<=i<36,hex(address);return i
    def center_tile(self,x,y):
        t=[i for i in range(36) if struct.unpack('<II',self.u.mem_read(self.tile(i)+0x54,8))==(x,y)];return t[0] if len(t)==1 else t
    def resting_index(self,x,y):
        t=[i for i in range(36) if struct.unpack('<II',self.u.mem_read(self.GAME+RESTING+8*i,8))==(x,y)];return t[0] if len(t)==1 else t
    def hook(self,u,address,size,context):
        if self.eot_running and self.ability_hook(u,address,self.end_events):return   # recovered abilities run as original code
        if self.eot_running and self.mode is None:
            if ENTRY<=address<EPILOGUE:self.eot_visits[hex(address)]=self.eot_visits.get(hex(address),0)+1
            if address==ACTIVATE:self.gen_active=True
            elif address==AFTER_ACTIVATE:self.gen_active=False
            lr=u.reg_read(self.LR)&~1;seg=segment_of(lr)
            small=[k for k,(a,b) in SMALL.items() if a<lr<=b]
            if address in self.quads and (FLAME<lr<=FLAME_END or FREEZE<lr<=FREEZE_END):
                if address==self.alpha and FLAME<lr<=FLAME_END:self.end_events.append(['flame_overlay',self.tile_of(u.reg_read(self.regs[0]),0x140)])
                return   # overlay quad calls run as original code
            kind=self.abilities.get(address)
            if kind and ACTIVATE<lr<=ACTIVATE_END:
                assert u.reg_read(self.regs[0])==self.GAME
                self.end_events.append(['ability',kind,-1 if kind==19 else self.tile_of(u.reg_read(self.regs[1]))])
                u.reg_write(self.PC,u.reg_read(self.LR));return
            name=self.eot_calls.get(address)
            if name and (seg or small):
                r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value;sp=u.reg_read(self.SP);e=None
                if name in ('check_end','move'):return super().hook(u,address,size,context)   # recorded by verify_turn_finish's hook; original runs
                if name=='freeze':self.end_events.append(['freeze',self.tile_of(r[0]),r[1]&0xff]);return super().hook(u,address,size,context)
                if name=='sound':e=['sound',r[1]]
                elif name=='text':e=['text',self.tile_of(r[0]),r[1]&0xff,r[2]&0xff,r[3]&0xff]
                elif name=='achievement':e=['achievement',r[1],s(r[2])]
                elif name=='particles':e=['particles',self.tile_of(r[1]),r[2]]
                elif name=='label':
                    tail=[r[1],s(r[3]),s(self.read(sp)),s(self.read(sp+4))]
                    if seg in ('burn','poison'):
                        o=r[2]-self.GAME-RESTING;assert o%8==0 and 0<=o//8<36;e=['label_rest',o//8,*tail]
                    elif seg=='regen':e=['label','target' if r[2]==TARGET else 'poison' if r[2]==getattr(self,'poison_out',None) else hex(r[2]),*tail]
                    else:e=['label',self.tile_of(r[2],0x54),*tail]
                elif name=='flare':
                    colour=s(self.read(self.read(sp)))
                    e=['flare_rest',self.resting_index(r[2],r[3]),r[1],colour] if seg=='burn' else ['flare',self.center_tile(r[2],r[3]),r[1],colour]
                elif name=='bar':assert r[0]==self.GAME+INTERFACE and r[1]==self.GAME+HEALTH_QUAD;e=['health_bar',s(r[2])]
                elif name=='target':assert r[0]==self.GAME+INTERFACE and r[1]==0;u.reg_write(self.regs[0],TARGET)
                elif name=='poison_position':assert r[1]==self.GAME+INTERFACE;self.poison_out=r[0]
                elif name=='update_skills':assert r[0]==self.GAME+0x4cdc;e=['update_skills']
                elif name=='arrow':assert r[0]==self.GAME+0x3658;e=['arrow',r[1],r[2],r[3]]
                elif name=='help':assert r[0]==self.GAME+0x10298;e=['help',self.center_tile(r[1],r[2]),self.read(sp+4),r[3],self.read(sp)]
                else:assert r[0]==self.GAME;e=['serialise_state']
                if e:self.end_events.append(e)
                u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def load(self,c):
        super().load(c)
        for k,o in FLAG_BYTES.items():self.u.mem_write(self.GAME+o,bytes([c['flags'][k]]))
        self.u.mem_write(self.GAME+0x165b8,bytes(c['flags']['b165b8']));self.u.mem_write(self.GAME+0xbe74,bytes(c['flags']['prev_be74']))
        self.u.mem_write(self.GAME+0xbe78,bytes(c['flags']['next_be78']))
        for i in range(4):self.u.mem_write(0x1700000+0x100*i+0x80,bytes([c['skill_active'][i]]))
        for i in range(36):self.u.mem_write(self.tile(i)+0x254,bytes([c['activated'][i]]))
        self.write(self.GAME+REGEN,c['regen'])
    def end_of_turn(self):
        self.all_events=[];self.enc_events=[];self.gen_events=[];self.refill_events=[];self.path_events=[]
        self.match_events=[];self.token_events=[];self.motion_events=[];self.end_events=[];self.int_sets={};self.mode=None;self.pending_gen=None
        self.ability_stack=[]
        u=self.u;u.reg_write(self.regs[0],self.GAME);u.reg_write(self.SP,0x140ff00);u.reg_write(self.LR,self.STOP|1)
        self.eot_running=self.all_running=self.recording=True
        try:
            u.emu_start(ENTRY|1,self.STOP,timeout=0,count=50000000);assert u.reg_read(self.PC)==self.STOP and self.mode is None,hex(u.reg_read(self.PC))
        finally:
            self.eot_running=self.all_running=self.recording=self.gen_active=False
            self.path_active=self.refill_active=self.enc_active=False
        path,enc=self.path_status(),self.enc_status()
        for t in path['combat']+enc['refill']['combat']:t['enemy_state']=C.c_int32(t['enemy_state']).value
        base=self.GAME+0x15564+388*self.read(self.GAME+0x1648c)
        return dict(path=path,enc=enc,all=self.all_events[:],events=self.end_events[:],begin=BeginOriginal.begin_state(self),fin=self.finish_state(),
                    activated=[self.u.mem_read(self.tile(i)+0x254,1)[0] for i in range(36)],
                    flame=[[self.u.mem_read(self.tile(i)+0x257,1)[0],C.c_int32(self.read(self.tile(i)+0x258)).value] for i in range(36)],
                    poison=C.c_int32(self.read(self.GAME+0x15540)).value,
                    cls={k:self.read(base+o)&0xffffffff for k,o in dict(games_played=0x58,enemies_killed=0x5c).items()})

class Native(FinishNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_turn_native.dylib'))
        self.eot_fn=lib.dr_end_of_turn
        self.eot_fn.argtypes=[C.POINTER(Resource),C.POINTER(Path),C.POINTER(Generation),C.POINTER(EndOfTurnState),C.POINTER(TurnHooks),C.POINTER(GenerationHooks)]
        self.eot_fn.restype=None
        def event(_,p):self.end_events.append(canonical(p.contents))
        def match(_,tile,reward):self.match_fn(C.byref(self.m),tile,reward,C.byref(self.match_hooks))
        def check(_):
            self.end_events.append(['check_end']);return self.check_fn(C.byref(self.r),C.byref(self.flags),C.byref(self.end_hooks))
        def move(_):
            self.end_events.append(['move']);self.refill_lib.dr_move_matched_tiles(C.byref(self.refill),C.byref(self.refill_hooks))
        def ability(_,kind,tile):self.end_events.append(['ability',kind,tile])
        def swap(_,x1,y1,x2,y2):self.refill_lib.dr_swap_tiles(C.byref(self.refill),x1,y1,x2,y2,C.byref(self.refill_hooks))
        self.eot_cb=(EVENT(event),MATCH(match),CHECK(check),MOVE_FN(move),ABILITY(ability),SWAP_FN(swap))
        self.token_cb=push_token_hook(self)
        self.eot_hooks=TurnHooks(None,self.eot_cb[0],self.eot_cb[1],self.cb[1],self.eot_cb[2],self.eot_cb[3],self.eot_cb[4],self.eot_cb[5],*self.token_cb)
        types=list(self.over_fn.argtypes);types[3]=C.POINTER(SkillSlots);self.over_fn.argtypes=types
    def load(self,c):
        super().load(c)
        self.skills=SkillSlots((I32*4)(*c['skill_id']),(I32*4)(*c['skill_level']),(U8*4)(*c['skill_active']))
        f=c['flags'];self.turn_flags=TurnFlags(f['b15561'],f['b15562'],(U8*5)(*f['b165b8']),f['arrow_hold_16492'],
            f['prev_164a7'],f['next_164a8'],(U8*4)(*f['next_be78']),f['next_coin_bfbc'])
        self.counter=U8(f['counterattack']);self.flags_254=(U8*36)(*c['activated']);self.rune=Rune();self.rune.enabled=f['arrow_pending_16491']
        self.state.selection.double_damage=f['prev_be74'][0]
        self.p.double_upgrade,self.p.double_healing,self.p.double_gold=f['prev_be74'][1:]
        follow_swaps(self)   # activated[] moves with tile swaps
        self.eot_state=EndOfTurnState(C.pointer(self.skills),C.pointer(self.turn_flags),C.pointer(self.rune),C.pointer(self.counter),C.pointer(self.flags),
                                  C.pointer(self.fin_flags),C.cast(self.flags_254,C.POINTER(U8)),c['regen'])
    def end_of_turn(self):
        self.all_events=[];self.enc_events=[];self.gen_events=[];self.refill_events=[];self.path_events=[]
        self.match_events=[];self.token_events=[];self.motion_events=[];self.end_events=[]
        self.eot_fn(C.byref(self.r),C.byref(self.path_state),C.byref(self.gen),C.byref(self.eot_state),C.byref(self.eot_hooks),C.byref(self.gen_hooks))
        return dict(path=self.path_status(),enc=self.enc_status(),all=self.all_events[:],events=self.end_events[:],begin=BeginNative.begin_state(self),
                    fin=self.finish_state(),activated=list(self.flags_254),
                    flame=[[t.self_flame,t.flame_damage] for t in self.state.selection.tiles],poison=self.r.poison,
                    cls={k:getattr(self.cls,k) for k in ('games_played','enemies_killed')})

def main():
    old,new=Original(),Native();rng=random.Random(0x13574);counts={'random':0,'turns':0};kinds={};seen=set()
    def case(health=None):
        c,_=scenario(rng)
        c.update(screen=0,victory=rng.randrange(2) if rng.random()<.2 else 0,revive2=rng.randrange(2),guard=rng.randrange(2),flag_146d0=0,flag_146d4=0,flag_15546=0)
        c['record']=rng.randrange(2);c['mode']=rng.randrange(3);c['game']['race']=rng.choice([1,7,8,rng.randrange(10)])
        c['path_state']['turn']=rng.choice([98,99,rng.randrange(0,400)]);c['match']['spawn_enabled_14ae0']=rng.randrange(5)
        c['resources'].update(health=health if health is not None else rng.choice([1,3,10,40,0,-2]),skill_count=rng.randrange(0,5),poison=rng.choice([0,0,1,4]),
            skill_max=[rng.randrange(1,8) for _ in range(4)],skill_current=[rng.randrange(0,9) for _ in range(4)])
        c['regen']=rng.choice([0,0,1,3,-1])
        c['cls']=dict(games_played=1,enemies_killed=2,normal_score=0,hard_score=0,harder_score=0)
        c['skill_id']=[1,2,3,4];c['skill_level']=[0,1,2,3];c['skill_active']=[rng.randrange(2) for _ in range(4)]
        c['flags']={k:rng.randrange(2) for k in FLAG_BYTES};c['flags'].update(b165b8=[rng.randrange(2) for _ in range(5)],
            prev_be74=[rng.randrange(2) for _ in range(4)],next_be78=[rng.randrange(2) for _ in range(4)])
        c['battle']['coin_on_attack']=c['flags']['coin']
        c['generation'].update(time_to_promotion=rng.choice([0,1,2,7]),one_health=rng.randrange(2),force_coins=rng.randrange(2),
                               filter_enabled=rng.randrange(2),filter_swords=rng.randrange(2))
        c['finish']=dict(guard_164a6=rng.randrange(2),next_one_health_14af7=rng.randrange(2),next_force_coins_14af8=rng.randrange(2),flag_1554c=rng.randrange(2),
                         help_flags_102d0=rng.choice([0,0,0x8000,0x200000,0x208000]))
        c['activated']=[int(rng.random()<.3) for _ in range(36)]
        for i,t in enumerate(c['board']):
            state=rng.choice(['plain','plain','plain','frozen','burning'])
            t['flag255']=int(state=='frozen');t['flaming']=int(state=='burning');t['self_flame']=rng.randrange(2)
            t['flame_damage']=rng.choice([0,1,3,rng.randrange(1,25)]);c['combat'][i]['overlay']=rng.randrange(2);c['combat'][i]['flag256']=t['flaming']
            if t['type']==1:t['enemy']=rng.choice([0,0,3,4,10,15,17,19,28,32,rng.randrange(0,35)])
            t['enemy_state']=rng.choice([0,1,1,2,5]);c['combat'][i]['flag25e']=rng.randrange(2);c['combat'][i]['attack_flag']=rng.randrange(2)
            if rng.random()<.3:c['combat'][i]['poison']=[rng.choice([0,1,2,5]),rng.choice([0,2]),0,rng.randrange(2),0,0]
            c['combat'][i]['health']=rng.choice([1,2,5,rng.randrange(-1,20)]);c['combat'][i]['defence']=rng.randrange(0,15)
            t['matched']=int(rng.random()<.05)
        return c
    def compare(c,group):
        a,b=old.end_of_turn(),new.end_of_turn()
        if a!=b:
            (HERE/'end_of_turn_failure.json').write_text(json.dumps(dict(case=c,original=a,native=b),indent=2))
            raise AssertionError('end_of_turn_failure.json')
        counts[group]+=1
        ev=a['events'];checks=ev.count(['check_end'])
        key='saved' if ['serialise_state'] in ev else 'ended@%d'%checks
        kinds[key]=kinds.get(key,0)+1
        for e in ev:seen.add(e[0])
    for _ in range(150):
        c=case();old.load(c);new.load(c);compare(c,'random')
    for game in range(10):
        c=case(health=60);old.load(c);new.load(c)
        for _ in range(8):compare(dict(game=game),'turns')
    assert all(k in kinds for k in ('saved','ended@1','ended@2','ended@3','ended@4'))
    assert {'ability','freeze','label_rest','flare_rest','particles','help','move','update_skills','label','flare'}<=seen,seen
    report=dict(status='passed',comparisons=sum(counts.values()),by_group=counts,outcomes=kinds,event_kinds=sorted(seen),
                function=dict(symbol='__ZN4Game9EndOfTurnEv',address=hex(ENTRY),native='dr_end_of_turn'),
                original='Whole EndOfTurn with original CheckEndGame (+bookkeeping), SetFreeze/FlameVisibility, AttackSkull, GetPoison, MatchTile, ProcessCripples, ActivateAbility (+MimicDefence/Resurrect/GenerateStats/UpdateValues), MoveMatchedTiles (+generation/encounters)',
                boundaries=['19 unrecovered ability functions recorded (TurnHooks.ability)','Game::SerialiseState recorded (save format not recovered)',
                            'presentation (labels, flares, particles, text, sounds, achievements, interface, help, arrow, score screens) adapted'],
                scope='Full shared board/combat/match/tokens/generation/encounters, resources, skills, per-turn flags, end flags, class stats',
                ended_at='ended@N: the Nth CheckEndGame (begin, regen, finish x2) ended the game')
    (HERE/'end_of_turn_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
