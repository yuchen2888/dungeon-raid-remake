#!/usr/bin/env python3
"""The setup screen's fades and Back button (T040-M7d): actual NameScreen::Process 0x3cac0 (with NameScreen::ProcessInput
0x3bff8 as original code) vs the native session's Name route (dr_session_frame) and dr_session_setup_back.

Each trial starts from a random setup screen (fading in or out or not, the timer at its end or not), the main menu open or
not, a random saved-game length and high-score counts (what MainMenu::Show reads), then plays up to 200 frames with random
dt and touch phase; in some frames the touch is on Back (mostly frames that begin a touch: phase 1 after phase 0). The original runs
Process from its entry with ProcessInput, MainMenu::Show / SetActive, ScoreScreen::GetScoreCount, Quad::SetAlpha,
Interpolate, Clamp and ClampI as original code; QuadStrip::ContainsPoint answers Back by the strip's address (+0x154),
Quad::ContainsPoint (the name box's keys) no, the keyboard is hidden; Game::QueueSound is recorded, display calls are
skipped. The native plays the frame, then (the touch on Back in that frame, whatever its phase) dr_session_setup_back,
sometimes twice (the second must do nothing). In a few frames a help popup is open (Game::Process routes there: the
original runs no setup screen, the native's popup fades in), so a press then does nothing.
Compared every frame: the screen (open, timer, closing, previous phase), the main menu (open, previous phase, Continue /
High scores shown) and the sounds.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_skills import Original as SkillsOriginal, case as skills_case
from verify_stroke import HERE
from verify_session import Objects, Host, EVENT, U8, I32, Point, Setup, HelpPopup
from verify_main_menu import MainMenuScreen

TEXT=(HERE.parent/'armv7-disassembly.txt').read_text()
def addr(symbol):return int(re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',TEXT,re.M)[1],16)
NAME,MENU,SCORES,SAVE_LENGTH=0x102dc,0xc3fc,0xef68,0x146d0
TIMER,CLOSING,OPEN,KEYBOARD,PREVIOUS,CLASS_OPEN,MODE_OPEN=0x2930,0x2934,0x292d,0x292c,0x2960,0x3408,0x36f8
PROCESS=addr('__ZN10NameScreen7ProcessEf')
RUN={PROCESS}|{addr(n) for n in ('__ZN10NameScreen12ProcessInputEf','__ZN8MainMenu4ShowEv','__ZN8MainMenu9SetActiveEb',
                                   '__ZN11ScoreScreen13GetScoreCountEv','__ZN4Quad8SetAlphaEh','__Z11Interpolatefff','__Z5Clampfff','__Z6ClampIiii')}
SOUND,STRIP,QUAD=addr('__ZN4Game10QueueSoundE5Sound'),addr('__ZN9QuadStrip13ContainsPointERK8GLfloat2'),addr('__ZN4Quad13ContainsPointERK8GLfloat2')
STARTS={int(a,16) for a in re.findall(r'^[^\s][^\n]*:\n\s+([0-9a-f]+):',TEXT,re.M)}
SOURCE_INTERFACE=35
def f32(x):return struct.unpack('<I',struct.pack('<f',x))[0]

class Original(SkillsOriginal):
    def __init__(self):super().__init__();self.screening=False;self.events=[];self.target=None
    def hook(self,u,address,size,context):
        if self.screening and (address in STARTS or 0x194000<=address<0x196000) and address not in RUN:
            r=[u.reg_read(x) for x in self.regs];lr=u.reg_read(self.LR);res=None
            if address==SOUND:self.events.append(['sound',C.c_int32(r[1]).value])
            elif address==STRIP:res=int(r[0]==self.target)
            elif address==QUAD:res=0
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

def main():
    old=Original();old.load(skills_case(random.Random(1)));u=old.u;G=old.GAME;N=G+NAME;M=G+MENU
    lib=C.CDLL(str(HERE/'recovered_session_native.dylib'))
    lib.dr_session_create.argtypes=[C.POINTER(Host),C.c_int32];lib.dr_session_create.restype=C.c_void_p
    lib.dr_session_destroy.argtypes=[C.c_void_p];lib.dr_session_destroy.restype=None
    lib.dr_session_objects.argtypes=[C.c_void_p];lib.dr_session_objects.restype=Objects
    lib.dr_session_frame.argtypes=[C.c_void_p,C.c_float,I32,Point];lib.dr_session_frame.restype=I32
    lib.dr_session_setup_back.argtypes=[C.c_void_p];lib.dr_session_setup_back.restype=C.c_bool
    native=[]
    def on_event(_,source,e):
        if source==SOURCE_INTERFACE:
            k,index,a,_b=struct.unpack('<4i',C.string_at(e,16))
            if k==1:native.append(['sound',a])
    callback=EVENT(on_event);host=Host();host.event=callback;session=None
    rng=random.Random(0x3cac0);counts=dict(trials=0,frames=0,backs=0,refused=0,second=0,help_frames=0,closed=0,faded_in=0,menu_open=0)
    def fail(**k):
        (HERE/'setup_screen_failure.json').write_text(json.dumps(k,indent=2,default=str));raise AssertionError('setup_screen_failure.json')
    for trial in range(1500):
        if session:lib.dr_session_destroy(session)
        session=lib.dr_session_create(C.byref(host),1);o=lib.dr_session_objects(session)
        n=Setup.from_address(o.setup);m=MainMenuScreen.from_address(o.main_menu);screens=(U8*15).from_address(o.screens);h=HelpPopup.from_address(o.help)
        dt0=rng.choice([1/60,1/30])
        timer=rng.choice([0.0,0.0,0.3,rng.uniform(0,0.3),dt0,2*dt0]);closing=rng.choice([0,0,1]);menu=rng.choice([0,1,1]);prev=rng.randrange(2)
        u.mem_write(N+OPEN,b'\1');old.write(N,G);old.write(N+TIMER,f32(timer));u.mem_write(N+CLOSING,bytes([closing]))
        u.mem_write(N+KEYBOARD,b'\0');old.write(N+PREVIOUS,prev);u.mem_write(N+CLASS_OPEN,b'\0');u.mem_write(N+MODE_OPEN,b'\0')
        old.write(N+0x295c,0xffffffff);old.write(N+0x2954,0)
        u.mem_write(M+4,bytes([menu]));old.write(M,G);old.write(M+0x6b8,0);u.mem_write(M+0x4e4,b'\0\0')   # as a new session's
        save=rng.choice([0,5]);old.write(G+SAVE_LENGTH,save);C.c_int32.from_address(o.end+4).value=save
        for k in range(6):v=rng.choice([0,0,3]);old.write(G+SCORES+0xf00+4*k,v);(I32*6).from_address(o.scores+0xd20)[k]=v
        n.timer=timer;n.closing=closing;n.previous_phase=prev;screens[4]=1;screens[2]=menu;m.previous_phase=0
        phase=prev;counts['trials']+=1;faded=timer>0
        for frame in range(200):
            press=rng.random()<(.3 if phase==0 else .05);helping=rng.random()<.04   # a help popup open in the frame: no setup route
            phase=1 if press and rng.random()<.9 else (1-phase if rng.random()<.3 else phase)
            dt=dt0 if rng.random()<.7 else rng.choice([1/60,1/30,0.05,rng.uniform(0.001,0.1)])
            old.target=N+0x154 if press else None;old.events=[];del native[:]
            old.write(G+0x10,phase);u.mem_write(G+0x14,struct.pack('<ff',0.5,0.5))
            if not helping:old.call(PROCESS,[N,f32(dt)])
            else:h.timer=1.0;h.closing=0;screens[0]=1;counts['help_frames']+=1   # (the popup fading in: HelpMenu::Process only counts down)
            lib.dr_session_frame(session,dt,phase,Point(0.5,0.5));screens[0]=0
            if press:
                done=lib.dr_session_setup_back(session);counts['backs' if done else 'refused']+=1
                if done and rng.random()<.2:   # a second call for the same press: one press a frame
                    if lib.dr_session_setup_back(session):fail(trial=trial,frame=frame,second_press=True)
                    counts['second']+=1
            b=lambda a:u.mem_read(a,1)[0]
            a=dict(screen=[b(N+OPEN),old.read(N+TIMER),b(N+CLOSING),C.c_int32(old.read(N+PREVIOUS)).value],menu=[b(M+4),C.c_int32(old.read(M+0x6b8)).value]+([b(M+0x4e4),b(M+0x4e5)] if b(M+4) else []),
                   events=old.events)
            nn=dict(screen=[screens[4],f32(n.timer),n.closing,n.previous_phase],menu=[screens[2],m.previous_phase]+([m.has_save,m.has_scores] if screens[2] else []),
                    events=list(native))
            if a!=nn:fail(trial=trial,frame=frame,phase=phase,dt=dt,press=press,original=a,native=nn)
            counts['frames']+=1;counts['menu_open']+=a['menu'][0]
            if faded and not a['screen'][1]:counts['faded_in']+=1;faded=False
            if not a['screen'][0]:counts['closed']+=1;break
    assert counts['backs'] and counts['refused'] and counts['second'] and counts['help_frames'] and counts['closed'] and counts['faded_in'],counts
    print(json.dumps(dict(status='passed',**counts,function='NameScreen::Process 0x3cac0 (ProcessInput 0x3bff8: Back)',
                          native='dr_session_frame (Name route), dr_session_setup_back',original='Actual functions from their entries',
                          boundaries=['QuadStrip::ContainsPoint answered by the press (Back\'s strip)','the keyboard hidden, its keys not touched',
                                      'display calls skipped'])))

if __name__=='__main__':main()
