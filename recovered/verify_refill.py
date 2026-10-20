#!/usr/bin/env python3
"""Execute original refill/position/fall instructions; generation/Stab isolated."""
import ctypes as C
import json,random,re,struct
from verify_path import Native as PathNative,Original as PathOriginal,Path,convert
from verify_round import base_case
from verify_selection import RULE_INTS,RULE_BYTES,TBYTES
from verify_stroke import HERE,I32,U8,Point
from verify_resources import bits

class Falling(C.Structure):
    _fields_=[('target',Point),('moving',U8),('speed',C.c_float),('acceleration',C.c_float)]
class Refill(C.Structure):_fields_=[('path',C.POINTER(Path)),('falling',Falling*36)]
EVENT=C.CFUNCTYPE(None,C.c_void_p,I32,I32,I32)
class Hooks(C.Structure):_fields_=[('context',C.c_void_p),('event',EVENT)]
def configure(c):
    c['falling']=[dict(target=[.1+i*.001,.2+i*.01],moving=i%2,speed=.5+i*.125,acceleration=2+i*.25) for i in range(36)]
    c['moving_list']=[]
    return c

class Native(PathNative):
    def __init__(self):
        super().__init__();self.refill_lib=C.CDLL(str(HERE/'recovered_refill_native.dylib'))
        for name,args in [('dr_move_matched_tiles',[C.POINTER(Refill),C.POINTER(Hooks)]),('dr_position_tile',[C.POINTER(Refill),C.c_uint32,I32,I32,C.c_bool]),('dr_process_falling_tile',[C.POINTER(Refill),C.c_uint32,C.c_float])]:
            f=getattr(self.refill_lib,name);f.argtypes=args;f.restype=None
    def load(self,c):
        super().load(c);self.refill=Refill();self.refill.path=C.pointer(self.path_state)
        self.moving_list=list(c['moving_list']);self.refill_events=[]
        for i,f in enumerate(c['falling']):
            for k,v in f.items():setattr(self.refill.falling[i],k,Point(*v) if k=='target' else v)
        def event(_,kind,i,j):
            self.refill_events.append([kind,i,j])
            if kind==2:self.moving_list.append(i)
            if kind==3: # Explicit deterministic dependency, not recovered generation.
                t=self.state.selection.tiles[i];t.rule.type=i%5;t.rule.enemy=31 if i%5==1 else 0
                self.path_state.combat[i].health=100+i
        self.refill_event=EVENT(event);self.refill_hooks=Hooks(None,self.refill_event)
    def refill_status(self):
        board=[]
        for i,t in enumerate(self.state.selection.tiles):
            f=self.refill.falling[i];p=self.p.potions[i]
            board.append(dict(rule={k:getattr(t.rule,k) for k in [*RULE_INTS,*RULE_BYTES]},flags={k:getattr(t,k) for k in TBYTES},
                center=[bits(t.geometry.center.x),bits(t.geometry.center.y)],resting=[bits(t.resting.x),bits(t.resting.y)],
                size=bits(t.size),half=bits(t.geometry.size),flame_damage=t.flame_damage,
                potion=list(bytes(p)),flag25d=self.m.flag_25d[i],
                target=[bits(f.target.x),bits(f.target.y)],moving=f.moving,speed=bits(f.speed),acceleration=bits(f.acceleration)))
        return dict(board=board,combat=self.path_status()['combat'],events=self.refill_events,moving_list=self.moving_list)
    def move(self):
        self.refill_events=[];self.refill_lib.dr_move_matched_tiles(C.byref(self.refill),C.byref(self.refill_hooks));return self.refill_status()
    def position(self,i,x,y,target):
        self.refill_lib.dr_position_tile(C.byref(self.refill),i,x,y,target);return self.refill_status()
    def fall(self,i,dt):
        self.refill_lib.dr_process_falling_tile(C.byref(self.refill),i,dt);return self.refill_status()

class Original(PathOriginal):
    def __init__(self):
        super().__init__();self.refill_active=False;text=(HERE.parent/'armv7-disassembly.txt').read_text()
        symbols={'__ZSt4swapI4TileEvRT_S2_':'swap','__ZNSt8_Rb_treeIP4TileS1_St9_IdentityIS1_ESt4lessIS1_ESaIS1_EE13_Rb_tree_implIS5_Lb0EEC2ERKSaISt13_Rb_tree_nodeIS1_EERKS5_':'tree','__ZN4Game13RandomiseTileER4Tile':'randomise','__ZN4Game4StabEP4Tile':'stab'}
        self.refill_calls={0x194cec:'unwind',0x194cf4:'unwind',0x194d30:'increment'}
        for s,n in symbols.items():
            m=re.search(r'^'+re.escape(s)+r':\n\s*([0-9a-f]+):',text,re.M);assert m,s;self.refill_calls[int(m[1],16)]=n
    def hook(self,u,address,size,context):
        if not getattr(self,'refill_active',False):return super().hook(u,address,size,context)
        name=self.refill_calls.get(address) or self.boundaries.get(address)
        if not name:return super().hook(u,address,size,context)
        r=[u.reg_read(v) for v in self.regs]
        if name=='swap':
            a,b=bytes(u.mem_read(r[0],608)),bytes(u.mem_read(r[1],608));u.mem_write(r[0],b);u.mem_write(r[1],a)
            self.refill_events.append([1,self.index(r[0]),self.index(r[1])])
        elif name=='push':
            assert r[0]==self.GAME+0xb3f8;i=self.index(self.read(r[1]));self.moving_list.append(i);self.refill_events.append([2,i,0]);self.push(r[0],self.tile(i))
        elif name=='randomise':
            i=self.index(r[1]);self.refill_events.append([3,i,0]);self.write(r[1]+0x9c,i%5);self.write(r[1]+0x24c,31 if i%5==1 else 0);self.write(r[1]+0xac,100+i)
        elif name=='stab':self.refill_events.append([4,self.index(r[1]),0])
        elif name=='tree':
            self.tree=r[0];self.tree_values=set();self.write(self.tree+12,self.tree+4)
        elif name=='set_insert':
            assert r[1]==self.tree;self.tree_values.add(self.read(r[2]));values=sorted(self.tree_values)
            self.write(self.tree+12,0x1511000)
            for i,value in enumerate(values):
                node=0x1511000+32*i;self.write(node,0x1511000+32*(i+1) if i+1<len(values) else self.tree+4);self.write(node+16,value)
        elif name=='increment':u.reg_write(self.regs[0],self.read(r[0]))
        elif name in ['set_clear','unwind']:pass
        else:return super().hook(u,address,size,context)
        u.reg_write(self.PC,u.reg_read(self.LR))
    def load(self,c):
        super().load(c);self.moving_list=list(c['moving_list']);self.refill_events=[];self.path_events=[]
        for i,f in enumerate(c['falling']):
            base=self.tile(i);self.u.mem_write(base+0x88,struct.pack('<ff',*f['target']));self.u.mem_write(base+0x90,bytes([f['moving']]))
            self.u.mem_write(base+0x94,struct.pack('<ff',f['speed'],f['acceleration']))
        for i in self.moving_list:self.push(self.GAME+0xb3f8,self.tile(i))
    def refill_status(self):
        board=[];signed=lambda a:C.c_int32(self.read(a)).value
        for i in range(36):
            base=self.tile(i)
            board.append(dict(rule=dict(**{k:signed(base+a) for k,a in RULE_INTS.items()},**{k:self.u.mem_read(base+a,1)[0] for k,a in RULE_BYTES.items()}),
                flags={k:self.u.mem_read(base+a,1)[0] for k,a in TBYTES.items()},center=[self.read(base+0x54),self.read(base+0x58)],
                resting=[self.read(self.GAME+0xb400+8*i),self.read(self.GAME+0xb404+8*i)],size=self.read(base+0x7c),half=self.read(base+0x80),flame_damage=signed(base+0x258),
                potion=list(self.u.mem_read(base+0x232,3)),flag25d=self.u.mem_read(base+0x25d,1)[0],
                target=[self.read(base+0x88),self.read(base+0x8c)],moving=self.u.mem_read(base+0x90,1)[0],speed=self.read(base+0x94),acceleration=self.read(base+0x98)))
        return dict(board=board,combat=self.path_status()['combat'],events=self.refill_events,moving_list=self.moving_list)
    def call(self,address,args,extra=0):
        u=self.u
        for reg,value in zip(self.regs,args):u.reg_write(reg,value&0xffffffff)
        u.reg_write(self.SP,0x140fff0);u.reg_write(self.LR,self.STOP|1);self.write(0x140fff0,extra);self.refill_active=True
        try:
            u.emu_start(address|1,self.STOP,timeout=0,count=1000000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.refill_active=False
        return self.refill_status()
    def move(self):self.refill_events=[];return self.call(0x10ed8,[self.GAME])
    def position(self,i,x,y,target):return self.call(0xb3c8,[self.GAME,self.tile(i),x,y],int(target))
    def fall(self,i,dt):return self.call(0x3d1d0,[self.tile(i),bits(dt)])

def main():
    old,new=Original(),Native();count=frames=positions=0;rng=random.Random(8241)
    def compare(c,a,b):
        if a!=b:
            (HERE/'refill_failure.json').write_text(json.dumps(dict(case=c,original=a,native=b),indent=2));raise AssertionError(f'{count=}: refill_failure.json')
    masks=[0,(1<<36)-1]+[1<<i for i in range(36)]+[sum(1<<(6*y+x) for y in range(6) if mask>>y&1) for x in range(6) for mask in range(64)]+[rng.getrandbits(36) for _ in range(100)]
    for mask in masks:
        c=configure(convert(base_case()));c['moving_list']=[35] if count%2 else []
        for i,t in enumerate(c['board']):
            t.update(matched=(mask>>i)&1,type=1 if i%3==0 else i%5,enemy=31 if i%3==0 else i,flame_damage=i+1)
            c['combat'][i].update(attack=i+2,defence=i+3,health=i+4)
            c['preview']['potions'][i]=[i%2,(i//2)%2,(i//4)%2];c['match']['flag_25d'][i]=i%2
        old.load(c);new.load(c);new.path_events=[];compare(c,old.move(),new.move());count+=1
        if count%30==0:
            for _ in range(100):
                active=[i for i,f in enumerate(new.refill.falling) if f.moving]
                if not active:break
                for i in active:compare(c,old.fall(i,1/60),new.fall(i,1/60));frames+=1
    for x in range(6):
      for y in range(-6,6):
       for target in ([False] if y<0 else [False,True]):
        c=configure(convert(base_case()));c['game']['offset']=.123
        old.load(c);new.load(c);new.path_events=[];compare(c,old.position(17,x,y,target),new.position(17,x,y,target));positions+=1
    report=dict(status='passed',refill_boards=count,position_cases=positions,fall_steps=frames,original='Actual MoveMatchedTiles/PositionTile/Tile::Process machine instructions; std::swap copies all 608 original bytes',boundaries=['RandomiseTile and Stab are deterministic dependency callbacks in this isolated test','original collection allocation adapted'],scope='All 64 column removal masks in each column, mixed boards, existing moving-list contents, stable swap state, falling values compared by float bits.')
    (HERE/'refill_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
