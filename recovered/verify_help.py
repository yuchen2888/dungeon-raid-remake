#!/usr/bin/env python3
"""The help popup (T040-M6): actual HelpMenu::Process 0x38128, HelpMenu::QueueHelp 0x38268 and Interface::ProcessHeartbeat
0x1e8e8 (with HelpMenu::Initialise / Show as original code) vs the native session (recovered_session).

Each trial starts from a closed popup, random queued topics (Game+0x102d0, often bit 14 alone or none) and a random help
switch, then plays a few hundred steps. A step is one of: a frame of Game::Process's help route while the popup is open
(the touch's phase 2 / 3 become 0, then HelpMenu::Process(dt); the native dr_session_frame, which routes there), touches
inside or outside the box (menu_button 0 / -1; the original's box is fixed at (0.1, 0.5, 0.8 x 0.5) when Show returns);
the setup screen's help button while the popup is closed (QueueHelp of its five texts; the native: a frame of the setup
screen beginning a touch, then dr_session_setup_help, T040-M7d) or the class screen's for a random tab
(dr_session_class_help, false for tabs other than 0..3); or Interface::ProcessHeartbeat with random shown health and ceiling
(the native's dr_session_interface_process with input not ready and no menu open; also while the popup is open, as a
second topic in the frame that showed the first). Compared after every step: the popup
(open, closing, timer, previous phase, the queued texts in order), the queued topics, the help switch and the texts shown
(screen texts by their string's address, topic 14 with its position and size). Display calls are skipped, std::string /
std::list<HelpItem> modelled.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_skills import Original as SkillsOriginal, case as skills_case
from verify_stroke import HERE
from verify_resources import Resource
from verify_stats import PlayerStats
from verify_session import Objects, Host, EVENT, HelpPopup, U8, I32, Point, HELP_TEXTS, HELP_TEXT_IDS, CLASS_HELP, HELP_BOX, Setup

TEXT=(HERE.parent/'armv7-disassembly.txt').read_text()
def addr(symbol):return int(re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',TEXT,re.M)[1],16)
HELP,INTERFACE,FLAGS,SWITCH,UI_HEALTH,UI_CEILING=0x10298,0x4cdc,0x102d0,0x13ec8,0x5994,0x5998
PROCESS,QUEUE,HEARTBEAT,INIT,SHOW=(addr(n) for n in ('__ZN8HelpMenu7ProcessEf','__ZN8HelpMenu9QueueHelpEPKcfff','__ZN9Interface16ProcessHeartbeatEf',
                                                      '__ZN8HelpMenu10InitialiseEffff8HelpType','__ZN8HelpMenu4ShowEPKcffff'))
RUN={PROCESS,QUEUE,HEARTBEAT,INIT,SHOW}|{addr(n) for n in ('__ZN4Game12SetHelpStateEb','__Z5Clampfff','__Z11Interpolatefff')}
PUSH,POP=addr('__ZNSt4listI8HelpItemSaIS0_EE9push_backERKS0_'),addr('__ZNSt4listI8HelpItemSaIS0_EE9pop_frontEv')
STRING_CTOR,STRING_COPY=0x194d10,0x194d18
STARTS={int(a,16) for a in re.findall(r'^[^\s][^\n]*:\n\s+([0-9a-f]+):',TEXT,re.M)}
SCRATCH=0x3500000   # the popup's quads and the list nodes (mapped by main)
SOURCE_INTERFACE=35
def f32(x):return struct.unpack('<I',struct.pack('<f',x))[0]

class Original(SkillsOriginal):
    def __init__(self):super().__init__();self.helping=False;self.shows=[];self.nodes=0;self.type=-1
    def hook(self,u,address,size,context):
        if not self.helping:return super().hook(u,address,size,context)
        r=[u.reg_read(x) for x in self.regs];sp=u.reg_read(self.SP);lr=u.reg_read(self.LR)&~1
        for undo in self.pending.pop(address,[]):undo()
        if address==INIT:self.type=C.c_int32(self.read(sp+4)).value
        if address==SHOW:
            text=self.type if INIT<=lr<INIT+0x70 else HELP_TEXT_IDS.get(r[1],-1)
            self.shows.append([text,r[2],r[3],self.read(sp),self.read(sp+4)] if text<100 else [text])
            def box(G=self.GAME):
                for k,v in enumerate(HELP_BOX):self.write(G+HELP+0x14+4*k,f32(v))
            self.pending.setdefault(lr,[]).append(box)
        if (address in STARTS or 0x194000<=address<0x196000) and address not in RUN:
            if address==STRING_CTOR:self.write(r[0],r[1])
            elif address==STRING_COPY:self.write(r[0],self.read(r[1]))
            elif address==PUSH:
                node=SCRATCH+0x4000+0x20*self.nodes;self.nodes+=1;tail=self.read(r[0]+4)
                for k,v in enumerate([r[0],tail,self.read(r[1]),self.read(r[1]+4),self.read(r[1]+8),self.read(r[1]+12)]):self.write(node+4*k,v)
                self.write(tail,node);self.write(r[0]+4,node)
            elif address==POP:
                first=self.read(r[0]);nxt=self.read(first);self.write(r[0],nxt);self.write(nxt+4,r[0])
            u.reg_write(self.PC,lr|1)
    def call(self,entry,args,stack=()):
        u=self.u;sp=0x140fe00
        for k,v in enumerate(stack):self.write(sp+4*k,v)
        for r,v in zip(self.regs,args):u.reg_write(r,v&0xffffffff)
        u.reg_write(self.SP,sp);u.reg_write(self.LR,self.STOP|1);self.helping=True;self.pending={}
        try:u.emu_start(entry|1,self.STOP,timeout=0,count=2000000)
        except Exception as e:raise AssertionError(f'{e} at {u.reg_read(self.PC):#x}') from e
        finally:
            self.helping=False
            for undo in self.pending.pop(self.STOP&~1,[]):undo()
        assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))

def main():
    old=Original();old.load(skills_case(random.Random(1)));u=old.u;G=old.GAME;H=G+HELP;u.mem_map(SCRATCH,0x10000)
    lib=C.CDLL(str(HERE/'recovered_session_native.dylib'))
    lib.dr_session_create.argtypes=[C.POINTER(Host),C.c_int32];lib.dr_session_create.restype=C.c_void_p
    lib.dr_session_destroy.argtypes=[C.c_void_p];lib.dr_session_destroy.restype=None
    lib.dr_session_objects.argtypes=[C.c_void_p];lib.dr_session_objects.restype=Objects
    lib.dr_session_frame.argtypes=[C.c_void_p,C.c_float,I32,Point];lib.dr_session_frame.restype=I32
    lib.dr_session_interface_process.argtypes=[C.c_void_p,C.c_float,C.c_bool];lib.dr_session_interface_process.restype=None
    lib.dr_session_setup_help.argtypes=[C.c_void_p];lib.dr_session_setup_help.restype=None
    lib.dr_session_class_help.argtypes=[C.c_void_p,I32];lib.dr_session_class_help.restype=C.c_bool
    shows=[]
    def on_event(_,source,e):
        if source==SOURCE_INTERFACE and C.cast(e,C.POINTER(I32))[0]==4:
            h=HelpPopup.from_address(lib.dr_session_objects(session).help)
            shows.append([h.text,f32(h.at.x),f32(h.at.y),f32(h.width),f32(h.height)] if h.text<100 else [h.text])
    callback=EVENT(on_event);host=Host();host.event=callback;session=None
    rng=random.Random(0x38128);counts=dict(steps=0,frames=0,heartbeats=0,setup=0,tabs={},shown={},closed=0,help_off=0)
    def fail(**k):
        (HERE/'help_failure.json').write_text(json.dumps(k,indent=2,default=str));raise AssertionError('help_failure.json')
    for trial in range(250):
        if session:lib.dr_session_destroy(session)
        session=lib.dr_session_create(C.byref(host),1);o=lib.dr_session_objects(session)
        h=HelpPopup.from_address(o.help);screens=(U8*15).from_address(o.screens);settings=(U8*12).from_address(o.settings)
        flags=C.c_uint32.from_address(o.finish+4);mb=I32.from_address(o.menu_button)
        res=Resource.from_address(o.resources);player=PlayerStats.from_address(o.player)
        queued=rng.choice([0,1<<14,1<<14,(1<<14)|(1<<rng.randrange(23)),0x7fffff,rng.getrandbits(23)]);switch=rng.randrange(2)
        u.mem_write(H,bytes(0x48));old.write(H+4,SCRATCH+0x2000);old.write(H+8,G);old.write(H+0x3c,H+0x3c);old.write(H+0x40,H+0x3c)
        old.write(H+0x38,queued);flags.value=queued;u.mem_write(G+SWITCH,bytes([switch]));settings[0]=switch
        old.write(G+INTERFACE+0x1030,G);old.nodes=0;old.shows=[];del shows[:]
        phase=0;before=None
        for step in range(300):
            kind=rng.choices(['frame','heartbeat','setup','class'],[8,2,.3,.3])[0] if not screens[0] else rng.choices(['frame','heartbeat','setup','class'],[20,1,.2,.2])[0]
            if kind in ('setup','class') and h.queued>50:kind='frame'   # (the native queue holds 64)
            if kind=='setup' and screens[0]:kind='class'   # (the setup screen takes no input while a popup is open)
            if kind=='frame':
                if not screens[0]:continue
                phase=rng.choice([0,0,1,1,2,3]) if rng.random()<.5 else phase;inside=rng.random()<.6;dt=rng.choice([1/60,1/30,0.05,rng.uniform(0,0.3)])
                touch=[0.5,0.75] if inside else [0.05,0.2]
                old.write(G+0x10,0 if phase in (2,3) else phase);u.mem_write(G+0x14,struct.pack('<ff',*touch))
                old.call(PROCESS,[H,f32(dt)]);mb.value=0 if inside else -1
                lib.dr_session_frame(session,dt,phase,Point(*touch));counts['frames']+=1
            elif kind=='heartbeat':
                ui,ceiling=rng.choice([(rng.randrange(0,40),rng.randrange(1,40)),(rng.randrange(-5,5),rng.choice([0,0,1])),(35,100),(36,100)])
                old.write(G+UI_HEALTH,ui&0xffffffff);old.write(G+UI_CEILING,ceiling&0xffffffff);res.ui_health=ui;player.ui_health_ceiling_5998=ceiling
                old.call(HEARTBEAT,[G+INTERFACE,f32(1/60)]);counts['heartbeats']+=1
                lib.dr_session_interface_process(session,1/60,False)
            elif kind=='setup':
                old.call(QUEUE,[H,HELP_TEXTS[0],0,0],[0])
                for a in HELP_TEXTS[1:5]:old.call(QUEUE,[H,a,0,0],[0])
                screens[4]=1;Setup.from_address(o.setup).previous_phase=0;lib.dr_session_frame(session,1/60,1,Point(0.5,0.5))   # the press's frame
                lib.dr_session_setup_help(session);screens[4]=0;counts['setup']+=1
            else:
                tab=rng.choice([0,1,2,3,3,-1,4])
                for a in (CLASS_HELP[tab] if 0<=tab<4 else []):old.call(QUEUE,[H,a,0,0],[0])
                ok=lib.dr_session_class_help(session,tab)
                if ok!=(0<=tab<4):fail(trial=trial,step=step,tab=tab,native=ok)
                counts['tabs'][tab]=counts['tabs'].get(tab,0)+1
            queue=[];node=old.read(H+0x3c)
            while node!=H+0x3c and len(queue)<70:queue.append(HELP_TEXT_IDS.get(old.read(node+8),-1));node=old.read(node)
            a=dict(popup=[u.mem_read(H+0xc,1)[0],u.mem_read(H+0xd,1)[0],old.read(H+0x10),C.c_int32(old.read(H+0x24)).value,queue],
                   flags=old.read(H+0x38),switch=u.mem_read(G+SWITCH,1)[0],shows=old.shows)
            b=dict(popup=[screens[0],h.closing,f32(h.timer),h.previous_phase,list(h.queue[:h.queued])],flags=flags.value,switch=settings[0],shows=shows)
            if a!=b:fail(trial=trial,step=step,kind=kind,original=a,native=b)
            counts['steps']+=1
            if before:
                counts['closed']+=before['popup'][0] and not a['popup'][0]
                counts['help_off']+=before['switch'] and not a['switch']
            before=a
        for s in old.shows:counts['shown'][s[0]]=counts['shown'].get(s[0],0)+1
    assert counts['closed'] and counts['help_off'] and set(counts['shown'])==set(range(100,123))|{14},counts
    counts['shown']=dict(sorted(counts['shown'].items()));counts['tabs']=dict(sorted(counts['tabs'].items()))
    print(json.dumps(dict(status='passed',**counts,functions=['HelpMenu::Process 0x38128','HelpMenu::QueueHelp 0x38268','Interface::ProcessHeartbeat 0x1e8e8',
                          'HelpMenu::Initialise','HelpMenu::Show'],native=['dr_session_frame (help route)','dr_session_setup_help','dr_session_class_help',
                          'dr_session_interface_process'],original='Actual functions from their entries',
                          boundaries=['the box fixed when Show returns','std::string / std::list<HelpItem> modelled','display calls skipped'])))

if __name__=='__main__':main()
