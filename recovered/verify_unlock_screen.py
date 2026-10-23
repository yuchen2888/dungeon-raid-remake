#!/usr/bin/env python3
"""The unlock popup (T040-M8): actual UnlockMenu::Process 0x1090e8 and UnlockMenu::Show(const char*, const char*) 0x1094b8 vs
the native session's Unlock route (dr_session_frame) and its class-scroll release event (ReleaseEventKind::UnlockMenu).

Each trial starts from a random popup (open, fading in or out, any alpha, previous phase), then plays up to 300 frames with
random dt (0 included) and touch phase; now and then the popup is shown again (the original's Show from its entry, its
effects compared with what the native's unlock_show does on the release event -- sound 12, open, not closing, previous
phase 1 -- written on the native side; verify_session runs the native's own through class scrolls). Show's texts, labels, icon and size are skipped, so is
the label loop and Quad::SetAlpha of Process; Game::QueueSound is recorded; the panel's vertices (UnlockMenu+4) are
scratch memory whose first alpha byte is the state. Compared every frame: open, closing, alpha, previous phase and sounds.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_skills import Original as SkillsOriginal, case as skills_case
from verify_stroke import HERE
from verify_session import Objects, Host, EVENT, U8, I32, Point, UnlockPopup

TEXT=(HERE.parent/'armv7-disassembly.txt').read_text()
def addr(symbol):return int(re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',TEXT,re.M)[1],16)
UNLOCK=0x164d8
PROCESS,SHOW=addr('__ZN10UnlockMenu7ProcessEf'),addr('__ZN10UnlockMenu4ShowEPKcS1_')
RUN={PROCESS,SHOW,addr('__Z6ClampIiii')}
SOUND=addr('__ZN4Game10QueueSoundE5Sound')
STARTS={int(a,16) for a in re.findall(r'^[^\s][^\n]*:\n\s+([0-9a-f]+):',TEXT,re.M)}
VERTICES=0x3700000
SOURCE_INTERFACE=35
def f32(x):return struct.unpack('<I',struct.pack('<f',x))[0]

class Original(SkillsOriginal):
    def __init__(self):super().__init__();self.screening=False;self.events=[]
    def hook(self,u,address,size,context):
        if self.screening and (address in STARTS or 0x194000<=address<0x196000) and address not in RUN:
            r=[u.reg_read(x) for x in self.regs];lr=u.reg_read(self.LR)
            if address==SOUND:self.events.append(['sound',C.c_int32(r[1]).value])
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
    old=Original();old.load(skills_case(random.Random(1)));u=old.u;G=old.GAME;M=G+UNLOCK
    u.mem_map(VERTICES,0x10000)
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
    rng=random.Random(0x1090e8);counts=dict(trials=0,frames=0,shows=0,closed=0,full=0,alphas=set())
    def fail(**k):
        (HERE/'unlock_screen_failure.json').write_text(json.dumps(k,indent=2,default=str));raise AssertionError('unlock_screen_failure.json')
    for trial in range(2000):
        if session:lib.dr_session_destroy(session)
        session=lib.dr_session_create(C.byref(host),1);o=lib.dr_session_objects(session)
        p=UnlockPopup.from_address(o.unlock);screens=(U8*15).from_address(o.screens)
        alpha=rng.choice([0,0,255,255,rng.randrange(256),1,254]);closing=rng.choice([0,0,1]);prev=rng.randrange(2)
        old.write(M+4,VERTICES);old.write(M+8,G);old.write(M+0x54,0);u.mem_write(M+0xc8,bytes([1,closing,0]));old.write(M+0xd4,prev)
        u.mem_write(VERTICES+0xb,bytes([alpha]))
        p.alpha=alpha;p.closing=closing;p.previous_phase=prev;screens[1]=1;screens[2]=0
        phase=prev;counts['trials']+=1
        for frame in range(300):
            if rng.random()<.3:phase=1-phase
            dt=rng.choice([1/60,1/30,0.0,rng.uniform(0,0.01),rng.uniform(0,0.2)])
            old.events=[];del native[:]
            show=rng.random()<.01
            if show:   # shown again (another class scroll)
                old.call(SHOW,[M,0,0]);p.previous_phase=1;p.closing=0;screens[1]=1;native.append(['sound',12]);counts['shows']+=1
            old.write(G+0x10,phase)
            if u.mem_read(M+0xc8,1)[0]:old.call(PROCESS,[M,f32(dt)])
            lib.dr_session_frame(session,dt,phase,Point(0.5,0.5))
            b=lambda a:u.mem_read(a,1)[0]
            a=dict(popup=[b(M+0xc8),b(M+0xc9),b(VERTICES+0xb),C.c_int32(old.read(M+0xd4)).value],events=old.events)
            n=dict(popup=[screens[1],p.closing,p.alpha,p.previous_phase],events=list(native))
            if a!=n:fail(trial=trial,frame=frame,phase=phase,dt=dt,show=show,original=a,native=n)
            counts['frames']+=1;counts['alphas'].add(a['popup'][2]);counts['full']+=a['popup'][2]==255
            if not a['popup'][0]:counts['closed']+=1;break
    assert counts['shows'] and counts['closed'] and counts['full'] and len(counts['alphas'])>200,counts
    counts['alphas']=len(counts['alphas'])
    print(json.dumps(dict(status='passed',**counts,function='UnlockMenu::Process 0x1090e8, UnlockMenu::Show 0x1094b8',
                          native='dr_session_frame (unlock route), the class-scroll release event',original='Actual functions from their entries',
                          boundaries=['Show\'s texts, labels, icon and size skipped','the panel\'s vertices in scratch memory','display calls skipped'])))

if __name__=='__main__':main()
