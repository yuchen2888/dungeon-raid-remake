#!/usr/bin/env python3
"""Actual enemy ability functions (Game members called by Tile::ActivateAbility) vs
native (recovered_turn), on the full shared state of verify_attack_all.py.

Each whole original function runs from its entry (R0=Game, R1=Tile). MatchTile
runs as original code with the match/token hooks; MoveMatchedTiles runs the
original (RandomiseTile/generation/encounters) via verify_attack_all.py's
subsystem switching; native wires match_tile / move_matched_tiles to
dr_match_tile / dr_move_matched_tiles. Their own AddFlare / QueueSound /
QueueAchievement / UpdateHealthBar calls are recorded in canonical form.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_turn_small import Original as SmallOriginal, Native as SmallNative, EVENT, MATCH
from verify_attack_all import scenario, ATTACK, MOVE_FN
from verify_turn_begin import CHECK
from verify_turn_burn import TILES, STRIDE, RESTING, FLAME, FLAME_END, QUAD_SYMBOLS
from verify_turn_regen import TARGET, INTERFACE, HEALTH_QUAD
from verify_resources import Resource
from verify_path import Path
from verify_generation import Generation, Hooks as GenerationHooks
from verify_stroke import HERE, I32, U8

FUNCTIONS={'run_away':(0x11170,0x11212,'__ZN4Game12RunAwayEnemyEP4Tile','dr_run_away_enemy'),
           'explode':(0x12da8,0x12e64,'__ZN4Game12ExplodeEnemyEP4Tile','dr_explode_enemy'),
           'teleport':(0xf4c8,0xf5aa,'__ZN4Game13TeleportEnemyEv','dr_teleport_enemy'),
           'lower':(0xc9e0,0xcae0,'__ZN4Game11LowerSkullsEP4Tile','dr_lower_skulls'),
           'flee':(0xc664,0xc772,'__ZN4Game6FleeUpEP4Tile','dr_flee_up'),
           'ignite':(0xa150,0xa274,'__ZN4Game11IgniteTilesEP4Tile','dr_ignite_tiles'),
           'stab':(0x127a8,0x128ea,'__ZN4Game10StabAttackEP4Tile','dr_stab_attack'),
           'convert':(0xdc38,0xdd94,'__ZN4Game19ConvertSwordToSkullEP4Tile','dr_convert_sword_to_skull')}
RAND_I=0x1bca0     # RandI(int, int, RandType)
SET_TYPE=0x3f32c   # Tile::SetType, run as original with the generation hooks (checked below)
SWAP=0xb494   # Game::SwapTiles, run as original with the refill/generation/encounter hooks
ACTIVATE,ACTIVATE_END=0x3f09c,0x3f25c   # Tile::ActivateAbility
ABILITY=C.CFUNCTYPE(None,C.c_void_p,I32,I32)
SWAP_FN=C.CFUNCTYPE(None,C.c_void_p,I32,I32,I32,I32)
class TurnHooks8(C.Structure):
    _fields_=[('context',C.c_void_p),('event',EVENT),('match_tile',MATCH),('attack_skull',ATTACK),('check_end_game',CHECK),
              ('move_matched_tiles',MOVE_FN),('ability',ABILITY),('swap_tiles',SWAP_FN)]

def canonical(e):
    """Native TurnEvent -> the canonical list the original-side harnesses record."""
    k=e.kind
    return {1:lambda:['sound',e.a],2:lambda:['text',e.tile,e.a,e.b,e.c],3:lambda:['label',e.tile,e.a,e.b,e.c,e.d],
            4:lambda:['flare',e.tile,e.a,e.b],5:lambda:['achievement',e.a,e.b],6:lambda:['label_rest',e.tile,e.a,e.b,e.c,e.d],
            7:lambda:['flare_rest',e.tile,e.a,e.b],8:lambda:['freeze',e.tile,e.a],9:lambda:['flame_overlay',e.tile],
            10:lambda:['particles',e.tile,e.a],11:lambda:['health_bar',e.a],12:lambda:['label','target',e.a,e.b,e.c,e.d],
            13:lambda:['label','poison',e.a,e.b,e.c,e.d],14:lambda:['update_skills'],15:lambda:['arrow',e.a,e.b,e.c],
            16:lambda:['help',e.tile,e.a,e.b&0xffffffff,e.c&0xffffffff],17:lambda:['serialise_state'],18:lambda:['flare_target',e.a,e.b]}[k]()
FLARE_AT=dict(run_away='center',explode='target',teleport='resting',lower='resting',flee='resting',ignite='resting',convert='resting')   # Tile+0x54 / Interface::GetTarget / Game+0xb400
SYMBOLS={'__ZN4Game10QueueSoundE5Sound':'sound','__ZN4Game8AddFlareE9FlareType8GLfloat2RK9GLcolour4':'flare',
         '__ZN4Game16QueueAchievementE11Achievementf':'achievement','__ZN9Interface15UpdateHealthBarER4Quadi':'bar',
         '__ZN9Interface9GetTargetE8TileType':'target','__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif':'label',
         '__ZN9Interface17GetPoisonPositionEv':'poison_position','__ZN4Tile10UpdateTextEbbb':'text'}

def follow_swaps(native):
    """Tile+0x254 (native activated[]) is per-tile state: the original Tile swap moves it, so an
    embedding swaps activated[] on RefillHooks Swap events (kind 1). Wires that into a harness."""
    previous=native.refill_event
    def refill_event(context,kind,i,j):
        previous(context,kind,i,j)
        if kind==1:native.flags_254[i],native.flags_254[j]=native.flags_254[j],native.flags_254[i]
    native.swap_cb=type(previous)(refill_event);native.refill_hooks.event=native.swap_cb

class AbilityMixin:
    """Original-side handling of the recovered ability functions wherever they run (alone, from
    ActivateAbility or from EndOfTurn): their own presentation calls are recorded in canonical
    form into a sink list, RandI runs as original code (compared through the RNG seeds), SetType
    runs with the generation hooks, SwapTiles/MoveMatchedTiles with the refill/generation/
    encounter hooks, and the generation hooks are off while an ability runs from ActivateAbility."""
    def ability_setup(self):
        text=(HERE.parent/'armv7-disassembly.txt').read_text();self.ab_calls={};self.ab_visits={};self.ability_stack=[]
        address=lambda s:int(re.search(r'^'+re.escape(s)+r':\n\s*([0-9a-f]+):',text,re.M)[1],16)
        for symbol,name in SYMBOLS.items():self.ab_calls[address(symbol)]=name
        self.quads={address(s) for s in QUAD_SYMBOLS};self.alpha=address('__ZN4Quad8SetAlphaEh')
        assert address('__ZN4Tile7SetTypeE8TileTypeii')==SET_TYPE and address('__Z5RandIii8RandType')==RAND_I
        assert address('__ZN4Game9SwapTilesEiiii')==SWAP and address('__ZN4Tile15ActivateAbilityEv')==ACTIVATE
        for key,(start,_,symbol,_) in FUNCTIONS.items():assert address(symbol)==start,symbol
        self.ab_starts={v[0]:k for k,v in FUNCTIONS.items()}
    def ability_ranges(self):return [v[:2] for v in FUNCTIONS.values()]
    def points(self,base):
        return {struct.unpack('<II',self.u.mem_read(base(i),8)):i for i in range(36)}
    def ability_hook(self,u,address,sink):
        """True when the call was handled here (the caller returns without the lower hooks)."""
        lr=u.reg_read(self.LR)&~1
        if address in self.ab_starts and ACTIVATE<lr<=ACTIVATE_END:
            self.ability_stack.append((lr,self.gen_active));self.gen_active=False
        elif self.ability_stack and address==self.ability_stack[-1][0] and self.mode is None:
            self.gen_active=self.ability_stack.pop()[1]
        if self.mode is not None:return False
        key=None
        for k,(a,b,*_) in FUNCTIONS.items():
            if a<=address<b:self.ab_visits[hex(address)]=self.ab_visits.get(hex(address),0)+1
            if a<lr<=b:key=k
        if address in self.quads and FLAME<lr<=FLAME_END:
            if address==self.alpha:sink.append(['flame_overlay',self.tile_of(u.reg_read(self.regs[0]),0x140)])
            return True   # SetFlameVisibility's overlay quad runs as original code
        if key is None:return False
        if address==RAND_I:return True   # the ability's own RandI runs as original code; compared through the RNG seeds and its outcome
        if address==SET_TYPE:self.mode=('settype',lr);self.gen_active=True;return False
        if address==SWAP:self.mode=('swap',lr);self.refill_active=self.gen_active=self.enc_active=True;return False
        name=self.ab_calls.get(address)
        if not name:return False
        r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value;sp=u.reg_read(self.SP);e=None
        if name=='sound':e=['sound',r[1]]
        elif name=='text':e=['text',self.tile_of(r[0]),r[1]&0xff,r[2]&0xff,r[3]&0xff]
        elif name=='achievement':e=['achievement',r[1],s(r[2])]
        elif name=='bar':assert r[0]==self.GAME+INTERFACE and r[1]==self.GAME+HEALTH_QUAD;e=['health_bar',s(r[2])]
        elif name=='target':assert r[0]==self.GAME+INTERFACE and r[1]==0;u.reg_write(self.regs[0],TARGET)
        elif name=='poison_position':assert r[1]==self.GAME+INTERFACE;self.poison_out=r[0]
        elif name=='label':   # labels take a pointer: resting table, poison position or a tile centre
            tail=[r[1],s(r[3]),s(self.read(sp)),s(self.read(sp+4))];o=r[2]-self.GAME-RESTING
            if 0<=o<36*8 and o%8==0:e=['label_rest',o//8,*tail]
            elif r[2]==getattr(self,'poison_out',None):e=['label','poison',*tail]
            else:e=['label',self.tile_of(r[2],0x54),*tail]
        else:
            # Which point the code passes is fixed per function (centre and resting coincide on a settled board).
            colour=s(self.read(self.read(sp)));xy=(r[2],r[3]);where=FLARE_AT[key]
            if where=='target':assert xy==struct.unpack('<II',self.u.mem_read(TARGET,8));e=['flare_target',r[1],colour]
            elif where=='center':e=['flare',self.points(lambda i:self.tile(i)+0x54)[xy],r[1],colour]
            else:e=['flare_rest',self.points(lambda i:self.GAME+RESTING+8*i)[xy],r[1],colour]
        if e:sink.append(e)
        u.reg_write(self.PC,u.reg_read(self.LR));return True

class Original(AbilityMixin,SmallOriginal):
    def __init__(self):
        super().__init__();self.ability_setup();self.ab=None
    def hook(self,u,address,size,context):
        if self.ab and self.all_running and self.ability_hook(u,address,self.ab_events):return
        return super().hook(u,address,size,context)
    def ability(self,key,tile):
        self.all_events=[];self.enc_events=[];self.gen_events=[];self.refill_events=[];self.path_events=[]
        self.match_events=[];self.token_events=[];self.motion_events=[];self.ab_events=[];self.int_sets={};self.mode=None
        start,end=FUNCTIONS[key][:2];self.ranges=[(start,end)];self.ab=key;self.ability_stack=[];u=self.u
        u.mem_write(TARGET,struct.pack('<ff',0.25,-0.75))
        u.reg_write(self.regs[0],self.GAME);u.reg_write(self.regs[1],self.tile(tile));u.reg_write(self.SP,0x140ff00);u.reg_write(self.LR,self.STOP|1)
        self.all_running=True
        try:
            u.emu_start(start|1,self.STOP,timeout=0,count=20000000);assert u.reg_read(self.PC)==self.STOP and self.mode is None,hex(u.reg_read(self.PC))
        finally:self.all_running=False;self.ab=None;self.path_active=self.refill_active=self.gen_active=self.enc_active=False
        return dict(path=self.path_status(),enc=self.enc_status(),events=self.ab_events[:],
                    flame=[[self.u.mem_read(self.tile(i)+0x257,1)[0],C.c_int32(self.read(self.tile(i)+0x258)).value] for i in range(36)])

class Native(SmallNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_turn_native.dylib'))
        self.ab_fns={k:getattr(lib,v[3]) for k,v in FUNCTIONS.items()}
        self.ab_fns['run_away'].argtypes=[C.POINTER(Path),C.c_uint32,C.POINTER(TurnHooks8)]
        self.ab_fns['explode'].argtypes=[C.POINTER(Resource),C.POINTER(Path),C.c_uint32,C.POINTER(TurnHooks8)]
        self.ab_fns['teleport'].argtypes=[C.POINTER(Path),C.POINTER(Generation),C.POINTER(TurnHooks8)]
        for k in ('lower','flee','ignite'):self.ab_fns[k].argtypes=[C.POINTER(Path),C.c_uint32,C.POINTER(TurnHooks8)]
        self.ab_fns['stab'].argtypes=[C.POINTER(Resource),C.POINTER(Path),C.c_uint32,C.POINTER(TurnHooks8)]
        self.ab_fns['convert'].argtypes=[C.POINTER(Generation),C.c_uint32,C.POINTER(TurnHooks8),C.POINTER(GenerationHooks)]
        for f in self.ab_fns.values():f.restype=None
        def event(_,p):self.ab_events.append(canonical(p.contents))
        def match(_,tile,reward):self.match_fn(C.byref(self.m),tile,reward,C.byref(self.match_hooks))
        def move(_):self.refill_lib.dr_move_matched_tiles(C.byref(self.refill),C.byref(self.refill_hooks))
        def swap(_,x1,y1,x2,y2):self.refill_lib.dr_swap_tiles(C.byref(self.refill),x1,y1,x2,y2,C.byref(self.refill_hooks))
        self.ab_cb=(EVENT(event),MATCH(match),MOVE_FN(move),SWAP_FN(swap))
        self.ab_hooks=TurnHooks8(None,self.ab_cb[0],self.ab_cb[1],ATTACK(0),CHECK(0),self.ab_cb[2],ABILITY(0),self.ab_cb[3])
    def ability(self,key,tile):
        self.all_events=[];self.enc_events=[];self.gen_events=[];self.refill_events=[];self.path_events=[]
        self.match_events=[];self.token_events=[];self.motion_events=[];self.ab_events=[]
        f=self.ab_fns[key];h=C.byref(self.ab_hooks)
        if key=='run_away':f(C.byref(self.path_state),tile,h)
        elif key in ('explode','stab'):f(C.byref(self.r),C.byref(self.path_state),tile,h)
        elif key=='convert':f(C.byref(self.gen),tile,h,C.byref(self.gen_hooks))
        elif key=='teleport':f(C.byref(self.path_state),C.byref(self.gen),h)
        else:f(C.byref(self.path_state),tile,h)
        return dict(path=self.path_status(),enc=self.enc_status(),events=self.ab_events[:],
                    flame=[[t.self_flame,t.flame_damage] for t in self.state.selection.tiles])

def main():
    old,new=Original(),Native();rng=random.Random(0xF4C8);counts={k:0 for k in FUNCTIONS};stats=dict(achievements=0,bars=0,moved=0,swapped=0,ignited=0,lowered=0,converted=0,stabbed=0)
    for n in range(80*len(FUNCTIONS)):
        key=list(FUNCTIONS)[n%len(FUNCTIONS)]
        c,_=scenario(rng);c['game']['race']=rng.choice([9,9,4,4,rng.randrange(10)]);c['generation']['one_health']=rng.randrange(2)
        c['resources'].update(health=rng.choice([1,2,3,7,40,0,-5,2**31-1]),ui_health=rng.choice([0,1,3,20]))
        for i,t in enumerate(c['board']):
            t['matched']=int(rng.random()<.15);t['flag255']=0;t['flaming']=int(rng.random()<.2);t['self_flame']=rng.randrange(2)
            t['flame_damage']=rng.randrange(0,9);c['combat'][i]['flag256']=t['flaming'];c['combat'][i]['attack']=rng.choice([0,1,2,5,9])
            if t['type']==1 and rng.random()<.3:t['enemy']=7
            if t['type']!=1 and rng.random()<.2:t['type']=4
        tile=rng.choice([rng.randrange(36),30+rng.randrange(6)]);c['board'][tile].update(type=1,matched=0)
        old.load(c);new.load(c);a,b=old.ability(key,tile),new.ability(key,tile)
        if a!=b:
            (HERE/'abilities_failure.json').write_text(json.dumps(dict(case=c,key=key,tile=tile,original=a,native=b),indent=2))
            raise AssertionError('abilities_failure.json')
        counts[key]+=1;stats['achievements']+=sum(1 for e in a['events'] if e[0]=='achievement')
        stats['bars']+=sum(1 for e in a['events'] if e[0]=='health_bar');stats['moved']+=bool(a['enc']['events'])
        stats['swapped']+=sum(1 for e in a['enc']['refill']['events'] if e[0]==1) if key=='flee' else 0
        stats['converted']+=sum(1 for e in a['events'] if e[0]=='label_rest' and key=='convert')
        stats['stabbed']+=sum(1 for e in a['events'] if e[0]=='label' and e[1]=='poison')
        stats['ignited']+=sum(1 for e in a['events'] if e[0]=='flame_overlay');stats['lowered']+=sum(1 for e in a['events'] if e[0]=='flare_rest' and key=='lower')
    assert all(stats.values())
    report=dict(status='passed',comparisons=sum(counts.values()),by_function=counts,**stats,
                functions=[dict(symbol=v[2],address=hex(v[0]),native=v[3]) for v in FUNCTIONS.values()],
                original='Actual ability functions with original MatchTile (+tokens/rewards) and MoveMatchedTiles (+RandomiseTile/generation/encounters)',
                boundaries=['own AddFlare/QueueSound/QueueAchievement/UpdateHealthBar adapted; Interface::GetTarget returns a harness point'],
                scope='Full shared board, combat, match state, tokens, refill/generation/encounters, resources and RNG',branch_visits=old.ab_visits)
    (HERE/'abilities_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='branch_visits'}))

if __name__=='__main__':main()
