#!/usr/bin/env python3
"""Item generation (T040-K3a): actual Item::Initialise(Item*) 0x2a584 (a shop item from an equipped one) and the
new-item steps of Item(Game*, ItemType) -- Item::Initialise(ItemType) 0x264a8, GenerateName(0) 0x263a0,
GenerateStats(0) 0x29e04 -- vs native dr_item_make (recovered_items), on the shared state of verify_menu_level.py.

Item::InitialiseNames 0x26acc runs once as original code (its std::vector storage on a bump heap:
operator new, delete and memmove answered here), so GenerateName reads the real name tables. Then the functions
run from their entries with GenerateName, GenerateStats, ItemUpgrade::IsUpgradeAllowed / GetRandomStat /
GetStatUpgrade / GetStatDowngrade, CharacterClass::HaveFlaw / HavePerk and RandI / Rand as original code;
std::set<int> (GetRandomStat's pool, GenerateStats' set of positive stats) as in verify_menu_level.py;
Item::MakeStats (the item text), Upgrade::SetIcon and sprintf skipped. Compared: the item's type, icon, name prefix
level and index, name index, its 20 stats, and the random seeds.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_menu_level import Original as LevelOriginal, Native as LevelNative, case as level_case
from verify_stats import ItemStats, AttackInputs, PlayerStats, StatsTargets, Resource
from verify_stroke import HERE, I32, U8

ITEM_INIT,ITEM_COPY,GEN_NAME,GEN_STATS,NAMES=0x264a8,0x2a584,0x263a0,0x29e04,0x26acc
NEW,DELETE,MEMMOVE=0x194d54,0x194d4c,0x194ef4
ITEM,EXISTING,HEAP=0x1709800,0x1709c00,0x1780000
CLASS0=0x15564
FIELDS=((0x80,'type'),(0x84,'icon'),(0x88,'prefix_level'),(0x8c,'prefix'),(0x90,'name'))
class ItemRecord(C.Structure):_fields_=[(k,I32) for _,k in FIELDS]+[('stats',ItemStats)]

class Original(LevelOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text()
        addr=lambda s:int(re.search(r'^'+re.escape(s)+r':\n\s*([0-9a-f]+):',text,re.M)[1],16)
        self.make_stats=addr('__ZN4Item9MakeStatsEv');self.u.mem_map(HEAP,0x80000);self.heap=HEAP;self.naming=False;self.names_ready=False
        assert addr('__ZN4Item10InitialiseEPS_')==ITEM_COPY and addr('__ZN4Item15InitialiseNamesEv')==NAMES
    def hook(self,u,address,size,context):
        if self.naming:
            if address==NEW:n=u.reg_read(self.regs[0]);u.reg_write(self.regs[0],self.heap);self.heap+=(n+15)&~15;u.reg_write(self.PC,u.reg_read(self.LR));return
            if address==DELETE:u.reg_write(self.PC,u.reg_read(self.LR));return
            if address==MEMMOVE:
                d,s,n=(u.reg_read(self.regs[i]) for i in range(3));u.mem_write(d,bytes(u.mem_read(s,n)));u.reg_write(self.PC,u.reg_read(self.LR));return
        if self.menuing and address==self.make_stats:u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def call(self,entry,args,flag):
        u=self.u
        for reg,v in zip(self.regs,args):u.reg_write(reg,v&0xffffffff)
        u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1);setattr(self,flag,True)
        try:u.emu_start(entry|1,self.STOP,timeout=0,count=5000000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:setattr(self,flag,False)
    def load(self,c):
        super().load(c);G=self.GAME;k=c['item']
        if not self.names_ready:self.call(NAMES,[],'naming');self.names_ready=True   # the name tables, once (static data)
        self.write(G+0x1648c,0)
        for i,p in enumerate(k['perks']):self.write(G+CLASS0+0x10+4*i,p)
        for i,f in enumerate(k['flaws']):self.write(G+CLASS0+0x20+4*i,f)
        for a,v in ((0xbe60,k['leech']),(0xbdcc,k['break']),(0xbdc8,k['loss']),(0xbe6c,k['weaken'])):self.write(G+a,v&0xffffffff)
        for a,v in ((0xbdd4,k['xp']),(0xbddc,k['gold']),(0xbde4,k['upgrade'])):self.u.mem_write(G+a,struct.pack('<f',v))
        for base,rec in ((ITEM,k['stale']),(EXISTING,k['existing'])):
            self.write(base+0x7c,G)
            for off,key in FIELDS:self.write(base+off,rec[key]&0xffffffff)
            for j,v in enumerate(rec['stats']):self.write(base+0x94+4*j,v&0xffffffff)
    def make(self,kind):
        if kind=='copy':self.call(ITEM_COPY,[ITEM,EXISTING],'menuing')
        else:
            self.call(ITEM_INIT,[ITEM,self.read(EXISTING+0x80)],'menuing');self.call(GEN_NAME,[ITEM,0],'menuing');self.call(GEN_STATS,[ITEM,0],'menuing')
        s=lambda a:C.c_int32(self.read(a)).value
        return dict(item={key:s(ITEM+off) for off,key in FIELDS},stats=[s(ITEM+0x94+4*j) for j in range(20)],
                    seeds=list(struct.unpack('<6I',self.u.mem_read(0x1eac20,24))))

class Native(LevelNative):
    def __init__(self):
        super().__init__();lib=self.items_lib=C.CDLL(str(HERE/'recovered_items_native.dylib'))
        lib.dr_item_make.argtypes=[C.POINTER(StatsTargets),C.POINTER(ItemRecord),I32,C.POINTER(ItemRecord)];lib.dr_item_make.restype=None
    def load(self,c):
        super().load(c);k=c['item']
        self.m.perks=(I32*4)(*k['perks']);sel=self.state.selection;sel.character.flaws=(I32*4)(*k['flaws']);sel.leech=k['leech']
        self.path_state.battle.break_chance=k['break'];self.attack=AttackInputs(k['loss'],k['weaken'],0);self.regen=I32(0);self.player=PlayerStats()
        self.p.xp_bonus,self.p.gold_bonus,self.p.upgrade_bonus=k['xp'],k['gold'],k['upgrade']
        self.targets=StatsTargets(C.cast(C.pointer(self.r),C.POINTER(Resource)),C.cast(C.pointer(self.p),C.c_void_p),C.cast(C.pointer(self.state),C.c_void_p),
                                  C.cast(C.pointer(self.path_state.battle),C.c_void_p),C.pointer(self.attack),C.pointer(self.regen),C.pointer(self.player))
        def rec(r):return ItemRecord(*[r[key] for _,key in FIELDS],ItemStats((I32*20)(*r['stats'])))
        self.item=rec(k['stale']);self.existing=rec(k['existing'])
    def make(self,kind):
        self.items_lib.dr_item_make(C.byref(self.targets),C.byref(self.item),self.existing.type,C.byref(self.existing) if kind=='copy' else None)
        return dict(item={key:getattr(self.item,key) for _,key in FIELDS},stats=list(self.item.stats.upgrade),seeds=list(self.m.random.seeds))

def case(rng):
    c=level_case(rng);c['record']=int(rng.random()<.3);c['mode']=rng.choice([0,1,2])
    def stats():
        s=[0]*20
        for j in rng.sample(range(20),rng.randrange(1,9)):s[j]=rng.choice([1,2,3,5,10,rng.randrange(-2,30)])
        return s
    def record():
        return dict(type=rng.randrange(5),icon=rng.randrange(400),prefix_level=rng.choice([-1,-1,0,5,135,136,137,147,rng.randrange(-1,148)]),prefix=rng.randrange(-1,148),
                    name=rng.randrange(20),stats=stats())
    f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
    c['item']=dict(stale=record(),existing=record(),perks=rng.choice([[255]*4,[5,255,255,255],[rng.randrange(10)]*4]),
                   flaws=rng.choice([[255]*4,[6,255,255,255],[rng.randrange(10),255,255,255]]),leech=rng.choice([0,10,24,25,rng.randrange(60)]),
                   break_=0,break_chance=0,
                   **{'break':rng.choice([50,94,95,rng.randrange(101)]),'loss':rng.choice([50,11,10,rng.randrange(-5,120)]),
                      'weaken':rng.choice([0,0,1,3,rng.randrange(10)]),'xp':f32(rng.choice([0,1.0,1.75,2.0,2.5])),
                      'gold':f32(rng.choice([0,1.0,2.0])),'upgrade':f32(rng.choice([0,0.5,2.0]))})
    return c

def main():
    old,new=Original(),Native();rng=random.Random(0x29e04);n=1500;kinds={};types={}
    for i in range(n):
        c=case(rng);old.load(c);new.load(c);kind=rng.choice(['copy','copy','copy','new'])
        a,b=old.make(kind),new.make(kind)
        if a!=b:
            (HERE/'items_failure.json').write_text(json.dumps(dict(case=i,kind=kind,item=c['item'],record=c['record'],mode=c['mode'],original=a,native=b),indent=2))
            raise AssertionError('items_failure.json')
        kinds[kind]=kinds.get(kind,0)+1;t=c['item']['existing']['type'];types[t]=types.get(t,0)+1
    assert set(types)=={0,1,2,3,4},types
    report=dict(status='passed',comparisons=n,kinds=kinds,item_types=dict(sorted(types.items())),
                functions=[dict(symbol='__ZN4Item10InitialiseEPS_',address=hex(ITEM_COPY),native='dr_item_make (from an existing item)'),
                           dict(symbol='__ZN4Item13GenerateStatsEPS_',address=hex(GEN_STATS),native='dr_item_generate_stats'),
                           dict(symbol='__ZN4Item12GenerateNameEPS_',address=hex(GEN_NAME),native='dr_item_generate_name'),
                           dict(symbol='__ZN11ItemUpgrade13GetRandomStatEibP4Game',address='0x2d314',native='dr_random_item_stat')],
                original='Actual item functions after the original InitialiseNames',
                boundaries=['std::set<int> modelled; MakeStats, SetIcon, sprintf skipped'])
    (HERE/'items_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
