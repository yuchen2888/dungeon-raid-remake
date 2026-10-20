#!/usr/bin/env python3
"""The level-up menu in use (T040-K2): actual FoldoutMenu::Process 0x23c44 (with FoldoutMenu::ProcessInput and
Game::SetSkill 0x13e68 as original code) vs native dr_menu_process (recovered_menu), frame by frame, after the
menu opened as in verify_menu_level.py.

Each frame the original runs FoldoutMenu::Process(dt) from its entry with the touch phase at Game+0x10.
FoldoutMenu::CursorInButton(b) answers whether b is the frame's button and CursorInQuad(7) whether it is the
confirm button (the layout is the renderer's). Recorded and skipped: QueueSound, FoldoutMenu::HighlightButton,
the confirm button's Menu::SetQuadColour, Interface::PositionSkill / UpdateSkills / UpdateHealthBar /
UpdateSkullValue; skipped: Quad::SetColour, Tooltip::Hide / ShowScroll (Interpolate and CharacterClass::HavePerk
run). Each case opens the menu, waits for the opening animation, taps options and the confirm button at random
(choosing, deselecting, a third option, the confirm button before it is enabled or released elsewhere), then
chooses two and confirms, and plays the closing animation until the choice applies. Compared after every frame:
the menu (open byte, choices, confirm state, timer bits, animation direction, previous phase), the four options,
the equipped skills in slot order and skill_count, healing, shield, the four bonus chances, health, health
maximum, interface health and ceiling, base damage, skull value, the stat counts Game+0xbde8.. and the events.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_menu_level import Original as LevelOriginal, Native as LevelNative, case as level_case, MenuSources, FM, OPTION_INTS, EVENT
from verify_stats import PlayerStats, PLAYER, UI
from verify_stroke import HERE, I32, U8

PROCESS=0x23c44
CLASSES,STRIDE=0x15564,388
CHANCE_ADDR=(0xbe18,0xbe20,0xbe28,0xbe30)        # SkillRecord.chance order
CHANCE_INDEX=(2,0,1,3)                           # MatchState.bonus_chance index of each
COUNTS=(0xbde8,0xbdf0,0xbdf8,0xbe00)
FLOW={'__ZN11FoldoutMenu14CursorInButtonEi':'button','__ZN11FoldoutMenu12CursorInQuadEi':'quad','__ZN11FoldoutMenu15HighlightButtonEiib':'highlight',
      '__ZN4Menu13SetQuadColourEihhhh':'confirm','__ZN4Quad9SetColourERK9GLcolour4':'skip','__ZN7Tooltip10ShowScrollE9SkillTypeRK8GLfloat2':'skip',
      '__ZN9Interface13PositionSkillEi':'position','__ZN9Interface12UpdateSkillsEv':'update_skills',
      '__ZN9Interface15UpdateHealthBarER4Quadi':'health_bar','__ZN9Interface16UpdateSkullValueEv':'skull'}
EVENT_NAMES={1:'sound',2:'position',3:'update_skills',4:'health_bar',5:'skull',6:'highlight',7:'confirm'}

def bits(f):return struct.unpack('<I',struct.pack('<f',f))[0]

class Original(LevelOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text()
        addr=lambda s:int(re.search(r'^'+re.escape(s)+r':\n\s*([0-9a-f]+):',text,re.M)[1],16)
        self.flow={addr(s):n for s,n in FLOW.items()};self.flowing=False;self.button=-1
        assert addr('__ZN11FoldoutMenu7ProcessEf')==PROCESS
    def hook(self,u,address,size,context):
        if self.flowing:
            name=self.flow.get(address)
            if name:
                r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value;e=None
                if name=='button':u.reg_write(self.regs[0],int(s(r[1])==self.button))
                elif name=='quad':u.reg_write(self.regs[0],int(s(r[1])==7 and self.button==7))
                elif name=='highlight':e=['highlight',s(r[1]),s(r[2]),r[3]&0xff]
                elif name=='confirm':assert s(r[1])==7;e=['confirm',int(r[2]&0xff==200)]
                elif name=='position':e=['position',s(r[1])]
                elif name=='update_skills':e=['update_skills']
                elif name=='health_bar':e=['health_bar',s(r[2])]
                elif name=='skull':e=['skull']
                if e:self.menu_events.append(e)
                u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def load(self,c):
        super().load(c);G=self.GAME;k=c['menu']['stats']
        for a,v in ((0xbe08,k['healing']),(0xbe10,k['shield']),(0xbdc0,k['base']),(0xbdc4,k['bonus_base']),(0x5998,k['ceiling']),(0x59c8,k['skull'])):self.write(G+a,v&0xffffffff)
        for a,v in zip(COUNTS,k['counts']):self.write(G+a,v)
        self.u.mem_write(G+0xbe64,bytes([k['cooldown']]))
        cls=G+CLASSES+STRIDE*c['menu']['class_index']
        for i,p in enumerate(k['perks']):self.write(cls+0x10+4*i,p)
    def frame(self,phase,button,dt):
        u=self.u;G=self.GAME;self.menu_events=[];self.button=button;self.write(G+0x10,phase)
        u.reg_write(self.regs[0],G+FM);u.reg_write(self.regs[1],bits(dt));u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1)
        self.menuing=self.flowing=True
        try:u.emu_start(PROCESS|1,self.STOP,timeout=0,count=2000000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.menuing=self.flowing=False
        return self.status()
    def status(self):
        G=self.GAME;i32=lambda a:C.c_int32(self.read(a)).value;b=lambda a:self.u.mem_read(a,1)[0]
        menu=dict(open=b(G+0x59f4),type=i32(G+FM+0xc),first=i32(G+FM+0x30),second=i32(G+FM+0x34),ready=b(G+FM+0x20),pressed=b(G+FM+0x21),
                  timer=self.read(G+FM+0x24),opening=b(G+FM+0x28),previous=i32(G+FM+0x2c))
        slots=[]
        for i in range(4):
            o=self.read(G+0xbf90+4*i);slots.append([i32(o+0x84),i32(o+0x88),b(o+0x80),i32(o+0x8c),i32(o+0x90)])
        return dict(menu=menu,options=[trim(self.read_option(self.read(G+FM+0x48+4*i))) for i in range(4)],slots=slots,count=i32(G+0xbfa0),
                    stats=dict(healing=i32(G+0xbe08),shield=i32(G+0xbe10),chances=[i32(G+a) for a in CHANCE_ADDR],health=i32(G+0xbd98),
                               health_max=i32(G+0xbd9c),ui_health=i32(G+0x5994),ceiling=i32(G+0x5998),base=i32(G+0xbdc0),skull=i32(G+0x59c8),
                               counts=[i32(G+a) for a in COUNTS]),events=self.menu_events)

def trim(o):   # a skill option's stat fields are stale object contents, not read for it
    return o if o['type']>=40 else {k:o[k] for k in ('type','level','max','current','active')}

class Native(LevelNative):
    def __init__(self):
        super().__init__();lib=self.menu_lib
        lib.dr_menu_process.argtypes=[C.c_void_p,C.POINTER(MenuSources),C.c_float,I32,I32,C.c_void_p];lib.dr_menu_process.restype=None
        def event(_,p):
            e=p.contents;n=EVENT_NAMES.get(e.kind)
            if n is None:return   # TooltipHide (skipped on the original side)
            self.menu_events.append({'sound':['sound',e.a],'position':['position',e.a],'update_skills':['update_skills'],'health_bar':['health_bar',e.a],
                                     'skull':['skull'],'highlight':['highlight',e.a,e.b,e.c],'confirm':['confirm',e.a]}[n])
        self.menu_cb=EVENT(event);self.menu_hooks.event=self.menu_cb
    def load(self,c):
        super().load(c);k=c['menu']['stats']
        self.p.healing_value=k['healing'];self.p.shield_value=k['shield']
        sel=self.state.selection;sel.base_damage=k['base'];sel.bonus_base_damage=k['bonus_base']
        self.player=PlayerStats();self.player.ui_health_ceiling_5998=k['ceiling'];self.player.ui_skull_59c8=k['skull'];self.player.skill_cooldown_be64=k['cooldown']
        self.counts=(I32*4)(*k['counts']);self.m.perks=(I32*4)(*k['perks'])
        s=self.sources;s.preview=C.addressof(self.p);s.selection=C.addressof(sel);s.player=C.addressof(self.player);s.stat_counts=C.addressof(self.counts)
    def frame(self,phase,button,dt):
        self.menu_events=[];self.menu_lib.dr_menu_process(C.addressof(self.menu),C.byref(self.sources),dt,phase,button,C.addressof(self.menu_hooks))
        return self.status()
    def status(self):
        m=self.menu;r=self.r
        menu=dict(open=self.open.value,type=m.type,first=m.first,second=m.second,ready=m.confirm_ready,pressed=m.confirm_pressed,timer=bits(m.timer),
                  opening=m.opening,previous=m.previous_phase)
        opts=[]
        for t in m.options:
            o={key:getattr(t,key) for _,key in OPTION_INTS};o['active']=t.active;o['chance']=list(t.chance);opts.append(trim(o))
        k=self.slots
        return dict(menu=menu,options=opts,slots=[[k.id[i],k.level[i],k.active[i],r.skill_max[i],r.skill_current[i]] for i in range(4)],count=r.skill_count,
                    stats=dict(healing=self.p.healing_value,shield=self.p.shield_value,chances=[self.m.bonus_chance[j] for j in CHANCE_INDEX],health=r.health,
                               health_max=r.health_max,ui_health=r.ui_health,ceiling=self.player.ui_health_ceiling_5998,base=self.state.selection.base_damage,
                               skull=self.player.ui_skull_59c8,counts=list(self.counts)),events=self.menu_events)

def case(rng):
    c=level_case(rng)
    c['menu']['stats']=dict(healing=rng.randrange(0,10),shield=rng.randrange(0,10),base=rng.randrange(1,30),bonus_base=rng.randrange(-3,10),
                            ceiling=rng.choice([0,rng.randrange(20,80)]),skull=rng.choice([0,rng.randrange(1,40)]),counts=[rng.randrange(5) for _ in range(4)],
                            cooldown=int(rng.random()<.3),perks=rng.choice([[255]*4,[3,255,255,255],[255,255,3,255],[rng.randrange(10),255,255,255]]))
    return c

def script(rng):
    f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
    dt=lambda:f32(rng.choice([1/60,1/60,1/30,0.05,0.1]))
    frames=[(0,-1,dt()) for _ in range(rng.randrange(1,4))]
    for _ in range(rng.randrange(0,8)):   # random taps while the menu may still be opening
        b=rng.choice([14,15,16,17,7,-1,rng.randrange(-1,20)])
        frames+=[(1,b,dt()),(rng.choice([2,2,2,3]),rng.choice([b,b,b,-1,7]),dt())]+[(0,-1,dt())]*rng.randrange(0,3)
    return frames

def main():
    old,new=Original(),Native();rng=random.Random(0x23c44);n=600;applied=0;frames=0;kinds=set();stats_applied=0;added=0
    for i in range(n):
        c=case(rng);old.load(c);new.load(c);old.open_level();new.open_level()
        plan=script(rng);step=0;done=False;guard=0
        while not done:
            if step<len(plan):phase,button,dt=plan[step]
            else:   # settle: choose two options and confirm, then let the closing animation run
                a=old.status()['menu']
                if a['timer']!=0xbf800000:phase,button,dt=0,-1,1/60
                elif a['first']==-1 or a['second']==-1:
                    free=[b for b in (14,15,16,17) if b not in (a['first'],a['second'])];b=rng.choice(free)
                    plan+=[(0,-1,1/60),(1,b,1/60),(2,b,1/60)];continue
                else:plan+=[(0,-1,1/60),(1,7,1/60),(2,7,1/60)];continue
            step+=1;guard+=1;assert guard<400,'menu did not close'
            before=new.status()
            a,b=old.frame(phase,button,dt),new.frame(phase,button,dt);frames+=1
            if a!=b:
                (HERE/'menu_flow_failure.json').write_text(json.dumps(dict(case=i,step=step,frame=[phase,button,dt],before=before,original=a,native=b),indent=2))
                raise AssertionError('menu_flow_failure.json')
            kinds|={e[0] for e in a['events']}
            if before['menu']['open'] and not a['menu']['open']:
                done=True;applied+=1;stats_applied+=sum(1 for o in before['options'] if o['type']>=40 and before['menu']['first']>=0)
                added+=a['count']>before['count']
        for _ in range(3):a,b=old.frame(0,-1,1/60),new.frame(0,-1,1/60);assert a==b
    assert {'sound','highlight','confirm','position','update_skills','health_bar','skull'}<=kinds and added>50,(kinds,added)
    report=dict(status='passed',cases=n,frames=frames,applied=applied,skills_added=added,events=sorted(kinds),
                function=dict(symbol='__ZN11FoldoutMenu7ProcessEf',address=hex(PROCESS),native='dr_menu_process (level-up menu)'),
                original='Actual FoldoutMenu::Process / ProcessInput and Game::SetSkill',
                boundaries=['button layout from the case; highlight, confirm colour, interface refreshes and sounds recorded; tooltips skipped'])
    (HERE/'menu_flow_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
