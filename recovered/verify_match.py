#!/usr/bin/env python3
"""Real MatchTile + GetRewards + RNG instructions versus native shared state."""
import ctypes as C
import hashlib
import json
import math
import random
import re
import struct
from verify_rune import Native as RuneNative, Original as RuneOriginal, configure as rune_configure, rectangles
from verify_preview import Preview
from verify_stroke import State as Stroke, Hooks, EVENT, I32, U8, HERE, initial

U32=C.c_uint32
class RandomState(C.Structure):_fields_=[('seeds',U32*6)]
class Match(C.Structure):
    _fields_=[('stroke',C.POINTER(Stroke)),('preview',C.POINTER(Preview)),('random',RandomState),
        ('matched_counts',I32*8),('bonus_chance',I32*4),('bonus_chance_extra',I32*4),('perks',I32*4),
        ('spawn_enabled_14ae0',I32),('spawn_remaining_15558',I32),('spawn_count_1555c',I32),('class_type',I32),
        ('class_level',U8),('unlocked',U8*9),('spawn_dirty_15555',U8),('sound_13ec4',U8),('flag_25d',U8*36),
        ('shake_progress_bd90',U32),('shake_scale_bd94',U32)]
class MatchEvent(C.Structure):_fields_=[(k,I32) for k in ['kind','tile','a','b','c','d']]
MATCH_EVENT=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(MatchEvent))
class MatchHooks(C.Structure):_fields_=[('context',C.c_void_p),('event',MATCH_EVENT)]
INTS=dict(spawn_enabled_14ae0=0x14ae0,spawn_remaining_15558=0x15558,spawn_count_1555c=0x1555c,class_type=0x15568)
BYTES=dict(class_level=0x155b8,spawn_dirty_15555=0x15555,sound_13ec4=0x13ec4)
UINTS=dict(shake_progress_bd90=0xbd90,shake_scale_bd94=0xbd94)
CHANCES=[0xbe20,0xbe28,0xbe18,0xbe30]

def configure(case):
    rune_configure(case)
    case['match']=dict(seeds=[123456+i*712 for i in range(6)],matched_counts=[0]*8,
        bonus_chance=[0]*4,bonus_chance_extra=[0]*4,perks=[255]*4,
        spawn_enabled_14ae0=0,spawn_remaining_15558=10,spawn_count_1555c=0,class_type=1,
        class_level=1,unlocked=[0]*9,spawn_dirty_15555=0,sound_13ec4=0,flag_25d=[0]*36,
        shake_progress_bd90=123,shake_scale_bd94=456)
    case['mark_matches']=False
    return case

class Native(RuneNative):
    def __init__(self):
        super().__init__();self.match_lib=C.CDLL(str(HERE/'recovered_match_native.dylib'))
        self.match_fn=self.match_lib.dr_match_tile
        self.match_fn.argtypes=[C.POINTER(Match),U32,I32,C.POINTER(MatchHooks)];self.match_fn.restype=None
    def load(self,case):
        super().load(case);self.m=Match();m=case['match']
        self.m.stroke=C.pointer(self.state);self.m.preview=C.pointer(self.p)
        self.m.random=RandomState((U32*6)(*m['seeds']))
        for k in [*INTS,*BYTES,*UINTS]:setattr(self.m,k,m[k])
        for k,n,t in [('matched_counts',8,I32),('bonus_chance',4,I32),('bonus_chance_extra',4,I32),('perks',4,I32),('unlocked',9,U8),('flag_25d',36,U8)]:setattr(self.m,k,(t*n)(*m[k]))
        def receive(_,pointer):
            e=pointer.contents;self.match_events.append([e.kind,e.tile,e.a,e.b,e.c,e.d])
            if e.kind==5 and hasattr(self,'token_callback'):self.token_callback(e.tile,e.a,bool(e.b),e.c)
            if e.kind==8 and case.get('mutate_special'):
                tile=self.state.selection.tiles[e.tile];tile.rule.type=6;tile.rule.special=e.a
            if e.kind==9 and 'shapeshift_race' in case:self.state.selection.character.race=case['shapeshift_race']
        self.match_callback=MATCH_EVENT(receive);self.match_hooks=MatchHooks(None,self.match_callback)
        original_callback=self.callback
        def selection_event(context,kind,index,a,b):
            original_callback(context,kind,index,a,b)
            if kind==18:self.match_fn(C.byref(self.m),index,a,C.byref(self.match_hooks))
        self.callback=EVENT(selection_event);self.hooks=Hooks(None,self.callback)
        self.match_events=[]
    def match_status(self):
        s=self.state.selection
        result={k:getattr(self.m,k) for k in [*INTS,*BYTES,*UINTS]}
        result.update(seeds=list(self.m.random.seeds),counts=list(self.m.matched_counts),
            tiles=[[t.rule.type,t.rule.special,t.rule.matched] for t in s.tiles],race=s.character.race,events=self.match_events)
        return result
    def run_match(self,index,reward):
        self.match_events=[];self.match_fn(C.byref(self.m),index,reward,C.byref(self.match_hooks));return self.match_status()
    def step(self,phase,touch):
        self.match_events=[];result=super().step(phase,touch);result['match']=self.match_status();return result

class Original(RuneOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.match_calls={}
        symbols={
          '__ZN4Game12AddParticlesEP4Tile12ParticleType':'particles',
          '__ZN4Game16QueueAchievementE11Achievementf':'achievement',
          '__ZN4Game10QueueSoundE5Sound':'sound',
          '__ZN4Game8AddFlareE9FlareType8GLfloat2RK9GLcolour4':'flare',
          '__ZN4Game8AddTokenEP4Tile8TileTypebPK8GLfloat2':'token',
          '__ZN8HelpMenu10InitialiseEffff8HelpType':'help',
          '__ZN4Game14AddSimpleLabelEP4Tile8TileType':'label',
          '__ZN4Tile14SetSpecialTypeE15SpecialTileType':'special',
          '__ZN4Game10ShapeshiftEv':'shapeshift',
          '__ZNSt4listI8TileTypeSaIS1_EE9push_backERKS1_':'reward_push',
          '__ZNSt10_List_baseI8TileTypeSaIS0_EE8_M_clearEv':'reward_clear'}
        # Symbol substitutions reflect the actual template mangling in this binary.
        symbols['__ZNSt4listI8TileTypeSaIS0_EE9push_backERKS0_']=symbols.pop('__ZNSt4listI8TileTypeSaIS1_EE9push_backERKS1_')
        for symbol,name in symbols.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M)
            assert m,symbol;self.match_calls[int(m[1],16)]=name
        self.match_visits={}
    def point_index(self,x,y,resting=False):
        point=struct.pack('<II',x,y)
        candidates=[i for i in range(36) if bytes(self.u.mem_read(self.GAME+0xb400+8*i if resting else self.tile(i)+0x54,8))==point]
        assert len(candidates)==1,(x,y,candidates);return candidates[0]
    def hook(self,u,address,size,context):
        if self.pending_random and address==self.pending_random[0]:
            _,lo,hi,stream=self.pending_random
            self.match_events.append([10,stream,lo,hi,C.c_int32(u.reg_read(self.regs[0])).value,0]);self.pending_random=None
        if address==0x1bca0:
            self.pending_random=(u.reg_read(self.LR)&~1,*[C.c_int32(u.reg_read(r)).value for r in self.regs[:3]])
        if address==0x194e20:
            value=struct.unpack('<f',struct.pack('<I',u.reg_read(self.regs[0])))[0]
            u.reg_write(self.regs[0],struct.unpack('<I',struct.pack('<f',float(math.floor(value))))[0])
            u.reg_write(self.PC,u.reg_read(self.LR));return
        if address in [0xbe60,0xbf32,0xc0f6,0xc114,0xc28e,0xc312,0xc378,0xc3b0,0xc3c0,0xc4a6,0xc520,0xc55a]:
            key=hex(address);self.match_visits[key]=self.match_visits.get(key,0)+1
        if address==0xbe60:
            if (u.reg_read(self.LR)&~1)==0xf9ce:self.events.append([18,self.index(u.reg_read(self.regs[1])),u.reg_read(self.regs[2]),0])
            return # Crucially execute the actual original MatchTile, including recursion.
        name=getattr(self,'match_calls',{}).get(address)
        if not name:return super().hook(u,address,size,context)
        r=[u.reg_read(v) for v in self.regs];sp=u.reg_read(self.SP);e=None
        if name=='particles':e=[1,self.index(r[1]),r[2],0,0,0]
        elif name=='achievement':
            # Rune's own achievement still belongs to the selection event stream.
            if (u.reg_read(self.LR)&~1)==0xfaec:self.events.append([19,-1,r[1],int(struct.unpack('<f',struct.pack('<I',r[2]))[0])])
            else:e=[2,-1,r[1],C.c_int32(r[2]).value,0,0]
        elif name=='sound':e=[3,-1,r[1],0,0,0]
        elif name=='flare':e=[4,self.point_index(r[2],r[3],True),r[1],C.c_int32(self.read(self.read(sp))).value,0,0]
        elif name=='token':
            position=self.read(sp);override=self.index(position-0x54) if position else -1
            e=[5,self.index(r[1]),r[2],r[3],override,0]
        elif name=='help':e=[6,self.point_index(r[1],r[2]),self.read(sp+4),C.c_int32(r[3]).value,C.c_int32(self.read(sp)).value,0]
        elif name=='label':e=[7,self.index(r[1]),r[2],0,0,0]
        elif name=='special':
            e=[8,self.index(r[0]),r[1],0,0,0]
            if self.case.get('mutate_special'):self.write(r[0]+0x9c,6);self.write(r[0]+0xa0,r[1])
        elif name=='shapeshift':
            e=[9,-1,0,0,0,0]
            if 'shapeshift_race' in self.case:self.write(self.GAME+0x1556c,self.case['shapeshift_race'])
        elif name=='reward_push':self.push(r[0],self.read(r[1]))
        elif name=='reward_clear':pass
        if e:self.match_events.append(e)
        if name=='token' and self.case.get('real_tokens'):return
        u.reg_write(self.PC,u.reg_read(self.LR))
    def load(self,case):
        self.pending_random=None;super().load(case);m=case['match'];self.match_events=[]
        for k,a in {**INTS,**UINTS}.items():self.write(self.GAME+a,m[k])
        for k,a in BYTES.items():self.u.mem_write(self.GAME+a,bytes([m[k]]))
        for i,v in enumerate(m['matched_counts']):self.write(self.GAME+0xbfa4+4*i,v)
        for i,a in enumerate(CHANCES):self.write(self.GAME+a,m['bonus_chance'][i]);self.write(self.GAME+a+4,m['bonus_chance_extra'][i])
        for i,v in enumerate(m['perks']):self.write(self.GAME+0x15574+4*i,v)
        for i,v in enumerate(m['unlocked']):self.u.mem_write(self.GAME+0x1573c+388*i,bytes([v]))
        for i,v in enumerate(m['flag_25d']):self.u.mem_write(self.tile(i)+0x25d,bytes([v]))
        self.u.mem_write(0x1eac20,struct.pack('<6I',*m['seeds']))
    def match_status(self):
        result={k:C.c_int32(self.read(self.GAME+a)).value for k,a in INTS.items()}
        result.update({k:self.read(self.GAME+a) for k,a in UINTS.items()})
        result.update({k:self.u.mem_read(self.GAME+a,1)[0] for k,a in BYTES.items()})
        result.update(seeds=list(struct.unpack('<6I',self.u.mem_read(0x1eac20,24))),
            counts=[C.c_int32(self.read(self.GAME+0xbfa4+4*i)).value for i in range(8)],
            tiles=[[self.read(self.tile(i)+0x9c),self.read(self.tile(i)+0xa0),self.u.mem_read(self.tile(i)+0x84,1)[0]] for i in range(36)],
            race=self.read(self.GAME+0x1556c),events=self.match_events)
        return result
    def run_match(self,index,reward):
        self.match_events=[];u=self.u
        for reg,value in zip(self.regs,[self.GAME,self.tile(index),reward,0]):u.reg_write(reg,value)
        u.reg_write(self.SP,0x140fff0);u.reg_write(self.LR,self.STOP|1)
        u.emu_start(0xbe61,self.STOP,timeout=2000000,count=2000000)
        assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        return self.match_status()
    def step(self,phase,touch):
        self.match_events=[];result=super().step(phase,touch);result['match']=self.match_status();return result

def cases():
    for kind in range(7):
      for reward in range(8):
       for matched in [0,1]:
        for broken in [0,1]:
         for special in [0,3]:
            case=configure(initial());case['board'][14].update(type=kind,matched=matched,broken=broken,special=special)
            case['calls']=[(14,reward)];yield case
    for kind in [0,1]:
      for index in range(36):
       for variant in range(3):
        case=configure(initial());case['board'][index].update(type=kind,enemy=10 if kind else 0)
        case['preview']['potions'][index]=[0,0,1] if kind==0 else [0,0,0]
        for i,t in enumerate(case['board']):
            if i!=index and (i+variant)%5==0:t.update(type=1,enemy=2)
            if i!=index and (i+variant)%7==0:t.update(type=0);case['preview']['potions'][i]=[0,0,1]
        case['calls']=[(index,5),(index,5)];yield case
    for enemy in range(33):
      for race in [0,7,9]:
       for spawn in [0,1,2]:
        case=configure(initial());case['game']['race']=race;case['board'][14].update(type=1,enemy=enemy)
        case['match'].update(spawn_enabled_14ae0=spawn,spawn_remaining_15558=spawn-1,
            spawn_count_1555c=spawn,class_type=spawn,class_level=10 if spawn==2 else 1)
        case['match']['flag_25d'][14]=1;case['mutate_special']=True;case['shapeshift_race']=0
        case['calls']=[(14,5)];yield case
    rng=random.Random(0xbe60)
    for _ in range(350):
        case=configure(initial());m=case['match'];m['seeds']=[rng.getrandbits(32) for _ in range(6)]
        m.update(spawn_enabled_14ae0=rng.randrange(3),spawn_remaining_15558=rng.randrange(-1,3),
            spawn_count_1555c=rng.randrange(5),class_type=rng.randrange(10),class_level=rng.choice([0,9,10]),
            unlocked=[rng.randrange(2) for _ in range(9)],matched_counts=[rng.choice([0,2,3,8,9,10,2147483647]) for _ in range(8)],
            bonus_chance=[rng.randrange(101) for _ in range(4)],bonus_chance_extra=[rng.randrange(10) for _ in range(4)],perks=[rng.choice([255,2])]*4)
        case['game']['race']=rng.randrange(10);case['record']=rng.randrange(2);case['mode']=rng.randrange(2)
        for i,t in enumerate(case['board']):
            t.update(type=rng.randrange(7),enemy=rng.randrange(33),special=rng.choice([0,1,3]),broken=rng.randrange(2))
            case['preview']['potions'][i]=[rng.randrange(2) for _ in range(3)]
        case['calls']=[(rng.randrange(36),rng.randrange(8)) for _ in range(6)];yield case

def main():
    old=Original();new=Native();count=0;calls=0;steps=0;events={}
    def compare(case,a,b):
        if a!=b:
            (HERE/'match_failure.json').write_text(json.dumps(dict(case=case,original=a,native=b),indent=2))
            raise AssertionError(f'Case {count}, calls {calls}: see match_failure.json')
    for case in cases():
        old.load(case);new.load(case)
        for index,reward in case['calls']:
            a=old.run_match(index,reward);b=new.run_match(index,reward);compare(case,a,b);calls+=1
            for event in a['events']:events[str(event[0])]=events.get(str(event[0]),0)+1
        count+=1
    gestures=0
    for path in rectangles():
        case=configure(initial());case['match']['bonus_chance']=[100]*4
        old.load(case);new.load(case)
        for index in path:
            touch=case['board'][index]['center'];compare(case,old.step(1,touch),new.step(1,touch));steps+=1
        compare(case,old.step(2,[.5,.5]),new.step(2,[.5,.5]));steps+=1;gestures+=1
    report=dict(status='passed',direct_scenarios=count,direct_calls=calls,integrated_gestures=gestures,integrated_steps=steps,
        event_counts=events,branch_visits=old.match_visits,
        actual_original_functions=['MatchTile including recursion','GetRewards','RandI / RandUnitF / Clamp','HavePerk','GetMortalEnemyType','IsNormalPotion','input/selection/rune/resource preview'],
        boundaries=['AddToken','SetSpecialType (optional same state adapter)','Shapeshift (optional same state adapter)','rendering/audio/UI/achievements','old list allocation','platform floorf/ceilf'],
        scope='Shared board matching and reward requests. No actual reward grant, complete token lifecycle, refill, turn or playable App.')
    (HERE/'match_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    provenance=dict(original_symbol='Game::MatchTile',address='0xbe60',size=0x804,
        sha256=hashlib.sha256(old.old.bytes_at(0xbe60,0x804)).hexdigest(),native_source='recovered_match.cpp',
        status='recursive control flow and state changes reconstructed with declared subsystem callbacks')
    (HERE/'match_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
