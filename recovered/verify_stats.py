#!/usr/bin/env python3
"""Actual Game::UpdateStats 0x14c04 and Game::DestroyUpgrade 0x1515c vs native dr_update_stats /
dr_destroy_upgrade (recovered_stats), on the shared state of verify_attack_all.py.

The whole original function runs from its entry (R0=Game). Its helpers run as original code:
CharacterClass::HaveFlaw, Skill::GetStat / GetStatChance, ItemUpgrade::GetFloatValue and
std::vector<Item**>::size. The equipped items are laid out by the harness: Item objects with
their 20 upgrade stats at Item+0x94, an Item** vector at Game+0xbe9c. Interface::UpdateHealthBar /
UpdateSwordValue / UpdateSkullValue / UpdateShieldValue / UpdateSkills are recorded.
DestroyUpgrade runs whole as well: RandI, Item::ReduceStat, ItemUpgrade::GetStatDowngrade /
GetStatUpgrade, CharacterClass::HavePerk and UpdateStats as original code; its std::vector<int>
is modelled by the harness; Item::MakeStats (item text), labels, sounds and achievements are recorded.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_attack_all import Original as AllOriginal, Native as AllNative, scenario
from verify_resources import Resource
from verify_stroke import HERE, I32, U8

ENTRY,END=0x14c04,0x15150
DESTROY,DESTROY_END,REDUCE,REDUCE_END=0x1515c,0x1528c,0x29d9c,0x29de0
INT_DATA=0x16bd000
ITEMS,ITEM_PTRS,ITEM_VECTOR=0x16c0000,0x16bf000,0x16be000
INTERFACE,HEALTH_QUAD=0x4cdc,0x4d4c
SYMBOLS={'__ZN9Interface15UpdateHealthBarER4Quadi':'health_bar','__ZN9Interface16UpdateSwordValueEv':'sword',
         '__ZN9Interface16UpdateSkullValueEv':'skull','__ZN9Interface17UpdateShieldValueEv':'shield','__ZN9Interface12UpdateSkillsEv':'update_skills'}
DESTROY_SYMBOLS={'__ZN4Item9MakeStatsEv':'item_text','__ZN4Game16QueueAchievementE11Achievementf':'achievement',
    '__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif':'label','__ZN4Game10QueueSoundE5Sound':'sound',
    '__ZNSt6vectorIiSaIiEE9push_backERKi':'vector_push','__ZNKSt6vectorIiSaIiEE4sizeEv':'vector_size','__ZNSt6vectorIiSaIiEED2Ev':'vector_free'}
STUBS={0x194cec:'unwind',0x194cf4:'unwind'}
INTS=dict(health=0xbd98,health_max=0xbd9c,health_bonus=0xbda0,ui_health=0x5994,ui_armour=0x59c0,armour_current=0xbda4,armour_max=0xbda8,
          healing_bonus=0xbe0c,shield_bonus=0xbe14,weapon_damage=0xbdbc,base_damage=0xbdc0,bonus_base_damage=0xbdc4,leech=0xbe60,
          break_chance=0xbdcc,poison_amount=0xbe5c,armour_loss_chance=0xbdc8,weaken=0xbe6c,damage_all=0xbe68,regen=0xbe70,
          base_bdec=0xbdec,base_bdf4=0xbdf4,base_bdfc=0xbdfc,base_be04=0xbe04,chance_be1c=0xbe1c,chance_be24=0xbe24,
          chance_be2c=0xbe2c,chance_be34=0xbe34,ui_health_ceiling_5998=0x5998,ui_sword_59bc=0x59bc,ui_armour_max_59c4=0x59c4,ui_skull_59c8=0x59c8)
FLOATS=dict(xp_bonus=0xbdd4,gold_bonus=0xbddc,upgrade_bonus=0xbde4)
PLAYER=['base_bdec','base_bdf4','base_bdfc','base_be04','chance_be1c','chance_be24','chance_be2c','chance_be34']
UI=['ui_health_ceiling_5998','ui_sword_59bc','ui_armour_max_59c4','ui_skull_59c8']
class ItemStats(C.Structure):_fields_=[('upgrade',I32*20)]
class PlayerStats(C.Structure):_fields_=[(k,I32) for k in PLAYER]+[('skill_cooldown_be64',U8)]+[(k,I32) for k in UI]
class AttackInputs(C.Structure):_fields_=[('armour_loss_chance',I32),('weaken',I32),('damage_all',I32)]
class StatsTargets(C.Structure):
    _fields_=[('resources',C.POINTER(Resource)),('preview',C.c_void_p),('stroke',C.c_void_p),('battle',C.c_void_p),
              ('attack',C.POINTER(AttackInputs)),('regen',C.POINTER(I32)),('player',C.POINTER(PlayerStats))]
class StatsEvent(C.Structure):_fields_=[(k,I32) for k in ('kind','tile','a','b','c','d')]
EVENT=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(StatsEvent))
class StatsHooks(C.Structure):_fields_=[('context',C.c_void_p),('event',EVENT)]
bits=lambda f:struct.unpack('<I',struct.pack('<f',f))[0]
from_bits=lambda b:struct.unpack('<f',struct.pack('<I',b))[0]

class Original(AllOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.stats_calls={};self.stats_visits={};self.updating=False
        for symbol,name in SYMBOLS.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol;self.stats_calls[int(m[1],16)]=name
        assert re.search(r'^__ZN4Game11UpdateStatsEv:\n\s*14c04:',text,re.M)
        self.destroy_calls=dict(STUBS);self.destroying=False
        for symbol,name in DESTROY_SYMBOLS.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol;self.destroy_calls[int(m[1],16)]=name
    def hook(self,u,address,size,context):
        if self.destroying:
            lr=u.reg_read(self.LR)&~1;name=self.destroy_calls.get(address)
            if DESTROY<=address<DESTROY_END or 0x2d774<=address<0x2d958:self.stats_visits[hex(address)]=self.stats_visits.get(hex(address),0)+1
            if name and (DESTROY<lr<=DESTROY_END or REDUCE<lr<=REDUCE_END):
                r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value;sp=u.reg_read(self.SP);e=None
                if name=='item_text':i,rest=divmod(r[0]-ITEMS,0x100);assert rest==0;e=['item_text',i]
                elif name=='achievement':e=['achievement',r[1],s(r[2])]
                elif name=='label':
                    i,rest=divmod(r[2]-0x54-self.GAME-0x5e58,608);assert rest==0
                    e=['label',i,r[1],s(r[3]),s(self.read(sp)),s(self.read(sp+4))]
                elif name=='sound':e=['sound',r[1]]
                elif name=='vector_push':
                    values=self.int_vectors.setdefault(r[0],[]);values.append(self.read(r[1]))
                    for k,v in enumerate(values):self.write(INT_DATA+4*k,v)
                    self.write(r[0],INT_DATA);self.write(r[0]+4,INT_DATA+4*len(values));self.write(r[0]+8,INT_DATA+4*len(values))
                elif name=='vector_size':u.reg_write(self.regs[0],len(self.int_vectors.get(r[0],[])))
                elif name=='vector_free':self.int_vectors.pop(r[0],None)
                if e:self.stats_events.append(e)
                u.reg_write(self.PC,u.reg_read(self.LR));return
        if self.updating:
            if ENTRY<=address<END:self.stats_visits[hex(address)]=self.stats_visits.get(hex(address),0)+1
            name=self.stats_calls.get(address)
            if name and ENTRY<u.reg_read(self.LR)&~1<=END:
                r=[u.reg_read(v) for v in self.regs]
                assert r[0]==self.GAME+INTERFACE
                if name=='health_bar':assert r[1]==self.GAME+HEALTH_QUAD;self.stats_events.append(['health_bar',C.c_int32(r[2]).value])
                else:self.stats_events.append([name])
                u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def load(self,c):
        super().load(c);s=c['stats']
        self.write(self.GAME+0x1648c,0)   # active class index: class 0 (flaws/perks written there by the shared loaders)
        for k,o in INTS.items():self.write(self.GAME+o,s[k])
        for k,o in FLOATS.items():self.write(self.GAME+o,bits(s[k]))
        self.u.mem_write(self.GAME+0xbe64,bytes([s['skill_cooldown_be64']]))
        self.write(self.GAME+0xbfa0,s['skill_count'])
        for i in range(4):
            base=0x1700000+0x100*i;self.write(self.GAME+0xbf90+4*i,base)
            self.write(base+0x8c,s['skill_max'][i]);self.write(base+0x90,s['skill_current'][i])
        for i,item in enumerate(s['items']):
            for k,v in enumerate(item):self.write(ITEMS+0x100*i+0x94+4*k,v)
            self.write(ITEMS+0x100*i+0x7c,self.GAME)   # Item::game (ReduceStat passes it to GetStatDowngrade)
            self.write(ITEM_PTRS+4*i,ITEMS+0x100*i);self.write(ITEM_VECTOR+4*i,ITEM_PTRS+4*i)
        self.write(self.GAME+0xbe9c,ITEM_VECTOR);self.write(self.GAME+0xbea0,ITEM_VECTOR+4*len(s['items']));self.write(self.GAME+0xbea4,ITEM_VECTOR+0x100)
    def stats(self):
        self.stats_events=[];self.updating=True;u=self.u
        u.reg_write(self.regs[0],self.GAME);u.reg_write(self.SP,0x140ff00);u.reg_write(self.LR,self.STOP|1)
        try:u.emu_start(ENTRY|1,self.STOP,timeout=0,count=1000000);assert u.reg_read(self.PC)==self.STOP
        finally:self.updating=False
        result=self.read_stats();result['events']=self.stats_events[:];return result
    def read_stats(self):
        out={k:C.c_int32(self.read(self.GAME+o)).value for k,o in INTS.items()}
        out.update({k:self.read(self.GAME+o) for k,o in FLOATS.items()})
        out['skill_cooldown_be64']=self.u.mem_read(self.GAME+0xbe64,1)[0]
        out['skills']=[[C.c_int32(self.read(0x1700000+0x100*i+o)).value for o in (0x8c,0x90)] for i in range(4)]
        return dict(stats=out)
    def destroy(self,tile,count):
        self.int_vectors={};self.destroying=self.updating=True;u=self.u;self.stats_events=[]
        u.reg_write(self.regs[0],self.GAME);u.reg_write(self.regs[1],self.tile(tile));u.reg_write(self.SP,0x140ff00);u.reg_write(self.LR,self.STOP|1)
        try:u.emu_start(DESTROY|1,self.STOP,timeout=0,count=2000000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.destroying=self.updating=False
        result=self.read_stats();result['events']=self.stats_events[:]
        result['items']=[[C.c_int32(self.read(ITEMS+0x100*i+0x94+4*k)).value for k in range(20)] for i in range(count)]
        result['seeds']=list(struct.unpack('<6I',self.u.mem_read(0x1eac20,24)))
        return result

class Native(AllNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_stats_native.dylib'))
        self.stats_fn=lib.dr_update_stats
        self.stats_fn.argtypes=[C.POINTER(StatsTargets),C.POINTER(C.POINTER(ItemStats)),C.c_uint32,C.POINTER(StatsHooks)];self.stats_fn.restype=None
        self.destroy_fn=lib.dr_destroy_upgrade
        self.destroy_fn.argtypes=[C.POINTER(StatsTargets),C.POINTER(C.POINTER(ItemStats)),C.c_uint32,C.c_uint32,C.POINTER(StatsHooks)];self.destroy_fn.restype=None
        def event(_,p):
            e=p.contents;k=e.kind;ev=self.stats_events.append
            if k==1:ev(['health_bar',e.a])
            elif k in (2,3,4,5):ev([{2:'sword',3:'skull',4:'shield',5:'update_skills'}[k]])
            elif k==6:ev(['item_text',e.a])
            elif k==7:ev(['achievement',e.a,e.b])
            elif k==8:ev(['label',e.tile,e.a,e.b,e.c,e.d])
            elif k==9:ev(['sound',e.a])
            else:raise AssertionError(k)
        self.stats_cb=EVENT(event);self.stats_hooks=StatsHooks(None,self.stats_cb)
    def load(self,c):
        super().load(c);s=c['stats'];r=self.r;p=self.p;sel=self.state.selection;b=self.path_state.battle
        for k in ('health','health_max','health_bonus','ui_health','ui_armour'):setattr(r,k,s[k])
        for k in ('armour_current','armour_max','healing_bonus','shield_bonus','xp_bonus','gold_bonus','upgrade_bonus'):setattr(p,k,s[k])
        for k in ('weapon_damage','base_damage','bonus_base_damage','leech'):setattr(sel,k,s[k])
        b.break_chance=s['break_chance'];b.poison_amount=s['poison_amount']
        self.attack=AttackInputs(s['armour_loss_chance'],s['weaken'],s['damage_all']);self.regen=I32(s['regen'])
        self.player=PlayerStats(*[s[k] for k in PLAYER],s['skill_cooldown_be64'],*[s[k] for k in UI])
        r.skill_count=s['skill_count'];r.skill_max=(I32*4)(*s['skill_max']);r.skill_current=(I32*4)(*s['skill_current'])
        self.items=[ItemStats((I32*20)(*item)) for item in s['items']]
        self.item_ptrs=(C.POINTER(ItemStats)*max(1,len(self.items)))(*[C.pointer(i) for i in self.items])
        self.targets=StatsTargets(C.pointer(r),C.cast(C.pointer(p),C.c_void_p),C.cast(C.pointer(self.state),C.c_void_p),
                                  C.cast(C.pointer(b),C.c_void_p),C.pointer(self.attack),C.pointer(self.regen),C.pointer(self.player))
    def stats(self):
        self.stats_events=[]
        self.stats_fn(C.byref(self.targets),self.item_ptrs,len(self.items),C.byref(self.stats_hooks))
        result=self.read_stats();result['events']=self.stats_events[:];return result
    def destroy(self,tile,count):
        self.stats_events=[]
        self.destroy_fn(C.byref(self.targets),self.item_ptrs,len(self.items),tile,C.byref(self.stats_hooks))
        result=self.read_stats();result['events']=self.stats_events[:]
        result['items']=[list(i.upgrade) for i in self.items];result['seeds']=list(self.m.random.seeds)
        return result
    def read_stats(self):
        r,p,sel,b,pl=self.r,self.p,self.state.selection,self.path_state.battle,self.player
        out=dict(health=r.health,health_max=r.health_max,health_bonus=r.health_bonus,ui_health=r.ui_health,ui_armour=r.ui_armour,
                 armour_current=p.armour_current,armour_max=p.armour_max,healing_bonus=p.healing_bonus,shield_bonus=p.shield_bonus,
                 weapon_damage=sel.weapon_damage,base_damage=sel.base_damage,bonus_base_damage=sel.bonus_base_damage,leech=sel.leech,
                 break_chance=b.break_chance,poison_amount=b.poison_amount,armour_loss_chance=self.attack.armour_loss_chance,
                 weaken=self.attack.weaken,damage_all=self.attack.damage_all,regen=self.regen.value,
                 **{k:getattr(pl,k) for k in PLAYER+UI})
        out.update({k:bits(getattr(p,k)) for k in FLOATS})
        out['skill_cooldown_be64']=pl.skill_cooldown_be64
        out['skills']=[[r.skill_max[i],r.skill_current[i]] for i in range(4)]
        return dict(stats=out)

def make_case(rng,min_items=0):
        c,_=scenario(rng);c['game']['flaws']=[rng.choice([5,255,7]),255,255,255]
        small=lambda:rng.choice([0,0,0,1,2,3,rng.randrange(-3,12)])
        items=[[small() for _ in range(20)] for _ in range(max(min_items,rng.choice([0,1,2,3,5,8])))]
        for item in items:
            if rng.random()<.2:item[5]=rng.choice([0,1])
            for k in (6,7,13):item[k]=rng.choice([0,1,2,4,9])
            if rng.random()<.1:item[4]=rng.choice([40,90])
            if rng.random()<.1:item[14]=rng.choice([30,60])
        if items and rng.random()<.15:   # armour loss chance lands exactly on the 4/5 boundary
            for item in items:item[14]=0
            items[0][14]=rng.choice([45,46,47])
        s=dict(items=items,record=rng.randrange(2),mode=rng.randrange(3),skill_count=rng.randrange(5),
               skill_max=[rng.randrange(1,8) for _ in range(4)],skill_current=[rng.randrange(0,9) for _ in range(4)],
               skill_cooldown_be64=rng.randrange(2),health=rng.randrange(-2,40),health_max=rng.randrange(10,40),health_bonus=rng.randrange(0,12),
               xp_bonus=rng.choice([0,.5,2.5]),gold_bonus=rng.choice([0,.25]),upgrade_bonus=rng.choice([0,1.75]))
        for k in INTS:
            if k not in s:s[k]=rng.choice([0,1,5,rng.randrange(-5,60)])
        if rng.random()<.3:s['ui_health']=s['health']
        c['stats']=s;c['record']=s['record'];c['mode']=s['mode']   # record/mode via the shared loaders
        return c

def main():
    old,new=Original(),Native();rng=random.Random(0x14C04);count=0;kinds={}
    for n in range(400):
        c=make_case(rng);old.load(c);new.load(c)
        a,b=old.stats(),new.stats()
        if a!=b:
            (HERE/'stats_failure.json').write_text(json.dumps(dict(case=c,original=a,native=b),indent=2))
            raise AssertionError('stats_failure.json')
        count+=1
        for e in a['events']:kinds[e[0]]=kinds.get(e[0],0)+1
    assert all(kinds.get(k) for k in ('health_bar','sword','skull','shield','update_skills'))
    # bonus up / down / unchanged, cooldown -1 / +1, health bonus skipped (record mode 1), clamps
    assert all(hex(x) in old.stats_visits for x in (0x14fd0,0x14fee,0x15052,0x150ec,0x150f6,0x14f28,0x14eea,0x14ef8,0x14da0)),old.stats_visits
    destroyed=0;rng=random.Random(0x1515C)
    for n in range(300):
        c=make_case(rng,min_items=1);c['match']['perks']=[rng.choice([5,1,255]),255,255,255]
        s=c['stats'];s['leech']=rng.choice([0,15,18,21,23]);s['armour_loss_chance']=rng.choice([5,12,13,14,17,18,20,40,120])
        for item in s['items']:
            if rng.random()<.3:item[rng.choice([2,10,14,17,3,4])]=rng.randrange(1,12)
        if rng.random()<.1:
            for item in s['items']:item[:]=[min(v,0) for v in item]   # no positive stat
        tile=rng.randrange(36);old.load(c);new.load(c)
        a,b=old.destroy(tile,len(s['items'])),new.destroy(tile,len(s['items']))
        if a!=b:
            (HERE/'stats_failure.json').write_text(json.dumps(dict(case=c,tile=tile,original=a,native=b),indent=2))
            raise AssertionError('stats_failure.json (destroy)')
        count+=1;destroyed+=sum(1 for e in a['events'] if e[0]=='item_text')
    # downgrade grades 2/3/5/10, upgrade 0/1/2/10 and both perk outcomes, no positive stat
    assert destroyed and all(hex(x) in old.stats_visits for x in (0x2d948,0x2d94c,0x2d950,0x2d93e,0x2d798,0x2d882,0x2d88e,0x2d7c8,0x2d87c,0x2d87e,0x15218)),\
        sorted(k for k in old.stats_visits if k.startswith('0x2d'))
    report=dict(status='passed',comparisons=count,events=kinds,destroyed_stats=destroyed,
                functions=[dict(symbol='__ZN4Game11UpdateStatsEv',address=hex(ENTRY),native='dr_update_stats'),
                           dict(symbol='__ZN4Game14DestroyUpgradeEP4Tile',address=hex(DESTROY),native='dr_destroy_upgrade'),
                           dict(symbol='__ZN11ItemUpgrade16GetStatDowngradeE11UpgradeTypeP4Game',address='0x2d8a4',native='dr_stat_downgrade'),
                           dict(symbol='__ZN11ItemUpgrade14GetStatUpgradeE11UpgradeTypeP4Game',address='0x2d774',native='dr_stat_upgrade')],
                original='Actual UpdateStats with original HaveFlaw, Skill::GetStat/GetStatChance, ItemUpgrade::GetFloatValue',
                boundaries=['items laid out by the harness (Item+0x94 stats, Item** vector)','Interface value/bar updates recorded'],
                scope='Resources, preview, selection, battle, ProcessAttack inputs, regeneration, player stats, skill cooldowns',
                branch_visits=old.stats_visits)
    (HERE/'stats_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='branch_visits'}))

if __name__=='__main__':main()
