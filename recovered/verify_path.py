#!/usr/bin/env python3
"""Actual path/battle/matching/reward integration, with refill boundary explicit."""
import ctypes as C
import json,re,struct
from verify_motion import Native as MotionNative,Original as MotionOriginal,settings
from verify_resources import configure
from verify_stroke import HERE,initial,I32,U8
from verify_match import Match,MatchHooks
from verify_tokens import Hooks as TokenHooks
from verify_battle import BattleGame,Poison
from verify_round import cases as round_cases,RoundEvent,GAME_KEYS
class Combat(C.Structure):
    _fields_=[(k,I32) for k in ['attack','defence','health']]+[('poison',Poison)]+[(k,U8) for k in ['overlay','flag25e','attack_flag']]
class PathBattle(C.Structure):
    _fields_=[(k,I32) for k in ['kills_a','kills_b','killed_attack','break_chance','poison_amount']]+[(k,U8) for k in ['coin_on_attack','poison_sound']]
class Path(C.Structure):
    _fields_=[('match',C.POINTER(Match)),('queue',C.c_void_p),('battle',PathBattle),('combat',Combat*36)]+[(k,I32) for k in ['turn']]+[('input_ready',U8)]+[(k,I32) for k in ['crossing_best','crossing_average','crossing_samples','total']]
EVENT=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(RoundEvent))
class Hooks(C.Structure):_fields_=[('context',C.c_void_p),('event',EVENT),('match',C.POINTER(MatchHooks)),('tokens',C.POINTER(TokenHooks))]
GAME_INTS=dict(kills_a=0x165b4,kills_b=0x15548,killed_attack=0x164ac,break_chance=0xbdcc,poison_amount=0xbe5c,lich_progress=0xbd90,lich_transition=0xbd94)
GAME_BYTES=dict(coin_on_attack=0xbfbb,poison_sound=0x13ec5)
PATH_INTS=dict(turn=0xc,base_attack=0xbe7c,direction_bonus=0xbdbc,crossing_best=0x16608,crossing_average=0x16604,crossing_samples=0x16600,total=0x165cc)
COMBAT_INTS=dict(attack=0xa4,defence=0xa8,health=0xac)
COMBAT_BYTES=dict(overlay=0x1b0,flag256=0x256,flag25e=0x25e,attack_flag=0x86)
def convert(source):
    c=settings(configure(initial()));g=source['game'];c['path']=source['path'];c['fake']=source['excluded']
    c['game'].update(race=g['race'],flaws=g['flaws'],current_damage=g['base_attack'],weapon_damage=g['direction_bonus']);c['record']=g['record_14aed'];c['mode']=g['mode_14ae8']
    c['match'].update(matched_counts=g['matched_counts']+[0]*3,sound_13ec4=g['sound_13ec4'],shake_progress_bd90=g['lich_progress'],shake_scale_bd94=g['lich_transition'])
    c['preview']['total']=g['round_kills_165d0'];c['tokens']['bonus_total']=g['pending_165d4']
    c['battle']={k:g[k] for k in GAME_KEYS};c['path_state']={k:g['total_165cc'] if k=='total' else g[k] for k in PATH_INTS};c['path_state']['input_ready']=g['flag_5e14'];c['combat']=[]
    for i,t in enumerate(source['board']):
        c['board'][i].update(type=t['type'],enemy=t['enemy'],enemy_state=t['enemy_state'],special=t['special'],flag231=t['flag231'],flag255=t['frozen'],flaming=t['flag256'],matched=t['matched'])
        c['combat'].append({k:t[k] for k in [*COMBAT_INTS,*COMBAT_BYTES,'poison']})
    return c
class Native(MotionNative):
    def __init__(self):
        super().__init__();self.path_lib=C.CDLL(str(HERE/'recovered_path_native.dylib'))
        self.commit_fn=self.path_lib.dr_commit_path;self.commit_fn.argtypes=[C.POINTER(Path),C.POINTER(U8),C.c_size_t,C.POINTER(U8),C.c_size_t,C.POINTER(Hooks)];self.commit_fn.restype=None
    def load(self,c):
        super().load(c);self.path_state=Path();p=self.path_state;p.match=C.pointer(self.m);p.queue=self.q
        for k,v in c['battle'].items():
            if not k.startswith('lich_'):setattr(p.battle,k,v)
        for k,v in c['path_state'].items():
            if k not in ['base_attack','direction_bonus']:setattr(p,k,v)
        for i,t in enumerate(c['combat']):
            for k,v in t.items():
                if k!='flag256':setattr(p.combat[i],k,Poison(*v) if k=='poison' else v)
        def event(_,ptr):
            e=ptr.contents;self.path_events.append([e.tile,e.kind,e.a,e.b,e.c,e.d])
        self.path_event=EVENT(event);self.path_hooks=Hooks(None,self.path_event,C.pointer(self.match_hooks),C.pointer(self.token_hooks))
    def path_status(self):
        p=self.path_state;board=[]
        for t,s in zip(p.combat,self.state.selection.tiles):
            po=t.poison;board.append(dict(**{k:(s.flaming if k=='flag256' else getattr(t,k)) for k in [*COMBAT_INTS,*COMBAT_BYTES]},poison=[po.current,po.next,po.following,po.active,po.clearing,po.progress],enemy_state=s.rule.enemy_state,frozen=s.rule.flag255))
        match=self.match_status();match['counts']=match['counts'][:5] # Only five actual counters; following bytes are flags.
        return dict(battle={k:(C.c_int32(self.m.shake_progress_bd90).value if k=='lich_progress' else C.c_int32(self.m.shake_scale_bd94).value if k=='lich_transition' else getattr(p.battle,k)) for k in GAME_KEYS},path={k:(self.state.selection.current_damage if k=='base_attack' else self.state.selection.weapon_damage if k=='direction_bonus' else getattr(p,k)) for k in [*PATH_INTS,'input_ready']},combat=board,events=self.path_events,match=match,tokens=self.token_status(),motion=self.motion_status())
    def commit(self):
        self.path_events=[];self.match_events=[];self.token_events=[];self.motion_events=[]
        s=self.state.selection;indices=list(s.path[:s.path_length]);fake=[i for i,v in enumerate(s.fake) if v]
        path=(U8*len(indices))(*indices);excluded=(U8*len(fake))(*fake)
        self.commit_fn(C.byref(self.path_state),path,len(path),excluded,len(excluded),C.byref(self.path_hooks));return self.path_status()
class Original(MotionOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.path_active=False;self.pending_path_random=None
        symbols={'__ZNSt3setIiSt4lessIiESaIiEE4findERKi':'find','__ZNSt3setIiSt4lessIiESaIiEE6insertERKi':'insert','__ZN4Game16MoveMatchedTilesEv':'move','__ZN4Tile10UpdateTextEbbb':'text','__ZN4Tile13UpdateEnemyUVEv':'uv','__ZN4Tile19SetFreezeVisibilityEb':'freeze','__ZN4Quad5SetUVERK8GLfloat2S2_':'quad','__ZN4Quad7SetSizeERK8GLfloat2':'quad','__ZN4Quad8SetAlphaEh':'quad','__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif':'label'}
        self.path_calls={0x194cec:'unwind',0x194cf4:'unwind',0x194d78:'divide',0x194d6c:'guard_acquire',0x194d70:'guard_release'}
        for symbol,name in symbols.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol;self.path_calls[int(m[1],16)]=name
    def hook(self,u,address,size,context):
        if not getattr(self,'path_active',False):return super().hook(u,address,size,context)
        r=[u.reg_read(v) for v in self.regs];lr=u.reg_read(self.LR)&~1;sp=u.reg_read(self.SP);signed=lambda x:C.c_int32(x).value
        if self.pending_path_random and address==self.pending_path_random[0]:
            _,tile,lo,hi,stream=self.pending_path_random;self.path_events.append([tile,0,lo,hi,stream,signed(r[0])]);self.pending_path_random=None
        if address==0xd788:self.current_battle=self.index(r[1])
        if address==0x1bca0 and 0xd788<=lr<0xdc00:
            self.pending_path_random=(lr,self.current_battle,*map(signed,r[:3]));return
        from_path=(0x12188<=lr<0x127a8) or (0xd788<=lr<0xdc00) or (0x1a110<=lr<0x1a200)
        name=self.path_calls.get(address)
        if name=='quad' and self.motion_running:return super().hook(u,address,size,context)
        if name:
            if name=='find':
                values=self.int_sets.setdefault(r[0],set());u.reg_write(self.regs[0],r[0]+8 if self.read(r[1]) in values else r[0]+4)
            elif name=='insert':self.int_sets.setdefault(r[1],set()).add(self.read(r[2]))
            elif name=='move':self.path_events.append([-1,12,0,0,0,0])
            elif name=='divide':u.reg_write(self.regs[0],int(signed(r[0])/signed(r[1]))&0xffffffff)
            elif name=='guard_acquire':u.reg_write(self.regs[0],1)
            elif name=='guard_release':u.mem_write(r[0],b'\1')
            elif name=='text':self.path_events.append([self.index(r[0]),3,r[1],r[2],r[3],0])
            elif name=='uv':self.path_events.append([self.index(r[0]),5,0,0,0,0])
            elif name=='freeze':self.path_events.append([self.index(r[0]),9,r[1],0,0,0]);return
            elif name=='label':self.path_events.append([self.current_battle if 0xd788<=lr<0xdc00 else -1,8,r[1],signed(r[3]),signed(self.read(sp)),signed(self.read(sp+4))])
            u.reg_write(self.PC,u.reg_read(self.LR));return
        match_name=self.match_calls.get(address)
        if from_path and (match_name or address==0xbe60):
            if address==0xbe60:
                self.path_events.append([self.index(r[1]),4,r[2],0,0,0]);return super().hook(u,address,size,context)
            if match_name=='token':self.path_events.append([self.index(r[1]),1,r[2],r[3],0,0]);return
            if match_name=='particles':self.path_events.append([self.index(r[1]),2,r[2],0,0,0])
            elif match_name=='sound':self.path_events.append([self.current_battle,7,r[1],0,0,0])
            elif match_name=='achievement':self.path_events.append([-1,10,r[1],signed(r[2]),0,0])
            elif match_name=='flare':self.path_events.append([self.current_battle,6,r[1],signed(self.read(self.read(sp))),0,0])
            else:return super().hook(u,address,size,context)
            u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def load(self,c):
        super().load(c);self.int_sets={};self.path_active=False;self.current_battle=-1;self.pending_path_random=None
        for k,a in GAME_INTS.items():self.write(self.GAME+a,c['battle'][k])
        for k,a in GAME_BYTES.items():self.u.mem_write(self.GAME+a,bytes([c['battle'][k]]))
        for k,a in PATH_INTS.items():self.write(self.GAME+a,c['path_state'][k])
        self.u.mem_write(self.GAME+0x5e14,bytes([c['path_state']['input_ready']]))
        for i,t in enumerate(c['combat']):
            base=self.tile(i)
            for k,a in COMBAT_INTS.items():self.write(base+a,t[k])
            for k,a in COMBAT_BYTES.items():self.u.mem_write(base+a,bytes([t[k]]))
            for a,v in zip([0x238,0x23c,0x240],t['poison'][:3]):self.write(base+a,v)
            self.u.mem_write(base+0x244,bytes(t['poison'][3:5]));self.write(base+0x248,t['poison'][5])
        for i in range(100,2000):self.write(0x1600098+160*i,-1)
    def path_status(self):
        signed=lambda a:C.c_int32(self.read(a)).value;board=[]
        for i in range(36):
            base=self.tile(i);board.append(dict(**{k:signed(base+a) for k,a in COMBAT_INTS.items()},**{k:self.u.mem_read(base+a,1)[0] for k,a in COMBAT_BYTES.items()},poison=[signed(base+a) for a in [0x238,0x23c,0x240]]+list(self.u.mem_read(base+0x244,2))+[self.read(base+0x248)],enemy_state=self.read(base+0x250),frozen=self.u.mem_read(base+0x255,1)[0]))
        match=self.match_status();match['counts']=match['counts'][:5] # +0xbfbb is a battle flag, not counter 5.
        return dict(battle=dict(**{k:signed(self.GAME+a) for k,a in GAME_INTS.items()},**{k:self.u.mem_read(self.GAME+a,1)[0] for k,a in GAME_BYTES.items()}),path=dict(**{k:signed(self.GAME+a) for k,a in PATH_INTS.items()},input_ready=self.u.mem_read(self.GAME+0x5e14,1)[0]),combat=board,events=self.path_events,match=match,tokens=self.token_status(),motion=self.motion_status())
    def commit(self):
        self.path_events=[];self.match_events=[];self.token_events=[];self.motion_events=[];self.path_active=True;self.int_sets={}
        u=self.u;u.reg_write(self.regs[0],self.GAME);u.reg_write(self.SP,0x140fff0);u.reg_write(self.LR,self.STOP|1)
        try:
            u.emu_start(0x12189,self.STOP,timeout=3000000,count=3000000)
            assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC));return self.path_status()
        finally:self.path_active=False

def main():
    old=Original();new=Native();count=steps=0
    def compare(c,a,b):
        if a!=b:
            (HERE/'path_failure.json').write_text(json.dumps(dict(case=c,original=a,native=b),indent=2));raise AssertionError(f'{count=}: see path_failure.json')
    for source in round_cases():
        c=convert(source);old.load(c);new.load(c);compare(c,old.commit(),new.commit());count+=1
    from verify_round import base_case
    for enemy in [3,10,14,30,32]:
      for race in [0,9]:
       for spawn in [0,1]:
        source=base_case();source['path']=[0,1,2];source['game'].update(race=race,base_attack=99)
        source['board'][1].update(type=1,enemy=enemy,health=1,defence=0)
        c=convert(source);c['match'].update(spawn_enabled_14ae0=spawn,spawn_remaining_15558=0)
        c['mutate_special']=True;c['shapeshift_race']=0
        c['board'][7]['type']=0;c['preview']['potions'][7]=[0,0,1]
        old.load(c);new.load(c);compare(c,old.commit(),new.commit());count+=1
    from verify_rune import rectangles
    from verify_round import base_case
    gestures=arrivals=0
    for path in list(rectangles())[::5]:
        c=convert(base_case());c['path']=[];c['fake']=[];c['resources']['gold']=0;c['preview'].update(xp_bonus=0,upgrade_bonus=0,gold_bonus=0)
        old.load(c);new.load(c)
        if hasattr(new,'batch_pending'):del new.batch_pending
        for index in path:compare(c,old.step(1,c['board'][index]['center']),new.step(1,c['board'][index]['center']));steps+=1
        compare(c,old.step(2,[.5,.5]),new.step(2,[.5,.5]));steps+=1;compare(c,old.commit(),new.commit())
        for frame in range(240):
            before=sum(t.active for t in new.motions.values());a=old.batch(1/60,[0,0,0]);compare(c,a,new.batch(1/60,[0,0,0]));steps+=1
            arrivals+=before-sum(t.active for t in new.motions.values())
            if not a['pending']:break
        else:raise AssertionError('reward queue not drained')
        compare(c,old.batch(1/60,[0,0,0]),new.batch(1/60,[0,0,0]));steps+=1;gestures+=1
    attack_gestures=0
    for enemy in [0,9,32]:
      for race in [0,5]:
        source=base_case();source['path']=[];source['game']['race']=race
        for i in [0,1,2]:source['board'][i].update(type=1,enemy=enemy,health=5,defence=0,frozen=0)
        c=convert(source);c['preview'].update(xp_bonus=0,upgrade_bonus=0,gold_bonus=0)
        old.load(c);new.load(c)
        if hasattr(new,'batch_pending'):del new.batch_pending
        for index in [0,1,2]:compare(c,old.step(1,c['board'][index]['center']),new.step(1,c['board'][index]['center']));steps+=1
        compare(c,old.step(2,[.5,.5]),new.step(2,[.5,.5]));steps+=1;compare(c,old.commit(),new.commit())
        for frame in range(240):
            before=sum(t.active for t in new.motions.values());a=old.batch(1/60,[0,0,0]);compare(c,a,new.batch(1/60,[0,0,0]));steps+=1
            arrivals+=before-sum(t.active for t in new.motions.values())
            if not a['pending']:break
        else:raise AssertionError('combat reward queue not drained')
        compare(c,old.batch(1/60,[0,0,0]),new.batch(1/60,[0,0,0]));steps+=1;attack_gestures+=1
    report=dict(status='passed',path_scenarios=count,integrated_gestures=gestures+attack_gestures,attack_gestures=attack_gestures,integrated_steps=steps,completed_rewards=arrivals,original='Actual MatchTiles/AttackSkull/MatchTile/AddToken/Token init/process/AddResource/RNG; real input and rune in gesture tests',boundaries=['MoveMatchedTiles','SetSpecialType','Shapeshift','special-token target chooser','UI/audio/rendering','Healing/CheckEndGame','old collections/platform runtime'],scope='Shared-state path and reward integration; no falling/refill/enemy phase or complete game turn.',note='Adapter adds no recovered original-function count; synthetic direct paths include nonadjacent branch-isolation inputs.')
    (HERE/'path_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));new.tokens_lib.dr_token_queue_destroy(new.q);new.q=None
if __name__=='__main__':main()
