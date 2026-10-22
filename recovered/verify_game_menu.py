#!/usr/bin/env python3
"""The game menu, the stats menu and Interface's menu / stats buttons (T040-M5): actual GameMenu::Process 0x32580,
StatsMenu::Process 0x33c0c and Interface::ProcessInput 0x209e4 vs native dr_session_interface_process (recovered_session).

Each trial starts from random menu states (open or closed, fading or not, a pressed button or tab), random switches
(sound, help, clock, attack dimming, high frame rate and their changed flags; now and then a byte other than 0 / 1),
random queued help topics (Game+0x102d0) and a random main menu fade, then plays a few hundred frames of touches (phase
0, 1 for a few frames, then 2 or 3), random dt and input ready. Each frame the original runs Interface::Process's
dispatch as at 0x20c64 (no FoldoutMenu open: the game menu, else the stats menu, else with input ready ProcessInput)
from the function's entry, with GameMenu::Show / StatsMenu::Show, Game::UpdateHelpState, HelpMenu::ResetHelp / ClearHelp,
Game::Set{Sound,Help,Clock,AttackDimming}State / SetHighFramerate, MainMenu::FadeIn and Interpolate as original code.
Answered: GameMenu::CursorInQuad / StatsMenu::CursorInQuad (the frame's menu button), StatsMenu::CursorOutsideMenu (menu
button -1), Interface::CursorInButton (the frame's skill button; no skills equipped) and Quad::ContainsPoint (the menu
button quad Interface+0xbd4: skill button 4; the stats button quad Interface+0xc44: 5); Game::QueueSound recorded;
Game::GetItem answers a scratch item (the stats menu's label colours); every other call (display) skipped.
Compared every frame: both menus (open, previous phase, pressed / tab, closing, timer), Interface's touched buttons, the
pressed skill button and Interface's previous phase, the ten switch bytes, the queued help topics, the main menu (open,
timer, fading) and the frame's sounds, switch changes (Game::Set*State) and MainMenu::FadeIn calls in order.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_skills import Original as SkillsOriginal, case as skills_case
from verify_stroke import HERE
from verify_session import Objects, Host, EVENT, Overlay, MainMenuScreen, U8, I32

TEXT=(HERE.parent/'armv7-disassembly.txt').read_text()
def addr(symbol):return int(re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',TEXT,re.M)[1],16)
INTERFACE,GAME_MENU,STATS_MENU,MAIN_MENU,HELP=0x4cdc,0x5b00,0x5b90,0xc3fc,0x10298
SETTINGS=0x13ec6   # ..0x13ece: sound, sound changed, help, clock, dimming, framerate, clock / dimming / framerate changed
FUNCS=dict(game_menu=addr('__ZN8GameMenu7ProcessEf'),stats_menu=addr('__ZN9StatsMenu7ProcessEf'),
           input=addr('__ZN9Interface12ProcessInputEv'))
assert FUNCS==dict(game_menu=0x32580,stats_menu=0x33c0c,input=0x209e4)
SETTERS={addr('__ZN4Game13SetSoundStateEb'):10,addr('__ZN4Game12SetHelpStateEb'):11,addr('__ZN4Game13SetClockStateEb'):12,
         addr('__ZN4Game21SetAttackDimmingStateEb'):13,addr('__ZN4Game16SetHighFramerateEb'):14}
RUN=set(SETTERS)|{addr(n) for n in ('__ZN8GameMenu4ShowEv','__ZN9StatsMenu4ShowEv','__ZN4Game15UpdateHelpStateEv','__ZN8HelpMenu9ResetHelpEv',
                       '__ZN8HelpMenu9ClearHelpEv','__ZN8MainMenu6FadeInEv','__Z11Interpolatefff',
                       '__ZNKSt6vectorIP5LabelSaIS1_EE4sizeEv')}|set(FUNCS.values())
FADE_IN,SOUND,GET_ITEM=addr('__ZN8MainMenu6FadeInEv'),addr('__ZN4Game10QueueSoundE5Sound'),addr('__ZN4Game7GetItemE8ItemType')
GM_CURSOR,SM_CURSOR,SM_OUTSIDE=addr('__ZN8GameMenu12CursorInQuadEi'),addr('__ZN9StatsMenu12CursorInQuadEi'),addr('__ZN9StatsMenu17CursorOutsideMenuEv')
CURSOR_BUTTON,CONTAINS=addr('__ZN9Interface14CursorInButtonEi'),addr('__ZN4Quad13ContainsPointERK8GLfloat2')
STRINGS=addr('__ZNKSt6vectorISsSaISsEE4sizeEv')   # the class tab's description lines (display): none
STARTS={int(a,16) for a in re.findall(r'^[^\s][^\n]*:\n\s+([0-9a-f]+):',TEXT,re.M)}
SCRATCH=0x170c000   # the stats menu's label vector and the answered item
SOURCE_INTERFACE,FINISH_HELP=35,4   # SessionSource::Interface; TurnFinishFlags.help_flags_102d0
SET_NATIVE=[4,5,0,6,8,10,7,9,11]   # the SaveSettings byte of Game+0x13ec6..0x13ece

class Original(SkillsOriginal):
    def __init__(self):super().__init__();self.screening=False;self.events=[]
    def hook(self,u,address,size,context):
        if self.screening and address in SETTERS:   # Game::Set*State run as original code
            self.events.append(['setting',SETTERS[address],u.reg_read(self.regs[1])&0xff])
        elif self.screening and address==FADE_IN:self.events.append(['main_menu'])
        elif self.screening and (address in STARTS or 0x194000<=address<0x196000) and address not in RUN:
            r=[u.reg_read(x) for x in self.regs];lr=u.reg_read(self.LR);res=None
            if address==SOUND:self.events.append(['sound',C.c_int32(r[1]).value])
            elif address==GET_ITEM:res=SCRATCH+0x400
            elif address==STRINGS:res=0
            elif address in (GM_CURSOR,SM_CURSOR):res=int(C.c_int32(r[1]).value==self.menu_button)
            elif address==SM_OUTSIDE:res=int(self.menu_button==-1)
            elif address==CURSOR_BUTTON:res=int(C.c_int32(r[1]).value==self.skill_button)
            elif address==CONTAINS:
                I=self.GAME+INTERFACE;assert r[0] in (I+0xbd4,I+0xc44),hex(r[0])
                res=int(self.skill_button==(4 if r[0]==I+0xbd4 else 5))
            if res is not None:u.reg_write(self.regs[0],res)
            u.reg_write(self.PC,lr|1);return
        return super().hook(u,address,size,context)
    def call(self,entry,args):
        u=self.u
        for r,v in zip(self.regs,args):u.reg_write(r,v&0xffffffff)
        u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1);self.screening=True
        try:u.emu_start(entry|1,self.STOP,timeout=0,count=2000000)
        except Exception as e:raise AssertionError(f'{e} at {u.reg_read(self.PC):#x}') from e
        finally:self.screening=False
        assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))

def f32(x):return struct.unpack('<I',struct.pack('<f',x))[0]
def fl(bits):return struct.unpack('<f',struct.pack('<I',bits&0xffffffff))[0]

def main():
    old=Original();old.load(skills_case(random.Random(1)));u=old.u;G=old.GAME;I=G+INTERFACE
    lib=C.CDLL(str(HERE/'recovered_session_native.dylib'))
    lib.dr_session_create.argtypes=[C.POINTER(Host),C.c_int32];lib.dr_session_create.restype=C.c_void_p
    lib.dr_session_objects.argtypes=[C.c_void_p];lib.dr_session_objects.restype=Objects
    lib.dr_session_interface_process.argtypes=[C.c_void_p,C.c_float,C.c_bool];lib.dr_session_interface_process.restype=None
    native_events=[]
    def on_event(_,source,e):
        if source!=SOURCE_INTERFACE:return
        k,index,a,_b=struct.unpack('<4i',C.string_at(e,16))
        native_events.append(['sound',a] if k==1 else ['setting',index,a] if k==2 else ['main_menu'])
    callback=EVENT(on_event);host=Host();host.event=callback
    session=lib.dr_session_create(C.byref(host),1);o=lib.dr_session_objects(session)
    gm,sm=Overlay.from_address(o.game_menu),Overlay.from_address(o.stats_menu);buttons=(U8*2).from_address(o.interface_buttons)
    main_menu=MainMenuScreen.from_address(o.main_menu);settings=(U8*12).from_address(o.settings)
    screens=(U8*15).from_address(o.screens)   # FrameScreens: help, unlock, main menu, score, name, intro, pad, state, menus
    MENUS=12;MAIN=2
    touch=(I32*3).from_address(o.touch);skill_input=(I32*2).from_address(o.skill_input)
    menu_button=I32.from_address(o.menu_button);skill_button=I32.from_address(o.skill_button)
    rng=random.Random(0x32580);counts=dict(frames=0,sounds=0,settings={},main_menu=0,opened=[0,0],closed=[0,0],tabs={},help_cleared=0,help_reset=0)
    def fail(**k):
        (HERE/'game_menu_failure.json').write_text(json.dumps(k,indent=2,default=str));raise AssertionError('game_menu_failure.json')
    for trial in range(400):
        # random states
        def menu_state(base,which):
            prev=rng.choice([0,0,1,2,3]);pressed=rng.choice([-1,-1,rng.randrange(9,16),rng.randrange(-3,20)]);closing=rng.choice([0,0,1])
            timer=rng.choice([0.0,0.0,rng.uniform(0,0.2),0.2,-0.01]);showing=rng.choice([0,0,1])
            old.write(base+0x10,prev);old.write(base+0x14,pressed);u.mem_write(base+0x18,bytes([closing]));old.write(base+0x1c,f32(timer))
            u.mem_write(base+0xc,bytes([showing]));old.write(base+8,G)
            m=gm if which==1 else sm;m.previous_phase=prev;m.pressed=pressed;m.closing=closing;m.timer=timer;screens[MENUS+which]=showing
        menu_state(G+GAME_MENU,1);menu_state(G+STATS_MENU,2)
        for k in range(24):old.write(SCRATCH+0x800+4*k,SCRATCH+0x1000+0x40*k)   # the stats menu's labels (display)
        for v in (0xdc,0xe8,0xf4):old.write(G+STATS_MENU+v,SCRATCH+0x800);old.write(G+STATS_MENU+v+4,SCRATCH+0x800+4*rng.randrange(0,8))
        u.mem_write(G+0x59f4,b'\0');screens[MENUS]=0
        vals=[rng.choice([0,1,1,rng.randrange(256)]) if rng.random()<0.1 else rng.choice([0,1]) for _ in range(9)]
        u.mem_write(G+SETTINGS,bytes(vals))
        for i,v in enumerate(vals):settings[SET_NATIVE[i]]=v
        queued=rng.choice([0,0,0x7fffff,rng.getrandbits(32),1<<rng.randrange(23)]);old.write(G+HELP+0x38,queued)
        fin=C.c_uint32.from_address(o.finish+FINISH_HELP);fin.value=queued
        mm=[rng.choice([0,1]),rng.choice([0.0,0.3,0.5]),rng.choice([0,1])]
        u.mem_write(G+MAIN_MENU+4,bytes([mm[0]]));old.write(G+MAIN_MENU+8,f32(mm[1]));u.mem_write(G+MAIN_MENU+0xc,bytes([mm[2]]))
        screens[MAIN]=mm[0];main_menu.timer=mm[1];main_menu.fading=mm[2]
        b=[rng.choice([0,0,1]),rng.choice([0,0,1])];u.mem_write(I+0xcb4,bytes(b));buttons[0],buttons[1]=b
        old.write(I+0xbd0,0xffffffff);skill_input[0]=-1;prev=rng.choice([0,0,1,2]);old.write(I+0x1034,prev);skill_input[1]=prev
        old.write(I+0x1030,G);old.write(G+0xbfa0,0)
        phase=0;held=0;before=None
        for frame in range(200):
            # the touch: 0 .. 1 (a few frames) .. 2 or 3 .. 0
            if phase in (2,3):phase=0
            elif phase==0:phase=1 if rng.random()<0.4 else 0;held=rng.randrange(1,5)
            else:
                held-=1
                if held<=0:phase=rng.choice([2,2,2,3])
            if rng.random()<0.03:phase=rng.choice([0,1,2,3])
            dt=rng.choice([1/60,1/30,0.05,rng.uniform(0,0.25)]);ready=rng.random()<0.9
            mb=rng.choice([-1,-1,rng.randrange(9,16),rng.randrange(9,16),rng.randrange(10,16),0,rng.randrange(-2,20)])
            sb=rng.choice([-1,-1,4,4,5,5,rng.randrange(0,6)])
            old.menu_button=mb;old.skill_button=sb;old.write(G+0x10,phase);old.events=[]
            menu_button.value=mb;skill_button.value=sb;touch[0]=phase;del native_events[:]
            # Interface::Process's dispatch (0x20c64)
            if u.mem_read(G+GAME_MENU+0xc,1)[0]:old.call(FUNCS['game_menu'],[G+GAME_MENU,f32(dt)])
            elif u.mem_read(G+STATS_MENU+0xc,1)[0]:old.call(FUNCS['stats_menu'],[G+STATS_MENU,f32(dt)])
            elif ready:old.call(FUNCS['input'],[I])
            lib.dr_session_interface_process(session,dt,ready)
            r=lambda a:C.c_int32(old.read(a)).value
            def menu(base):return [u.mem_read(base+0xc,1)[0],r(base+0x10),r(base+0x14),u.mem_read(base+0x18,1)[0],old.read(base+0x1c)]
            a=dict(game_menu=menu(G+GAME_MENU),stats_menu=menu(G+STATS_MENU),buttons=list(u.mem_read(I+0xcb4,2)),skill=[r(I+0xbd0),r(I+0x1034)],
                   settings=list(u.mem_read(G+SETTINGS,9)),help=old.read(G+HELP+0x38),
                   main_menu=[u.mem_read(G+MAIN_MENU+4,1)[0],old.read(G+MAIN_MENU+8),u.mem_read(G+MAIN_MENU+0xc,1)[0]],events=old.events)
            nm=lambda m,w:[screens[MENUS+w],m.previous_phase,m.pressed,m.closing,f32(m.timer)]
            b_=dict(game_menu=nm(gm,1),stats_menu=nm(sm,2),buttons=[buttons[0],buttons[1]],skill=[skill_input[0],skill_input[1]],
                    settings=[settings[SET_NATIVE[i]] for i in range(9)],help=C.c_uint32.from_address(o.finish+FINISH_HELP).value,
                    main_menu=[screens[MAIN],f32(main_menu.timer),main_menu.fading],events=list(native_events))
            if a!=b_:fail(trial=trial,frame=frame,phase=phase,dt=dt,ready=ready,menu_button=mb,skill_button=sb,original=a,native=b_)
            counts['frames']+=1
            if before:
                for k,name in enumerate(('game_menu','stats_menu')):
                    if a[name][0]!=before[name][0]:counts['opened' if a[name][0] else 'closed'][k]+=1
                if a['stats_menu'][2]!=before['stats_menu'][2] and a['stats_menu'][2]>=10:counts['tabs'][a['stats_menu'][2]]=counts['tabs'].get(a['stats_menu'][2],0)+1
                if before['help'] and not a['help']:counts['help_cleared']+=1
                if not before['help'] and a['help']:counts['help_reset']+=1
            before=a
            for e in a['events']:
                if e[0]=='sound':counts['sounds']+=1
                elif e[0]=='setting':counts['settings'][e[1]]=counts['settings'].get(e[1],0)+1
                else:counts['main_menu']+=1
    assert set(counts['settings'])=={10,11,12,13,14} and set(counts['tabs'])==set(range(10,16)) and counts['main_menu'] and min(counts['opened']+counts['closed']) \
        and counts['help_cleared'] and counts['help_reset'],counts
    counts['tabs']=dict(sorted(counts['tabs'].items()));counts['settings']=dict(sorted(counts['settings'].items()))
    print(json.dumps(dict(status='passed',trials=400,**counts,functions=['GameMenu::Process 0x32580','StatsMenu::Process 0x33c0c','Interface::ProcessInput 0x209e4',
                          'GameMenu::Show','StatsMenu::Show','Game::UpdateHelpState','Game::Set*State','MainMenu::FadeIn'],native='dr_session_interface_process',
                          original='Actual functions from their entries (Interface::Process dispatch as at 0x20c64)',
                          boundaries=['cursor and button hit tests answered by the frame\'s buttons','display calls skipped','no skills equipped'])))

if __name__=='__main__':main()
