#!/usr/bin/env python3
"""Actual original type generation/promotion/stats with graphics at boundaries."""
import ctypes as C
import json,random,re,struct
from verify_refill import Native as RefillNative,Original as RefillOriginal,Refill,configure as refill_configure
from verify_path import convert
from verify_round import base_case
from verify_resources import Resource,bits
from verify_stroke import HERE,I32,U8
class Extra(C.Structure):_fields_=[('variant',I32),('max_health',I32),('label_offset',C.c_float),('flag224',U8)]
GINTS=dict(time_to_promotion=0x14af0,generated_count=0x165c0,generated_enemies=0x165c4)
GBYTES=dict(promotion_enabled=0x14af4,force_coins=0x14af6,inhibit_force_coins=0x15563,one_health=0x14af5,filter_enabled=0xbfb8,filter_swords=0xbfb9)
class Generation(C.Structure):_fields_=[('refill',C.POINTER(Refill)),('resources',C.POINTER(Resource)),('tiles',Extra*36)]+[(k,I32) for k in GINTS]+[(k,U8) for k in GBYTES]
class Event(C.Structure):_fields_=[(k,I32) for k in ['kind','tile','a','b','c','d']]
EVENT=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(Event))
class Hooks(C.Structure):_fields_=[('context',C.c_void_p),('event',EVENT)]
FUNCTIONS={'stats':(0x3e740,'dr_generate_stats',2),'type':(0x3f32c,'dr_set_tile_type',3),'promote':(0x3f260,'dr_promote_tile',3),'randomise':(0xf5b8,'dr_randomise_tile',0),'arrow':(0x3d870,'dr_make_arrow',0),'mana':(0x3d814,'dr_make_mana_potion',0),'broken':(0x3d714,'dr_make_broken',0),'values':(0x3db9c,'dr_update_generated_values',0),'due':(0xcbc4,'dr_time_to_promote',-1),'set_due':(0x90d8,'dr_set_time_to_promotion',-2),'xp':(0x189fc,'dr_generation_total_xp',-1)}
def configure(c=None):
    if c is None:c=convert(base_case())
    refill_configure(c);c['generation']={**{k:0 for k in GBYTES},'promotion_enabled':1,'time_to_promotion':30,'generated_count':5,'generated_enemies':3}
    c['extras']=[dict(variant=i%8,max_health=90+i,label_offset=-.02,flag224=i%2) for i in range(36)]
    c['path_state']['turn']=123;c['board'][17]['type']=1;c['board'][17]['enemy']=0
    return c

class Native(RefillNative):
    def __init__(self):
        super().__init__();self.gen_lib=C.CDLL(str(HERE/'recovered_generation_native.dylib'));self.gen_fns={}
        for key,(_,name,n) in FUNCTIONS.items():
            f=getattr(self.gen_lib,name)
            f.argtypes=[C.POINTER(Generation)]+([C.c_uint32]+[I32]*n+[C.POINTER(Hooks)] if n>=0 else [I32,C.POINTER(Hooks)] if n==-2 else [])
            f.restype=I32 if key=='xp' else C.c_bool if key=='due' else None;self.gen_fns[key]=f
    def load(self,c):
        super().load(c);self.gen=Generation();self.gen.refill=C.pointer(self.refill);self.gen.resources=C.pointer(self.r)
        for k,v in c['generation'].items():setattr(self.gen,k,v)
        for i,t in enumerate(c['extras']):
            for k,v in t.items():setattr(self.gen.tiles[i],k,v)
        self.path_events=[];self.gen_events=[]
        def event(_,ptr):
            e=ptr.contents;self.gen_events.append([e.kind,e.tile,e.a,e.b,e.c,e.d])
        self.gen_event=EVENT(event);self.gen_hooks=Hooks(None,self.gen_event)
    def gen_status(self):
        return dict(refill=self.refill_status(),generation={k:getattr(self.gen,k) for k in [*GINTS,*GBYTES]},extras=[dict(variant=t.variant,max_health=t.max_health,label_offset=bits(t.label_offset),flag224=t.flag224) for t in self.gen.tiles],events=self.gen_events,seeds=list(self.m.random.seeds),armour=self.p.armour_current,ui_armour=self.r.ui_armour)
    def generate(self,key,i=17,*args):
        self.gen_events=[];n=FUNCTIONS[key][2];f=self.gen_fns[key]
        result=f(C.byref(self.gen),i,*args,C.byref(self.gen_hooks)) if n>=0 else f(C.byref(self.gen),i,C.byref(self.gen_hooks)) if n==-2 else f(C.byref(self.gen))
        return dict(result=int(result) if result is not None else None,**self.gen_status())

class Original(RefillOriginal):
    def __init__(self):
        super().__init__();self.gen_active=False;self.pending_gen=None;self.gen_calls={};self.gen_visits={}
        text=(HERE.parent/'armv7-disassembly.txt').read_text()
        names={'__ZN4Quad9SetColourERK9GLcolour4':'colour','__ZN4Quad5SetUVEffff':'uv','__ZN4Tile10UpdateTextEbbb':'text','__ZN4Tile15UpdateCountdownEv':'countdown','__ZN4Tile13UpdateEnemyUVEv':'enemy_uv','__ZN4Game10QueueSoundE5Sound':'sound','__ZN4Game16QueueAchievementE11Achievementf':'achievement','__ZN9Interface17UpdateShieldValueEv':'shield','__ZN4Game21InialiseShieldShatterEv':'shatter','__ZN4Game8JumpDownEP4Tile':'jump'}
        for s,n in names.items():
            m=re.search(r'^'+re.escape(s)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,s;self.gen_calls[int(m[1],16)]=n
    def hook(self,u,address,size,context):
        if not getattr(self,'gen_active',False):return super().hook(u,address,size,context)
        r=[u.reg_read(v) for v in self.regs];signed=lambda v:C.c_int32(v).value
        if self.pending_gen and address==self.pending_gen[0]:
            _,lo,hi,stream=self.pending_gen;self.gen_events.append([1,-1,lo,hi,stream,signed(r[0])]);self.pending_gen=None
        if address==0x1bca0:self.pending_gen=(u.reg_read(self.LR)&~1,*map(signed,r[:3]));return
        if address in [0xf5b8,0x3f32c,0x3e740,0x3f260,0xcbc4,0x90d8]:
            self.gen_visits[hex(address)]=self.gen_visits.get(hex(address),0)+1;return
        name=self.gen_calls.get(address)
        if not name:return super().hook(u,address,size,context)
        e=None
        if name=='colour':e=[2,self.index(r[0]),signed(self.read(r[1])),0,0,0]
        elif name=='uv':e=[3,self.index(r[0]),*map(signed,r[1:]),signed(self.read(u.reg_read(self.SP)))]
        elif name=='text':e=[4,self.index(r[0]),*r[1:],0]
        elif name=='countdown':e=[5,self.index(r[0]),0,0,0,0]
        elif name=='enemy_uv':e=[6,self.index(r[0]),0,0,0,0]
        elif name=='sound':e=[7,-1,r[1],0,0,0]
        elif name=='achievement':e=[8,-1,r[1],signed(r[2]),0,0]
        elif name=='shield':e=[9,-1,0,0,0,0]
        elif name=='shatter':e=[10,-1,0,0,0,0]
        elif name=='jump':e=[11,self.index(r[1]),0,0,0,0]
        self.gen_events.append(e);u.reg_write(self.PC,u.reg_read(self.LR))
    def load(self,c):
        super().load(c);self.gen_events=[];self.pending_gen=None
        for k,a in GINTS.items():self.write(self.GAME+a,c['generation'][k])
        for k,a in GBYTES.items():self.u.mem_write(self.GAME+a,bytes([c['generation'][k]]))
        for i,t in enumerate(c['extras']):
            base=self.tile(i);self.write(base+0x22c,t['variant']);self.write(base+0xb0,t['max_health']);self.write(base+0xb4,bits(t['label_offset']));self.u.mem_write(base+0x224,bytes([t['flag224']]))
    def gen_status(self):
        signed=lambda a:C.c_int32(self.read(a)).value
        return dict(refill=self.refill_status(),generation=dict(**{k:signed(self.GAME+a) for k,a in GINTS.items()},**{k:self.u.mem_read(self.GAME+a,1)[0] for k,a in GBYTES.items()}),extras=[dict(variant=signed(self.tile(i)+0x22c),max_health=signed(self.tile(i)+0xb0),label_offset=self.read(self.tile(i)+0xb4),flag224=self.u.mem_read(self.tile(i)+0x224,1)[0]) for i in range(36)],events=self.gen_events,seeds=list(struct.unpack('<6I',self.u.mem_read(0x1eac20,24))),armour=signed(self.GAME+0xbda4),ui_armour=signed(self.GAME+0x59c0))
    def generate(self,key,i=17,*args):
        self.gen_events=[];self.pending_gen=None;addr,_,n=FUNCTIONS[key];self.gen_active=True
        params=([self.GAME,self.tile(i)] if key=='randomise' else [self.tile(i),*args]) if n>=0 else [self.GAME,i] if n==-2 else [self.GAME]
        try:self.call(addr,params)
        finally:self.gen_active=False
        return dict(result=C.c_int32(self.u.reg_read(self.regs[0])).value if key in ['xp','due'] else None,**self.gen_status())

def scenarios():
    for difficulty in range(5):
     for turn in [1,4,69,70,99,100,499,500,501,800,2000]:
      for enemy in range(33):
        c=configure();c['board'][17]['enemy']=enemy;c['game']['race']=6 if enemy%2 else 0
        c['game']['flaws']=[3,8,9,255];c['resources']['total_xp']=4100 if turn%2 else 0
        yield c,'stats',[turn,difficulty]
    for mode in [0,1,2]:
     for difficulty in range(4):
      for turn in [1,19,500,503,1000]:
       c=configure();c['record']=1;c['mode']=mode;c['board'][17]['enemy']=5;c['resources']['total_xp']=20000
       yield c,'stats',[turn,difficulty]
    for seed in range(1,251):
     for filter_mode in range(3):
       c=configure();c['match']['seeds']=[seed*712+i*7919 for i in range(6)];c['match']['perks']=[1,6,8,255];c['game']['flaws']=[7,255,255,255]
       c['match']['class_type']=seed%2;c['game']['race']=seed%10;c['generation'].update(filter_enabled=int(filter_mode>0),filter_swords=int(filter_mode==2),force_coins=int(seed%7==0),inhibit_force_coins=int(seed%11==0),one_health=seed%2,time_to_promotion=0 if seed%3==0 else 10)
       c['record']=int(seed%13==0);c['mode']=seed%2
       for k in ['flag231','flag255','selected','magic_sword','broken','flaming','self_flame']:c['board'][17][k]=1
       c['preview']['potions'][17]=[1,1,1];c['combat'][17]['poison']=[3,5,7,1,1,123];c['match']['flag_25d'][17]=1
       yield c,'randomise',[]
    for kind in range(7):
     for method in ['type','arrow','mana','broken','values']:
       c=configure();c['board'][17]['type']=kind;c['generation']['time_to_promotion']=0
       yield c,method,[kind,123,2] if method=='type' else []
    for due in [-1,0,1,2,10,199,200]:
     for record in [0,1]:
      for mode in [0,1]:
       for turn in [1,3,4,12,13,14,23,24,100]:
        for flaw in [8,255]:
         c=configure();c['generation']['time_to_promotion']=due;c['record']=record;c['mode']=mode;c['path_state']['turn']=turn;c['game']['flaws']=[flaw,255,255,255]
         yield c,'due',[]

def main():
    old,new=Original(),Native();counts={}
    for c,key,args in scenarios():
        old.load(c);new.load(c);a=old.generate(key,17,*args);b=new.generate(key,17,*args)
        if a!=b:
            (HERE/'generation_failure.json').write_text(json.dumps(dict(case=c,key=key,args=args,original=a,native=b),indent=2));raise AssertionError(f'{key} {args}: generation_failure.json')
        counts[key]=counts.get(key,0)+1
    report=dict(status='passed',cases=sum(counts.values()),by_function=counts,original='Actual RandomiseTile/SetType/Promote/GenerateStats/IsTimeToPromote/SetTimeToPromotion/GetTotalXP/MakeArrow/MakeManaPotion/MakeBroken/UpdateValues and RNG',boundaries=['UI text/countdown rendering, atlas mutation, audio/achievements','JumpDown and shield-shatter dependency callbacks'],scope='Live shared tile, combat, resource, promotion and RNG state; exact ordered events and float bits. Positive turns through 2000; no claim for undefined original overflow domains.')
    (HERE/'generation_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
