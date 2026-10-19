#!/usr/bin/env python3
"""Actual token init/motion/Rand instructions with explicit UI-target adapters."""
import ctypes as C
import hashlib
import json
import random
import re
import struct
from verify_resources import Native as ResourceNative,Original as ResourceOriginal,configure,bits,Resource,Hooks as ResourceHooks
from verify_tokens import TOKEN_EVENT,Hooks as TokenHooks
from verify_match import Match
from verify_stroke import I32,U8,HERE,initial,Point,State as Stroke
from verify_rune import rectangles

class Motion(C.Structure):
    _fields_=[('position',Point),('scale',Point),('active',U8),('reward',I32),('token',I32),('direction',Point),
        ('speed',C.c_float),('progress',C.c_float),('acceleration',C.c_float),('distance',C.c_float),('amount',I32),('linked',I32)]
EVENT=C.CFUNCTYPE(None,C.c_void_p,I32,I32)
TARGET=C.CFUNCTYPE(None,C.c_void_p,I32,I32,C.POINTER(Point))
CHOOSE=C.CFUNCTYPE(I32,C.c_void_p,C.POINTER(Motion))
class Hooks(C.Structure):_fields_=[('context',C.c_void_p),('event',EVENT),('target',TARGET),('choose',CHOOSE)]
def target(kind,index):return [.1+index*.12,.08 if kind==0 else 1.4]
def settings(c):c.update(special_choice=1,special_link=-1);return c

class Native(ResourceNative):
    def __init__(self):
        super().__init__();self.motion_lib=C.CDLL(str(HERE/'recovered_motion_native.dylib'))
        self.init_token=self.motion_lib.dr_initialise_token;self.init_token.argtypes=[C.POINTER(Motion),C.POINTER(Match),C.c_uint32,I32,C.POINTER(Point),I32,C.POINTER(Hooks)];self.init_token.restype=None
        self.process_token=self.motion_lib.dr_process_token;self.process_token.argtypes=[C.POINTER(Motion),C.POINTER(Stroke),C.c_float,C.POINTER(Hooks)];self.process_token.restype=None
        self.process_batch=self.motion_lib.dr_process_reward_tokens
        self.process_batch.argtypes=[C.POINTER(Motion),C.POINTER(C.c_uint32),C.POINTER(Resource),C.c_float,C.POINTER(Hooks),C.POINTER(ResourceHooks),C.POINTER(U8)];self.process_batch.restype=C.c_bool
    def load(self,c):
        super().load(c);self.motion_events=[];self.motions={}
        def event(_,kind,index):self.motion_events.append([kind,index])
        def get_target(_,kind,index,out):
            self.motion_events.append([5,kind,index]);out[0]=Point(*target(kind,index))
        def choose(_,p):
            self.motion_events.append([6,c['special_choice'],c['special_link']]);p.contents.linked=c['special_link'];return c['special_choice']
        self.motion_callbacks=[EVENT(event),TARGET(get_target),CHOOSE(choose)]
        self.motion_hooks=Hooks(None,*self.motion_callbacks)
        original_event=self.token_event
        def token_event(ctx,p):
            original_event(ctx,p);e=p.contents
            if e.kind==2:self.initialise(e.index,e.a,e.b,e.c,e.d)
        self.token_event=TOKEN_EVENT(token_event);self.token_hooks=TokenHooks(None,self.token_event)
    def initialise(self,slot,tile,reward,position,incoming):
        if slot not in self.motions:
            self.motions[slot]=Motion();self.motions[slot].amount=-1;self.motions[slot].linked=-1
        t=self.motions[slot];t.scale=Point(1,1)
        # The original passes &tile->center (Tile+0x54): use the CURRENT center,
        # not the case's initial one, so tiles moved by refill stay correct.
        current=self.state.selection.tiles[position].geometry.center if position>=0 else None
        override=Point(current.x,current.y) if position>=0 else None
        self.init_token(C.byref(t),C.byref(self.m),tile,reward,C.byref(override) if override else None,incoming,C.byref(self.motion_hooks))
    def motion_status(self):
        return dict(tokens=[dict(position=[bits(t.position.x),bits(t.position.y)],scale=[bits(t.scale.x),bits(t.scale.y)],active=t.active,
            reward=t.reward,token=t.token,direction=[bits(t.direction.x),bits(t.direction.y)],
            **{k:bits(getattr(t,k)) for k in ['speed','progress','acceleration','distance']},amount=t.amount,linked=t.linked) for _,t in sorted(self.motions.items())],
            seeds=list(self.m.random.seeds),events=self.motion_events)
    def init_direct(self,tile,reward,position,incoming):
        self.motion_events=[];self.initialise(0,tile,reward,position,incoming);return self.motion_status()
    def frame(self,slot,dt):
        self.motion_events=[];self.process_token(C.byref(self.motions[slot]),C.byref(self.state),dt,C.byref(self.motion_hooks));return self.motion_status()
    def override(self,slot,values):
        for k,v in values.items():setattr(self.motions[slot],k,Point(*v) if k in ['position','scale','direction'] else v)
    def batch(self,dt,menus):
        self.motion_events=[];self.resource_events=[]
        if not hasattr(self,'batch_pending'):self.batch_pending=len(self.motions)
        array=(Motion*len(self.motions))(*[t for _,t in sorted(self.motions.items())]);pending=C.c_uint32(self.batch_pending)
        result=self.process_batch(array,C.byref(pending),C.byref(self.r),dt,C.byref(self.motion_hooks),C.byref(self.resource_hooks),(U8*3)(*menus))
        self.batch_pending=pending.value
        for i,t in enumerate(array):self.motions[i]=t
        return dict(continued=result,pending=self.batch_pending,motion=self.motion_status(),resources=self.resource_status())

class Original(ResourceOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.motion_calls={};self.motion_running=False;self.motion_return=None
        symbols={'__ZN4Quad8CopyFromEPS_':'copy','__ZN4Quad9SetColourERK9GLcolour4':'colour',
            '__ZN9Interface16GetSpecialTargetEP5Token':'choose','__ZN9Interface16GetSpecialTargetEi':'special',
            '__ZN9Interface9GetTargetE8TileType':'target','__ZN4Quad5SetUVERK8GLfloat2S2_':'uv',
            '__ZN4Quad7SetSizeERK8GLfloat2':'size','__ZN4Tile9GetTileUVEiR8GLfloat2S1_':'tile_uv'}
        for symbol,name in symbols.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol
            self.motion_calls[int(m[1],16)]=name
        self.motion_visits={}
    def hook(self,u,address,size,context):
        if getattr(self,'batch_active',False) and address in [0x174dc,0x17da4]:
            self.batch_continued=address==0x174dc;u.emu_stop();return
        if getattr(self,'motion_return',None)==address:self.motion_running=False;self.motion_return=None
        if address in [0x21448,0x21644]:
            self.motion_running=True;self.motion_return=u.reg_read(self.LR)&~1
            if address==0x21448:
                r=[u.reg_read(v) for v in self.regs];slot=(r[0]-0x1600000)//160
                if not self.motion_direct:
                    request=[self.index(r[1]),r[2],self.index(r[3]-0x54) if r[3] else -1,self.read(u.reg_read(self.SP))]
                    self.requests[slot]=request;self.token_events.append([2,slot,*request])
                self.motion_slots.add(slot)
            return
        if address in [0x214a4,0x214be,0x214ca,0x2150e,0x21514,0x215b4,0x215f4,0x2165a,0x2166a,0x21684,0x216ee,0x21714,0x2176a,0x21772]:
            self.motion_visits[hex(address)]=self.motion_visits.get(hex(address),0)+1
        if not getattr(self,'motion_running',False):return super().hook(u,address,size,context)
        name=self.motion_calls.get(address)
        if not name:return super().hook(u,address,size,context)
        r=[u.reg_read(v) for v in self.regs]
        if name=='copy':
            self.motion_events.append([1,self.index(r[1])]);u.mem_write(r[0]+0x54,bytes(u.mem_read(r[1]+0x54,8)));u.mem_write(r[0]+0x64,struct.pack('<ff',1,1))
        elif name=='colour':assert self.read(r[1])==0xffffffff;self.motion_events.append([2,0])
        elif name=='choose':
            choice=self.case['special_choice'];linked=self.case['special_link'];self.motion_events.append([6,choice,linked])
            self.write(r[1]+0x9c,self.tile(linked) if linked>=0 else 0);u.reg_write(self.regs[0],choice & 0xffffffff)
        elif name=='target':
            self.motion_events.append([5,0,r[1]]);u.mem_write(0x170f000,struct.pack('<ff',*target(0,r[1])));u.reg_write(self.regs[0],0x170f000)
        elif name=='special':
            index=C.c_int32(r[2]).value;self.motion_events.append([5,1,index]);u.mem_write(r[0],struct.pack('<ff',*target(1,index)))
        elif name=='uv':
            if (u.reg_read(self.LR)&~1)==0x215d2:
                assert bytes(u.mem_read(r[1],8))==struct.pack('<II',0x3ed40000,0x3a800000)
                assert bytes(u.mem_read(r[2],8))==struct.pack('<II',0x3ee78000,0x3cb80000)
                self.motion_events.append([3,0])
        elif name=='size':assert bytes(u.mem_read(r[1],8))==struct.pack('<II',0x3df9999a,0x3d933333)
        elif name=='tile_uv':
            self.motion_events.append([4,r[0]]);u.mem_write(r[1],b'\0'*8);u.mem_write(r[2],b'\0'*8)
        u.reg_write(self.PC,u.reg_read(self.LR))
    def load(self,c):
        super().load(c);self.motion_running=False;self.motion_return=None;self.motion_direct=False;self.motion_events=[];self.motion_slots=set()
        self.u.mem_write(0x1600000,b'\0'*0x10000)
        for i in range(100):self.write(0x1600098+160*i,-1)
    def motion_status(self):
        tokens=[]
        for slot in sorted(self.motion_slots):
            base=0x1600000+160*slot;linked=self.read(base+0x9c)
            tokens.append(dict(position=[self.read(base+0x54),self.read(base+0x58)],scale=[self.read(base+0x64),self.read(base+0x68)],
                active=self.u.mem_read(base+0x70,1)[0],reward=self.read(base+0x78),token=self.read(base+0x7c),
                direction=[self.read(base+0x80),self.read(base+0x84)],
                **{k:self.read(base+a) for k,a in dict(speed=0x88,progress=0x8c,acceleration=0x90,distance=0x94).items()},
                amount=C.c_int32(self.read(base+0x98)).value,linked=self.index(linked) if linked else -1))
        return dict(tokens=tokens,seeds=list(struct.unpack('<6I',self.u.mem_read(0x1eac20,24))),events=self.motion_events)
    def init_direct(self,tile,reward,position,incoming):
        self.motion_direct=True;self.motion_events=[];u=self.u
        for reg,value in zip(self.regs,[0x1600000,self.tile(tile),reward,self.tile(position)+0x54 if position>=0 else 0]):u.reg_write(reg,value)
        u.reg_write(self.SP,0x140fff0);u.reg_write(self.LR,self.STOP|1);self.write(0x140fff0,incoming)
        u.emu_start(0x21449,self.STOP,timeout=1000000,count=1000000);assert u.reg_read(self.PC)==self.STOP
        self.motion_running=False;self.motion_return=None;return self.motion_status()
    def frame(self,slot,dt):
        self.motion_events=[];u=self.u;u.reg_write(self.regs[0],0x1600000+160*slot);u.reg_write(self.regs[1],bits(dt))
        u.reg_write(self.SP,0x140fff0);u.reg_write(self.LR,self.STOP|1)
        u.emu_start(0x21645,self.STOP,timeout=1000000,count=1000000);assert u.reg_read(self.PC)==self.STOP
        self.motion_running=False;self.motion_return=None;return self.motion_status()
    def override(self,slot,values):
        offsets=dict(position=0x54,scale=0x64,direction=0x80,speed=0x88,progress=0x8c,acceleration=0x90,distance=0x94)
        for k,v in values.items():
            base=0x1600000+160*slot
            if k in offsets:self.u.mem_write(base+offsets[k],struct.pack('<ff' if isinstance(v,list) else '<f',*(v if isinstance(v,list) else [v])))
            elif k=='active':self.u.mem_write(base+0x70,bytes([v]))
            elif k=='linked':self.write(base+0x9c,self.tile(v) if v>=0 else 0)
    def batch(self,dt,menus):
        self.motion_events=[];self.resource_events=[];self.resource_active=True;self.batch_active=True;self.batch_continued=None
        for a,v in zip([0x59f4,0x5b0c,0x5b9c],menus):self.u.mem_write(self.GAME+a,bytes([v]))
        self.write(self.GAME+4,bits(dt));u=self.u
        # Enter a bounded subsection with its sole live input r4=Game*.
        from unicorn.arm_const import UC_ARM_REG_R4
        u.reg_write(UC_ARM_REG_R4,self.GAME);u.reg_write(self.SP,0x140fff0)
        try:
            u.emu_start(0x1744d,self.STOP,timeout=1000000,count=1000000)
            assert self.batch_continued is not None,hex(u.reg_read(self.PC))
            return dict(continued=self.batch_continued,pending=self.read(self.GAME+0xb52c),motion=self.motion_status(),resources=self.resource_status())
        finally:self.batch_active=False;self.resource_active=False

def cases():
    for kind in range(7):
      for reward in range(6):
       for incoming in [0,3]:
        for flags in range(4):
         for choice in [-1,1]:
            c=settings(configure(initial()));c['board'][14]['type']=kind;c['preview']['potions'][14]=[flags&1,flags>>1,0]
            c['special_choice']=choice;c['args']=[14,reward,-1,incoming];yield c
    rng=random.Random(0x21448)
    for _ in range(250):
        c=settings(configure(initial()));c['match']['seeds']=[rng.getrandbits(32) for _ in range(6)]
        c['board'][14]['type']=rng.randrange(7);c['preview']['potions'][14]=[1,0,0]
        c['special_link']=rng.choice([-1,0,35]);c['special_choice']=rng.randrange(4)
        c['args']=[14,rng.randrange(6),rng.choice([-1,0,35]),rng.choice([0,3])];yield c
    c=settings(configure(initial()));c['match']['seeds'][0]=0x80000000;c['args']=[14,2,-1,0];yield c

def main():
    old=Original();new=Native();count=frames=arrivals=gestures=boundary_cases=batch_frames=0
    def compare(case,a,b):
        if a!=b:
            (HERE/'motion_failure.json').write_text(json.dumps(dict(case=case,original=a,native=b),indent=2))
            raise AssertionError(f'{count=} {frames=}: see motion_failure.json')
    for c in cases():
        old.load(c);new.load(c);a=old.init_direct(*c['args']);compare(c,a,new.init_direct(*c['args']))
        for _ in range(180):
            if not a['tokens'][0]['active']:break
            dt=[1/60,1/120,.033,.1][count%4];a=old.frame(0,dt);compare(c,a,new.frame(0,dt));frames+=1
        assert not a['tokens'][0]['active'];count+=1
    for progress in [0,.5,.99,1,1.01,2]:
      for dt in [0,.01,.25]:
       for distance in [.01,.1,1]:
        c=settings(configure(initial()));old.load(c);new.load(c)
        compare(c,old.init_direct(14,2,-1,0),new.init_direct(14,2,-1,0))
        end=target(0,2);values=dict(position=[end[0]-distance,end[1]],progress=progress,acceleration=0,speed=1)
        old.override(0,values);new.override(0,values)
        compare(c,old.frame(0,dt),new.frame(0,dt));boundary_cases+=1
    for path in list(rectangles())[::5]:
        c=settings(configure(initial()))
        for t in c['board']:t['type']=2
        old.load(c);new.load(c)
        if hasattr(new,'batch_pending'):del new.batch_pending
        for index in path:compare(c,old.step(1,c['board'][index]['center']),new.step(1,c['board'][index]['center']))
        compare(c,old.step(2,[.5,.5]),new.step(2,[.5,.5]));compare(c,old.motion_status(),new.motion_status())
        # Execute the actual bounded Game::Process token subsection.
        for frame in range(180):
            before=sum(t.active for t in new.motions.values())
            a=old.batch(1/60,[0,0,0]);compare(c,a,new.batch(1/60,[0,0,0]));batch_frames+=1
            arrivals+=before-sum(t.active for t in new.motions.values())
            if not a['pending']:break
        else:raise AssertionError('motion did not complete')
        gestures+=1
        # An extra frame after completion must not grant again.
        compare(c,old.batch(1/60,[0,0,0]),new.batch(1/60,[0,0,0]));batch_frames+=1
    early_cases=0
    for menus in [[1,0,0],[0,1,0],[0,0,1],[0,0,0]]:
      for health in [0,10]:
       for linked in [-1,0]:
        c=settings(configure(initial()));c['resources']['health']=health;old.load(c);new.load(c)
        if hasattr(new,'batch_pending'):del new.batch_pending
        for tile in [14,15]:compare(c,old.run_token(tile,2,False,-1),new.run_token(tile,2,False,-1))
        for slot in range(2):old.override(slot,dict(speed=100,linked=linked));new.override(slot,dict(speed=100,linked=linked))
        for _ in range(3):compare(c,old.batch(.25,menus),new.batch(.25,menus));batch_frames+=1
        early_cases+=1
    report=dict(status='passed',initialisation_cases=count,motion_frames=frames,integrated_gestures=gestures,
        naturally_completed_coin_rewards=arrivals,boundary_cases=boundary_cases,batch_frames=batch_frames,menu_death_link_cases=early_cases,branch_visits=old.motion_visits,
        actual_original=['Token::InitialiseFromTile','Token::Process','Rand(float,float,RandType)','RandUnitF','Clamp','vector normalization/division',
            'rune/MatchTile/AddToken/AddResource in integration'],
        boundaries=['Interface target coordinates and special-target choice','quad rendering (position/scale copy adapted)',
            'Game::Process outside token subsection','Healing/CheckEndGame/UI'],
        scope='Token init/motion/arrival plus normal coin reward integration. Not a full game turn.')
    (HERE/'motion_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    functions=[]
    for symbol,addr,size,fn,module in [('Token::InitialiseFromTile',0x21448,0x1fc,'dr_initialise_token','motion'),
        ('Token::Process',0x21644,0x174,'dr_process_token','motion'),('Rand(float,float,RandType)',0x1b7a8,0x44,'dr_random_float','random')]:
        functions.append(dict(original_symbol=symbol,address=hex(addr),size=size,sha256=hashlib.sha256(old.old.bytes_at(addr,size)).hexdigest(),native_function=fn,module=module))
    (HERE/'motion_provenance.json').write_text(json.dumps(dict(functions=functions),indent=2)+'\n')
    (HERE/'token_loop_provenance.json').write_text(json.dumps(dict(original_symbol='Game::Process',native_function='dr_process_reward_tokens',
        status='partial function: token subsection only',ranges=[dict(address=hex(a),size=n,sha256=hashlib.sha256(old.old.bytes_at(a,n)).hexdigest())
            for a,n in [(0x1744c,0x90),(0x17d56,0xe)]]),indent=2)+'\n')
    print(json.dumps(report));new.tokens_lib.dr_token_queue_destroy(new.q);new.q=None
if __name__=='__main__':main()
