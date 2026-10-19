#!/usr/bin/env python3
"""Actual ProcessAttack damage-all (Game+0xbe68) vs native, on the full shared state.

Original side runs [0x14938,0x14a14) plus blocks [0x14b5e,0x14b9c) and
[0x14bbe,0x14be0) until 0x14ae4. Its Game::AttackSkull calls execute the
original function (with MatchTile, tokens, rewards as in verify_path) and its
Game::MoveMatchedTiles call executes the original refill (with RandomiseTile,
generation, Stab/JumpDown as in verify_encounters). The harness only switches
which existing subsystem hooks are active while each callee runs.
Native side: dr_process_attack_damage_all whose callbacks call the recovered
dr_path_attack_skull adapter and dr_move_matched_tiles on the same state.
Only QueueSound/AddSimpleLabel/QueueAchievement issued by ProcessAttack itself
are recorded here; callee presentation goes through the existing hooks.
"""
import ctypes as C
import hashlib
import json
import random
import re
from verify_refill_integration import Original as IntegrationOriginal, Native as IntegrationNative
from verify_encounters import configure
from verify_path import Path, Hooks as PathHooks
from verify_stroke import HERE, I32, U8

START,STOP_AT=0x14938,0x14ae4
RANGES=[(0x14938,0x14a14),(0x14b5e,0x14b9c),(0x14bbe,0x14be0)]
AMOUNT=0xbe68
ATTACK_SKULL,MOVE=0xd788,0x10ed8

def in_all(address):return any(a<=address<b for a,b in RANGES)

class Event(C.Structure):
    _fields_=[(k,I32) for k in ('kind','tile','a','b','c','d')]
EVENT=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(Event))
ATTACK=C.CFUNCTYPE(C.c_bool,C.c_void_p,I32,I32,C.c_bool)
MOVE_FN=C.CFUNCTYPE(None,C.c_void_p)
class AllHooks(C.Structure):
    _fields_=[('context',C.c_void_p),('event',EVENT),('attack_skull',ATTACK),('move_matched_tiles',MOVE_FN)]

class Original(IntegrationOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.pa_calls={};self.all_running=False;self.mode=None;self.all_visits={}
        for symbol,name in [('__ZN4Game10QueueSoundE5Sound','sound'),('__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif','label'),
                            ('__ZN4Game16QueueAchievementE11Achievementf','achievement')]:
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol
            self.pa_calls[int(m[1],16)]=name
    def hook(self,u,address,size,context):
        if self.all_running:
            if in_all(address):self.all_visits[hex(address)]=self.all_visits.get(hex(address),0)+1
            if self.mode is None:
                if address==STOP_AT:u.emu_stop();return
                lr=u.reg_read(self.LR)&~1;r=[u.reg_read(v) for v in self.regs];signed=lambda v:C.c_int32(v).value
                name=self.pa_calls.get(address)
                if name and in_all(lr):
                    sp=u.reg_read(self.SP)
                    if name=='sound':e=['A',1,-1,r[1],0,0,0]
                    elif name=='label':e=['A',2,self.index(r[2]-0x54),r[1],signed(r[3]),signed(self.read(sp)),signed(self.read(sp+4))]
                    else:e=['A',3,-1,r[1],signed(r[2]),0,0]
                    self.all_events.append(e);u.reg_write(self.PC,u.reg_read(self.LR));return
                if address==ATTACK_SKULL and in_all(lr):
                    self.mode=('attack',lr,self.index(r[1]),signed(r[2]),r[3]&0xff);self.path_active=True
                elif address==MOVE and in_all(lr):
                    self.mode=('move',lr);self.refill_active=self.gen_active=self.enc_active=True
            elif address==self.mode[1]:
                if self.mode[0]=='attack':
                    _,_,tile,amount,effects=self.mode;self.all_events.append(['A',9,tile,amount,effects,u.reg_read(self.regs[0])&0xff,0]);self.path_active=False
                else:self.refill_active=self.gen_active=self.enc_active=False
                self.mode=None
        return super().hook(u,address,size,context)
    def damage_all(self,amount):
        self.all_events=[];self.enc_events=[];self.gen_events=[];self.refill_events=[];self.path_events=[]
        self.match_events=[];self.token_events=[];self.motion_events=[];self.int_sets={};self.mode=None
        self.write(self.GAME+AMOUNT,amount);u=self.u
        u.reg_write(self.regs[0],0);u.reg_write(self.SP,0x140ff00);u.reg_write(self.LR,self.STOP|1)
        from unicorn.arm_const import UC_ARM_REG_R8
        u.reg_write(UC_ARM_REG_R8,self.GAME);self.all_running=True
        try:
            u.emu_start(START|1,self.STOP,timeout=5000000,count=5000000)
            assert u.reg_read(self.PC)==STOP_AT and self.mode is None,hex(u.reg_read(self.PC))
        finally:self.all_running=False;self.path_active=self.refill_active=self.gen_active=self.enc_active=False
        return dict(path=self.path_status(),enc=self.enc_status(),all=self.all_events[:])

class Native(IntegrationNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_attack_shield_native.dylib'))
        self.all_fn=lib.dr_process_attack_damage_all;self.all_fn.argtypes=[C.POINTER(Path),I32,C.POINTER(AllHooks)];self.all_fn.restype=None
        self.single=self.path_lib.dr_path_attack_skull
        self.single.argtypes=[C.POINTER(Path),C.c_uint32,I32,C.c_bool,C.POINTER(PathHooks)];self.single.restype=C.c_bool
        def event(_,p):
            e=p.contents;self.all_events.append(['A',e.kind,e.tile,e.a,e.b,e.c,e.d])
        def attack(_,tile,amount,effects):
            result=bool(self.single(C.byref(self.path_state),tile,amount,effects,C.byref(self.path_hooks)))
            self.all_events.append(['A',9,tile,amount,int(effects),int(result),0]);return result
        def move(_):self.refill_lib.dr_move_matched_tiles(C.byref(self.refill),C.byref(self.refill_hooks))
        self.cb=(EVENT(event),ATTACK(attack),MOVE_FN(move));self.all_hooks=AllHooks(None,*self.cb)
    def damage_all(self,amount):
        self.all_events=[];self.enc_events=[];self.gen_events=[];self.refill_events=[];self.path_events=[]
        self.match_events=[];self.token_events=[];self.motion_events=[]
        self.all_fn(C.byref(self.path_state),amount,C.byref(self.all_hooks))
        return dict(path=self.path_status(),enc=self.enc_status(),all=self.all_events[:])

def scenario(rng,amount_choices=(1,2,3,5,10,40)):
    c=configure();c['resources'].update(health=500,ui_health=500);c['match']['seeds']=[rng.getrandbits(32) for _ in range(6)]
    c['game']['race']=rng.randrange(10);c['generation']['time_to_promotion']=rng.randrange(3)
    for i,t in enumerate(c['board']):
        enemy=rng.random()<.5
        t.update(type=1 if enemy else rng.choice([0,2,3,4]),enemy=rng.choice([0,2,2,9,20,31,rng.randrange(33)]) if enemy else 0,matched=0)
        k=c['combat'][i];k.update(attack=rng.randrange(1,20),defence=rng.choice([0,0,rng.randrange(1,8)]),health=rng.randrange(1,25),
                                  attack_flag=int(rng.random()<.2))
    for f in c['falling']:f.update(moving=0,speed=1)
    return c,rng.choice(amount_choices)

def main():
    old,new=Original(),Native();rng=random.Random(0x14938);counts={'boundary':0,'random':0,'repeated':0,'falling_frames':0};kills=attacks=0
    def compare(c,amount,group):
        nonlocal kills,attacks
        a,b=old.damage_all(amount),new.damage_all(amount)
        if a!=b:
            (HERE/'attack_all_failure.json').write_text(json.dumps(dict(case=c,amount=amount,original=a,native=b),indent=2))
            raise AssertionError('attack_all_failure.json')
        counts[group]+=1;hits=[e for e in a['all'] if e[1]==9];attacks+=len(hits);kills+=sum(e[5] for e in hits)
        return a
    for amount in (-1,0,1,3,100):
        for n in range(8):
            c,_=scenario(rng);old.load(c);new.load(c);compare(c,amount,'boundary')
    for _ in range(120):
        c,amount=scenario(rng);old.load(c);new.load(c);compare(c,amount,'random')
    # Repeated attacks on carried state; as in play, refilled tiles finish falling
    # (original Game::Process falling-list subsection vs native) before the next one.
    for game in range(6):
        c,amount=scenario(rng,(2,4,6));old.load(c);new.load(c)
        for step in range(4):
            compare(dict(game=game,step=step),amount,'repeated')
            for frame in range(240):
                a,b=old.falling_frame(1/60),new.falling_frame(1/60);counts['falling_frames']+=1
                if a!=b:
                    (HERE/'attack_all_failure.json').write_text(json.dumps(dict(case=dict(game=game,step=step,frame=frame),original=a,native=b),indent=2))
                    raise AssertionError('attack_all_failure.json')
                if not new.moving_list:break
            else:raise AssertionError('did not settle')
    assert kills and attacks and all(hex(a) in old.all_visits for a in (0x14946,0x14980,0x14988,0x149e8,0x14a0a,0x14b66,0x14b9a))
    report=dict(status='passed',comparisons=sum(counts.values()),by_group=counts,attack_skull_calls=attacks,kills=kills,
                ranges=[[hex(a),hex(b)] for a,b in RANGES],
                original='Actual ProcessAttack damage-all with original AttackSkull (+MatchTile/tokens) and MoveMatchedTiles (+RandomiseTile/generation/Stab/JumpDown)',
                boundaries=['ProcessAttack sound/label/achievement adapted','callee presentation adapted by existing path/refill/generation/encounter hooks',
                            'damage amount written to Game+0xbe68 by the harness (producer not recovered)','no phase scheduler'],
                scope='Full shared board, combat, match counts, tokens, refill, generation and RNG state',
                byte_sha256=hashlib.sha256(b''.join(old.old.bytes_at(a,b-a) for a,b in RANGES)).hexdigest(),
                branch_visits=old.all_visits)
    (HERE/'attack_all_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='branch_visits'}))

if __name__=='__main__':main()
