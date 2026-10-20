#!/usr/bin/env python3
"""The level-up menu's options (T040-K1): actual FoldoutMenu::Initialise(0) 0x24a54 (with CharacterClass::
GetSkillPool, Game::IsSkillUnlocked, Skill::Initialise(SkillType, Skill*) / Skill::Initialise(StatType),
Skill::SetStatChance and RandI as original code) vs native dr_menu_open_level (recovered_menu), on the shared
state of verify_skills.py.

The original runs from its entry (R0 = the FoldoutMenu at Interface+0xd10, R1 = 0). Its four option Skill
objects (FoldoutMenu+0x48..) and the equipped ones (Game+0xbf90) hold the case's fields; each class record
(Game+0x15564 + 388 * i) has its base skills (Class+0x30, as CharacterClass::Initialise builds them for its
class type) and replacement skills (+0x48). std::set<int> (the skill and stat pools, the class's pool at
Class+0x16c) is modelled here: its insert / erase / clear / assignment change a Python set whose nodes are laid
out as a list in node order (header Class+4, leftmost +0xc, size +0x14, node value +0x10, the
_Rb_tree_increment stub follows node+0). Skipped: the menu quads, labels, text (Font::SplitLines, string
vectors, Skill::GetDescription / GetStats, Upgrade::SetIcon, strcpy, sprintf, Label::SetText), Tooltip::Hide,
FoldoutMenu::UpdateLabels and the SjLj stubs; QueueSound recorded. Compared: the open byte, the skill option
count (+0x78), every option's type, level, cooldowns, active byte, line count and increments, the random
seeds and the sounds.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_skills import Original as SkillsOriginal, Native as SkillsNative, case as skills_case
from verify_progression import Profile
from verify_stroke import HERE, I32, U8

ENTRY,END=0x24a54,0x25c80
FM=0x4cdc+0xd10
OPTIONS,CLASS_ARRAYS,SET_NODES=0x1709000,0x170a000,0x170c000
CLASSES,STRIDE,CLASS_INDEX=0x15564,388,0x1648c
CHANCES=dict(be18=0xbe18,be20=0xbe20,be28=0xbe28,be30=0xbe30)
SKIP=['__ZN7Tooltip4HideEv','__ZN4Menu7SetQuadEiRK8GLfloat2S2_S2_ff','__ZN11FoldoutMenu8AddLabelEiPKc',
      '__ZN4Font10SplitLinesEPKcffRSt6vectorISsSaISsEE','__ZN5Skill14GetDescriptionEv','__ZN5Skill8GetStatsEi',
      '__ZNSt6vectorISsSaISsEED2Ev','__ZN7Upgrade7SetIconEiiii','__ZN5Label7SetTextEPKci','__ZN11FoldoutMenu12UpdateLabelsEv']
SIZE_ZERO=['__ZNKSt6vectorISsSaISsEE4sizeEv']
SET_OPS={'__ZNSt8_Rb_treeIiiSt9_IdentityIiESt4lessIiESaIiEE13_Rb_tree_implIS3_Lb0EEC2ERKSaISt13_Rb_tree_nodeIiEERKS3_':'init',
         '__ZNSt3setIiSt4lessIiESaIiEE6insertERKi':'insert','__ZNSt8_Rb_treeIiiSt9_IdentityIiESt4lessIiESaIiEE5eraseERKi':'erase',
         '__ZNSt8_Rb_treeIiiSt9_IdentityIiESt4lessIiESaIiEE8_M_eraseEPSt13_Rb_tree_nodeIiE':'clear',
         '__ZNSt8_Rb_treeIiiSt9_IdentityIiESt4lessIiESaIiEEaSERKS5_':'assign'}
STUBS={0x194cec:'skip',0x194cf0:'skip',0x194cf4:'skip',0x194fb0:'skip',0x194f60:'skip',0x194d30:'increment'}
BASE=[[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19],[31,2,3,4,5,7,8,9,10,12,13,14,16,18,21,22,23,24,25,29],
      [32,2,3,4,6,8,9,11,12,15,16,17,18,19,20,22,23,24,25,27],[33,1,2,5,6,7,8,9,10,12,13,15,18,19,21,20,25,26,28,29],
      [34,3,4,5,7,9,10,11,12,13,14,16,18,19,21,20,22,23,25,27],[35,1,2,3,6,7,8,9,10,12,15,17,18,21,20,24,25,26,28,29],
      [36,0,2,3,4,6,8,9,10,11,12,13,14,15,17,18,22,23,24,25],[37,2,3,4,5,8,9,11,12,13,14,16,18,19,21,20,23,24,25,27],
      [38,2,3,4,5,6,7,10,11,12,13,14,15,16,19,21,22,23,25,27],[39,0,1,4,5,7,8,9,12,14,15,16,18,21,22,23,24,25,27,28]]

class SkillRecord(C.Structure):
    _fields_=[(k,I32) for k in ('type','level','max','current')]+[('active',U8)]+[(k,I32) for k in ('lines','health','healing','shield','damage')]+[('chance',I32*4)]
class MenuState(C.Structure):
    _fields_=[(k,I32) for k in ('type','first','second','skill_options','previous_phase')]+[('timer',C.c_float)]+\
             [(k,U8) for k in ('opening','confirm_ready','confirm_pressed')]+[('options',SkillRecord*4)]
class MenuSources(C.Structure):
    _fields_=[('resources',C.c_void_p),('slots',C.c_void_p),('classes',C.c_void_p),('class_index',I32),('open',C.POINTER(U8))]
class MenuEvent(C.Structure):_fields_=[('kind',I32),('a',I32)]
EVENT=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(MenuEvent))
class MenuHooks(C.Structure):_fields_=[('context',C.c_void_p),('event',EVENT)]
# option object fields: offset of type, level, max, current; active byte; lines; increments
OPTION_INTS=((0x84,'type'),(0x88,'level'),(0x8c,'max'),(0x90,'current'),(0xcc,'lines'),(0x1d0,'health'),(0x1d4,'healing'),(0x1d8,'shield'),(0x1dc,'damage'))
OPTION_CHANCES=(0x1e0,0x1e4,0x1e8,0x1ec)

class Original(SkillsOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text()
        addr=lambda s:int(re.search(r'^'+re.escape(s)+r':\n\s*([0-9a-f]+):',text,re.M)[1],16)
        self.menu_skip={addr(s) for s in SKIP};self.size_zero={addr(s) for s in SIZE_ZERO};self.set_ops={addr(s):n for s,n in SET_OPS.items()}
        self.sound=addr('__ZN4Game10QueueSoundE5Sound');self.menuing=False;self.sets={}
        assert addr('__ZN11FoldoutMenu10InitialiseE8MenuType')==ENTRY
    def write_set(self,tree):
        values=sorted(self.sets[tree]);header=tree+4;base=SET_NODES+0x400*list(self.sets).index(tree)
        self.write(tree+0x14,len(values));self.write(tree+0xc,base if values else header);self.write(tree+8,base if values else 0)
        for i,v in enumerate(values):node=base+32*i;self.write(node,base+32*(i+1) if i+1<len(values) else header);self.write(node+16,v&0xffffffff)
    def hook(self,u,address,size,context):
        if self.menuing:
            lr=u.reg_read(self.LR);r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value
            op=self.set_ops.get(address)
            if op:
                if op=='init':self.sets[r[0]]=set();self.write_set(r[0])
                elif op=='insert':self.sets.setdefault(r[1],set()).add(s(self.read(r[2])));self.write_set(r[1])
                elif op=='erase':
                    k=s(self.read(r[1]));had=k in self.sets.setdefault(r[0],set());self.sets[r[0]].discard(k);self.write_set(r[0]);u.reg_write(self.regs[0],int(had))
                elif op=='clear':self.sets[r[0]]=set();self.write_set(r[0])
                else:self.sets[r[0]]=set(self.sets.get(r[1],set()));self.write_set(r[0])
                u.reg_write(self.PC,lr);return
            stub=STUBS.get(address)
            if stub:
                if stub=='increment':u.reg_write(self.regs[0],self.read(r[0]))
                u.reg_write(self.PC,lr);return
            if address in self.menu_skip:u.reg_write(self.PC,lr);return
            if address in self.size_zero:u.reg_write(self.regs[0],0);u.reg_write(self.PC,lr);return
            if address==self.sound:self.menu_events.append(['sound',s(r[1])]);u.reg_write(self.PC,lr);return
        return super().hook(u,address,size,context)
    def load(self,c):
        super().load(c);G=self.GAME;k=c['menu'];self.sets={}
        self.write(G+FM+0x10,G);self.write(G+FM+0x14,G+0x4cdc);self.u.mem_write(G+0x59f4,b'\0')
        for i,o in enumerate(k['options']):self.write_option(OPTIONS+0x200*i,o);self.write(G+FM+0x48+4*i,OPTIONS+0x200*i)
        for i,(type_,level,replacements) in enumerate(k['classes']):
            b=G+CLASSES+STRIDE*i;arrays=CLASS_ARRAYS+0x100*i
            self.write(b,G);self.write(b+4,type_);self.u.mem_write(b+0x54,bytes([level]))
            for j in range(20):self.write(arrays+4*j,BASE[type_][j]);self.write(arrays+0x80+4*j,replacements[j])
            self.write(b+0x30,arrays);self.write(b+0x34,arrays+80);self.write(b+0x48,arrays+0x80);self.write(b+0x4c,arrays+0x80+80)
        self.write(G+CLASS_INDEX,k['class_index'])
        for i in range(4):   # the equipped skills' cooldowns (the resource loader's) and Skill -> Game
            base=0x1700000+0x100*i;self.write(base+0x7c,G)
        for name,a in CHANCES.items():self.write(G+a,k['chances'][name][0]);self.write(G+a+4,k['chances'][name][1])
    def write_option(self,base,o):
        self.write(base+0x7c,self.GAME);self.u.mem_write(base+0x80,bytes([o['active']]))
        for off,key in OPTION_INTS:self.write(base+off,o[key]&0xffffffff)
        for j,off in enumerate(OPTION_CHANCES):self.write(base+off,o['chance'][j]&0xffffffff)
    def read_option(self,base):
        s=lambda a:C.c_int32(self.read(a)).value
        o={key:s(base+off) for off,key in OPTION_INTS};o['active']=self.u.mem_read(base+0x80,1)[0];o['chance']=[s(base+off) for off in OPTION_CHANCES]
        return o
    def open_level(self):
        u=self.u;G=self.GAME;self.menu_events=[]
        u.reg_write(self.regs[0],G+FM);u.reg_write(self.regs[1],0);u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1);self.menuing=True
        try:u.emu_start(ENTRY|1,self.STOP,timeout=0,count=3000000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.menuing=False
        return dict(open=u.mem_read(G+0x59f4,1)[0],n=C.c_int32(self.read(G+FM+0x78)).value,
                    options=[self.read_option(self.read(G+FM+0x48+4*i)) for i in range(4)],events=self.menu_events,
                    seeds=list(struct.unpack('<6I',u.mem_read(0x1eac20,24))))

class Native(SkillsNative):
    def __init__(self):
        super().__init__();lib=self.menu_lib=C.CDLL(str(HERE/'recovered_menu_native.dylib'))
        lib.dr_menu_open_level.argtypes=[C.POINTER(MenuState),C.POINTER(MenuSources),C.POINTER(MenuHooks)];lib.dr_menu_open_level.restype=None
        def event(_,p):e=p.contents;self.menu_events.append(['sound',e.a] if e.kind==1 else ['other',e.kind,e.a])
        self.menu_cb=EVENT(event);self.menu_hooks=MenuHooks(None,self.menu_cb)
    def load(self,c):
        super().load(c);k=c['menu']
        self.menu=MenuState();self.open=U8(0)
        for i,o in enumerate(k['options']):
            t=self.menu.options[i]
            for _,key in OPTION_INTS:setattr(t,key,o[key])
            t.active=o['active'];t.chance=(I32*4)(*o['chance'])
        self.classes=(Profile*10)();self.replacements=[]
        for i,(type_,level,replacements) in enumerate(k['classes']):
            arr=(I32*20)(*replacements);self.replacements.append(arr)
            p=self.classes[i];p.class_type=type_;p.level=level;p.replacement_skills=C.cast(arr,C.POINTER(C.c_int32));p.replacement_skill_count=20
        m=self.m
        for j,name in enumerate(('be20','be28','be18','be30')):m.bonus_chance[j],m.bonus_chance_extra[j]=k['chances'][name]
        self.sources=MenuSources(C.addressof(self.r),C.addressof(self.slots),C.addressof(self.classes),k['class_index'],C.pointer(self.open))
    def open_level(self):
        self.menu_events=[];self.menu_lib.dr_menu_open_level(C.byref(self.menu),C.byref(self.sources),C.byref(self.menu_hooks))
        opts=[]
        for t in self.menu.options:
            o={key:getattr(t,key) for _,key in OPTION_INTS};o['active']=t.active;o['chance']=list(t.chance);opts.append(o)
        return dict(open=self.open.value,n=self.menu.skill_options,options=opts,events=self.menu_events,seeds=list(self.m.random.seeds))

def case(rng):
    c=skills_case(rng);r=c['resources']
    count=rng.choice([0,1,2,3,3,4,4]);r['skill_count']=count
    types=rng.sample(range(40),4) if rng.random()<.9 else [rng.randrange(40) for _ in range(4)]
    c['skills']=dict(type=types,level=[rng.choice([1,2,5,9,10,10,rng.randrange(1,11)]) for _ in range(4)],active=[rng.randrange(2) for _ in range(4)])
    r['skill_max']=[rng.choice([-1,5,10,rng.randrange(1,36)]) for _ in range(4)];r['skill_current']=[rng.randrange(0,36) for _ in range(4)]
    r['level']=rng.choice([1,2,2,3,5,rng.randrange(1,40)])
    rec=rng.random()<.35;c['record']=int(rec);c['mode']=rng.choice([0,1,2]) if rec else rng.randrange(3)
    classes=[]
    for i in range(10):
        type_=i if rng.random()<.8 else rng.randrange(10)
        repl=[255]*20
        if rng.random()<.3:
            for j in rng.sample(range(1,20),rng.randrange(1,6)):repl[j]=rng.randrange(40)
        classes.append([type_,rng.choice([0,1,5,10,10,rng.randrange(11)]),repl])
    full=rng.random()<.3
    chances={k:[rng.choice([100,95,99,rng.randrange(101)]) if full else rng.randrange(101),rng.choice([0,0,5,rng.randrange(10)])] for k in CHANCES}
    def option():
        return dict(type=rng.randrange(48),level=rng.randrange(12),max=rng.randrange(40),current=rng.randrange(40),active=rng.randrange(2),
                    lines=rng.randrange(5),health=rng.randrange(20),healing=rng.randrange(5),shield=rng.randrange(5),damage=rng.randrange(5),
                    chance=[rng.choice([0,5,7]) for _ in range(4)])
    c['menu']=dict(options=[option() for _ in range(4)],classes=classes,class_index=rng.choice([0,rng.randrange(10),rng.randrange(10)]),chances=chances)
    return c

def main():
    old,new=Original(),Native();rng=random.Random(0x24a54);n=1500;kinds={};types=set();stats=set()
    for i in range(n):
        c=case(rng);old.load(c);new.load(c)
        a,b=old.open_level(),new.open_level()
        if a!=b:
            (HERE/'menu_level_failure.json').write_text(json.dumps(dict(case=i,menu=c['menu'],skills=c['skills'],resources=c['resources'],
                                                                         record=c['record'],mode=c['mode'],original=a,native=b),indent=2))
            raise AssertionError('menu_level_failure.json')
        kinds[a['n']]=kinds.get(a['n'],0)+1
        for o in a['options']:(types if o['type']<40 else stats).add(o['type'])
    assert set(kinds)=={0,1,2} and len(types)==40 and len(stats)==8,(kinds,sorted(set(range(40))-types),stats)
    report=dict(status='passed',comparisons=n,skill_options=kinds,skill_types=len(types),stat_options=sorted(stats),
                function=dict(symbol='__ZN11FoldoutMenu10InitialiseE8MenuType',address=hex(ENTRY),native='dr_menu_open_level (type 0)'),
                original='Actual FoldoutMenu::Initialise(0) with GetSkillPool, IsSkillUnlocked, both Skill::Initialise, SetStatChance and RandI',
                boundaries=['std::set<int> modelled; quads, labels, text, tooltip and SjLj stubs skipped; sounds recorded'])
    (HERE/'menu_level_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
