#!/usr/bin/env python3
"""Original AddToken dispatch and counters; Token initialisation is explicit boundary."""
import ctypes as C
import hashlib
import json
import random
import re
from verify_match import Native as MatchNative,Original as MatchOriginal,Match,configure as match_configure,cases as match_cases
from verify_stroke import I32,U8,HERE,initial
from verify_rune import rectangles
U32=C.c_uint32
class Counters(C.Structure):
    _fields_=[('pending',U32),('allocated',U32),('normal',I32*3),('bonus',I32*3),('bonus_total',I32)]
class Request(C.Structure):_fields_=[(k,I32) for k in ['tile','reward','position','token_type']]
class TokenEvent(C.Structure):_fields_=[(k,I32) for k in ['kind','index','a','b','c','d']]
TOKEN_EVENT=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(TokenEvent))
class Hooks(C.Structure):_fields_=[('context',C.c_void_p),('event',TOKEN_EVENT)]

def configure(case):
    match_configure(case);case['real_tokens']=True
    case['tokens']=dict(pending=0,allocated=0,normal=[0]*3,bonus=[0]*3,bonus_total=77)
    return case

class Native(MatchNative):
    def __init__(self):
        super().__init__();lib=self.tokens_lib=C.CDLL(str(HERE/'recovered_tokens_native.dylib'));self.q=None
        lib.dr_token_queue_create.argtypes=[C.POINTER(Match)];lib.dr_token_queue_create.restype=C.c_void_p
        lib.dr_token_queue_destroy.argtypes=[C.c_void_p];lib.dr_token_queue_destroy.restype=None
        lib.dr_token_queue_restore.argtypes=[C.c_void_p,C.POINTER(Counters)];lib.dr_token_queue_restore.restype=None
        lib.dr_token_queue_counters.argtypes=[C.c_void_p];lib.dr_token_queue_counters.restype=C.POINTER(Counters)
        lib.dr_token_queue_request.argtypes=[C.c_void_p,U32,C.POINTER(Request)];lib.dr_token_queue_request.restype=C.c_bool
        lib.dr_enqueue_token.argtypes=[C.c_void_p,U32,I32,C.c_bool,I32,C.POINTER(Hooks)];lib.dr_enqueue_token.restype=None
    def load(self,case):
        if self.q:self.tokens_lib.dr_token_queue_destroy(self.q)
        super().load(case);self.q=self.tokens_lib.dr_token_queue_create(C.byref(self.m))
        c=case['tokens'];self.initial_pending=c['pending']
        counters=Counters(c['pending'],c['allocated'],(I32*3)(*c['normal']),(I32*3)(*c['bonus']),c['bonus_total'])
        self.tokens_lib.dr_token_queue_restore(self.q,C.byref(counters))
        def receive(_,p):
            e=p.contents;self.token_events.append([e.kind,e.index,e.a,e.b,e.c,e.d])
        self.token_event=TOKEN_EVENT(receive);self.token_hooks=Hooks(None,self.token_event)
        self.token_callback=lambda tile,reward,bonus,position:self.tokens_lib.dr_enqueue_token(self.q,tile,reward,bonus,position,C.byref(self.token_hooks))
        self.token_events=[]
    def token_status(self):
        c=self.tokens_lib.dr_token_queue_counters(self.q).contents;requests=[]
        for index in range(self.initial_pending,c.pending):
            r=Request();assert self.tokens_lib.dr_token_queue_request(self.q,index,C.byref(r))
            requests.append([r.tile,r.reward,r.position,r.token_type])
        return dict(pending=c.pending,allocated=c.allocated,normal=list(c.normal),bonus=list(c.bonus),
            bonus_total=c.bonus_total,total=self.p.total,requests=requests,events=self.token_events)
    def run_token(self,tile,reward,bonus,position):
        self.token_events=[];self.token_callback(tile,reward,bonus,position);return self.token_status()
    def run_match(self,index,reward):
        self.token_events=[];result=super().run_match(index,reward);result['tokens']=self.token_status();return result
    def step(self,phase,touch):
        self.token_events=[];result=super().step(phase,touch);result['tokens']=self.token_status();return result

class Original(MatchOriginal):
    def __init__(self):
        super().__init__();self.u.mem_map(0x1600000,0x100000);self.token_calls={}
        text=(HERE.parent/'armv7-disassembly.txt').read_text()
        symbols={'__ZNKSt6vectorI5TokenSaIS0_EE4sizeEv':'size',
            '__ZNSt6vectorI5TokenSaIS0_EE9push_backERKS0_':'push',
            '__ZN5TokenC1EP9Interface':'ctor','__ZN5TokenD1Ev':'dtor',
            '__ZN5Token18InitialiseFromTileEP4Tile8TileTypePK8GLfloat29TokenType':'init'}
        for symbol,name in symbols.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol
            self.token_calls[int(m[1],16)]=name
        self.token_visits={}
    def hook(self,u,address,size,context):
        if address in [0x98e8,0x992e,0x998a,0x99c2,0x99ee,0x9a2e,0x9a88,0x9b0e,0x9c26]:
            key=hex(address);self.token_visits[key]=self.token_visits.get(key,0)+1
        if address==0x9890 and getattr(self,'token_direct',False):return
        name=getattr(self,'token_calls',{}).get(address)
        if self.match_calls.get(address)=='help' and 0x9890<(u.reg_read(self.LR)&~1)<0x9c78:name='help'
        if not name:return super().hook(u,address,size,context)
        r=[u.reg_read(v) for v in self.regs];sp=u.reg_read(self.SP)
        if name=='size':u.reg_write(self.regs[0],self.token_allocated)
        elif name=='push':
            self.token_events.append([1,-1,self.token_allocated,0,0,0]);self.token_allocated+=1
        elif name=='init':
            slot=(r[0]-0x1600000)//160;position=self.index(r[3]-0x54) if r[3] else -1
            request=[self.index(r[1]),r[2],position,self.read(sp)];self.requests[slot]=request
            self.token_events.append([2,slot,*request])
        elif name=='help':
            self.token_events.append([3,self.point_index(r[1],r[2]),self.read(sp+4),C.c_int32(r[3]).value,C.c_int32(self.read(sp)).value,0])
        u.reg_write(self.PC,u.reg_read(self.LR))
    def load(self,case):
        super().load(case);c=case['tokens'];self.token_direct=False;self.token_events=[];self.requests={}
        self.initial_pending=c['pending'];self.token_allocated=c['allocated']
        self.write(self.GAME+0xb520,0x1600000);self.write(self.GAME+0xb52c,c['pending'])
        for i,v in enumerate(c['normal']):self.write(self.GAME+0x165dc+4*i,v)
        for i,v in enumerate(c['bonus']):self.write(self.GAME+0x165f0+4*i,v)
        self.write(self.GAME+0x165d4,c['bonus_total'])
    def token_status(self):
        pending=self.read(self.GAME+0xb52c)
        return dict(pending=pending,allocated=self.token_allocated,
            normal=[C.c_int32(self.read(self.GAME+0x165dc+4*i)).value for i in range(3)],
            bonus=[C.c_int32(self.read(self.GAME+0x165f0+4*i)).value for i in range(3)],
            bonus_total=C.c_int32(self.read(self.GAME+0x165d4)).value,total=self.total(),
            requests=[self.requests[i] for i in range(self.initial_pending,pending)],events=self.token_events)
    def run_token(self,tile,reward,bonus,position):
        self.token_events=[];self.token_direct=True;u=self.u
        for reg,value in zip(self.regs,[self.GAME,self.tile(tile),reward,int(bonus)]):u.reg_write(reg,value)
        u.reg_write(self.SP,0x140fff0);u.reg_write(self.LR,self.STOP|1)
        self.write(0x140fff0,self.tile(position)+0x54 if position>=0 else 0)
        u.emu_start(0x9891,self.STOP,timeout=1000000,count=1000000)
        assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC));return self.token_status()
    def run_match(self,index,reward):
        self.token_direct=False;self.token_events=[];result=super().run_match(index,reward);result['tokens']=self.token_status();return result
    def step(self,phase,touch):
        self.token_direct=False;self.token_events=[];result=super().step(phase,touch);result['tokens']=self.token_status();return result

def cases():
    for reward in range(8):
      for bonus in [False,True]:
       for broken in [0,1]:
        for mode in [0,1,2]:
         for allocated in [0,5]:
            case=configure(initial());case['record']=1;case['mode']=mode
            case['board'][14]['broken']=broken;case['tokens']['allocated']=allocated
            case['calls']=[(14,reward,bonus,-1),(0,reward,bonus,14)];yield case
    rng=random.Random(0x9890)
    for _ in range(250):
        case=configure(initial());case['record']=1;case['mode']=0;p=case['preview'];c=case['tokens']
        c.update(pending=2,allocated=4,normal=[rng.randrange(15) for _ in range(3)],bonus=[rng.randrange(15) for _ in range(3)])
        p.update(armour_current=rng.randrange(20),armour_max=rng.randrange(30),shield_value=rng.randrange(5),shield_bonus=rng.randrange(3))
        for key in ['xp_bonus','gold_bonus','upgrade_bonus']:p[key]=rng.choice([0,.1,.25,.5,2,10])
        for key in ['double_upgrade','double_gold']:p[key]=rng.randrange(2)
        case['calls']=[(rng.randrange(36),rng.randrange(8),bool(rng.randrange(2)),rng.choice([-1,0,14])) for _ in range(5)]
        yield case

def main():
    old=Original();new=Native();direct=0;calls=0;matched=0;match_calls_count=0;steps=0
    def compare(case,a,b):
        if a!=b:
            (HERE/'tokens_failure.json').write_text(json.dumps(dict(case=case,original=a,native=b),indent=2))
            raise AssertionError('See tokens_failure.json')
    for case in cases():
        old.load(case);new.load(case)
        for args in case['calls']:compare(case,old.run_token(*args),new.run_token(*args));calls+=1
        direct+=1
    for case in match_cases():
        case['real_tokens']=True;case['tokens']=dict(pending=0,allocated=0,normal=[0]*3,bonus=[0]*3,bonus_total=77)
        old.load(case);new.load(case)
        for index,reward in case['calls']:compare(case,old.run_match(index,reward),new.run_match(index,reward));match_calls_count+=1
        matched+=1
    gestures=0
    for path in rectangles():
        case=configure(initial());old.load(case);new.load(case)
        for index in path:
            touch=case['board'][index]['center'];compare(case,old.step(1,touch),new.step(1,touch));steps+=1
        compare(case,old.step(2,[.5,.5]),new.step(2,[.5,.5]));steps+=1;gestures+=1
    report=dict(status='passed',direct_scenarios=direct,direct_calls=calls,match_scenarios=matched,match_calls=match_calls_count,
        integrated_gestures=gestures,integrated_steps=steps,branch_visits=old.token_visits,
        original='Actual AddToken, recursive MatchTile, GetRewards, RNG, input/selection/rune/preview instructions',
        boundaries=['Token::InitialiseFromTile (request recorded, no motion RNG)','SetSpecialType','Shapeshift','rendering/audio/UI/achievements','old containers','platform floorf/ceilf'],
        scope='Pending reward requests and counters, not Token::Process, actual player resource grants, refill or full turn.')
    (HERE/'tokens_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    provenance=dict(original_symbol='Game::AddToken',address='0x9890',size=0x3e8,
        sha256=hashlib.sha256(old.old.bytes_at(0x9890,0x3e8)).hexdigest(),native_source='recovered_tokens.cpp',
        status='dispatch, pending storage and counters reconstructed; Token initialisation/processing remain separate')
    (HERE/'tokens_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(json.dumps(report));new.tokens_lib.dr_token_queue_destroy(new.q);new.q=None

if __name__=='__main__':main()
