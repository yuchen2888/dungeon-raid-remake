#!/usr/bin/env python3
"""The shop (T040-K3b): actual FoldoutMenu::Initialise(1) 0x24a54, then FoldoutMenu::Process frame by frame up to
Game::SetItem 0x8b08 and Game::UpdateStats 0x14c04, vs native dr_menu_open_shop / dr_menu_process
(recovered_menu), as verify_menu_flow.py with the item functions of verify_items.py.

The original Initialise(1) runs from its entry with Game::GetItem, Item::Initialise(Item*) (GenerateName,
GenerateStats ... as in verify_items.py), Rand / RandI, Game::IsSkillUnlocked and Skill::CanActivate(int) on the
case's board as original code; std::set<ItemType> and std::vector<int> (the scroll candidates) are modelled
like std::set<int>. The five equipped items are at Game+0xbe88..0xbe98 with the Item** vector Game+0xbe9c that
UpdateStats reads. The scroll draw reads the 40 words at Game+0xbf90 (see docs/T040_MENU.md): the case writes
random words into the label memory Game+0xbfc4..0xc02f and the native side is given the same 40 words. Recorded
and skipped besides verify_menu_flow.py's calls: Tooltip::ShowScroll, Skill::Activate of the scroll object,
QueueAchievement and UpdateStats' interface refreshes (health bar, sword, skull, shield values, UpdateSkills).
Compared after every frame: the menu, its three items and scroll, the five equipped items (type, icon, name
indices, stats), every field UpdateStats writes, the random seeds and the events.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_menu_flow import Original as FlowOriginal, Native as FlowNative, case as flow_case, trim, bits
from verify_items import Original as ItemsOriginal, Native as ItemsNative, ItemRecord, FIELDS, case as items_case
from verify_menu_level import MenuSources, FM, EVENT
from verify_stats import INTS as STATS_INTS, FLOATS as STATS_FLOATS, StatsHooks, EVENT as STATS_EVENT, PLAYER, UI
from verify_skills import SkillState
from verify_stroke import HERE, I32, U8

INIT=0x24a54
EQUIPPED,OPTION_ITEMS,SCROLL,VEC,VEC_DATA=0x17e0000,0x17e1000,0x17e2000,0x17e3000,0x17e4000
CLASSES,STRIDE=0x15564,388
ITEM_SETS={'__ZNSt8_Rb_treeI8ItemTypeS0_St9_IdentityIS0_ESt4lessIS0_ESaIS0_EE13_Rb_tree_implIS4_Lb0EEC2ERKSaISt13_Rb_tree_nodeIS0_EERKS4_':'init',
           '__ZNSt3setI8ItemTypeSt4lessIS0_ESaIS0_EE6insertERKS0_':'insert',
           '__ZNSt8_Rb_treeI8ItemTypeS0_St9_IdentityIS0_ESt4lessIS0_ESaIS0_EE5eraseESt23_Rb_tree_const_iteratorIS0_E':'erase_node',
           '__ZNSt8_Rb_treeI8ItemTypeS0_St9_IdentityIS0_ESt4lessIS0_ESaIS0_EE8_M_eraseEPSt13_Rb_tree_nodeIS0_E':'clear'}
VECTOR_OPS={'__ZNSt6vectorIiSaIiEE9push_backERKi':'push','__ZNKSt6vectorIiSaIiEE4sizeEv':'size','__ZNSt6vectorIiSaIiEED2Ev':'free'}
SHOP_CALLS={'__ZN7Tooltip10ShowScrollE9SkillTypeRK8GLfloat2':'scroll_tooltip','__ZN5Skill8ActivateEv':'activate_scroll',
            '__ZN4Game16QueueAchievementE11Achievementf':'achievement','__ZN9Interface16UpdateSwordValueEv':'sword',
            '__ZN9Interface17UpdateShieldValueEv':'shield'}
STAT_NAMES={1:'health_bar',2:'sword',3:'skull',4:'shield',5:'update_skills'}

class Original(FlowOriginal,ItemsOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text()
        addr=lambda s:int(re.search(r'^'+re.escape(s)+r':\n\s*([0-9a-f]+):',text,re.M)[1],16)
        self.set_ops.update({addr(s):n for s,n in ITEM_SETS.items()})
        self.vector_ops={addr(s):n for s,n in VECTOR_OPS.items()};self.shop_calls={addr(s):n for s,n in SHOP_CALLS.items()}
        # EQUIPPED.. lie in the heap page that verify_items maps (its allocator stays far below)
    def hook(self,u,address,size,context):
        if self.menuing:
            r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value;lr=u.reg_read(self.LR)
            op=self.set_ops.get(address)
            if op=='erase_node':
                v=s(self.read(r[1]+16));self.sets.setdefault(r[0],set()).discard(v);self.write_set(r[0]);u.reg_write(self.PC,lr);return
            vop=self.vector_ops.get(address)
            if vop:
                if vop=='push':
                    vals=self.vectors.setdefault(r[0],[]);vals.append(s(self.read(r[1])))
                    base=VEC_DATA+0x400*list(self.vectors).index(r[0])
                    for k,v in enumerate(vals):self.write(base+4*k,v&0xffffffff)
                    self.write(r[0],base);self.write(r[0]+4,base+4*len(vals));self.write(r[0]+8,base+0x400)
                elif vop=='size':u.reg_write(self.regs[0],len(self.vectors.get(r[0],[])))
                else:self.vectors.pop(r[0],None)
                u.reg_write(self.PC,lr);return
            name=self.shop_calls.get(address)
            if name:
                e={'scroll_tooltip':['scroll_tooltip',s(r[1])],'activate_scroll':['activate_scroll',s(self.read(r[0]+0x84))],
                   'achievement':['achievement',s(r[1]),r[2]],'sword':['sword'],'shield':['shield']}[name]
                self.menu_events.append(e);u.reg_write(self.PC,lr);return
        return super().hook(u,address,size,context)
    def load(self,c):
        super().load(c);G=self.GAME;k=c['shop'];self.vectors={}
        for i,rec in enumerate(k['equipped']):self.write_item(EQUIPPED+0x200*i,rec);self.write(G+0xbe88+4*i,EQUIPPED+0x200*i);self.write(VEC+4*i,G+0xbe88+4*i)
        self.write(G+0xbe9c,VEC);self.write(G+0xbea0,VEC+20);self.write(G+0xbea4,VEC+20)
        for i,rec in enumerate(k['options']):self.write_item(OPTION_ITEMS+0x200*i,rec);self.write(G+FM+0x38+4*i,OPTION_ITEMS+0x200*i)
        self.write(G+FM+0x44,OPTION_ITEMS+0x600)   # a fourth item object (Initialise places it; not an option)
        self.write(SCROLL+0x7c,G);self.write(G+FM+0x110,SCROLL)
        for off,key in ((0x84,'type'),(0x88,'level'),(0x8c,'max'),(0x90,'current')):self.write(SCROLL+off,k['scroll'][key]&0xffffffff)
        self.u.mem_write(SCROLL+0x80,bytes([k['scroll']['active']]));self.write(G+FM+0x10c,k['scroll_slot']&0xffffffff)
        self.write(G+CLASSES+STRIDE*c['menu']['class_index']+8,k['race'])
        for j,w in enumerate(k['label_words']):self.write(G+0xbfc4+4*j,w)
        for key,a in STATS_INTS.items():self.write(G+a,k['stats'][key]&0xffffffff)
        for key,a in STATS_FLOATS.items():self.u.mem_write(G+a,struct.pack('<f',k['stats'][key]))
        self.u.mem_write(G+0xbe64,bytes([k['stats']['cooldown']]))
    def write_item(self,base,rec):
        self.write(base+0x7c,self.GAME)
        for off,key in FIELDS:self.write(base+off,rec[key]&0xffffffff)
        for j,v in enumerate(rec['stats']):self.write(base+0x94+4*j,v&0xffffffff)
    def read_item(self,base):
        s=lambda a:C.c_int32(self.read(a)).value
        return dict(**{key:s(base+off) for off,key in FIELDS},stats=[s(base+0x94+4*j) for j in range(20)])
    def probe(self):return list(struct.unpack('<40I',self.u.mem_read(self.GAME+0xbf90,160)))
    def open_shop(self):
        u=self.u;G=self.GAME;self.menu_events=[]
        u.reg_write(self.regs[0],G+FM);u.reg_write(self.regs[1],1);u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1);self.menuing=True
        try:u.emu_start(INIT|1,self.STOP,timeout=0,count=5000000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.menuing=False
        return self.shop_status()
    def frame(self,phase,button,dt):super().frame(phase,button,dt);return self.shop_status()
    def shop_status(self):
        st=self.status();G=self.GAME;i32=lambda a:C.c_int32(self.read(a)).value
        st.pop('options');st.pop('slots');st.pop('stats')
        sc=self.read(G+FM+0x110)
        st.update(items=[self.read_item(self.read(G+FM+0x38+4*i)) for i in range(3)],equipped=[self.read_item(self.read(G+0xbe88+4*i)) for i in range(5)],
                  scroll_slot=i32(G+FM+0x10c),scroll=[i32(sc+0x84),i32(sc+0x88),i32(sc+0x8c),i32(sc+0x90)],
                  stats={key:i32(G+a) for key,a in STATS_INTS.items()}|{key:self.read(G+a) for key,a in STATS_FLOATS.items()}|{'cooldown':self.u.mem_read(G+0xbe64,1)[0]},
                  seeds=list(struct.unpack('<6I',self.u.mem_read(0x1eac20,24))))
        return st

class Native(FlowNative,ItemsNative):
    def __init__(self):
        super().__init__();lib=self.menu_lib
        lib.dr_menu_open_shop.argtypes=[C.c_void_p,C.POINTER(Sources),C.c_void_p];lib.dr_menu_open_shop.restype=None
        lib.dr_menu_process.argtypes=[C.c_void_p,C.POINTER(Sources),C.c_float,I32,I32,C.c_void_p];lib.dr_menu_process.restype=None
        def menu_event(_,p):
            e=p.contents
            if e.kind==9:self.menu_events.append(['scroll_tooltip',e.a])
            elif e.kind==10:self.menu_events.append(['activate_scroll',e.a])
            elif e.kind==11:self.menu_events.append(['achievement',e.a,e.b])
            else:self.flow_event(_,p)
        self.flow_event=self.menu_cb;self.shop_cb=EVENT(menu_event);self.menu_hooks.event=self.shop_cb
        def stats_event(_,p):
            e=p.contents;n=STAT_NAMES[e.kind];self.menu_events.append(['health_bar',e.a] if n=='health_bar' else [n])
        self.stats_cb=STATS_EVENT(stats_event);self.stats_hooks=StatsHooks(None,self.stats_cb)
    def load(self,c):
        super().load(c);k=c['shop'];r=self.r;p=self.p;sel=self.state.selection;b=self.path_state.battle;st=k['stats']
        from verify_menu_level import ItemRecord as MItem
        rec=lambda x:MItem(*[x[key] for _,key in FIELDS],(I32*20)(*x['stats']))
        self.equipped=(MItem*5)(*[rec(x) for x in k['equipped']])
        for i,x in enumerate(k['options']):self.menu.items[i]=rec(x)
        sc=self.menu.scroll;sc.type,sc.level,sc.max,sc.current,sc.active=(k['scroll'][key] for key in ('type','level','max','current','active'))
        self.menu.scroll_slot=k['scroll_slot'];self.classes[c['menu']['class_index']].race=k['race']
        for key in ('health','health_max','health_bonus','ui_health','ui_armour'):setattr(r,key,st[key])
        for key in ('armour_current','armour_max','healing_bonus','shield_bonus','xp_bonus','gold_bonus','upgrade_bonus'):setattr(p,key,st[key])
        for key in ('weapon_damage','base_damage','bonus_base_damage','leech'):setattr(sel,key,st[key])
        b.break_chance=st['break_chance'];b.poison_amount=st['poison_amount']
        self.attack.armour_loss_chance,self.attack.weaken,self.attack.damage_all=st['armour_loss_chance'],st['weaken'],st['damage_all'];self.regen.value=st['regen']
        for key in PLAYER+UI:setattr(self.player,key,st[key])
        self.player.skill_cooldown_be64=st['cooldown']
        self.targets.player=C.pointer(self.player)
        self.skill_state_obj=self.state_obj   # verify_skills' SkillState (board, resources ...)
        self.probe_words=(C.c_uint32*40)()
        s=self.sources
        self.shop_sources=Sources(*[getattr(s,f) for f,_ in MenuSources._fields_],C.addressof(self.equipped),C.addressof(self.targets),
                                  C.addressof(self.stats_hooks),C.addressof(self.skill_state_obj),C.addressof(self.probe_words))
    def set_probe(self,words):
        for i,w in enumerate(words):self.probe_words[i]=w
    def open_shop(self):
        self.menu_events=[];self.menu_lib.dr_menu_open_shop(C.addressof(self.menu),C.byref(self.shop_sources),C.addressof(self.menu_hooks))
        return self.shop_status()
    def frame(self,phase,button,dt):
        self.menu_events=[];self.menu_lib.dr_menu_process(C.addressof(self.menu),C.byref(self.shop_sources),dt,phase,button,C.addressof(self.menu_hooks))
        return self.shop_status()
    def shop_status(self):
        st=self.status();st.pop('options');st.pop('slots');st.pop('stats')
        item=lambda x:dict(**{key:getattr(x,key) for _,key in FIELDS},stats=list(x.stats))
        r=self.r;p=self.p;sel=self.state.selection;b=self.path_state.battle;a=self.attack
        stats=dict(health=r.health,health_max=r.health_max,health_bonus=r.health_bonus,ui_health=r.ui_health,ui_armour=r.ui_armour,
                   armour_current=p.armour_current,armour_max=p.armour_max,healing_bonus=p.healing_bonus,shield_bonus=p.shield_bonus,
                   weapon_damage=sel.weapon_damage,base_damage=sel.base_damage,bonus_base_damage=sel.bonus_base_damage,leech=sel.leech,
                   break_chance=b.break_chance,poison_amount=b.poison_amount,armour_loss_chance=a.armour_loss_chance,weaken=a.weaken,
                   damage_all=a.damage_all,regen=self.regen.value,**{key:getattr(self.player,key) for key in PLAYER+UI},
                   **{key:bits(getattr(p,key)) for key in STATS_FLOATS},cooldown=self.player.skill_cooldown_be64)
        sc=self.menu.scroll
        st.update(items=[item(x) for x in self.menu.items],equipped=[item(x) for x in self.equipped],scroll_slot=self.menu.scroll_slot,
                  scroll=[sc.type,sc.level,sc.max,sc.current],stats=stats,seeds=list(self.m.random.seeds))
        return st

class Sources(C.Structure):
    _fields_=MenuSources._fields_+[('equipped',C.c_void_p),('stats',C.c_void_p),('stats_hooks',C.c_void_p),('skills',C.c_void_p),('probe',C.c_void_p)]

def case(rng):
    c=flow_case(rng);it=items_case(rng);c['item']=it['item']
    c['menu']['class_index']=0   # verify_items' load uses class 0 (its flaws and perks)
    def item(t):
        s=[0]*20
        for j in rng.sample(range(20),rng.randrange(1,7)):s[j]=rng.choice([1,2,3,5,10,rng.randrange(0,25)])
        return dict(type=t,icon=rng.randrange(400),prefix_level=rng.choice([-1,0,5,rng.randrange(-1,148)]),prefix=rng.randrange(-1,148),name=rng.randrange(20),stats=s)
    f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
    stats={key:rng.randrange(0,60) for key in STATS_INTS}
    stats.update(health_max=rng.randrange(20,80),break_chance=rng.choice([50,94,95]),armour_loss_chance=rng.choice([50,11,10]),leech=rng.choice([0,24,25]),
                 weaken=rng.choice([0,1,3]),**{key:f32(rng.choice([0,1.0,2.0])) for key in STATS_FLOATS},cooldown=rng.randrange(2))
    c['shop']=dict(equipped=[item(i if rng.random()<.95 else rng.randrange(5)) for i in range(5)],options=[item(rng.randrange(5)) for _ in range(3)],
                   scroll=dict(type=rng.randrange(40),level=rng.randrange(11),max=rng.randrange(36),current=rng.randrange(36),active=rng.randrange(2)),
                   scroll_slot=rng.randrange(-1,3),race=rng.choice([3,3,rng.randrange(10)]),
                   label_words=[rng.choice([0,0,0x3f800000,rng.getrandbits(32)]) for _ in range(27)],stats=stats)
    return c

def main():
    old,new=Original(),Native();rng=random.Random(0x25298);n=500;frames=0;applied=0;scrolls=0;activated=0;kinds=set()
    f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
    for i in range(n):
        c=case(rng);old.load(c);new.load(c);new.set_probe(old.probe())
        a,b=old.open_shop(),new.open_shop()
        def check(stage,a,b,extra=None):
            if a!=b:
                (HERE/'menu_shop_failure.json').write_text(json.dumps(dict(case=i,stage=stage,extra=extra,shop=c['shop'],original=a,native=b),indent=2))
                raise AssertionError(f'menu_shop_failure.json ({stage})')
        check('open',a,b);scrolls+=a['scroll_slot']>=0
        plan=[(0,-1,f32(1/60))]*rng.randrange(1,4)
        for _ in range(rng.randrange(0,6)):
            bt=rng.choice([14,15,16,17,7,-1])
            plan+=[(1,bt,f32(1/60)),(rng.choice([2,2,3]),rng.choice([bt,bt,-1,7]),f32(rng.choice([1/60,1/30]))),(0,-1,f32(1/60))]
        step=0;guard=0;done=False
        while not done:
            if step<len(plan):phase,button,dt=plan[step];step+=1
            else:
                m=old.shop_status()['menu']
                if m['timer']!=0xbf800000:phase,button,dt=0,-1,f32(1/60)
                elif m['first']==-1:plan+=[(0,-1,f32(1/60)),(1,rng.choice([14,15,16]),f32(1/60)),(2,-2,f32(1/60))];continue
                else:plan+=[(0,-1,f32(1/60)),(1,7,f32(1/60)),(2,7,f32(1/60))];continue
            if button==-2:button=old.shop_status()['menu']['first']
            guard+=1;assert guard<400,'shop did not close'
            before=old.shop_status()['menu']
            a,b=old.frame(phase,button,dt),new.frame(phase,button,dt);frames+=1
            check('frame',a,b,[phase,button,dt])
            kinds|={e[0] for e in a['events']}
            if before['open'] and not a['menu']['open']:done=True;applied+=1;activated+=any(e[0]=='activate_scroll' for e in a['events'])
    assert scrolls>50 and activated>10 and {'scroll_tooltip','achievement'}<=kinds,(scrolls,activated,kinds)
    report=dict(status='passed',cases=n,frames=frames,applied=applied,scrolls_offered=scrolls,scrolls_activated=activated,events=sorted(kinds),
                function=dict(symbol='__ZN11FoldoutMenu10InitialiseE8MenuType',address=hex(INIT),native='dr_menu_open_shop, dr_menu_process (shop)'),
                original='Actual FoldoutMenu::Initialise(1) / Process with the item functions, Game::SetItem and Game::UpdateStats',
                boundaries=['std::set / std::vector modelled; the scroll probe words given; Skill::Activate of the scroll recorded'])
    (HERE/'menu_shop_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
