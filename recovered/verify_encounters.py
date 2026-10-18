#!/usr/bin/env python3
"""Actual Stab/JumpDown/SwapTiles and full refill+generation dependency chain."""
import ctypes as C
import json,re,struct,random
from verify_generation import Native as GenNative,Original as GenOriginal,Generation,configure,EVENT as GEN_EVENT,Hooks as GenHooks
from verify_refill import EVENT as REFILL_EVENT,Hooks as RefillHooks,Refill
from verify_stroke import HERE,I32
from verify_resources import bits
class Event(C.Structure):_fields_=[(k,I32) for k in ['kind','tile','a','b','c','d']]
EVENT=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(Event))
class Hooks(C.Structure):_fields_=[('context',C.c_void_p),('event',EVENT),('refill',C.POINTER(RefillHooks))]
class Native(GenNative):
    def __init__(self):
        super().__init__();self.enc_lib=C.CDLL(str(HERE/'recovered_encounters_native.dylib'))
        for name in ['dr_stab','dr_jump_down']:
            f=getattr(self.enc_lib,name);f.argtypes=[C.POINTER(Generation),C.c_uint32,C.POINTER(Hooks)];f.restype=None
        self.refill_lib.dr_swap_tiles.argtypes=[C.POINTER(Refill),I32,I32,I32,I32,C.POINTER(RefillHooks)];self.refill_lib.dr_swap_tiles.restype=None
    def load(self,c):
        super().load(c);self.enc_events=[]
        def encounter(_,p):
            e=p.contents;self.enc_events.append([e.kind,e.tile,e.a,e.b,e.c,e.d])
        self.enc_event=EVENT(encounter)
        def refill(_,kind,i,j):
            self.refill_events.append([kind,i,j])
            if kind==1:
                a=bytes(self.gen.tiles[i]);b=bytes(self.gen.tiles[j]);C.memmove(C.byref(self.gen.tiles[i]),b,len(b));C.memmove(C.byref(self.gen.tiles[j]),a,len(a))
            elif kind==2:self.moving_list.append(i)
            elif kind==3:self.gen_fns['randomise'](C.byref(self.gen),i,C.byref(self.gen_hooks))
            elif kind==4:self.enc_lib.dr_stab(C.byref(self.gen),i,C.byref(self.enc_hooks))
        self.refill_event=REFILL_EVENT(refill);self.refill_hooks=RefillHooks(None,self.refill_event);self.enc_hooks=Hooks(None,self.enc_event,C.pointer(self.refill_hooks))
        original=self.gen_event
        def generation(ctx,p):
            original(ctx,p)
            if p.contents.kind==11:self.enc_lib.dr_jump_down(C.byref(self.gen),p.contents.tile,C.byref(self.enc_hooks))
        self.gen_event=GEN_EVENT(generation);self.gen_hooks=GenHooks(None,self.gen_event)
    def enc_status(self):
        return dict(**self.gen_status(),encounters=self.enc_events,health=self.r.health,ui_health=self.r.ui_health,shake=[self.m.shake_progress_bd90,self.m.shake_scale_bd94])
    def encounter(self,key,i=17,j=30):
        self.enc_events=[];self.gen_events=[];self.refill_events=[]
        if key=='move':self.refill_lib.dr_move_matched_tiles(C.byref(self.refill),C.byref(self.refill_hooks))
        elif key=='swap':self.refill_lib.dr_swap_tiles(C.byref(self.refill),i%6,i//6,j%6,j//6,C.byref(self.refill_hooks))
        else:getattr(self.enc_lib,'dr_'+key)(C.byref(self.gen),i,C.byref(self.enc_hooks))
        return self.enc_status()

class Original(GenOriginal):
    def __init__(self):
        super().__init__();self.enc_active=False;self.enc_calls={}
        text=(HERE.parent/'armv7-disassembly.txt').read_text()
        names={'__ZN4Game10QueueSoundE5Sound':'sound','__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif':'label','__ZN9Interface15UpdateHealthBarER4Quadi':'health','__ZN9Interface17GetPoisonPositionEv':'poison','__ZN4Game12CheckEndGameEv':'end','__ZN4Game8AddFlareE9FlareType8GLfloat2RK9GLcolour4':'flare'}
        for s,n in names.items():
            m=re.search(r'^'+re.escape(s)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,s;self.enc_calls[int(m[1],16)]=n
    def hook(self,u,address,size,context):
        if not getattr(self,'enc_active',False):return super().hook(u,address,size,context)
        r=[u.reg_read(v) for v in self.regs];lr=u.reg_read(self.LR)&~1;sp=u.reg_read(self.SP);signed=lambda v:C.c_int32(v).value
        if address==0xf5b8 and lr==0x110ac:self.refill_events.append([3,self.index(r[1]),0]);return
        if address==0x10e24:
            if lr==0x110de:self.refill_events.append([4,self.index(r[1]),0])
            self.stab_tile=self.index(r[1]);return
        if address==0xb5c4:
            if lr==0xf726:self.gen_events.append([11,self.index(r[1]),0,0,0,0])
            self.jump_tile=self.index(r[1]);self.jump_column=self.read(r[1]+0x74);return
        from_enc=0x10e24<=lr<0x10ed8 or 0xb5c4<=lr<0xb648
        if not from_enc:return super().hook(u,address,size,context)
        name=self.enc_calls.get(address)
        if not name:return super().hook(u,address,size,context)
        if name=='sound':e=[1,-1,r[1],0,0,0]
        elif name=='label':
            index=self.stab_tile if lr==0x10e60 else -1 if lr==0x10ec6 else 30+self.jump_column
            e=[2,index,r[1],signed(r[3]),signed(self.read(sp)),signed(self.read(sp+4))]
        elif name=='health':e=[3,-1,r[2],0,0,0]
        elif name=='poison':e=[4,-1,0,0,0,0];u.mem_write(r[0],struct.pack('<ff',.1,.1))
        elif name=='end':e=[5,-1,0,0,0,0];u.reg_write(self.regs[0],0)
        elif name=='flare':e=[6,30+self.jump_column,r[1],signed(self.read(self.read(sp))),0,0]
        self.enc_events.append(e);u.reg_write(self.PC,u.reg_read(self.LR))
    def load(self,c):super().load(c);self.enc_events=[]
    def enc_status(self):
        signed=lambda a:C.c_int32(self.read(a)).value
        return dict(**self.gen_status(),encounters=self.enc_events,health=signed(self.GAME+0xbd98),ui_health=signed(self.GAME+0x5994),shake=[self.read(self.GAME+0xbd90),self.read(self.GAME+0xbd94)])
    def encounter(self,key,i=17,j=30):
        self.enc_events=[];self.gen_events=[];self.refill_events=[];self.gen_active=True;self.enc_active=True
        try:
            if key=='move':self.call(0x10ed8,[self.GAME])
            elif key=='swap':self.call(0xb494,[self.GAME,i%6,i//6,j%6],j//6)
            else:self.call(0x10e24 if key=='stab' else 0xb5c4,[self.GAME,self.tile(i)])
        finally:self.enc_active=False;self.gen_active=False
        return self.enc_status()

def main():
    old,new=Original(),Native();counts={};rng=random.Random(9271)
    def compare(c,key,a,b):
        if a!=b:
            (HERE/'encounters_failure.json').write_text(json.dumps(dict(case=c,key=key,original=a,native=b),indent=2));raise AssertionError(f'{key}: encounters_failure.json')
    for i in range(36):
     for j in range(36):
        c=configure();old.load(c);new.load(c);compare(c,'swap',old.encounter('swap',i,j),new.encounter('swap',i,j));counts['swap']=counts.get('swap',0)+1
    for i in range(36):
        c=configure();old.load(c);new.load(c);compare(c,'jump_down',old.encounter('jump_down',i),new.encounter('jump_down',i));counts['jump_down']=counts.get('jump_down',0)+1
    for hp in [0,1,5,10,100]:
     for atk in [0,1,2,3,10,101]:
      for poison in [0,3]:
       for race in [0,1,9]:
        for ui in [0,1]:
         c=configure();c['resources'].update(health=hp,ui_health=hp if ui else 0);c['combat'][17]['attack']=atk;c['combat'][17]['poison'][0]=poison;c['game']['race']=race
         old.load(c);new.load(c);compare(c,'stab',old.encounter('stab'),new.encounter('stab'));counts['stab']=counts.get('stab',0)+1
    for n in range(300):
        c=configure();c['path_state']['turn']=rng.randint(1,1500);c['match']['spawn_enabled_14ae0']=n%4;c['match']['seeds']=[rng.getrandbits(32) for _ in range(6)]
        c['match']['perks']=[1,6,8,255];c['game']['flaws']=[7,8,9,255];c['game']['race']=n%10;c['generation']['time_to_promotion']=n%3;c['resources']['health']=2000;c['record']=int(n%11==0);c['mode']=n%2
        for i,t in enumerate(c['board']):
            t.update(matched=int(rng.random()<.5),type=1 if i%3==0 else 2,enemy=31 if i%3==0 else 0)
        old.load(c);new.load(c);compare(c,'move',old.encounter('move'),new.encounter('move'));counts['move']=counts.get('move',0)+1
    report=dict(status='passed',cases=sum(counts.values()),by_function=counts,original='Actual SwapTiles/JumpDown/Stab/MoveMatchedTiles/RandomiseTile/SetType/Promote/GenerateStats/RNG and attack getter',boundaries=['UI/render/audio/achievement dispatch','CheckEndGame response and shield-shatter presentation'],scope='Integrated refill with real random generation, state swaps, special-enemy jump and damage. No full enemy phase or full Game::Process claim.')
    (HERE/'encounters_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
