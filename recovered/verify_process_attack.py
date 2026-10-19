#!/usr/bin/env python3
"""Whole original Game::ProcessAttack 0x14118 vs native dr_process_attack, frame by frame.

Each frame calls the original function from its entry with LR=STOP and the
native orchestrator, on the full shared state of verify_attack_all.py. All
gameplay callees run as original code: InitialiseFlares, Tile::GetAttack,
Rand/RandI and floorf (existing harness), Interpolate/Sqr, Quad::SetAlpha,
DoCounterattack, AttackSkull (+MatchTile/tokens), MoveMatchedTiles (+generation,
Stab, JumpDown), GetEnemyCount, ProcessVampires, Tile::AddHealth. Presentation
calls are recorded in one canonical form on both sides. Two harness models:
the platform powf stub is answered by the host C powf (native uses the same),
and Game::AddFlare is modelled as "append one flare and increment Game+0xbd8c"
on both sides (the flare list lives at a fixed emulator address).
A game runs whole attacks from phase 1 to phase 8, letting refilled tiles
settle between attacks, with the board, RNG and resources carried throughout.
"""
import ctypes as C
import ctypes.util
import json
import random
import re
import struct
from verify_attack_all import Original as AllOriginal, Native as AllNative, scenario, ATTACK, MOVE_FN, EVENT as ALL_EVENT, AllHooks
from verify_attack_absorb import AttackDamage
from verify_attack_phase4 import AnimState, MOTION
from verify_encounters import Hooks as EncHooks, EVENT as ENC_EVENT
from verify_generation import Generation
from verify_path import Path
from verify_stroke import HERE, I32, U8

ENTRY,FUNCTION_END=0x14118,0x14c04
GAMES=24
RECORD=[(0x14118,0x14c04),(0xd9b0,0xdaf4),(0xdaf8,0xdc30),(0x3dc6c,0x3dc98),(0x11214,0x1133c)]
PHASE,DT,DAMAGE,ENEMY9,POISON,HEALTH,UI_HEALTH=0xb8a8,0x4,0xbe84,0x1553c,0x15540,0xbd98,0x5994
CHANCE,WEAKEN,ALL_AMOUNT=0xbdc8,0xbe6c,0xbe68
PROGRESS,LABEL_Y,DAMAGE_ALPHA,POISON_ALPHA,COUNT,LIST,COUNTER_FLAG=0xbd58,0xbd54,0xbd38,0x15520,0xbd8c,0xbd80,0xbfba
OVERLAY_ALPHA=0xb92b
QUADS={0xb91c:'overlay',0xb8ac:'q1',0xb98c:'q2'}
LABELS={0xb9fc:0,0x151e4:1}
FLARES,FLARE_STRIDE=0x1518000,0x70
TILES,STRIDE=0x5e58,608
VERTEX_ALPHA=(0xf,0x23,0x37,0x4b)
POWF,RAND_FLOAT=0x194f40,0x1b7a8
LIBM=C.CDLL(ctypes.util.find_library('m'));LIBM.powf.argtypes=[C.c_float,C.c_float];LIBM.powf.restype=C.c_float
def fbits(x):return struct.unpack('<I',struct.pack('<f',x))[0]
def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
def sbits(x):return C.c_int32(fbits(x)).value

SYMBOLS={'__ZN4Game10QueueSoundE5Sound':'sound','__ZN4Quad8SetAlphaEh':'alpha',
 '__ZN9Interface15SetHealthShadowEi':'shadow0','__ZN9Interface11SetXPshadowEi':'shadow1','__ZN9Interface11SetUPshadowEi':'shadow2','__ZN9Interface13SetGoldShadowEi':'shadow3',
 '__ZN4Tile14GetEyePositionEi':'eye','__ZN4Game8AddFlareE9FlareType8GLfloat2RK9GLcolour4':'flare',
 '__ZN11SimpleLabel9SetNumberEi':'label_number','__ZN11SimpleLabel11SetPositionERK8GLfloat2':'label_position','__ZN11SimpleLabel8SetAlphaEh':'label_alpha',
 '__ZN8HelpMenu10InitialiseEffff8HelpType':'help','__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif':'add_label',
 '__ZN9Interface17UpdateShieldValueEv':'shield_value','__ZN4Game21InialiseShieldShatterEv':'shatter','__ZN4Tile10UpdateTextEbbb':'text',
 '__ZN4Tile22GetAttackLabelPositionEv':'attack_label_position','__ZN4Game12AddParticlesEP4Tile12ParticleType':'particles',
 '__ZN4Game16QueueAchievementE11Achievementf':'achievement','__ZN9Interface9SetPoisonEi':'poison_bar','__ZN9Interface14ShowHelpHealthEv':'help_health',
 '__ZN9Interface15UpdateHealthBarER4Quadi':'health_bar','__ZN4Game15ProcessVampiresEv':'vampires','__ZN4Game15DoCounterattackEv':'counterattack'}
RUN_ORIGINAL={'alpha','vampires','counterattack'}

class Original(AllOriginal):
    ranges,entry=[(ENTRY,FUNCTION_END),(0x11214,0x1133c)],ENTRY
    def __init__(self):
        super().__init__();self.stop_at=self.STOP;text=(HERE.parent/'armv7-disassembly.txt').read_text();self.symbols={}
        for symbol,name in SYMBOLS.items():
            m=re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,symbol;self.symbols[int(m[1],16)]=name
        self.visits={}
    def tile_of(self,address,offset=0):
        i,rest=divmod(address-self.GAME-TILES-offset,STRIDE);assert rest==0 and 0<=i<36,hex(address);return i
    def position_tag(self,address):
        o=address-self.GAME
        if o==0xbd30:return 'bd30'
        if o==0x15518:return 'poison'
        if address==getattr(self,'attack_label_out',None):return ['attack_label',self.attack_label_tile]
        if 0xb400<=o<0xb400+8*36 and (o-0xb400)%8==0:return ['rest',(o-0xb400)//8]
        return ['tile',self.tile_of(address,0x54)]
    def hook(self,u,address,size,context):
        if self.all_running:
            if ENTRY<=address<FUNCTION_END:self.visits[hex(address)]=self.visits.get(hex(address),0)+1
            if self.mode is None:
                lr=u.reg_read(self.LR)&~1
                if address==POWF:
                    x,y=struct.unpack('<ff',struct.pack('<II',u.reg_read(self.regs[0]),u.reg_read(self.regs[1])))
                    u.reg_write(self.regs[0],fbits(LIBM.powf(x,y)));u.reg_write(self.PC,u.reg_read(self.LR));return
                if any(a<lr<=b for a,b in RECORD):
                    r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value;sp=u.reg_read(self.SP)
                    if address==RAND_FLOAT:self.all_events.append(['rand_f',s(r[0]),s(r[1]),r[2]]);return super().hook(u,address,size,context)
                    name=self.symbols.get(address)
                    if name:
                        e=None
                        if name=='sound':e=['sound',r[1]]
                        elif name=='alpha':
                            o=r[0]-self.GAME
                            tag=QUADS.get(o) or ['flare',(r[0]-FLARES)//FLARE_STRIDE]
                            e=['alpha',tag,r[1]&0xff]
                        elif name.startswith('shadow'):e=['shadow',int(name[-1]),s(r[1])]
                        elif name=='eye':self.eye=(self.tile_of(r[1]),r[2])
                        elif name=='flare':
                            colour=struct.unpack('<i',u.mem_read(self.read(sp),4))[0];e=['flare',self.eye[0],self.eye[1],r[1],colour]
                            self.write(self.GAME+COUNT,self.read(self.GAME+COUNT)+1)   # AddFlare model: append one flare
                        elif name=='label_number':e=['label_number',LABELS[r[0]-self.GAME],s(r[1])]
                        elif name=='label_position':x,y=struct.unpack('<ii',u.mem_read(r[1],8));e=['label_position',LABELS[r[0]-self.GAME],x,y]
                        elif name=='label_alpha':e=['label_alpha',LABELS[r[0]-self.GAME],r[1]&0xff]
                        elif name=='help':assert r[0]==self.GAME+0x10298 and r[3]==0;e=['help',s(r[1]),s(r[2]),self.read(sp),self.read(sp+4)]
                        elif name=='add_label':e=['add_label',r[1],self.position_tag(r[2]),s(r[3]),s(self.read(sp)),s(self.read(sp+4))]
                        elif name=='shield_value':e=['shield_value',s(self.read(self.GAME+0x59c0))]
                        elif name=='shatter':e=['shatter']
                        elif name=='text':e=['text',self.tile_of(r[0]),r[1]&0xff,r[2]&0xff,r[3]&0xff]
                        elif name=='attack_label_position':self.attack_label_out=r[0];self.attack_label_tile=self.tile_of(r[1])
                        elif name=='particles':e=['particles',self.tile_of(r[1]),r[2]]
                        elif name=='achievement':e=['achievement',r[1],s(r[2])]
                        elif name=='poison_bar':e=['poison_bar',s(r[1])]
                        elif name=='help_health':e=['help_health']
                        elif name=='health_bar':e=['health_bar',s(r[2])]
                        elif name=='vampires':e=['vampires']
                        elif name=='counterattack':e=['counterattack']
                        if e:self.all_events.append(e)
                        if name in RUN_ORIGINAL:return super().hook(u,address,size,context)
                        u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)
    def load(self,c):
        super().load(c);w=lambda o,v:self.write(self.GAME+o,v)
        for o,k in ((PHASE,'phase'),(DAMAGE,'damage'),(ENEMY9,'enemy9'),(COUNT,'count'),(CHANCE,'chance'),(WEAKEN,'weaken'),(ALL_AMOUNT,'damage_all')):w(o,c[k])
        for o,k in ((PROGRESS,'progress'),(LABEL_Y,'label_y'),(DAMAGE_ALPHA,'damage_alpha'),(POISON_ALPHA,'poison_alpha')):w(o,fbits(c[k]))
        for k,o in MOTION.items():w(o,fbits(c[k]))
        w(LIST,FLARES);self.u.mem_write(self.GAME+COUNTER_FLAG,bytes([c['counter']]));self.u.mem_write(FLARES,bytes([0x5a])*(FLARE_STRIDE*80))
        for q in QUADS:
            for v in VERTEX_ALPHA:self.u.mem_write(self.GAME+q+v,bytes([0x5a]))
        self.u.mem_write(self.GAME+OVERLAY_ALPHA,bytes([c['overlay']]))
    def anim_state(self):
        rd=lambda o:self.read(self.GAME+o)&0xffffffff;sg=lambda o:C.c_int32(rd(o)).value
        count=sg(COUNT);flares=[]
        for i in range(min(max(count,0),80)):
            b=FLARES+FLARE_STRIDE*i;flares.append([self.u.mem_read(b+0xf,1)[0],struct.unpack('<I',self.u.mem_read(b+0x64,4))[0]])
        quads={name:self.u.mem_read(self.GAME+q+0xf,1)[0] for q,name in QUADS.items()}
        return dict(phase=sg(PHASE),damage=sg(DAMAGE),enemy9=sg(ENEMY9),poison=sg(POISON),count=count,
                    floats=[rd(o) for o in (PROGRESS,LABEL_Y,DAMAGE_ALPHA,POISON_ALPHA)]+[rd(o) for o in MOTION.values()],
                    flares=flares,quads=quads,counter=self.u.mem_read(self.GAME+COUNTER_FLAG,1)[0])
    def frame(self,dt):
        self.write(self.GAME+DT,fbits(dt));result=self.run_original();result['anim']=self.anim_state();return result
    def set_phase(self,phase):self.write(self.GAME+PHASE,phase)

class AttackFlareEvent(C.Structure):_fields_=[(k,I32) for k in ('kind','tile','a','b','c')]
class AnimEvent(C.Structure):_fields_=[(k,I32) for k in ('kind','a','b','c')]
class Event5(C.Structure):_fields_=[(k,I32) for k in ('kind','a','b','c','d')]
class Event6(C.Structure):_fields_=[(k,I32) for k in ('kind','tile','a','b','c','d')]
class FadeEvent(C.Structure):_fields_=[(k,I32) for k in ('kind','a','b')]
def hooks_type(event_type,extra=()):
    fn=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(event_type))
    return fn,type('Hooks',(C.Structure,),{'_fields_':[('context',C.c_void_p),('event',fn)]+list(extra)})
FLARE_FN,FlareHooks=hooks_type(AttackFlareEvent)
COUNTER_FN=C.CFUNCTYPE(None,C.c_void_p)
ANIM_FN,AnimHooks=hooks_type(AnimEvent,[('counterattack',COUNTER_FN)])
E5_FN,E5Hooks=hooks_type(Event5)
E6_FN,E6Hooks=hooks_type(Event6)
FADE_FN,FadeHooks=hooks_type(FadeEvent)
class Inputs(C.Structure):_fields_=[(k,I32) for k in ('armour_loss_chance','weaken','damage_all')]
class ProcessHooks(C.Structure):
    _fields_=[('flare',C.POINTER(FlareHooks)),('anim',C.POINTER(AnimHooks)),('absorb',C.POINTER(E5Hooks)),('shield',C.POINTER(E5Hooks)),
              ('weaken',C.POINTER(E6Hooks)),('all',C.POINTER(AllHooks)),('health',C.POINTER(E5Hooks)),('fade',C.POINTER(FadeHooks))]

class Native(AllNative):
    def __init__(self):
        super().__init__();lib=C.CDLL(str(HERE/'recovered_attack_shield_native.dylib'))
        self.process=lib.dr_process_attack
        self.process.argtypes=[C.POINTER(AttackDamage),C.POINTER(Path),C.POINTER(AnimState),C.POINTER(C.c_uint8),C.c_float,C.POINTER(Inputs),C.POINTER(ProcessHooks)]
        self.process.restype=None
        self.counter_fn=lib.dr_do_counterattack;self.counter_fn.argtypes=[C.POINTER(Path),C.c_void_p];self.counter_fn.restype=None
        enc=C.CDLL(str(HERE/'recovered_encounters_native.dylib'));self.vampires=enc.dr_process_vampires
        self.vampires.argtypes=[C.POINTER(Generation),C.POINTER(EncHooks)];self.vampires.restype=None
        def ev(x):self.all_events.append(x)
        def flare(_,p):
            e=p.contents
            if e.kind==1:ev(['sound',e.a])
            elif e.kind==2:ev(['flare',e.tile,e.a,e.b,e.c]);self.anim.flare_count+=1   # AddFlare model
            elif e.kind==3:self.quads['overlay']=e.b&0xff;ev(['alpha','overlay',e.b&0xff])
            else:ev(['shadow',e.a,e.b])
        def anim(_,p):
            e=p.contents;k=e.kind
            if k==1:ev(['sound',e.a])
            elif k==2:ev(['label_number',e.a,e.b])
            elif k==3:ev(['label_position',e.a,e.b,e.c])
            elif k==4:self.flare_mirror.setdefault(e.a,[0x5a,0x5a5a5a5a])[0]=e.b;ev(['alpha',['flare',e.a],e.b])
            elif k==5:self.flare_mirror.setdefault(e.a,[0x5a,0x5a5a5a5a])[1]=e.b&0xffffffff
            elif k==6:name={1:'q1',2:'q2'}[e.a];self.quads[name]=e.b;ev(['alpha',name,e.b])
            elif k==7:ev(['label_alpha',e.a,e.b])
            elif k==8:ev(['help',e.a,e.b,0x3dcccccd if e.c==17 else 0,e.c])
            elif k==9:ev(['rand_f',e.a,e.b,e.c])
            elif k==10:ev(['add_label',e.a,'bd30',e.b,e.c,0x3f000000])
        def counter(_):ev(['counterattack']);self.counter_fn(C.byref(self.path_state),C.addressof(self.all_hooks))
        def absorb(_,p):
            e=p.contents
            if e.kind==1:ev(['label_number',0,e.a])
            else:ev(['add_label',e.a,'poison',e.b,e.c,e.d])
        def shield(_,p):
            e=p.contents
            if e.kind==1:self.match_events.append([10,e.c,e.a,e.b,e.d,0])   # RandI as observed by the match harness
            elif e.kind==2:ev(['shield_value',e.a])
            elif e.kind==3:ev(['shatter'])
            else:ev(['sound',e.a])
        def weaken(_,p):
            e=p.contents
            if e.kind==1:ev(['sound',e.a])
            elif e.kind==2:ev(['text',e.tile,e.a,e.b,e.c])
            elif e.kind==3:ev(['add_label',e.a,['attack_label',e.tile],e.b,e.c,e.d])
            else:ev(['particles',e.tile,e.a])
        def health(_,p):
            e=p.contents
            if e.kind==1:ev(['sound',e.a])
            elif e.kind==2:ev(['add_label',e.a,'bd30' if e.a==2 else 'poison',e.b,e.c,e.d])
            elif e.kind==3:ev(['poison_bar',e.a])
            elif e.kind==4:ev(['vampires']);self.vampires(C.byref(self.gen),C.byref(self.vamp_hooks))
            elif e.kind==5:ev(['help_health'])
            else:ev(['health_bar',e.a])
        def vamp(_,p):
            e=p.contents
            if e.kind==7:ev(['text',e.tile,e.a,e.b,e.c])
            elif e.kind==2:ev(['add_label',e.a,['tile',e.tile],e.b,e.c,e.d])
            elif e.kind==1:ev(['sound',e.a])
        def fade(_,p):
            e=p.contents;name=['overlay','q1','q2'][e.a];self.quads[name]=e.b;ev(['alpha',name,e.b])
        # Damage-all / counterattack presentation (AllHooks events).
        def all_event(_,p):
            e=p.contents
            if e.kind==1:ev(['sound',e.a])
            elif e.kind==2:ev(['add_label',e.a,['rest' if e.a==2 else 'tile',e.tile],e.b,e.c,e.d])
            else:ev(['achievement',e.a,e.b])
        self.cbs=[FLARE_FN(flare),ANIM_FN(anim),COUNTER_FN(counter),E5_FN(absorb),E5_FN(shield),E6_FN(weaken),E5_FN(health),FADE_FN(fade),
                  ENC_EVENT(vamp),ALL_EVENT(all_event)]
        self.all_hooks=AllHooks(None,self.cbs[9],self.cb[1],self.cb[2])
        self.hook_objs=dict(flare=FlareHooks(None,self.cbs[0]),anim=AnimHooks(None,self.cbs[1],self.cbs[2]),absorb=E5Hooks(None,self.cbs[3]),
                            shield=E5Hooks(None,self.cbs[4]),weaken=E6Hooks(None,self.cbs[5]),health=E5Hooks(None,self.cbs[6]),fade=FadeHooks(None,self.cbs[7]))
        self.vamp_hooks=EncHooks(None,self.cbs[8],None)
        h=self.hook_objs
        self.process_hooks=ProcessHooks(C.pointer(h['flare']),C.pointer(h['anim']),C.pointer(h['absorb']),C.pointer(h['shield']),
                                        C.pointer(h['weaken']),C.pointer(self.all_hooks),C.pointer(h['health']),C.pointer(h['fade']))
    def load(self,c):
        super().load(c)
        self.damage=AttackDamage(C.pointer(self.r),c['phase'],c['damage'],c['enemy9'])
        self.anim=AnimState(c['progress'],c['label_y'],c['damage_alpha'],c['poison_alpha'],c['count'],c['counter'],*[c[k] for k in MOTION])
        self.overlay=C.c_uint8(c['overlay']);self.inputs=Inputs(c['chance'],c['weaken'],c['damage_all'])
        self.flare_mirror={};self.quads={'overlay':0x5a,'q1':0x5a,'q2':0x5a}
    def anim_state(self):
        a=self.anim;count=a.flare_count
        flares=[list(self.flare_mirror.get(i,[0x5a,0x5a5a5a5a])) for i in range(min(max(count,0),80))]
        return dict(phase=self.damage.phase,damage=self.damage.incoming_damage,enemy9=self.damage.enemy9_damage,poison=self.r.poison,count=count,
                    floats=[fbits(getattr(a,k)) for k in ('label_progress','label_y','damage_label_alpha','poison_label_alpha')]+[fbits(getattr(a,k)) for k in MOTION],
                    flares=flares,quads=dict(self.quads),counter=a.counterattack)
    def frame(self,dt):
        self.all_events=[];self.enc_events=[];self.gen_events=[];self.refill_events=[];self.path_events=[]
        self.match_events=[];self.token_events=[];self.motion_events=[]
        self.process(C.byref(self.damage),C.byref(self.path_state),C.byref(self.anim),C.byref(self.overlay),dt,C.byref(self.inputs),C.byref(self.process_hooks))
        return dict(path=self.path_status(),enc=self.enc_status(),all=self.all_events[:],anim=self.anim_state())
    def set_phase(self,phase):self.damage.phase=phase

def game_case(rng):
    c,_=scenario(rng)
    for i,t in enumerate(c['board']):
        if t['type']==1 and rng.random()<.25:t['enemy']=rng.choice([9,20,29])
        c['combat'][i]['poison'][0]=rng.choice([0,0,0,rng.randrange(1,4)])
    c['preview']['armour_current']=rng.choice([0,rng.randrange(1,12),rng.randrange(20,60)])
    c['resources'].update(health=rng.randrange(60,400),ui_health=0,poison=rng.randrange(0,3))
    c.update(phase=1,damage=0,enemy9=0,count=0,chance=rng.randrange(0,101),weaken=rng.choice([0,0,1,2]),damage_all=rng.choice([0,0,1,3]),
             progress=0.0,label_y=f32(rng.uniform(0.2,0.8)),damage_alpha=0.0,poison_alpha=0.0,counter=rng.randrange(2),overlay=0)
    for k in MOTION:c[k]=f32(rng.uniform(0,1))
    return c

def main():
    old,new=Original(),Native();rng=random.Random(0x14118);frames=attacks=settle=0;phases={};counter_runs=0;seen={}
    def compare(c,a,b,stage):
        if a!=b:
            (HERE/'process_attack_failure.json').write_text(json.dumps(dict(case=c,stage=stage,original=a,native=b),indent=2))
            raise AssertionError('process_attack_failure.json')
    for game in range(GAMES):
        c=game_case(rng);old.load(c);new.load(c)
        for attack in range(2):
            if attack:old.set_phase(1);new.set_phase(1)
            for frame in range(2000):
                dt=f32(rng.choice([1/60,1/30,rng.uniform(0,0.04)]))
                a,b=old.frame(dt),new.frame(dt);compare(dict(game=game,attack=attack,frame=frame),a,b,'frame');frames+=1
                phases[a['anim']['phase']]=phases.get(a['anim']['phase'],0)+1;counter_runs+=a['all'].count(['counterattack'])
                for e in a['all']:
                    key=e[0] if e[0]!='add_label' else 'add_label_%d'%e[1]
                    if e[0]=='A':key='attack_skull'
                    seen[key]=seen.get(key,0)+1
                if a['anim']['phase']==8:break
            else:raise AssertionError('attack did not finish')
            attacks+=1
            for f in range(240):
                a,b=old.falling_frame(1/60),new.falling_frame(1/60);compare(dict(game=game,attack=attack,settle=f),a,b,'settle');settle+=1
                if not new.moving_list:break
    assert all(phases.get(p) for p in (1,2,3,4,5,6,7,8))
    for key in ('flare','shadow','rand_f','help','shatter','particles','vampires','counterattack','attack_skull','health_bar','poison_bar',
                'add_label_2','add_label_4','add_label_5','add_label_7','add_label_26'):
        assert seen.get(key),key
    report=dict(status='passed',games=GAMES,event_counts=dict(sorted(seen.items())),attacks=attacks,frames=frames,settle_frames=settle,phase_frames={str(k):v for k,v in sorted(phases.items())},
                counterattacks=counter_runs,function=dict(symbol='__ZN4Game13ProcessAttackEv',address=hex(ENTRY),native='dr_process_attack'),
                original='Whole original ProcessAttack each frame with all gameplay callees as original code',
                boundaries=['presentation calls recorded in canonical form','platform powf answered by host C powf on both sides',
                            'Game::AddFlare modelled as append+count on both sides (flare quads at a fixed address)',
                            'Game+0xbdc8/+0xbe6c/+0xbe68 and dt supplied by the harness; phase 1 restart and phase 8 handling belong to the caller (not ProcessAttack)'],
                scope='Full shared state: board, combat, tokens, refill, generation, RNG, resources, animation fields, flares and quads',
                branch_visits_count=len(old.visits))
    (HERE/'process_attack_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
