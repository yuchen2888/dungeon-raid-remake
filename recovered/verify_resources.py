#!/usr/bin/env python3
"""Original AddResource instructions vs source; token arrival is injected explicitly."""
import ctypes as C
import hashlib
import json
import random
import re
import struct
from verify_tokens import Native as TokenNative, Original as TokenOriginal, configure as token_configure
from verify_match import Match
from verify_stroke import I32,U8,HERE,initial
from verify_rune import rectangles

INTS=dict(health=0xbd98,health_max=0xbd9c,health_bonus=0xbda0,xp=0xbdb0,up=0xbdb4,gold=0xbdb8)
FLOATS=dict(xp_fraction=0xbdd0,up_fraction=0xbde0,gold_fraction=0xbdd8)
MORE=dict(level=0xbe4c,total_xp=0xbe50,total_gold=0xbe54,total_up=0xbe58,
    ui_health=0x5994,ui_xp=0x599c,ui_up=0x59a0,ui_gold=0x59a4,ui_armour=0x59c0,poison=0x15540,skill_count=0xbfa0)
BYTES=dict(guard_164a6=0x164a6,guard_164a4=0x164a4)
class Resource(C.Structure):
    _fields_=[('match',C.POINTER(Match))]+[(k,I32) for k in INTS]+[(k,C.c_float) for k in FLOATS]+[(k,I32) for k in MORE]+[('skill_max',I32*4),('skill_current',I32*4)]+[(k,U8) for k in BYTES]
class Event(C.Structure):_fields_=[(k,I32) for k in ['kind','a','b','c','d']]
CALLBACK=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(Event))
class Hooks(C.Structure):_fields_=[('context',C.c_void_p),('event',CALLBACK)]
def bits(x):return struct.unpack('<I',struct.pack('<f',x))[0]
def configure(case):
    token_configure(case)
    case['resources']=dict(health=10,health_max=30,health_bonus=2,xp=0,up=0,gold=0,
        xp_fraction=0,up_fraction=0,gold_fraction=0,level=1,total_xp=0,total_gold=0,total_up=0,
        ui_health=10,ui_xp=0,ui_up=0,ui_gold=0,ui_armour=5,poison=3,skill_count=2,
        skill_max=[5]*4,skill_current=[0]*4,guard_164a6=0,guard_164a4=0)
    return case

class Native(TokenNative):
    def __init__(self):
        super().__init__();self.resources_lib=C.CDLL(str(HERE/'recovered_resources_native.dylib'))
        self.add=self.resources_lib.dr_add_resource;self.add.argtypes=[C.POINTER(Resource),I32,I32,I32,C.POINTER(Hooks)];self.add.restype=None
    def load(self,case):
        super().load(case);self.r=Resource();self.r.match=C.pointer(self.m)
        for k in [*INTS,*FLOATS,*MORE,*BYTES]:setattr(self.r,k,case['resources'][k])
        for k in ['skill_max','skill_current']:setattr(self.r,k,(I32*4)(*case['resources'][k]))
        def receive(_,p):
            e=p.contents;self.resource_events.append([e.kind,e.a,e.b,e.c,e.d])
        self.resource_event=CALLBACK(receive);self.resource_hooks=Hooks(None,self.resource_event)
    def resource_status(self):
        return dict(**{k:getattr(self.r,k) for k in [*INTS,*MORE,*BYTES]},
            **{k:bits(getattr(self.r,k)) for k in FLOATS},
            skill_max=list(self.r.skill_max),skill_current=list(self.r.skill_current),
            armour=self.p.armour_current,events=self.resource_events)
    def run_resource(self,reward,token,amount):
        self.resource_events=[];self.add(C.byref(self.r),reward,token,amount,C.byref(self.resource_hooks));return self.resource_status()

class Original(TokenOriginal):
    def __init__(self):
        super().__init__();self.u.mem_map(0x1700000,0x10000);self.resource_calls={};self.resource_active=False;self.resource_visits={}
        text=(HERE.parent/'armv7-disassembly.txt').read_text()
        symbols={
            '__ZN4Game10QueueSoundE5Sound':'sound','__ZN9Interface12UpdateSkillsEv':'skills',
            '__ZN9Interface15UpdateHealthBarER4Quadi':'health','__ZN9Interface9SetPoisonEi':'poison',
            '__ZN9Interface9GetTargetE8TileType':'target','__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif':'label',
            '__ZN4Game12CheckEndGameEv':'end','__ZN9Interface10ShowHelpXPEv':'help_xp',
            '__ZN9Interface10ShowHelpUPEv':'help_up','__ZN9Interface12ShowHelpGoldEv':'help_gold',
            '__ZN9Interface14ShowHelpArmourEv':'help_armour','__ZN9Interface11SetXPshadowEi':'shadow_xp',
            '__ZN9Interface11SetUPshadowEi':'shadow_up','__ZN9Interface13SetGoldShadowEi':'shadow_gold',
            '__ZN9Interface8ShowMenuE8MenuType':'menu','__ZN4Game7HealingEv':'healing',
            '__ZN4Game16QueueAchievementE11Achievementf':'achievement',
            '__ZN9Interface11UpdateXPBarER4Quadi':'bar_xp','__ZN9Interface11UpdateUPBarER4Quadi':'bar_up',
            '__ZN9Interface13UpdateGoldBarERA2_4Quadi':'bar_gold','__ZN9Interface17UpdateShieldValueEv':'shield'}
        for symbol,name in symbols.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol
            self.resource_calls[int(m[1],16)]=name
    def hook(self,u,address,size,context):
        if not getattr(self,'resource_active',False):return super().hook(u,address,size,context)
        if address in [0x12f3c,0x12f7a,0x12fa0,0x12fd2,0x13064,0x13078,0x130f2,0x13100,0x13108,0x13188,0x131e4,0x13222,0x13276,0x132d4,0x1337c,0x1340e,0x134b6,0x13512]:
            key=hex(address);self.resource_visits[key]=self.resource_visits.get(key,0)+1
        name=self.resource_calls.get(address)
        if not name:return super().hook(u,address,size,context)
        r=[C.c_int32(u.reg_read(v)).value for v in self.regs];sp=u.reg_read(self.SP);e=None
        if name=='sound':e=[1,r[1],0,0,0]
        elif name=='skills':e=[2,0,0,0,0]
        elif name=='health':e=[3,r[2],0,0,0]
        elif name=='poison':e=[4,r[1],0,0,0]
        elif name=='target':e=[5,r[1],0,0,0];u.reg_write(self.regs[0],0x170f000)
        elif name=='label':
            assert r[2]==0x170f000
            e=[6,r[1],r[3],self.read(sp),self.read(sp+4)]
        elif name=='end':e=[7,u.mem_read(self.GAME+BYTES['guard_164a4'],1)[0],C.c_int32(self.read(self.GAME+INTS['health'])).value,0,0]
        elif name.startswith('help_'):e=[8,{'gold':0,'xp':1,'up':2,'armour':3}[name[5:]],0,0,0]
        elif name.startswith('shadow_'):e=[9,{'xp':1,'gold':2,'up':3}[name[7:]],r[1],0,0]
        elif name=='menu':e=[10,r[1],0,0,0]
        elif name=='healing':e=[11,0,0,0,0]
        elif name=='achievement':e=[12,r[1],r[2],0,0]
        elif name.startswith('bar_'):e=[{'xp':13,'up':14,'gold':15}[name[4:]],r[2],0,0,0]
        elif name=='shield':e=[16,0,0,0,0]
        assert e is not None;self.resource_events.append(e);u.reg_write(self.PC,u.reg_read(self.LR))
    def load(self,case):
        super().load(case);c=case['resources']
        for k,a in {**INTS,**MORE}.items():self.write(self.GAME+a,c[k])
        for k,a in FLOATS.items():self.write(self.GAME+a,bits(c[k]))
        for k,a in BYTES.items():self.u.mem_write(self.GAME+a,bytes([c[k]]))
        for i in range(4):
            base=0x1700000+0x100*i;self.write(self.GAME+0xbf90+4*i,base)
            self.write(base+0x8c,c['skill_max'][i]);self.write(base+0x90,c['skill_current'][i])
    def resource_status(self):
        return dict(**{k:C.c_int32(self.read(self.GAME+a)).value for k,a in {**INTS,**MORE}.items()},
            **{k:self.read(self.GAME+a) for k,a in FLOATS.items()},
            **{k:self.u.mem_read(self.GAME+a,1)[0] for k,a in BYTES.items()},
            skill_max=[C.c_int32(self.read(0x170008c+0x100*i)).value for i in range(4)],
            skill_current=[C.c_int32(self.read(0x1700090+0x100*i)).value for i in range(4)],
            armour=C.c_int32(self.read(self.GAME+0xbda4)).value,events=self.resource_events)
    def run_resource(self,reward,token,amount):
        self.resource_active=True;self.resource_events=[];u=self.u
        for reg,value in zip(self.regs,[self.GAME,reward,token,amount]):u.reg_write(reg,value & 0xffffffff)
        u.reg_write(self.SP,0x140fff0);u.reg_write(self.LR,self.STOP|1)
        try:
            u.emu_start(0x12ee9,self.STOP,timeout=1000000,count=1000000)
            assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
            return self.resource_status()
        finally:self.resource_active=False

def cases():
    for reward in range(8):
      for token in range(4):
       for amount in [-1,0,1,2,3,4,20]:
        for skills in [0,2,4]:
            c=configure(initial());c['resources']['skill_count']=skills;c['calls']=[(reward,token,amount)];yield c
    for race in range(10):
      for enemy in [0,9,12]:
       for matched in [0,1]:
        c=configure(initial());c['game']['race']=race;c['board'][14].update(type=1,enemy=enemy,matched=matched)
        c['calls']=[(0,0,-1),(3,0,-1),(3,0,-1)];yield c
    for level in [1,4,9,24,49,99]:
      for mode in [0,1]:
       for class_type in [0,1]:
        for perks in [0,1,2]:
         for flaws in [0,4]:
            c=configure(initial());c['game'].update(race=4,flaws=[1]*flaws+[255]*(4-flaws))
            c['match'].update(spawn_enabled_14ae0=3,class_type=class_type,perks=[2]*perks+[255]*(4-perks))
            c['record']=1;c['mode']=mode;c['resources'].update(level=level,xp=99,skill_count=0)
            c['calls']=[(1,0,-1)];yield c
    for health in [0,2,3,4,30,32,33,2147483647,-2147483648]:
      for token in [0,2,3]:
       for guard in range(4):
        c=configure(initial());c['resources'].update(health=health,guard_164a6=guard&1,guard_164a4=guard>>1)
        c['calls']=[(1 if token==3 else 0,token,3)];yield c
    rng=random.Random(0x12ee8)
    for _ in range(600):
        c=configure(initial());r=c['resources'];p=c['preview'];c['record']=rng.randrange(2);c['mode']=rng.randrange(3)
        r.update(health=rng.randrange(60),health_max=rng.randrange(1,60),health_bonus=rng.randrange(10),poison=rng.randrange(10),skill_count=rng.randrange(5),
            guard_164a6=rng.randrange(2),guard_164a4=rng.randrange(2),skill_max=[rng.randrange(1,10) for _ in range(4)],skill_current=[rng.randrange(10) for _ in range(4)])
        for k in ['xp','gold','up']:r[k]=rng.choice([0,90,98,99,100,199,2147483647])
        for k in FLOATS:r[k]=rng.choice([0,.1,.5,.9999999,1,4])
        for k in ['xp_bonus','upgrade_bonus','gold_bonus']:p[k]=rng.choice([-.5,0,.1,.25,.5,1,4,110])
        for k in ['double_upgrade','double_healing','double_gold']:p[k]=rng.randrange(2)
        p.update(armour_current=rng.randrange(20),armour_max=rng.randrange(20),shield_value=rng.randrange(5),shield_bonus=rng.randrange(4),healing_value=rng.randrange(5),healing_bonus=rng.randrange(4))
        c['calls']=[(rng.randrange(4),rng.randrange(4),rng.randrange(-1,8)) for _ in range(8)];yield c

def main():
    old=Original();new=Native();direct=calls=gestures=steps=arrivals=0
    def compare(case,a,b):
        if a!=b:
            (HERE/'resources_failure.json').write_text(json.dumps(dict(case=case,original=a,native=b),indent=2))
            raise AssertionError(f'{direct=} {calls=}: see resources_failure.json')
    for case in cases():
        old.load(case);new.load(case)
        for args in case['calls']:compare(case,old.run_resource(*args),new.run_resource(*args));calls+=1
        direct+=1
    for path in rectangles():
        case=configure(initial());case['record']=1;case['mode']=0
        # Ordinary coins isolate arrival application from unrecovered token classification.
        for t in case['board']:t.update(type=2)
        case['resources']['gold']=98;old.load(case);new.load(case)
        for index in path:compare(case,old.step(1,case['board'][index]['center']),new.step(1,case['board'][index]['center']));steps+=1
        compare(case,old.step(2,[.5,.5]),new.step(2,[.5,.5]));steps+=1
        requests=old.token_status()['requests'];assert requests==new.token_status()['requests']
        for tile,reward,position,token in requests:
            assert reward==2 and token==0
            compare(case,old.run_resource(reward,token,-1),new.run_resource(reward,token,-1));arrivals+=1
        gestures+=1
    report=dict(status='passed',direct_scenarios=direct,direct_calls=calls,integrated_gestures=gestures,integrated_steps=steps,
        injected_normal_coin_arrivals=arrivals,branch_visits=old.resource_visits,
        original='Actual AddResource/GetEnemyCount/GetMortalEnemyType/GetPerkCount/GetFlawCount instructions; integrated rune/MatchTile/AddToken',
        boundaries=['Token initialisation, motion and completion timing (normal coin arrivals explicitly injected)',
            'Healing','CheckEndGame','UI, sound, achievements','old collection allocation'],
        scope='Health/skill charges/XP/gold/UP/armour state changes and ordered callback requests; not complete turn or App.')
    (HERE/'resources_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    provenance=dict(original_symbol='Game::AddResource',address='0x12ee8',size=0x68c,
        sha256=hashlib.sha256(old.old.bytes_at(0x12ee8,0x68c)).hexdigest(),native_source='recovered_resources.cpp',
        status='resource dispatch and state changes reconstructed; completion timing and declared subsystem callbacks separate')
    (HERE/'resources_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(json.dumps(report));new.tokens_lib.dr_token_queue_destroy(new.q);new.q=None
if __name__=='__main__':main()
