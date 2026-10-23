#!/usr/bin/env python3
"""The high-score screen (T040-M7): actual ScoreScreen::Process 0x367f8 vs the native session's score route
(dr_session_frame).

Each trial starts from a random screen (fading in or out, sliding toward a page or not, a drag or a button held, the
page 0..5) and plays up to 300 frames of touches (phase 0 / 1), random dt and touch x, the touch on the pages' rows or
not and on Back / the arrows or not (the native's menu_button: 1 Back, 2 left, 3 right, +16 on the rows, -1 none). The
original runs from its entry with Game::SetScorePage, MainMenu::Show / SetActive, ScoreScreen::GetScoreCount, ClampI,
Interpolate and fabsf-free code as original code; QuadStrip::ContainsPoint answers the button by the strip's address,
QuadStrip::GetSize gives the rows' height (the rows: above panel+0x340, below panel+0x5ec plus the height, fixed in the page panel, the touch's y put inside
or outside them), Game::QueueSound is recorded, display calls are skipped. Compared every frame: the screen (open,
closing, timer, previous phase, dragging, last / start x, velocity, shift, sliding, direction, the three buttons, page),
the saved page and its changed flag, the main menu's open flag and Continue / High scores, and the frame's sounds.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_skills import Original as SkillsOriginal, case as skills_case
from verify_stroke import HERE
from verify_session import Objects, Host, EVENT, U8, I32, Point
from verify_main_menu import MainMenuScreen

TEXT=(HERE.parent/'armv7-disassembly.txt').read_text()
def addr(symbol):return int(re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',TEXT,re.M)[1],16)
SCREEN,MENU,PAGE,SAVE_LENGTH=0xef68,0xc3fc,0x1660c,0x146d0
PROCESS=addr('__ZN11ScoreScreen7ProcessEf')
RUN={PROCESS}|{addr(n) for n in ('__ZN4Game12SetScorePageEi','__ZN8MainMenu4ShowEv','__ZN8MainMenu9SetActiveEb','__ZN11ScoreScreen13GetScoreCountEv',
                                   '__Z6ClampIiii','__Z11Interpolatefff')}
SOUND,CONTAINS,GET_SIZE=addr('__ZN4Game10QueueSoundE5Sound'),addr('__ZN9QuadStrip13ContainsPointERK8GLfloat2'),addr('__ZN9QuadStrip7GetSizeEv')
STARTS={int(a,16) for a in re.findall(r'^[^\s][^\n]*:\n\s+([0-9a-f]+):',TEXT,re.M)}
PANELS=0x3600000   # three page panels (+0x1d4 / +0x1d8 / +0x1dc), 0x3000 bytes each
TOP,HEIGHT=0.4,0.6   # the rows: panel+0x340 is their top, GetSize of panel+0x5a4 their height
SOURCE_INTERFACE=35
class ScorePages(C.Structure):
    _fields_=[('closing',U8),('timer',C.c_float),('previous_phase',I32),('dragging',U8),('last_x',C.c_float),('start_x',C.c_float),
              ('velocity',C.c_float),('drag',C.c_float),('unused_174',C.c_float),('sliding',U8),('direction',I32),('back',U8),('left',U8),
              ('right',U8),('page',I32)]
def f32(x):return struct.unpack('<I',struct.pack('<f',x))[0]

class Original(SkillsOriginal):
    def __init__(self):super().__init__();self.screening=False;self.events=[]
    def hook(self,u,address,size,context):
        if self.screening and (address in STARTS or 0x194000<=address<0x196000) and address not in RUN:
            r=[u.reg_read(x) for x in self.regs];lr=u.reg_read(self.LR);res=None;S=self.GAME+SCREEN
            if address==SOUND:self.events.append(['sound',C.c_int32(r[1]).value])
            elif address==CONTAINS:
                which=1 if r[0]==S+0x180 else 2 if r[0]==self.read(S+0x1d8)+0x27d8 else 3 if r[0]==self.read(S+0x1d8)+0x2870 else -2
                res=int(which==self.button)
            elif address==GET_SIZE:u.mem_write(r[0],struct.pack('<ff',0.9,HEIGHT))
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
    old=Original();old.load(skills_case(random.Random(1)));u=old.u;G=old.GAME;S=G+SCREEN;M=G+MENU
    u.mem_map(PANELS,0x10000)
    for k in range(3):old.write(S+0x1d4+4*k,PANELS+0x3000*k+0x100);old.write(PANELS+0x3000*k+0x100+0x340,f32(TOP));old.write(PANELS+0x3000*k+0x100+0x5ec,f32(TOP))
    lib=C.CDLL(str(HERE/'recovered_session_native.dylib'))
    lib.dr_session_create.argtypes=[C.POINTER(Host),C.c_int32];lib.dr_session_create.restype=C.c_void_p
    lib.dr_session_destroy.argtypes=[C.c_void_p];lib.dr_session_destroy.restype=None
    lib.dr_session_objects.argtypes=[C.c_void_p];lib.dr_session_objects.restype=Objects
    lib.dr_session_frame.argtypes=[C.c_void_p,C.c_float,I32,Point];lib.dr_session_frame.restype=I32
    native=[]
    def on_event(_,source,e):
        if source==SOURCE_INTERFACE:
            k,index,a,_b=struct.unpack('<4i',C.string_at(e,16))
            if k==1:native.append(['sound',a])
    callback=EVENT(on_event);host=Host();host.event=callback;session=None
    rng=random.Random(0x367f8);counts=dict(trials=0,frames=0,pages={},closed=0,slides=0,drags=0,sounds=0)
    def fail(**k):
        (HERE/'score_screen_failure.json').write_text(json.dumps(k,indent=2,default=str));raise AssertionError('score_screen_failure.json')
    for trial in range(1500):
        if session:lib.dr_session_destroy(session)
        session=lib.dr_session_create(C.byref(host),1);o=lib.dr_session_objects(session)
        p=ScorePages.from_address(o.scores_screen);m=MainMenuScreen.from_address(o.main_menu)
        screens=(U8*15).from_address(o.screens);settings=(U8*20).from_address(o.settings);mb=I32.from_address(o.menu_button)
        page_setting=I32.from_address(o.settings+12)
        st=dict(closing=rng.choice([0,0,1]),timer=rng.choice([0.0]*5+[0.3,rng.uniform(0,0.3)]),previous_phase=rng.choice([0,0,1]),
                dragging=rng.choice([0,0,1]),last_x=rng.uniform(0,1),start_x=rng.uniform(0,1),velocity=rng.uniform(-2,2),drag=rng.uniform(-1,1),
                sliding=rng.choice([0,0,0,1]),direction=rng.choice([-1,0,1]),back=rng.choice([0,0,1]),left=rng.choice([0,0,1]),
                right=rng.choice([0,0,1]),page=rng.randrange(6))
        offs=dict(closing=(5,'B'),timer=(8,'f'),previous_phase=(0x15c,'i'),dragging=(0x160,'B'),last_x=(0x164,'f'),start_x=(0x168,'f'),
                  velocity=(0x16c,'f'),drag=(0x170,'f'),sliding=(0x178,'B'),direction=(0x17c,'i'),back=(0x1cc,'B'),left=(0x1cd,'B'),
                  right=(0x1ce,'B'),page=(0x1d0,'i'))
        for k,v in st.items():
            off,fmt=offs[k];u.mem_write(S+off,struct.pack('<'+fmt,v));setattr(p,k,v)
        u.mem_write(S+4,b'\1');old.write(S,G);old.write(S+0x174,0);p.unused_174=0.0;screens[3]=1
        saved=rng.randrange(6);old.write(G+PAGE,saved);u.mem_write(G+PAGE+4,b'\0');page_setting.value=saved;settings[16]=0
        old.write(G+SAVE_LENGTH,rng.choice([0,5]));C.c_int32.from_address(o.end+4).value=old.read(G+SAVE_LENGTH)
        for k in range(6):v=rng.choice([0,0,3]);old.write(S+0xf00+4*k,v);(I32*6).from_address(o.scores+0xd20)[k]=v
        u.mem_write(M+4,b'\0');screens[2]=0;old.write(M,G)
        phase=0;counts['trials']+=1
        for frame in range(300):
            if rng.random()<.25:phase=1-phase
            dt=rng.choice([1/60,1/30,0.05,rng.uniform(0.001,0.1)]);x=rng.uniform(0,1) if rng.random()<.3 else min(1,max(0,old_x+rng.uniform(-.1,.1))) if frame else .5
            old_x=x;rows=rng.random()<.6;y=TOP+HEIGHT/2 if rows else TOP-0.2;button=rng.choice([0,0,0,1,2,3])
            old.button=button if button else -2;mb.value=(button|(16 if rows else 0)) if (button or rows) else -1
            old.events=[];del native[:]
            old.write(G+0x10,phase);u.mem_write(G+0x14,struct.pack('<ff',x,y));old.call(PROCESS,[S,f32(dt)])
            lib.dr_session_frame(session,dt,phase,Point(x,y))
            r=lambda a:C.c_int32(old.read(a)).value;b=lambda a:u.mem_read(a,1)[0]
            a=dict(screen=[b(S+4),b(S+5),old.read(S+8),r(S+0x15c),b(S+0x160),old.read(S+0x164),old.read(S+0x168),old.read(S+0x16c),old.read(S+0x170),
                           b(S+0x178),r(S+0x17c),b(S+0x1cc),b(S+0x1cd),b(S+0x1ce),r(S+0x1d0)],saved=[r(G+PAGE),b(G+PAGE+4)],
                   menu=[b(M+4),b(M+0x4e4),b(M+0x4e5)] if b(M+4) else [0],events=old.events)
            n=dict(screen=[screens[3],p.closing,f32(p.timer),p.previous_phase,p.dragging,f32(p.last_x),f32(p.start_x),f32(p.velocity),f32(p.drag),
                           p.sliding,p.direction,p.back,p.left,p.right,p.page],saved=[page_setting.value,settings[16]],
                   menu=[screens[2],m.has_save,m.has_scores] if screens[2] else [0],events=list(native))
            if a!=n:fail(trial=trial,frame=frame,phase=phase,dt=dt,x=x,rows=rows,button=button,original=a,native=n)
            counts['frames']+=1;counts['sounds']+=len(old.events);counts['pages'][a['screen'][14]]=counts['pages'].get(a['screen'][14],0)+1
            counts['slides']+=a['screen'][9];counts['drags']+=a['screen'][4]
            if not a['screen'][0]:counts['closed']+=1;break
    assert len(counts['pages'])==6 and counts['closed'] and counts['slides'] and counts['drags'] and counts['sounds'],counts
    counts['pages']=dict(sorted(counts['pages'].items()))
    print(json.dumps(dict(status='passed',**counts,function='ScoreScreen::Process 0x367f8',native='dr_session_frame (score route)',
                          original='Actual function from its entry',boundaries=['QuadStrip::ContainsPoint answered by the frame\'s button',
                          'the rows\' top and height fixed (panel+0x340, QuadStrip::GetSize)','display calls skipped'])))

if __name__=='__main__':main()
