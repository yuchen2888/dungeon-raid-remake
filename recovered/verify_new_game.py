#!/usr/bin/env python3
"""Actual Game::InitNewGame 0x15c50 and Game::CalculateTilePositions 0xb264 vs native dr_init_new_game /
dr_calculate_tile_positions (recovered_schedule), on the shared state of verify_attack_all.py.

The original runs from its entry (R0=Game) to its return with time() returning the case seed. SetRandSeed,
FlushRandSeeds, CharacterClass::UnlockAchievement / CheckIfAllClassesMaxed, HavePerk / HaveFlaw,
Game::PositionTile and Game::RandomiseTile (with the generation harness recording its calls, as in
verify_generation.py) run as original code. Recorded and skipped (native: NewGameHooks events):
QueueAchievement, Quad::SetSize, Tile::InitialiseLabels, Label::SetText / UpdateColour (Game+0x5e18),
Interface value/bar updates and Reset, Item deletion and construction (operator new returns harness
memory), Game::UpdateStats and the falling-list clear. Every Game field the original writes (found by
tracing its stores) is compared, except the presentation label fields Game+0x5e30..0x5e47 and the item
pointers.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_input_gate import Original as GateOriginal, Native as GateNative
from verify_attack_all import scenario
from verify_generation import Generation
from verify_game_over import EndGameState
from verify_turn_begin import TurnFlags
from verify_turn_finish import TurnFinishFlags
from verify_stats import PlayerStats, PLAYER, UI
from verify_progression import Profile
from verify_stroke import HERE, I32, U8

ENTRY,CTP=0x15c50,0xb264
CLASSES,CLASS_STRIDE=0x15564,388
SKILLS=0x1700000
ITEM_MEMORY=0x1517000
TIME_STUB,NEW_STUB,DELETE_STUB=0x194fcc,0x194d54,0x194d4c
SYMBOLS={'__ZN4Game16QueueAchievementE11Achievementf':'achievement','__ZN4Quad7SetSizeERK8GLfloat2':'size',
         '__ZN4Tile16InitialiseLabelsEP4Game':'labels','__ZN5Label7SetTextEPKci':'turn_label','__ZN5Label12UpdateColourEv':'colour',
         '__ZN9Interface16UpdateSkullValueEv':'skull','__ZN9Interface15UpdateHealthBarER4Quadi':'health_bar',
         '__ZN9Interface11UpdateXPBarER4Quadi':'xp_bar','__ZN9Interface11UpdateUPBarER4Quadi':'up_bar',
         '__ZN9Interface13UpdateGoldBarERA2_4Quadi':'gold_bar','__ZN9Interface5ResetEv':'reset','__ZN4ItemD1Ev':'item_free',
         '__ZN4ItemC1EP4Game8ItemType':'item','__ZN4Game11UpdateStatsEv':'update_stats',
         '__ZNSt10_List_baseIP4TileSaIS1_EE8_M_clearEv':'list_clear'}
KINDS=dict(achievement=1,size=2,labels=3,turn_label=4,skull=5,health_bar=6,xp_bar=7,up_bar=8,gold_bar=9,item=10,update_stats=11,reset=12)
QUADS=dict(health_bar=0x4d4c,xp_bar=0x4dbc,up_bar=0x4e2c,gold_bar=0x4e9c)
INTS=dict(turn=0xc,ui_health=0x5994,ui_ceiling=0x5998,ui_xp=0x599c,ui_up=0x59a0,ui_gold=0x59a4,ui_skull=0x59c8,phase=0xb8a8,
          tokens_pending=0xb52c,tokens_b53c=0xb53c,tokens_b54c=0xb54c,health=0xbd98,health_max=0xbd9c,health_bonus=0xbda0,
          armour_current=0xbda4,armour_max=0xbda8,xp=0xbdb0,up=0xbdb4,gold=0xbdb8,base_damage=0xbdc0,
          xp_fraction=0xbdd0,gold_fraction=0xbdd8,up_fraction=0xbde0,base_bde8=0xbde8,base_bdf0=0xbdf0,base_bdf8=0xbdf8,
          base_be00=0xbe00,healing_value=0xbe08,shield_value=0xbe10,chance_be18=0xbe18,chance_be20=0xbe20,chance_be28=0xbe28,
          chance_be30=0xbe30,level=0xbe4c,total_xp=0xbe50,total_gold=0xbe54,total_up=0xbe58,current_damage=0xbe7c,
          skill_count=0xbfa0,current_leech=0xc318,time_to_promotion=0x14af0,flame=0x14e54,spike=0x151c8,poison=0x15540,
          spawn_count=0x1555c,value_164d4=0x164d4,kills_a=0x165b4,vertical_offset=0x165c8,total=0x165cc,round_kills=0x165d0,
          bonus_total=0x165d4,crossing_samples=0x16600,crossing_average=0x16604,crossing_best=0x16608)
INTS.update({f'tokens_{i}':0x165d8+4*i for i in range(5)});INTS.update({f'bonus_{i}':0x165ec+4*i for i in range(5)})
BYTES=dict(input_ready=0x5e14,cooldown=0xbe64,flag_bf88=0xbf88,filter_enabled=0xbfb8,filter_swords=0xbfb9,counterattack=0xbfba,
           coin=0xbfbb,next_coin=0xbfbc,label_bfc0=0xbfc0,promotion_enabled=0x14af4,one_health=0x14af5,force_coins=0x14af6,
           next_one_health=0x14af7,next_force_coins=0x14af8,label_14afc=0x14afc,flame_moving=0x14e58,label_14e70=0x14e70,
           spiky=0x151cc,spike_moving=0x151cd,label_151e4=0x151e4,flag_1554c=0x1554c,b15561=0x15561,b15562=0x15562,
           inhibit=0x15563,rune_enabled=0x16491,arrow_hold=0x16492,guard_164a4=0x164a4,revive_second=0x164a5,
           guard_164a6=0x164a6,prev_164a7=0x164a7,next_164a8=0x164a8,victory=0x16611)
BYTES.update({f'double_{i}':0xbe74+i for i in range(4)});BYTES.update({f'next_be78_{i}':0xbe78+i for i in range(4)})
class Extra(C.Structure):
    _fields_=[(k,I32) for k in ('tokens_type0_165d8','tokens_type4_165e8','bonus_type0_165ec','bonus_type4_165fc','value_164d4',
              'tokens_b53c','tokens_b54c')]+[('base_bde8',I32*4),('flag_bf88',U8),('label_active',U8*4),('skill_ff',(U8*4)*4)]
class State(C.Structure):
    _fields_=[('match',C.c_void_p),('preview',C.c_void_p),('resources',C.c_void_p),('path',C.c_void_p),('generation',C.c_void_p),
              ('tokens',C.c_void_p),('flags',C.POINTER(TurnFlags)),('finish',C.POINTER(TurnFinishFlags)),('rune',C.c_void_p),
              ('end',C.POINTER(EndGameState)),('counterattack',C.POINTER(U8)),('attack',C.c_void_p),('player',C.POINTER(PlayerStats)),
              ('classes',C.POINTER(Profile)),('difficulty',I32),('extra',C.POINTER(Extra))]
class Event(C.Structure):_fields_=[(k,I32) for k in ('kind','tile','a','b')]
EVENT=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(Event))
class Hooks(C.Structure):_fields_=[('context',C.c_void_p),('event',EVENT),('generation',C.c_void_p)]
def bits(v):return struct.unpack('<i',struct.pack('<f',v))[0]

class Original(GateOriginal):
    def __init__(self):
        super().__init__();self.initialising=False;self.new_calls={};self.new_visits={}
        text=(HERE.parent/'armv7-disassembly.txt').read_text()
        for symbol,name in SYMBOLS.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol;self.new_calls[int(m[1],16)]=name
        assert re.search(r'^__ZN4Game11InitNewGameEv:\n\s*15c50:',text,re.M) and re.search(r'^__ZN4Game22CalculateTilePositionsEv:\n\s*b264:',text,re.M)
    def hook(self,u,address,size,context):
        if not self.initialising:return super().hook(u,address,size,context)
        if ENTRY<=address<0x16450 or CTP<=address<0xb3b4:self.new_visits[hex(address)]=self.new_visits.get(hex(address),0)+1
        lr=u.reg_read(self.LR)
        if address in (0x194cec,0x194cf4) and ENTRY<(lr&~1)<0x16450:u.reg_write(self.PC,lr);return   # SjLj (un)register
        if address==TIME_STUB:u.reg_write(self.regs[0],self.case_time);u.reg_write(self.PC,lr);return
        if address==NEW_STUB:u.reg_write(self.regs[0],ITEM_MEMORY+0x200*self.items_made);u.reg_write(self.PC,lr);return
        if address==DELETE_STUB:u.reg_write(self.PC,lr);return
        name=self.new_calls.get(address)
        if name is None:return super().hook(u,address,size,context)
        r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value;e=None
        if name=='achievement':assert r[0]==self.GAME;e=[-1,s(r[1]),s(r[2])]
        elif name=='size':
            if not CTP<(lr&~1)<0xb3b4:return super().hook(u,address,size,context)
            e=[self.index(r[0]),*struct.unpack('<ii',u.mem_read(r[1],8))]
        elif name=='labels':assert r[1]==self.GAME;e=[self.index(r[0]),0,0]
        elif name=='turn_label':assert r[0]==self.GAME+0x5e18;e=[-1,0,0]
        elif name in ('colour','item_free','list_clear'):
            if name=='colour':assert r[0]==self.GAME+0x5e18
            if name=='list_clear':assert r[0]==self.GAME+0xb3f8
            u.reg_write(self.PC,lr);return
        elif name in QUADS:assert r[0]==self.GAME+0x4cdc and r[1]==self.GAME+QUADS[name];e=[-1,s(r[2]),0]
        elif name in ('skull','reset'):assert r[0]==self.GAME+0x4cdc;e=[-1,0,0]
        elif name=='item':assert r[1]==self.GAME;e=[-1,self.items_made,s(r[2])];self.items_made+=1
        elif name=='update_stats':assert r[0]==self.GAME;e=[-1,0,0]
        self.new_events.append([KINDS[name],*e]);u.reg_write(self.PC,lr)
    def load(self,c):
        super().load(c);G=self.GAME;n=c['new_game'];self.case_time=n['time']
        for i,(type_,base,level) in enumerate(n['classes']):
            b=G+CLASSES+CLASS_STRIDE*i;self.write(b,G);self.write(b+4,type_);self.write(b+0xc,base);self.u.mem_write(b+0x54,bytes([level]))
        self.write(G+0x1648c,0)
        for k,v in n['ints'].items():self.write(G+INTS[k],v)
        for k,v in n['bytes'].items():self.u.mem_write(G+BYTES[k],bytes([v]))
        for i in range(4):
            self.write(G+0xbf90+4*i,SKILLS+0x100*i)
            for k,o in enumerate((0xf,0x23,0x37,0x4b)):self.u.mem_write(SKILLS+0x100*i+o,bytes([n['skill_bytes'][i][k]]))
    def run(self):
        self.new_events=[];self.items_made=0;self.initialising=self.gen_active=True;self.gen_events=[];self.pending_gen=None;u=self.u
        u.reg_write(self.regs[0],self.GAME);u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1)
        try:u.emu_start(ENTRY|1,self.STOP,timeout=0,count=3000000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.initialising=self.gen_active=False
        G=self.GAME;s=lambda a:C.c_int32(self.read(a)).value
        fields={k:s(G+a) for k,a in INTS.items()};fields.update({k:self.u.mem_read(G+a,1)[0] for k,a in BYTES.items()})
        fields['skill_bytes']=[[self.u.mem_read(SKILLS+0x100*i+o,1)[0] for o in (0xf,0x23,0x37,0x4b)] for i in range(4)]
        tiles=[]
        for i in range(36):
            t=self.tile(i);tiles.append([s(t+0x74),s(t+0x78),*[s(t+a) for a in (0x54,0x58,0x7c,0x80)],*[s(G+0xb400+8*i+a) for a in (0,4)]])
        return dict(new_events=self.new_events,fields=fields,tiles=tiles,**self.gen_status())

class Native(GateNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_schedule_native.dylib'))
        self.init_fn=lib.dr_init_new_game;self.init_fn.argtypes=[C.POINTER(State),C.c_uint32,C.POINTER(Hooks)];self.init_fn.restype=None
        def event(_,p):e=p.contents;self.new_events.append([e.kind,e.tile,e.a,e.b])
        self.new_cb=EVENT(event)
    def load(self,c):
        super().load(c);n=c['new_game'];self.case_time=n['time']
        self.classes=(Profile*10)()
        for i,(type_,base,level) in enumerate(n['classes']):
            p=self.classes[i];p.class_type=type_;p.base_race=base;p.level=level
        m=self.m;m.class_type=self.classes[0].class_type;m.class_level=self.classes[0].level   # MatchState views of the roster
        for i in range(1,10):m.unlocked[i-1]=self.classes[i].level
        iv,bv=n['ints'],n['bytes'];r,pv,s,p,g=self.r,self.p,self.state.selection,self.path_state,self.gen
        self.flags=TurnFlags();self.finish=TurnFinishFlags();self.end=EndGameState();self.counter=U8(bv['counterattack'])
        self.player=PlayerStats();self.extra=Extra()
        self.native_fields={}
        for k,v in iv.items():self.set_field(k,v)
        for k,v in bv.items():self.set_field(k,v)
        for i in range(4):
            for k in range(4):self.extra.skill_ff[i][k]=n['skill_bytes'][i][k]
        self.state_obj=State(C.cast(C.pointer(m),C.c_void_p),C.cast(C.pointer(pv),C.c_void_p),C.cast(C.pointer(r),C.c_void_p),
                             C.cast(C.pointer(p),C.c_void_p),C.cast(C.pointer(g),C.c_void_p),C.c_void_p(self.q),C.pointer(self.flags),
                             C.pointer(self.finish),C.cast(C.pointer(self.rune),C.c_void_p),C.pointer(self.end),C.pointer(self.counter),
                             C.cast(C.pointer(self.damage),C.c_void_p),C.pointer(self.player),self.classes,1,C.pointer(self.extra))
        self.hooks=Hooks(None,self.new_cb,C.cast(C.pointer(self.gen_hooks),C.c_void_p))
    # field name -> (object, attribute or (attribute, index))
    def targets(self):
        r,pv,s,p,g,m,f,fin,x,pl=self.r,self.p,self.state.selection,self.path_state,self.gen,self.m,self.flags,self.finish,self.extra,self.player
        t=dict(turn=(p,'turn'),ui_health=(r,'ui_health'),ui_ceiling=(pl,'ui_health_ceiling_5998'),ui_xp=(r,'ui_xp'),ui_up=(r,'ui_up'),
               ui_gold=(r,'ui_gold'),ui_skull=(pl,'ui_skull_59c8'),phase=(self.damage,'phase'),tokens_b53c=(x,'tokens_b53c'),
               tokens_b54c=(x,'tokens_b54c'),health=(r,'health'),health_max=(r,'health_max'),health_bonus=(r,'health_bonus'),
               armour_current=(pv,'armour_current'),armour_max=(pv,'armour_max'),xp=(r,'xp'),up=(r,'up'),gold=(r,'gold'),
               base_damage=(s,'base_damage'),xp_fraction=(r,'xp_fraction'),gold_fraction=(r,'gold_fraction'),up_fraction=(r,'up_fraction'),
               base_bde8=(x,('base_bde8',0)),base_bdf0=(x,('base_bde8',1)),base_bdf8=(x,('base_bde8',2)),base_be00=(x,('base_bde8',3)),
               healing_value=(pv,'healing_value'),shield_value=(pv,'shield_value'),chance_be20=(m,('bonus_chance',0)),
               chance_be28=(m,('bonus_chance',1)),chance_be18=(m,('bonus_chance',2)),chance_be30=(m,('bonus_chance',3)),
               level=(r,'level'),total_xp=(r,'total_xp'),total_gold=(r,'total_gold'),total_up=(r,'total_up'),
               current_damage=(s,'current_damage'),skill_count=(r,'skill_count'),current_leech=(s,'current_leech'),
               time_to_promotion=(g,'time_to_promotion'),flame=(s,'current_flame_damage'),spike=(s,'current_spike_damage'),
               poison=(r,'poison'),spawn_count=(m,'spawn_count_1555c'),value_164d4=(x,'value_164d4'),kills_a=(p.battle,'kills_a'),
               vertical_offset=(s.geometry,'offset'),total=(p,'total'),round_kills=(pv,'total'),
               crossing_samples=(p,'crossing_samples'),crossing_average=(p,'crossing_average'),crossing_best=(p,'crossing_best'),
               tokens_0=(x,'tokens_type0_165d8'),tokens_4=(x,'tokens_type4_165e8'),bonus_0=(x,'bonus_type0_165ec'),bonus_4=(x,'bonus_type4_165fc'),
               input_ready=(p,'input_ready'),cooldown=(pl,'skill_cooldown_be64'),flag_bf88=(x,'flag_bf88'),filter_enabled=(g,'filter_enabled'),
               filter_swords=(g,'filter_swords'),coin=(p.battle,'coin_on_attack'),next_coin=(f,'next_coin_bfbc'),
               label_bfc0=(x,('label_active',0)),label_14afc=(x,('label_active',1)),label_14e70=(x,('label_active',2)),
               label_151e4=(x,('label_active',3)),promotion_enabled=(g,'promotion_enabled'),one_health=(g,'one_health'),
               force_coins=(g,'force_coins'),next_one_health=(fin,'next_one_health_14af7'),next_force_coins=(fin,'next_force_coins_14af8'),
               flame_moving=(s,'flame_label_moving'),spiky=(s,'spiky_enemy_attacked'),spike_moving=(s,'spike_label_moving'),
               flag_1554c=(fin,'flag_1554c'),b15561=(f,'b15561'),b15562=(f,'b15562'),inhibit=(g,'inhibit_force_coins'),
               rune_enabled=(self.rune,'enabled'),arrow_hold=(f,'arrow_hold_16492'),guard_164a4=(r,'guard_164a4'),
               revive_second=(self.end,'revive_second'),guard_164a6=(r,'guard_164a6'),prev_164a7=(f,'prev_164a7'),
               next_164a8=(f,'next_164a8'),victory=(self.end,'victory'),double_0=(s,'double_damage'),double_1=(pv,'double_upgrade'),
               double_2=(pv,'double_healing'),double_3=(pv,'double_gold'))
        t.update({f'next_be78_{i}':(f,('next_be78',i)) for i in range(4)})
        return t
    def get_field(self,k):
        if k=='counterattack':return self.counter.value
        if k in ('tokens_pending','bonus_total') or k[:7] in ('tokens_','bonus_1','bonus_2','bonus_3') and k[-1] in '123' and k not in ('tokens_b53c','tokens_b54c'):
            c=self.token_counters()
            if k=='tokens_pending':return c.pending
            if k=='bonus_total':return c.bonus_total
            i=int(k[-1])-1;return (c.normal if k.startswith('tokens') else c.bonus)[i]
        obj,attr=self.targets()[k]
        v=getattr(obj,attr[0])[attr[1]] if isinstance(attr,tuple) else getattr(obj,attr)
        if isinstance(v,float):return bits(v)
        return v
    def set_field(self,k,v):
        if k=='counterattack':return
        if k in ('tokens_pending','bonus_total') or k[:7] in ('tokens_','bonus_1','bonus_2','bonus_3') and k[-1] in '123' and k not in ('tokens_b53c','tokens_b54c'):
            return   # token counters come from the shared token loader (verify_tokens.py)
        obj,attr=self.targets()[k]
        cur=getattr(obj,attr[0])[attr[1]] if isinstance(attr,tuple) else getattr(obj,attr)
        if isinstance(cur,float):v=struct.unpack('<f',struct.pack('<i',v))[0]
        if isinstance(attr,tuple):getattr(obj,attr[0])[attr[1]]=v
        else:setattr(obj,attr,v)
    def token_counters(self):
        from verify_tokens import Counters
        fn=self.tokens_lib.dr_token_queue_counters;fn.restype=C.POINTER(Counters);fn.argtypes=[C.c_void_p]
        return fn(C.c_void_p(self.q)).contents
    def run(self):
        self.new_events=[];self.gen_events=[]
        self.init_fn(C.byref(self.state_obj),self.case_time,C.byref(self.hooks))
        fields={k:self.get_field(k) for k in list(INTS)+list(BYTES)}
        fields['skill_bytes']=[list(self.extra.skill_ff[i]) for i in range(4)]
        s=self.state.selection;tiles=[]
        for t in s.tiles:
            tiles.append([t.rule.x,t.rule.y,bits(t.geometry.center.x),bits(t.geometry.center.y),bits(t.size),bits(t.geometry.size),
                          bits(t.resting.x),bits(t.resting.y)])
        return dict(new_events=self.new_events,fields=fields,tiles=tiles,**self.gen_status())

TOKEN_FIELDS={'tokens_pending','bonus_total','tokens_1','tokens_2','tokens_3','bonus_1','bonus_2','bonus_3'}
FLOAT_FIELDS={'xp_fraction','gold_fraction','up_fraction','vertical_offset'}
def case(rng):
    c,_=scenario(rng);g=c['game']
    g['flaws']=[rng.choice([1,4,8,255,255]),rng.choice([1,4,8,255,255]),255,255];c['match']['perks']=[rng.choice([4,7,9,255]),rng.choice([4,7,9,255]),255,255]
    c['record']=rng.randrange(2);c['mode']=rng.randrange(3)
    ints={k:rng.choice([0,1,7,-3,rng.randrange(1000)]) for k in INTS if k not in TOKEN_FIELDS and k not in FLOAT_FIELDS}
    ints.update({k:struct.unpack('<i',struct.pack('<f',rng.choice([0.0,0.5,0.75])))[0] for k in FLOAT_FIELDS})
    if rng.random()<.3:ints['ui_skull']=3   # interface already showing the starting values
    if rng.random()<.3:ints['ui_ceiling']=40
    if rng.random()<.3:ints['ui_health']=40
    for k in ('ui_xp','ui_up','ui_gold'):
        if rng.random()<.4:ints[k]=0
    byt={k:rng.choice([0,1,1,0xff]) for k in BYTES}
    classes=[[rng.choice([0,i,rng.randrange(10)]),rng.randrange(10),rng.choice([0,0,1,5,9,10])] for i in range(10)]
    if rng.random()<.2:
        for k in classes[1:]:k[2]=10
    c['new_game']=dict(time=rng.getrandbits(32),ints=ints,bytes=byt,classes=classes,skill_bytes=[[rng.randrange(256) for _ in range(4)] for _ in range(4)])
    t=c['tokens'];t.update(allocated=rng.choice([0,2,5]),normal=[rng.randrange(5) for _ in range(3)],bonus=[rng.randrange(5) for _ in range(3)],bonus_total=rng.randrange(9))
    t['pending']=rng.randrange(t['allocated']+1)   # reset to 0 by InitNewGame
    c['moving_list']=rng.choice([[],[3,4]]);c['gate']=dict(tokens_pending=0,flare_count=0,phase=0,touch_phase=0,input_target=-1,rune=0)
    return c

def main():
    old,new=Original(),Native();rng=random.Random(0x15c50);compared=0;seen={}
    for n in range(200):
        c=case(rng);old.load(c);new.load(c);a,b=old.run(),new.run()
        if a!=b:
            (HERE/'new_game_failure.json').write_text(json.dumps(dict(case=c,original=a,native=b),indent=2))
            raise AssertionError('new_game_failure.json')
        compared+=1;f=a['fields'];ev=a['new_events']
        for k in ('time_to_promotion','base_damage','chance_be18','chance_be30'):seen.setdefault(k,set()).add(f[k])
        seen.setdefault('health_bars',set()).add(sum(1 for e in ev if e[0]==KINDS['health_bar']))
        for k in ('skull','xp_bar','up_bar','gold_bar'):seen.setdefault(k,set()).add(any(e[0]==KINDS[k] for e in ev))
        seen.setdefault('achievements',set()).update(e[2] for e in ev if e[0]==KINDS['achievement'])
        seen.setdefault('health_max',set()).add(f['health_max'])
    # record-mode promotion 200 / flaw 8 49 / 50; perk 4, perk 7, flaw 4; both health bars, unchanged
    # interface values; class achievements incl. all classes maxed (28); health 100 (record mode 1), perk 9, flaw 1
    need=dict(time_to_promotion={200,49,50},base_damage={3,4},chance_be18={20,30},chance_be30={20,10},health_bars={0,1,2},
              skull={True,False},xp_bar={True,False},up_bar={True,False},gold_bar={True,False})
    missing={k:v-seen[k] for k,v in need.items() if not v<=seen[k]}
    assert not missing and 28 in seen['achievements'] and {100,40,50,30}<=seen['health_max'],(missing,seen)
    report=dict(status='passed',comparisons=compared,outcomes={k:sorted(v) for k,v in seen.items()},
                functions=[dict(symbol='__ZN4Game11InitNewGameEv',address=hex(ENTRY),native='dr_init_new_game'),
                           dict(symbol='__ZN4Game22CalculateTilePositionsEv',address=hex(CTP),native='dr_calculate_tile_positions')],
                original='Actual InitNewGame with original SetRandSeed/FlushRandSeeds, UnlockAchievement, HavePerk/HaveFlaw, PositionTile, RandomiseTile',
                boundaries=['time() returns the case seed','Item deletion/construction recorded (Item::Initialise/GenerateName/GenerateStats/MakeStats)',
                            'UpdateStats recorded (dr_update_stats in an embedding)','Interface values/bars/Reset, tile labels, Quad::SetSize, turn label recorded',
                            'presentation label fields Game+0x5e30..0x5e47 and item pointers not compared'],
                scope='every Game field InitNewGame stores (write trace), 36 tiles, generation/refill board state and events, RNG seeds')
    (HERE/'new_game_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
