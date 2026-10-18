#!/usr/bin/env python3
"""Real gesture -> path -> actual refill/generation -> actual falling/rewards."""
import ctypes as C
import json
from verify_encounters import Native as EncounterNative,Original as EncounterOriginal,configure
from verify_refill import Refill
from verify_stroke import HERE,I32
from verify_resources import bits
from verify_rune import rectangles

class Native(EncounterNative):
    def __init__(self):
        super().__init__();self.fall_list=self.refill_lib.dr_process_falling_list
        self.fall_list.argtypes=[C.POINTER(Refill),C.POINTER(I32),C.POINTER(C.c_uint32),C.c_float];self.fall_list.restype=None
    def falling_frame(self,dt):
        indices=(I32*len(self.moving_list))(*self.moving_list);count=C.c_uint32(len(indices))
        self.fall_list(C.byref(self.refill),indices,C.byref(count),dt);self.moving_list=list(indices[:count.value]);return self.enc_status()
class Original(EncounterOriginal):
    def hook(self,u,address,size,context):
        if getattr(self,'fall_loop',False) and address in [0x17400,0x1744c]:u.emu_stop();return
        return super().hook(u,address,size,context)
    def falling_frame(self,dt):
        from unicorn.arm_const import UC_ARM_REG_R4
        u=self.u;u.reg_write(UC_ARM_REG_R4,self.GAME);u.reg_write(self.SP,0x140fff0);self.write(self.GAME+4,bits(dt));self.fall_loop=True
        try:
            u.emu_start(0x173c9,self.STOP,timeout=1000000,count=1000000);assert u.reg_read(self.PC) in [0x17400,0x1744c]
        finally:self.fall_loop=False
        self.moving_list=[self.index(v) for v in self.list_values(self.GAME+0xb3f8)];return self.enc_status()
def main():
    old,new=Original(),Native();gestures=steps=arrivals=spawned=0
    def compare(c,stage,a,b):
        if a!=b:
            (HERE/'refill_integration_failure.json').write_text(json.dumps(dict(case=c,stage=stage,original=a,native=b),indent=2));raise AssertionError(stage)
    for n,path in enumerate(list(rectangles())[::5]):
        c=configure();c['path']=[];c['fake']=[];c['resources'].update(health=500,ui_health=500);c['preview'].update(xp_bonus=0,upgrade_bonus=0,gold_bonus=0);c['generation']['time_to_promotion']=n%3
        c['match']['seeds']=[123456+i*712+n*1823 for i in range(6)]
        for t in c['board']:t.update(type=2,enemy=0)
        for f in c['falling']:f.update(moving=0,speed=1)
        old.load(c);new.load(c)
        if hasattr(new,'batch_pending'):del new.batch_pending
        for i in path:compare(c,'input',old.step(1,c['board'][i]['center']),new.step(1,c['board'][i]['center']));steps+=1
        compare(c,'release',old.step(2,[.5,.5]),new.step(2,[.5,.5]));steps+=1
        compare(c,'path',old.commit(),new.commit());steps+=1
        compare(c,'refill',old.encounter('move'),new.encounter('move'));steps+=1
        spawned+=new.gen.generated_count-c['generation']['generated_count']
        for _ in range(240):
            compare(c,'falling',old.falling_frame(1/60),new.falling_frame(1/60));steps+=1
            before=sum(t.active for t in new.motions.values())
            compare(c,'rewards',old.batch(1/60,[0,0,0]),new.batch(1/60,[0,0,0]));steps+=1
            arrivals+=before-sum(t.active for t in new.motions.values())
            if not new.moving_list and not new.batch_pending:break
        else:raise AssertionError('did not settle')
        compare(c,'extra falling frame',old.falling_frame(1/60),new.falling_frame(1/60));steps+=1
        compare(c,'extra reward frame',old.batch(1/60,[0,0,0]),new.batch(1/60,[0,0,0]));steps+=1
        assert not any(t.rule.matched for t in new.state.selection.tiles)
        assert not new.path_state.input_ready # Do not bypass the unresolved turn scheduler.
        gestures+=1
    report=dict(status='passed',gestures=gestures,steps=steps,completed_rewards=arrivals,generated_tiles=spawned,original='Actual input, rune, MatchTiles, MatchTile, token creation, generation, refill, special jumps/stabs, falling-list Game::Process subsection, reward subsection and AddResource',boundaries=['UI/render/audio','special reward target chooser','CheckEndGame and shield-shatter presentation','full enemy phase and turn scheduler'],scope='A continuous shared-state chain through settled refill and rewards; deliberately does not reopen input or claim a complete playable turn.')
    (HERE/'refill_integration_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
