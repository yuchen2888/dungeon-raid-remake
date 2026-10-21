#!/usr/bin/env python3
"""The upgrade menu (T040-K4): actual FoldoutMenu::Initialise(2) 0x24a54 (with Game::GetItem, ItemUpgrade::
Initialise 0x2da74 -- GetRandomStat, GetStatUpgrade -- as original code), then FoldoutMenu::Process frame by
frame up to Item::AddUpgrade 0x29de0 and Game::UpdateStats, vs native dr_menu_open_upgrade / dr_menu_process
(recovered_menu), on the harness of verify_menu_shop.py.

The four ItemUpgrade objects (FoldoutMenu+0x68..) point back to the Game (+0x7c); their text
(ItemUpgrade::WriteStatFloat / WriteStatPercent / WriteStatInt, GetDescription, GetStats), Upgrade::SetIcon,
strcpy and Item::MakeStats are skipped. Compared after every frame as verify_menu_shop.py, plus the four
proposals (which equipped item, stat type, amount).
"""
import ctypes as C
import json
import random
import re
import struct
from verify_menu_shop import Original as ShopOriginal, Native as ShopNative, Sources, case as shop_case
from verify_menu_level import FM
from verify_stroke import HERE, I32

INIT=0x24a54
UPGRADES=0x17e5000
SKIP=['__ZN11ItemUpgrade14WriteStatFloatEPKcP4Item','__ZN11ItemUpgrade16WriteStatPercentEPKcP4Item','__ZN11ItemUpgrade12WriteStatIntEPKcP4Item',
      '__ZN11ItemUpgrade14GetDescriptionEv','__ZN11ItemUpgrade8GetStatsEv']

class Original(ShopOriginal):
    def __init__(self):
        super().__init__();text=(HERE.parent/'armv7-disassembly.txt').read_text()
        addr=lambda s:int(re.search(r'^'+re.escape(s)+r':\n\s*([0-9a-f]+):',text,re.M)[1],16)
        self.menu_skip|={addr(s) for s in SKIP}
    def load(self,c):
        super().load(c);G=self.GAME
        for i in range(4):self.write(UPGRADES+0x100*i+0x7c,G);self.write(G+FM+0x68+4*i,UPGRADES+0x100*i);self.write(G+FM+0x58+4*i,0)
    def open_upgrade(self):
        u=self.u;G=self.GAME;self.menu_events=[]
        u.reg_write(self.regs[0],G+FM);u.reg_write(self.regs[1],2);u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1);self.menuing=True
        try:u.emu_start(INIT|1,self.STOP,timeout=0,count=5000000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.menuing=False
        return self.upgrade_status()
    def frame(self,phase,button,dt):super().frame(phase,button,dt);return self.upgrade_status()
    def upgrade_status(self):
        st=self.shop_status();G=self.GAME;i32=lambda a:C.c_int32(self.read(a)).value
        slots=[self.read(G+0xbe88+4*j) for j in range(5)]
        st['upgrades']=[[slots.index(self.read(G+FM+0x58+4*i)) if self.read(G+FM+0x58+4*i) in slots else -1,
                         i32(self.read(G+FM+0x68+4*i)+0x80),i32(self.read(G+FM+0x68+4*i)+0x84)] for i in range(4)]
        st.pop('items');st.pop('scroll');st.pop('scroll_slot')
        return st

class Native(ShopNative):
    def __init__(self):
        super().__init__();lib=self.menu_lib
        lib.dr_menu_open_upgrade.argtypes=[C.c_void_p,C.POINTER(Sources),C.c_void_p];lib.dr_menu_open_upgrade.restype=None
    def load(self,c):
        super().load(c)
        for i in range(4):self.menu.upgrade_items[i]=-1;self.menu.upgrade_type[i]=0;self.menu.upgrade_amount[i]=0
    def open_upgrade(self):
        self.menu_events=[];self.menu_lib.dr_menu_open_upgrade(C.addressof(self.menu),C.byref(self.shop_sources),C.addressof(self.menu_hooks))
        return self.upgrade_status()
    def frame(self,phase,button,dt):super().frame(phase,button,dt);return self.upgrade_status()
    def upgrade_status(self):
        st=self.shop_status();m=self.menu
        st['upgrades']=[[m.upgrade_items[i],m.upgrade_type[i],m.upgrade_amount[i]] for i in range(4)]
        st.pop('items');st.pop('scroll');st.pop('scroll_slot')
        return st

def main():
    old,new=Original(),Native();rng=random.Random(0x256f4);n=500;frames=0;applied=0;stats=set();f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
    for i in range(n):
        c=shop_case(rng);old.load(c);new.load(c)
        a,b=old.open_upgrade(),new.open_upgrade()
        def check(stage,a,b,extra=None):
            if a!=b:
                (HERE/'menu_upgrade_failure.json').write_text(json.dumps(dict(case=i,stage=stage,extra=extra,shop=c['shop'],original=a,native=b),indent=2))
                raise AssertionError(f'menu_upgrade_failure.json ({stage})')
        check('open',a,b);stats|={u[1] for u in a['upgrades']}
        plan=[(0,-1,f32(1/60))]*rng.randrange(1,4)
        for _ in range(rng.randrange(0,6)):
            bt=rng.choice([14,15,16,17,7,-1])
            plan+=[(1,bt,f32(1/60)),(rng.choice([2,2,3]),rng.choice([bt,bt,-1,7]),f32(rng.choice([1/60,1/30]))),(0,-1,f32(1/60))]
        step=0;guard=0;done=False
        while not done:
            if step<len(plan):phase,button,dt=plan[step];step+=1
            else:
                m=old.upgrade_status()['menu']
                if m['timer']!=0xbf800000:phase,button,dt=0,-1,f32(1/60)
                elif m['first']==-1:plan+=[(0,-1,f32(1/60)),(1,rng.choice([14,15,16,17]),f32(1/60)),(2,-2,f32(1/60))];continue
                else:plan+=[(0,-1,f32(1/60)),(1,7,f32(1/60)),(2,7,f32(1/60))];continue
            if button==-2:button=old.upgrade_status()['menu']['first']
            guard+=1;assert guard<400,'menu did not close'
            before=old.upgrade_status()['menu']
            a,b=old.frame(phase,button,dt),new.frame(phase,button,dt);frames+=1
            check('frame',a,b,[phase,button,dt])
            if before['open'] and not a['menu']['open']:done=True;applied+=1
    assert len(stats)>=18,sorted(stats)
    report=dict(status='passed',cases=n,frames=frames,applied=applied,proposed_stats=sorted(stats),
                function=dict(symbol='__ZN11FoldoutMenu10InitialiseE8MenuType',address=hex(INIT),native='dr_menu_open_upgrade, dr_menu_process (upgrade)'),
                original='Actual FoldoutMenu::Initialise(2) / Process with ItemUpgrade::Initialise, Item::AddUpgrade and Game::UpdateStats',
                boundaries=['std::set modelled; upgrade text, icons and item text skipped'])
    (HERE/'menu_upgrade_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
