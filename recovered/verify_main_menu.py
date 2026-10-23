#!/usr/bin/env python3
"""The main menu (T040-M7): actual MainMenu::Process 0x2e668 vs the native session's main-menu route (dr_session_frame).

Each trial starts from a random main menu (fading in or out or not, the title's alpha, a touched button, the
"overwrite the saved game?" confirmation open, fading or closing), a random saved-game length (Continue shown or not),
random high-score counts (High scores shown or not), the bonus button shown or not and the sound switch, then plays up to
300 frames of touches (phase 0 / 1: Game::Process's screen route turns an ended touch into 0) with random dt and the
element under the touch (menu_button: buttons 0..7 -- 7 the bonus button --, 8 more games, 10 / 11 the confirmation's yes / no, -1).
The original runs from its entry with ScoreScreen::GetScoreCount, Game::SetSoundState, Quad::SetAlpha and Interpolate as
original code; Quad::ContainsPoint answers the frame's element by the quad's address; Game::QueueSound, ContinueGame,
NewGame, StartChallenge, StartTutorial, ShowScores, ShowMoreGames and ShowBonusRequest are recorded and skipped, the
Dashboard request read from Game+0x15545; other calls (display) skipped. A trial ends with the first action (the native
session performs it). Compared every frame: the menu (open, fade timer and direction, title alpha, Continue / High
scores / bonus shown, touched button, the confirmation's open / answer / closing / kind / timer, previous phase), the
sound switch and its changed flag, and the frame's sounds, switch changes and actions in order.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_skills import Original as SkillsOriginal, case as skills_case
from verify_stroke import HERE
from verify_session import Objects, Host, EVENT, U8, I32, Point

TEXT=(HERE.parent/'armv7-disassembly.txt').read_text()
def addr(symbol):return int(re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',TEXT,re.M)[1],16)
MENU,SCORES,SAVE_LENGTH,SOUND,DASHBOARD=0xc3fc,0xef68,0x146d0,0x13ec6,0x15545
PROCESS=addr('__ZN8MainMenu7ProcessEf')
RUN={PROCESS}|{addr(n) for n in ('__ZN11ScoreScreen13GetScoreCountEv','__ZN4Game13SetSoundStateEb','__ZN4Quad8SetAlphaEh','__Z11Interpolatefff')}
ACTIONS={addr('__ZN4Game12ContinueGameEv'):0,addr('__ZN4Game7NewGameEv'):1,addr('__ZN4Game14StartChallengeEv'):2,
         addr('__ZN4Game13StartTutorialEv'):3,addr('__ZN4Game10ShowScoresEv'):4}
OTHER={addr('__ZN4Game13ShowMoreGamesEv'):'more_games',addr('__ZN4Game16ShowBonusRequestEv'):'bonus'}
SOUND_FN,SET_SOUND,CONTAINS=addr('__ZN4Game10QueueSoundE5Sound'),addr('__ZN4Game13SetSoundStateEb'),addr('__ZN4Quad13ContainsPointERK8GLfloat2')
STARTS={int(a,16) for a in re.findall(r'^[^\s][^\n]*:\n\s+([0-9a-f]+):',TEXT,re.M)}
QUADS={0xf0:8,0x5c8:10,0x638:11,**{0x160+0x70*i:i for i in range(8)}}   # button 7's quad is the bonus button's (+0x470)
SOURCE_INTERFACE=35
class MainMenuScreen(C.Structure):
    _fields_=[('timer',C.c_float),('fading',U8),('splash',U8),('has_save',U8),('has_scores',U8),('bonus',U8),('pressed',I32),
              ('confirm',U8),('chosen',U8),('closing',U8),('confirm_kind',I32),('confirm_timer',C.c_float),('previous_phase',I32)]

class Original(SkillsOriginal):
    def __init__(self):super().__init__();self.screening=False;self.events=[]
    def hook(self,u,address,size,context):
        if self.screening and address==SET_SOUND:self.events.append(['setting',10,u.reg_read(self.regs[1])&0xff])
        if self.screening and (address in STARTS or 0x194000<=address<0x196000) and address not in RUN:
            r=[u.reg_read(x) for x in self.regs];lr=u.reg_read(self.LR);res=None
            if address==SOUND_FN:self.events.append(['sound',C.c_int32(r[1]).value])
            elif address in ACTIONS:self.events.append(['button',ACTIONS[address]])
            elif address in OTHER:self.events.append([OTHER[address]])
            elif address==CONTAINS:res=int(QUADS.get(r[0]-self.GAME-MENU,-2)==self.menu_button)
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

def main():
    old=Original();old.load(skills_case(random.Random(1)));u=old.u;G=old.GAME;M=G+MENU
    lib=C.CDLL(str(HERE/'recovered_session_native.dylib'))
    lib.dr_session_create.argtypes=[C.POINTER(Host),C.c_int32];lib.dr_session_create.restype=C.c_void_p
    lib.dr_session_destroy.argtypes=[C.c_void_p];lib.dr_session_destroy.restype=None
    lib.dr_session_objects.argtypes=[C.c_void_p];lib.dr_session_objects.restype=Objects
    lib.dr_session_frame.argtypes=[C.c_void_p,C.c_float,I32,Point];lib.dr_session_frame.restype=I32
    native=[]
    def on_event(_,source,e):
        if source!=SOURCE_INTERFACE:return
        k,index,a,_b=struct.unpack('<4i',C.string_at(e,16))
        if k==1:native.append(['sound',a])
        elif k==2:native.append(['setting',index,a])
        elif k==5:native.append(['more_games'])
        elif k==6:native.append(['bonus'])
        elif k==7:native.append(['dashboard'])
        elif k==8 and index<5:native.append(['button',index])
    callback=EVENT(on_event);host=Host();host.event=callback;session=None
    rng=random.Random(0x2e668);counts=dict(trials=0,frames=0,actions={},sounds=0,switches=0,confirm_opened=0,splash_done=0,faded_out=0)
    def fail(**k):
        (HERE/'main_menu_failure.json').write_text(json.dumps(k,indent=2,default=str));raise AssertionError('main_menu_failure.json')
    for trial in range(1500):
        if session:lib.dr_session_destroy(session)
        session=lib.dr_session_create(C.byref(host),1);o=lib.dr_session_objects(session)
        m=MainMenuScreen.from_address(o.main_menu);screens=(U8*15).from_address(o.screens);settings=(U8*12).from_address(o.settings)
        end_save=I32.from_address(o.end+4);counts_n=(I32*6).from_address(o.scores+0xd20);mb=I32.from_address(o.menu_button)
        # a random menu
        timer=rng.choice([0.0]*6+[0.3,0.5,rng.uniform(0,0.5),-0.1]);fading=rng.randrange(2);splash=rng.choice([0]*6+[255,rng.randrange(256)])
        save=rng.choice([0,0,1,200]);sc=[rng.choice([0,0,0,rng.randrange(1,11)]) for _ in range(6)];bonus=rng.choice([0,0,1])
        pressed=rng.choice([-1,-1,-1,rng.randrange(8)]);confirm=rng.choice([0,0,0,1]);chosen=rng.randrange(2);closing=rng.choice([0,0,1])
        kind=rng.randrange(3);ctimer=rng.choice([0.0,0.0,0.3,rng.uniform(0,0.3)]);prev=rng.choice([0,0,1]);sound=rng.randrange(2)
        u.mem_write(M+4,b'\1');old.write(M,G);old.write(M+8,f32(timer));u.mem_write(M+0xc,bytes([fading]))
        for k in range(4):u.mem_write(M+0x80+0xf+0x14*k,bytes([splash]))
        old.write(G+SAVE_LENGTH,save)
        for k,v in enumerate(sc):old.write(G+SCORES+0xf00+4*k,v)
        u.mem_write(M+0x4e6,bytes([bonus]));old.write(M+0x4e0,pressed&0xffffffff);u.mem_write(M+0x6a8,bytes([confirm]))
        u.mem_write(M+0x6b0,bytes([chosen,closing]));old.write(M+0x6ac,kind);old.write(M+0x6b4,f32(ctimer));old.write(M+0x6b8,prev)
        u.mem_write(M+0x6c0,b'\0');u.mem_write(G+SOUND,bytes([sound,0]));u.mem_write(G+DASHBOARD,b'\0')
        m.timer=timer;m.fading=fading;m.splash=splash;end_save.value=save
        for k,v in enumerate(sc):counts_n[k]=v
        m.bonus=bonus;m.pressed=pressed;m.confirm=confirm;m.chosen=chosen;m.closing=closing;m.confirm_kind=kind;m.confirm_timer=ctimer
        m.previous_phase=prev;settings[4]=sound;settings[5]=0;screens[2]=1
        phase=0;counts['trials']+=1
        for frame in range(300):
            if rng.random()<.3:phase=1-phase if rng.random()<.7 else phase
            dt=rng.choice([1/60,1/30,0.05,rng.uniform(0,0.2)])
            button=rng.choice([-1,-1,rng.randrange(8),rng.randrange(8),rng.randrange(8),7,8,10,11,10,11])
            old.menu_button=button;mb.value=button;old.events=[];del native[:]
            old.write(G+0x10,phase);old.call(PROCESS,[M,f32(dt)])
            if u.mem_read(G+DASHBOARD,1)[0]:old.events.append(['dashboard']);u.mem_write(G+DASHBOARD,b'\0')
            lib.dr_session_frame(session,dt,phase,Point(0.5,0.5))
            acted=any(e[0] in ('button','dashboard','more_games','bonus') for e in old.events)
            r=lambda a:C.c_int32(old.read(a)).value;b=lambda a:u.mem_read(a,1)[0]
            a=dict(menu=[old.read(M+8),b(M+0xc),b(M+0x8f),b(M+0x4e4),b(M+0x4e5),b(M+0x4e6),r(M+0x4e0),b(M+0x6a8),b(M+0x6b0),b(M+0x6b1),
                         r(M+0x6ac),old.read(M+0x6b4),r(M+0x6b8)],sound=list(u.mem_read(G+SOUND,2)),events=old.events)
            n=dict(menu=[f32(m.timer),m.fading,m.splash,m.has_save,m.has_scores,m.bonus,m.pressed,m.confirm,m.chosen,m.closing,
                         m.confirm_kind,f32(m.confirm_timer),m.previous_phase],sound=[settings[4],settings[5]],events=list(native))
            if not acted:a['open']=b(M+4);n['open']=screens[2]
            else:   # the native performed the action (a game, the scores, the menu's fade-out): the action and the touched button
                a=dict(events=a['events'],pressed=a['menu'][6]);n=dict(events=n['events'],pressed=n['menu'][6])
            if a!=n:fail(trial=trial,frame=frame,phase=phase,dt=dt,button=button,original=a,native=n)
            counts['frames']+=1;counts['sounds']+=sum(e[0]=='sound' for e in old.events);counts['switches']+=sum(e[0]=='setting' for e in old.events)
            if not acted:counts['confirm_opened']+=bool(not confirm and a['menu'][7]);confirm=a['menu'][7]
            if acted:
                key='/'.join(str(x) for x in old.events[-1]);counts['actions'][key]=counts['actions'].get(key,0)+1;break
            if not a.get('open',1):counts['faded_out']+=1;break
        counts['splash_done']+=splash>0 and 'menu' in a and a['menu'][2]==0
    acts=set(counts['actions'])
    assert {'button/0','button/1','button/2','button/3','button/4','dashboard','more_games','bonus'}<=acts and counts['switches'] \
        and counts['confirm_opened'] and counts['splash_done'] and counts['faded_out'],counts
    counts['actions']=dict(sorted(counts['actions'].items()))
    print(json.dumps(dict(status='passed',**counts,function='MainMenu::Process 0x2e668',native='dr_session_frame (main-menu route)',
                          original='Actual function from its entry',boundaries=['Quad::ContainsPoint answered by the frame\'s element',
                          'the actions recorded and skipped (the native performs them; a trial ends there)','display calls skipped'])))

if __name__=='__main__':main()
