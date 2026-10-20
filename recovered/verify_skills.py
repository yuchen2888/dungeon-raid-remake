#!/usr/bin/env python3
"""Actual Skill::Activate 0x2ad40, Skill::CanActivate(int) 0x2ac74 and Game::RemoveSkill 0x9114 vs native
dr_skill_activate / dr_skill_can_activate / dr_remove_skill (recovered_skills), on the shared state of
verify_attack_all.py (T040-H1).

The original functions run from their entry to their return with R0 = a Skill object (Skill+0x7c Game,
+0x80 active, +0x84 type, +0x88 level; the equipped ones at Game+0xbf90, skill_count Game+0xbfa0; an
unequipped skill object for slot -1). GetTileCount, GetSpecialEnemyCount, GetNormalPotionCount (with
Tile::IsNormalPotion), GetNormalSwordCount and RemoveSkill run as original code. Recorded and skipped:
QueueSound, QueueAchievement, Arrow::SetColour, Interface::PositionSkill and the Game skill functions
(FreezeSkulls ... CreateChain, still boundaries: SkillHooks.action). Compared: events, actions, every flag
Activate writes, the equipped skills (order, type, level, active, cooldowns) and skill_count, and the
CanActivate result for every type 0..40.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_input_gate import Original as GateOriginal, Native as GateNative
from verify_attack_all import scenario
from verify_turn_begin import SkillSlots, TurnFlags
from verify_turn_finish import TurnFinishFlags
from verify_game_over import EndGameState
from verify_attack_phase4 import AnimState
from verify_stroke import HERE, I32, U8

ACTIVATE,ACTIVATE_END,CAN,REMOVE,REMOVE_END=0x2ad40,0x2b0f0,0x2ac74,0x9114,0x918c
SKILLS,SPARE=0x1700000,0x1700400
ACTIONS=['FreezeSkulls','GrabTiles','ShatterDefence','ConvertTiles','Teleport','CreateExplosivePotions','Upgrade','CollectRandomRow',
         'DemoteSpecialEnemy','KillSpecialEnemy','PromoteNormalEnemy','CreateMagicSword','Earthquake','ExplodeArmour','CollectRandomBlock',
         'CreateManaPotions','ConvertColumnToSwords','CreateArrows','KillSkullsNextToCoins','CollectEdgeTiles','CreateChain','CollectBoard']
# Game byte offsets Activate writes or reads (name -> offset)
FLAGS=dict(coin=0xbfbb,next_coin=0xbfbc,counter=0xbfba,double_damage=0xbe74,double_upgrade=0xbe75,double_healing=0xbe76,double_gold=0xbe77,
           next_damage=0xbe78,next_upgrade=0xbe79,next_healing=0xbe7a,next_gold=0xbe7b,one_health=0x14af5,force_coins=0x14af6,
           next_one_health=0x14af7,next_force_coins=0x14af8,flag_1554c=0x1554c,prev_164a7=0x164a7,next_164a8=0x164a8,
           rune=0x16491,arrow_hold=0x16492,guard_164a4=0x164a4,revive_second=0x164a5)

class SkillState(C.Structure):_fields_=[(k,C.c_void_p) for k in ('slots','resources','path','generation','flags','finish','rune','animation','end')]
class SkillEvent(C.Structure):_fields_=[('kind',I32),('a',I32),('b',I32),('c',I32)]
EVENT=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(SkillEvent))
ACTION=C.CFUNCTYPE(None,C.c_void_p,I32,I32,I32)
class SkillHooks(C.Structure):_fields_=[('context',C.c_void_p),('event',EVENT),('action',ACTION)]

def address(text,symbol):
    m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol;return int(m[1],16)

class Original(GateOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text();self.skill_calls={};self.skilling=False
        for symbol,name in {'__ZN4Game10QueueSoundE5Sound':'sound','__ZN4Game16QueueAchievementE11Achievementf':'achievement',
                            '__ZN5Arrow9SetColourEjjj':'arrow','__ZN9Interface13PositionSkillEi':'position'}.items():
            self.skill_calls[address(text,symbol)]=name
        for name in ACTIONS:
            symbol=next(m[0] for m in re.finditer(r'^__ZN4Game'+str(len(name))+name+r'E\S*(?=:)',text,re.M))
            self.skill_calls[address(text,symbol)]=name
        assert address(text,'__ZN5Skill8ActivateEv')==ACTIVATE and address(text,'__ZN4Game11RemoveSkillEP5Skill')==REMOVE
        assert address(text,'__ZN5Skill11CanActivateEi')==CAN
    def hook(self,u,address,size,context):
        if self.skilling:
            name=self.skill_calls.get(address);lr=u.reg_read(self.LR)&~1
            if name and (ACTIVATE<lr<ACTIVATE_END or REMOVE<lr<REMOVE_END):
                r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value
                if name=='sound':e=['sound',s(r[1])]
                elif name=='achievement':e=['achievement',s(r[1]),s(r[2])]
                elif name=='arrow':assert r[0]==self.GAME+0x3658;e=['arrow',s(r[1]),s(r[2]),s(r[3])]
                elif name=='position':assert r[0]==self.GAME+0x4cdc;e=['position',s(r[1])]
                else:
                    assert r[0]==self.GAME
                    e=['action',name,s(r[1]),s(r[2])] if name in ('GrabTiles','ConvertTiles') else ['action',name,0,0]
                self.skill_events.append(e);u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def load(self,c):
        super().load(c);k=c['skills']
        for i in range(4):
            base=SKILLS+0x100*i;self.write(base+0x7c,self.GAME);self.u.mem_write(base+0x80,bytes([k['active'][i]]))
            self.write(base+0x84,k['type'][i]);self.write(base+0x88,k['level'][i])
        self.write(SPARE+0x7c,self.GAME);self.u.mem_write(SPARE+0x80,b'\0')
        for name,o in FLAGS.items():self.u.mem_write(self.GAME+o,bytes([c['flags'][name]]))
    def call(self,entry,args):
        u=self.u;self.skill_events=[];self.skilling=True
        for reg,v in zip(self.regs,args):u.reg_write(reg,v&0xffffffff)
        u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1)
        try:u.emu_start(entry|1,self.STOP,timeout=0,count=500000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.skilling=False
        return u.reg_read(self.regs[0])
    def can(self,type_):return bool(self.call(CAN,[SKILLS,type_])&0xff)
    def activate(self,type_,slot):
        obj=SKILLS+0x100*slot if slot>=0 else SPARE
        if slot<0:self.write(SPARE+0x84,type_)
        else:assert self.read(obj+0x84)==type_
        self.call(ACTIVATE,[obj]);return self.status(obj)
    def remove(self,slot):self.call(REMOVE,[self.GAME,SKILLS+0x100*slot if slot>=0 else SPARE]);return self.status(None)
    def status(self,obj):
        G=self.GAME;count=C.c_int32(self.read(G+0xbfa0)).value;slots=[]
        for i in range(4):
            p=self.read(G+0xbf90+4*i)
            slots.append([(p-SKILLS)//0x100 if SKILLS<=p<SKILLS+0x400 else -1,C.c_int32(self.read(p+0x84)).value,C.c_int32(self.read(p+0x88)).value,
                          self.u.mem_read(p+0x80,1)[0],C.c_int32(self.read(p+0x8c)).value,C.c_int32(self.read(p+0x90)).value])
        return dict(events=self.skill_events,flags={k:self.u.mem_read(G+o,1)[0] for k,o in FLAGS.items()},count=count,slots=slots,
                    spare_active=self.u.mem_read(SPARE+0x80,1)[0])

class Native(GateNative):
    def __init__(self):
        super().__init__();lib=self.skills_lib=C.CDLL(str(HERE/'recovered_skills_native.dylib'))
        lib.dr_skill_can_activate.argtypes=[C.POINTER(SkillState),I32];lib.dr_skill_can_activate.restype=C.c_bool
        lib.dr_skill_activate.argtypes=[C.POINTER(SkillState),I32,I32,C.POINTER(U8),C.POINTER(SkillHooks)];lib.dr_skill_activate.restype=None
        lib.dr_remove_skill.argtypes=[C.POINTER(SkillState),I32,C.POINTER(SkillHooks)];lib.dr_remove_skill.restype=None
        def event(_,p):
            e=p.contents
            self.skill_events.append(['sound',e.a] if e.kind==1 else ['achievement',e.a,e.b] if e.kind==2 else ['arrow',e.a,e.b,e.c] if e.kind==3 else ['position',e.a])
        def action(_,kind,a,b):self.skill_events.append(['action',ACTIONS[kind-1],a,b])
        self.skill_cb=(EVENT(event),ACTION(action));self.skill_hooks=SkillHooks(None,*self.skill_cb)
    def load(self,c):
        super().load(c);k=c['skills'];f=c['flags']
        # each slot's object: an equipped skill keeps its type / level / active / cooldowns when slots move
        self.slots=SkillSlots((I32*4)(*k['type']),(I32*4)(*k['level']),(U8*4)(*k['active']));self.slot_ids=list(range(4))
        self.flags=TurnFlags();self.finish=TurnFinishFlags();self.end=EndGameState();self.anim=AnimState();self.spare=U8(0)
        self.state_obj=SkillState(*[C.addressof(x) for x in (self.slots,self.r,self.path_state,self.gen,self.flags,self.finish,self.rune,self.anim,self.end)])
        for name,v in f.items():self.set_flag(name,v)
    def refs(self):
        s,p,f,fin=self.state.selection,self.p,self.flags,self.finish
        return dict(coin=(self.path_state.battle,'coin_on_attack'),next_coin=(f,'next_coin_bfbc'),counter=(self.anim,'counterattack'),
                    double_damage=(s,'double_damage'),double_upgrade=(p,'double_upgrade'),double_healing=(p,'double_healing'),double_gold=(p,'double_gold'),
                    next_damage=(f.next_be78,0),next_upgrade=(f.next_be78,1),next_healing=(f.next_be78,2),next_gold=(f.next_be78,3),
                    one_health=(self.gen,'one_health'),force_coins=(self.gen,'force_coins'),next_one_health=(fin,'next_one_health_14af7'),
                    next_force_coins=(fin,'next_force_coins_14af8'),flag_1554c=(fin,'flag_1554c'),prev_164a7=(f,'prev_164a7'),next_164a8=(f,'next_164a8'),
                    rune=(self.rune,'enabled'),arrow_hold=(f,'arrow_hold_16492'),guard_164a4=(self.r,'guard_164a4'),revive_second=(self.end,'revive_second'))
    def set_flag(self,name,v):
        o,a=self.refs()[name]
        if isinstance(a,int):o[a]=v
        else:setattr(o,a,v)
    def get_flag(self,name):
        o,a=self.refs()[name];return o[a] if isinstance(a,int) else getattr(o,a)
    def can(self,type_):return bool(self.skills_lib.dr_skill_can_activate(C.byref(self.state_obj),type_))
    def activate(self,type_,slot):
        self.skill_events=[];active=C.pointer(self.spare) if slot<0 else C.cast(C.addressof(self.slots)+SkillSlots.active.offset+slot,C.POINTER(U8))
        if slot>=0:assert self.slots.id[slot]==type_
        self.skills_lib.dr_skill_activate(C.byref(self.state_obj),type_,slot,active,C.byref(self.skill_hooks));return self.status()
    def remove(self,slot):
        self.skill_events=[];self.skills_lib.dr_remove_skill(C.byref(self.state_obj),slot,C.byref(self.skill_hooks));return self.status()
    def status(self):
        # the original's pointer order is the order of the moved slots: follow the objects through dr_remove_skill
        k,r=self.slots,self.r;slots=[[None,k.id[i],k.level[i],k.active[i],r.skill_max[i],r.skill_current[i]] for i in range(4)]
        return dict(events=self.skill_events,flags={n:self.get_flag(n) for n in FLAGS},count=r.skill_count,slots=slots,spare_active=self.spare.value)

def case(rng):
    c,_=scenario(rng)
    for i,t in enumerate(c['board']):
        t['type']=rng.choice([0,1,1,2,3,4,4,5,6]) if rng.random()<.8 else rng.choice([0,1,2,4])
        if t['type']==1:t['enemy']=rng.choice([0,0,0,2,9,20,rng.randrange(33)])
        t['magic_sword']=int(rng.random()<.2);t['flag231']=int(rng.random()<.2)
        c['preview']['potions'][i]=[int(rng.random()<.25) for _ in range(3)]
    if rng.random()<.2:   # boards without some tile kinds, so that CanActivate is false
        gone=rng.sample([0,1,2,3,4],rng.randrange(1,4))
        for t in c['board']:
            if t['type'] in gone:t['type']=5;t['enemy']=0
    if rng.random()<.15:   # 19 or 20 plain skulls (CollectBoard's achievement threshold) next to a few special enemies
        cells=rng.sample(range(36),rng.choice([19,20])+rng.randrange(3))
        for k,i in enumerate(cells):c['board'][i].update(type=1,enemy=0 if k>=len(cells)-rng.choice([19,20]) else 9)
    c['preview']['armour_current']=rng.choice([0,0,3,rng.randrange(1,40)])
    count=rng.choice([0,1,2,3,4,4])
    c['resources'].update(skill_count=count,skill_max=[rng.randrange(1,9) for _ in range(4)],skill_current=[rng.randrange(0,9) for _ in range(4)])
    c['skills']=dict(type=[rng.randrange(0,42) for _ in range(4)],level=[rng.randrange(0,4) for _ in range(4)],active=[rng.randrange(2) for _ in range(4)])
    c['flags']={k:rng.randrange(2) for k in FLAGS}
    c['moving_list']=[];c['gate']=dict(tokens_pending=0,flare_count=0,phase=0,touch_phase=0,input_target=-1,rune=0)
    return c

def main():
    old,new=Original(),Native();rng=random.Random(0x2ad40);counts={'can':0,'activate':0,'remove':0};types={};removed=0
    def compare(c,what,a,b):
        if a!=b:
            (HERE/'skills_failure.json').write_text(json.dumps(dict(case=c,what=what,original=a,native=b),indent=2))
            raise AssertionError(f'skills_failure.json ({what})')
        counts[what.split()[0]]+=1
    def order(status):   # slot objects as the original orders them; native slots carry no object id
        return [s[1:] for s in status['slots']]
    for n in range(1200):
        c=case(rng);old.load(c);new.load(c)
        for t in range(41):
            a,b=old.can(t),new.can(t);compare(c,f'can {t}',a,b);types.setdefault(t,set()).add(a)
        count=c['resources']['skill_count']
        if n%4==0:   # Game::RemoveSkill directly
            slot=rng.choice([-1,0,1,2,3]);a,b=old.remove(slot),new.remove(slot)
            a=dict(a,slots=order(a));b=dict(b,slots=order(b));compare(c,f'remove {slot}',a,b);removed+=a['count']<count
            continue
        if count and rng.random()<.7:slot=rng.randrange(count);type_=c['skills']['type'][slot]
        else:
            slot=-1;type_=rng.choice([33,33,rng.randrange(0,42)])
        if rng.random()<.25 and slot>=0:   # make the slot's skill the one-shot CollectBoard
            type_=33;c['skills']['type'][slot]=33;old.write(SKILLS+0x100*slot+0x84,33);new.slots.id[slot]=33
        a,b=old.activate(type_,slot),new.activate(type_,slot)
        a=dict(a,slots=order(a));b=dict(b,slots=order(b));compare(c,f'activate {type_}',a,b)
    assert all(v=={False,True} for t,v in types.items() if t in (0,1,2,3,4,5,6,8,9,12,13,14,15,20,21,23,25,27,29,31,32,34,36)),types
    assert removed>50,removed
    report=dict(status='passed',comparisons=counts,skills_removed=removed,
                functions=[dict(symbol='__ZN5Skill8ActivateEv',address=hex(ACTIVATE),native='dr_skill_activate'),
                           dict(symbol='__ZN5Skill11CanActivateEi',address=hex(CAN),native='dr_skill_can_activate'),
                           dict(symbol='__ZN4Game11RemoveSkillEP5Skill',address=hex(REMOVE),native='dr_remove_skill')],
                original='Actual functions; GetTileCount / GetSpecialEnemyCount / GetNormalPotionCount / GetNormalSwordCount / RemoveSkill as original code',
                boundaries=['QueueSound, QueueAchievement, Arrow::SetColour, Interface::PositionSkill and the Game skill functions recorded'])
    (HERE/'skills_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
