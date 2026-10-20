#!/usr/bin/env python3
"""Actual Game::ProcessInput release [0x16890,0x16e10) and Game::AddRevengeHealth 0xce7c vs native
dr_release_path / dr_add_revenge_health / dr_release_clear (recovered_schedule), on the shared state
of verify_attack_all.py.

The original runs ProcessInput from its entry (R0=Game) with the gate open (phase 0, input ready, no
input target) and a released touch (Game+0x10 = 2) until the epilogue 0x170e6, or 0x16c1c for a
class scroll (a later unit). The release prefix (Undim, ProcessRune, SetSize) is the verified
dr_prepare_release; ProcessRune(true) is skipped (dr_process_rune) and the other prefix calls
are skipped by the selection harness. Rand, std::list::size and
AddRevengeHealth run as original code. Recorded and skipped boundaries (native: ReleaseHooks events):
QueueSound, HelpMenu::Initialise, Game::MatchTiles (an embedding wires dr_commit_path; here both sides
add the case's counts), QueueAchievement, AddSimpleLabel, Tile::UpdateText,
Item::IncreaseStat, Game::UpdateStats, Interface::UpdateHealthBar, Interface::GetTarget (returns the
case's health target) and Game::UpdateCrossVisibility.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_input_gate import Original as GateOriginal, Native as GateNative
from verify_attack_all import scenario
from verify_resources import Resource
from verify_path import Path
from verify_generation import Generation
from verify_turn_begin import TurnFlags
from verify_turn_finish import TurnFinishFlags
from verify_stroke import HERE, I32, U8, State as StrokeState
from verify_selection import Point, Hooks as SelectionHooks, EVENT as SELECTION_EVENT

ENTRY,EPILOGUE,SCROLL=0x16638,0x170e6,0x16c1c
REVENGE,REVENGE_END=0xce7c,0xcf48
MATCH_TILES,INCREASE_STAT,UPDATE_STATS=0x12188,0x29d58,0x14c04
FLIGHTS=dict(flame=0x14e5c,spike=0x151d0,leech=0xc31c)
LABELS=dict(flame=0x14e30,spike=0x151a4,leech=0xc2f4)
TARGET_POINT=0x1517f00
EFFECT_INTS=dict(kills_b=0x15548,killed_attack=0x164ac,generated_count=0x165c0,generated_enemies=0x165c4)
SYMBOLS={'__ZN4Game10QueueSoundE5Sound':'sound','__ZN8HelpMenu10InitialiseEffff8HelpType':'help',
         '__ZN4Game16QueueAchievementE11Achievementf':'achievement',
         '__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif':'label','__ZN4Tile10UpdateTextEbbb':'text',
         '__ZN9Interface15UpdateHealthBarER4Quadi':'health_bar','__ZN9Interface9GetTargetE8TileType':'target',
         '__ZN4Game21UpdateCrossVisibilityEv':'cross','__ZN4Game10MatchTilesEv':'match_tiles',
         '__ZN4Item12IncreaseStatE11UpgradeType':'increase_stat','__ZN4Game11UpdateStatsEv':'update_stats',
         '__ZN4Game16AddRevengeHealthEv':'revenge','__ZN4Game11ProcessRuneEb':'rune'}
KINDS=dict(sound=1,help=2,match_tiles=3,achievement=4,label=5,text=6,increase_stat=7,update_stats=8,health_bar=9,cross=10)
class Flight(C.Structure):_fields_=[('arc',C.c_float),('start',Point),('progress',C.c_float),('speed',C.c_float)]
class Flights(C.Structure):_fields_=[(k,Flight) for k in FLIGHTS]
class Inputs(C.Structure):_fields_=[(k+'_label',Point) for k in LABELS]+[('health_target',Point)]
class ReleaseState(C.Structure):
    _fields_=[('path',C.POINTER(Path)),('generation',C.POINTER(Generation)),('resources',C.POINTER(Resource)),
              ('flags',C.POINTER(TurnFlags)),('finish',C.POINTER(TurnFinishFlags)),('flights',C.POINTER(Flights))]
class Event(C.Structure):_fields_=[(k,I32) for k in ['kind','tile','a','b','c','d']]+[('x',C.c_float),('y',C.c_float)]
EVENT=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(Event))
class Hooks(C.Structure):_fields_=[('context',C.c_void_p),('event',EVENT)]
ROUTES=['clear','match','scroll']
def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
def bits(v):return struct.unpack('<i',struct.pack('<f',v))[0]

class Original(GateOriginal):
    def __init__(self):
        super().__init__();self.releasing=False;self.release_visits={};self.release_calls={}
        text=(HERE.parent/'armv7-disassembly.txt').read_text()
        for symbol,name in SYMBOLS.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol;self.release_calls[int(m[1],16)]=name
        assert self.release_calls[MATCH_TILES]=='match_tiles' and self.release_calls[INCREASE_STAT]=='increase_stat' and self.release_calls[UPDATE_STATS]=='update_stats'
    def hook(self,u,address,size,context):
        if not self.releasing:return super().hook(u,address,size,context)
        if 0x16890<=address<0x16e10 or REVENGE<=address<REVENGE_END:self.run_visits.add(address);self.release_visits[hex(address)]=self.release_visits.get(hex(address),0)+1
        if address==SCROLL:self.route=2;u.emu_stop();return
        name=self.release_calls.get(address)
        if name is None or name=='revenge':return super().hook(u,address,size,context)
        if name=='rune':u.reg_write(self.PC,u.reg_read(self.LR));return   # prefix: dr_prepare_release / dr_process_rune
        r=[u.reg_read(v) for v in self.regs];sp=u.reg_read(self.SP);s=lambda v:C.c_int32(v).value
        fl=lambda a:struct.unpack('<f',u.mem_read(a,4))[0]
        tile=-1;e=[0,0,0,0,0.0,0.0]
        if name=='sound':e[0]=s(r[1])
        elif name=='help':
            assert r[0]==self.GAME+0x10298 and self.read(sp)==r[3],(hex(r[0]),self.read(sp),r[3])
            e=[s(self.read(sp+4)),0,0,s(r[3]),struct.unpack('<f',struct.pack('<I',r[1]))[0],struct.unpack('<f',struct.pack('<I',r[2]))[0]]
            tile=self.first_tile
        elif name=='achievement':e[:2]=[s(r[1]),s(r[2])]
        elif name=='label':
            lr=u.reg_read(self.LR)&~1
            if REVENGE<=lr<REVENGE_END:tile=self.index(r[2]-0x54)
            e=[s(r[1]),s(r[3]),s(self.read(sp)),s(self.read(sp+4)),fl(r[2]),fl(r[2]+4)]
        elif name=='text':tile=self.index(r[0]);e[:3]=[s(r[1]),s(r[2]),s(r[3])]
        elif name=='increase_stat':
            assert r[0]==self.read(self.GAME+0xbe90);e[0]=s(r[1])
        elif name=='health_bar':
            assert r[0]==self.GAME+0x4cdc and r[1]==self.GAME+0x4d4c;e[0]=s(r[2])
        elif name=='target':
            assert r[0]==self.GAME+0x4cdc and r[1]==0,(hex(r[0]),r[1],hex(u.reg_read(self.LR)));u.reg_write(self.regs[0],TARGET_POINT);u.reg_write(self.PC,u.reg_read(self.LR));return
        elif name=='match_tiles':
            for k,a in EFFECT_INTS.items():self.write(self.GAME+a,self.read(self.GAME+a)+self.case_effect[k])   # MatchTiles counts up
        self.release_events.append([KINDS[name],tile,*e])
        u.reg_write(self.PC,u.reg_read(self.LR))
    def load(self,c):
        super().load(c);G=self.GAME;r=c['release']
        for k,a in LABELS.items():self.u.mem_write(G+a,struct.pack('<ff',*r[k+'_label']))
        self.u.mem_write(TARGET_POINT,struct.pack('<ff',*r['health_target']))
        for k,a in FLIGHTS.items():self.u.mem_write(G+a,struct.pack('<5f',*r['flights'][k]))
        self.u.mem_write(G+0x164a7,bytes([r['prev_164a7']]));self.u.mem_write(G+0x165b8,bytes([r['b165b8']]))
        self.u.mem_write(G+0x1554c,bytes([r['flag_1554c']]));self.write(G+0x102d0,r['help_flags'])
        self.write(G+0xbe90,0x1517e00);self.case_effect=r['effect'];self.first_tile=c['path'][0]
        self.write(G+0x10,2);self.write(G+0xb8a8,0);self.write(G+0x58ac,-1);self.u.mem_write(G+0x5e14,b'\1')
        self.write(G+0xb3f4,len(c['fake']))
    def release_run(self):
        self.release_events=[];self.route=None;self.run_visits=set();self.releasing=True;u=self.u
        u.reg_write(self.regs[0],self.GAME);u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1)
        try:
            u.emu_start(ENTRY|1,EPILOGUE,timeout=0,count=400000);pc=u.reg_read(self.PC)
        finally:self.releasing=False
        if self.route is None:assert pc==EPILOGUE,hex(pc);self.route=1 if 0x168a6 in self.run_visits else 0
        return self.status()
    def status(self):
        G=self.GAME;u=self.u;s=lambda a:C.c_int32(self.read(a)).value
        sel={k:s(G+a) for k,a in dict(current_damage=0xbe7c,current_leech=0xc318,current_flame_damage=0x14e54,current_spike_damage=0x151c8).items()}
        sel.update({k:u.mem_read(G+a,1)[0] for k,a in dict(flame_label_moving=0x14e58,spike_label_moving=0x151cd).items()})
        flights={k:[f32(x) for x in struct.unpack('<5f',u.mem_read(G+a,20))] for k,a in FLIGHTS.items()}
        return dict(route=ROUTES[self.route],events=self.release_events,selection=sel,flights=flights,
                    counters={k:s(G+a) for k,a in EFFECT_INTS.items()},flag_1554c=u.mem_read(G+0x1554c,1)[0],
                    health=[s(G+0xbd98),s(G+0x5994)],attack=[s(self.tile(i)+0xa4) for i in range(36)],
                    path=len(self.list_values(G+0xb3d8)),fake=s(G+0xb3f4),seeds=list(struct.unpack('<6I',u.mem_read(0x1eac20,24))))

class Native(GateNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_schedule_native.dylib'))
        self.release_fn=lib.dr_release_path;self.release_fn.restype=I32
        self.release_fn.argtypes=[C.POINTER(ReleaseState),C.POINTER(Inputs),C.POINTER(Hooks)]
        self.prepare_fn=lib.dr_prepare_release;self.prepare_fn.restype=I32
        self.prepare_fn.argtypes=[C.POINTER(StrokeState),C.POINTER(SelectionHooks)]
        def event(_,ptr):
            e=ptr.contents;self.release_events.append([e.kind,e.tile,e.a,e.b,e.c,e.d,f32(e.x),f32(e.y)])
            if e.kind==KINDS['match_tiles']:
                b=self.path_state.battle;e=self.case_effect;b.kills_b+=e['kills_b'];b.killed_attack+=e['killed_attack']
                self.gen.generated_count+=e['generated_count'];self.gen.generated_enemies+=e['generated_enemies']
        self.release_cb=EVENT(event);self.release_hooks=Hooks(None,self.release_cb)
        self.selection_cb=SELECTION_EVENT(lambda *a:None);self.selection_hooks=SelectionHooks(None,self.selection_cb)
    def load(self,c):
        super().load(c);r=c['release']
        self.inputs=Inputs(*[Point(*r[k+'_label']) for k in LABELS],Point(*r['health_target']))
        self.flights=Flights(*[Flight(v[0],Point(v[1],v[2]),v[3],v[4]) for v in (r['flights'][k] for k in FLIGHTS)])
        self.flags=TurnFlags();self.flags.prev_164a7=r['prev_164a7'];self.flags.b165b8[0]=r['b165b8']
        self.finish=TurnFinishFlags();self.finish.flag_1554c=r['flag_1554c'];self.finish.help_flags_102d0=r['help_flags']
        self.release_state=ReleaseState(C.pointer(self.path_state),C.pointer(self.gen),C.pointer(self.r),C.pointer(self.flags),
                                        C.pointer(self.finish),C.pointer(self.flights))
        self.case_effect=r['effect']
    def release_run(self):
        self.release_events=[]
        self.prepare_fn(C.byref(self.state),C.byref(self.selection_hooks))
        route=self.release_fn(C.byref(self.release_state),C.byref(self.inputs),C.byref(self.release_hooks))
        s=self.state.selection;f=self.flights
        sel={k:getattr(s,k) for k in ['current_damage','current_leech','current_flame_damage','current_spike_damage','flame_label_moving','spike_label_moving']}
        flights={k:[f32(x) for x in (getattr(f,k).arc,getattr(f,k).start.x,getattr(f,k).start.y,getattr(f,k).progress,getattr(f,k).speed)] for k in FLIGHTS}
        b=self.path_state.battle
        return dict(route=ROUTES[route],events=self.release_events,selection=sel,flights=flights,
                    counters=dict(kills_b=b.kills_b,killed_attack=b.killed_attack,generated_count=self.gen.generated_count,generated_enemies=self.gen.generated_enemies),
                    flag_1554c=self.finish.flag_1554c,health=[self.r.health,self.r.ui_health],attack=[t.attack for t in self.path_state.combat],
                    path=s.path_length,fake=sum(1 for v in s.fake if v),seeds=list(self.m.random.seeds))

def case(rng,n):
    c,_=scenario(rng);g=c['game']
    if rng.random()<.35:g['race']=6
    for i,t in enumerate(c['board']):
        if t['type']==1 and rng.random()<.3:t['enemy']=21
        t['matched']=int(rng.random()<.15)
    length=rng.choice([1,1,2,3,3,4,5,6,8]);path=rng.sample(range(36),length)
    for i in path:c['board'][i]['selected']=1
    if length==1 and rng.random()<.5:c['board'][path[0]].update(type=6,special=rng.choice([1,1,0,2]))
    c['path']=path;c['fake']=rng.sample(path,rng.choice([0,0,0,1,min(2,length)])) if length>1 else []
    if rng.random()<.25:
        for i in path:c['board'][i]['type']=rng.choice([4,4,0,2])
    for k in ('current_damage','current_leech'):g[k]=rng.choice([0,3,17,-2])
    for k in ('current_flame_damage','current_spike_damage'):g[k]=rng.choice([0,0,4,9,-1])
    c['path_state'].update(base_attack=g['current_damage'],direction_bonus=g['weapon_damage'])   # same Game fields (verify_path)
    for k in ('flame_label_moving','spike_label_moving','skull_counted'):g[k]=int(rng.random()<.4)
    res=c['resources'];res.update(health_max=rng.choice([20,60,100]),health_bonus=rng.choice([0,0,5,-3]))
    res['health']=rng.randrange(1,res['health_max']+5);res['ui_health']=rng.choice([res['health'],res['health']+1,0])
    if rng.random()<.25:res['health']=res['ui_health']=res['health_max']+res['health_bonus']   # capped heal, bar unchanged
    count=rng.choice([0,9,10,10,12,15]);effect=dict(kills_b=rng.choice([0,1,5,14,15,15,30,-1]),killed_attack=rng.choice([0,3,50,-1,12]),
        generated_count=count,generated_enemies=count if rng.random()<.6 else rng.choice([0,count-1,count+1]))
    c['battle'].update(kills_b=rng.choice([0,3,20]),killed_attack=rng.choice([0,7]))   # reset before MatchTiles
    c['generation'].update(generated_count=rng.choice([0,4,11]),generated_enemies=rng.choice([0,4,11]))
    pt=lambda:[round(rng.uniform(-1,2),4),round(rng.uniform(-1,2),4)]
    c['release']=dict(flame_label=pt(),spike_label=pt(),leech_label=pt(),health_target=pt(),
        flights={k:[rng.uniform(-1,2) for _ in range(5)] for k in FLIGHTS},prev_164a7=int(rng.random()<.5),
        b165b8=int(rng.random()<.5),flag_1554c=rng.randrange(2),help_flags=rng.choice([0,0x10,0x8010,0x200000,0xffffffef]),effect=effect)
    c['moving_list']=[];c['gate']=dict(tokens_pending=0,flare_count=0,phase=0,touch_phase=2,input_target=-1,rune=rng.randrange(4))
    return c

def main():
    old,new=Original(),Native();rng=random.Random(0x16890);routes={};compared=0
    for n in range(500):
        c=case(rng,n);old.load(c);new.load(c);a,b=old.release_run(),new.release_run()
        if a!=b:
            (HERE/'release_failure.json').write_text(json.dumps(dict(case=c,original=a,native=b),indent=2))
            raise AssertionError('release_failure.json')
        compared+=1;routes[a['route']]=routes.get(a['route'],0)+1
    branches=dict(enemy_sound=0x168f8,sword_sound=0x168b6,help=0x168d2,refill_achievement=0x16940,flame=0x16956,spike=0x169cc,
                  revenge=0x16a46,revenge_tile=0xceb4,race_upgrade=0x16a7a,achievement_57=0x16ac4,heal=0x16ae6,health_bar=0x16b3c,
                  leech_cleared=0x16b7e,leech_flight=0x16b86,short_path=0x16bea,class_scroll=0x16c1c,flame_cleared=0x16dec,spike_cleared=0x16dfa)
    missing=[k for k,v in branches.items() if hex(v) not in old.release_visits]
    assert not missing and len(routes)==3,(missing,routes)
    assert old.release_visits['0x16ae6']>old.release_visits['0x16b3c'],'heal without a health bar change'
    report=dict(status='passed',comparisons=compared,routes=routes,branches={k:old.release_visits[hex(v)] for k,v in branches.items()},
                functions=[dict(symbol='__ZN4Game12ProcessInputEv',address=hex(ENTRY),release=['0x16890','0x16e10'],native=['dr_release_path','dr_release_clear']),
                           dict(symbol='__ZN4Game16AddRevengeHealthEv',address=hex(REVENGE),native='dr_add_revenge_health')],
                original='Actual ProcessInput from its entry (gate, dispatch, release prefix) to the epilogue; original Rand and AddRevengeHealth',
                boundaries=['MatchTiles recorded (native event; dr_commit_path in an embedding), the case counts added on both sides',
                            'Item::IncreaseStat, UpdateStats, UpdateCrossVisibility, labels, sounds, achievements, help, health bar recorded',
                            'class scroll branch [0x16c1c,0x16d88) is a later unit (stopped at its entry)'],
                scope='path enemy/sword/fake, refill counters, flame/spike/leech flights, revenge, race 6, healing, health bar, tail')
    (HERE/'release_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
