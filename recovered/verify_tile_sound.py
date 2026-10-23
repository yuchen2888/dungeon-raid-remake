#!/usr/bin/env python3
"""Game::QueueTileSound's sounds (T040-P): actual Game::QueueTileSound 0x9094 vs the native dr_session_queue_tile_sound.

3000 draws: a random tile, tile type (-1..8), the potion flags +0x232 / +0x233 / +0x234 and the sound switch. The
original runs from its entry; its Game::QueueSound 0x903c is recorded as verify_session.py does (queued only while the
sound switch Game+0x13ec6 is on). Compared: the queued sounds. The whole-game test reaches this through the selection's
TileSound events but never selected an acid potion (only +0x233 set: sound 24), so every flag combination is drawn here.
"""
import ctypes as C
import json
import random
from verify_skills import Original as SkillsOriginal, case as skills_case
from verify_stroke import HERE, State as Stroke
from verify_session import Objects, Host, U8, QUEUE_SOUND, QUEUE_TILE_SOUND, SETTINGS_BYTES, SETTINGS_NATIVE, I32

POTIONS=0x2c   # ResourcePreviewState.potions (flags 232, 233, 234 per tile)
def tile(G,i):return G+0x5e58+608*i

class Original(SkillsOriginal):
    def __init__(self):super().__init__();self.screening=False;self.sounds=[]
    def hook(self,u,address,size,context):
        if self.screening and address==QUEUE_SOUND:
            if u.mem_read(self.GAME+SETTINGS_BYTES,1)[0]:self.sounds.append(C.c_int32(u.reg_read(self.regs[1])).value)
            u.reg_write(self.PC,u.reg_read(self.LR)|1);return
        if self.screening and QUEUE_TILE_SOUND<=address<QUEUE_TILE_SOUND+0x44:return   # (the selection harness's boundary: run here)
        return super().hook(u,address,size,context)
    def call(self,entry,args):
        u=self.u
        for r,v in zip(self.regs,args):u.reg_write(r,v&0xffffffff)
        u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1);self.screening=True
        try:u.emu_start(entry|1,self.STOP,timeout=0,count=10000)
        finally:self.screening=False
        assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))

def main():
    old=Original();old.load(skills_case(random.Random(1)));u=old.u;G=old.GAME
    lib=C.CDLL(str(HERE/'recovered_session_native.dylib'))
    lib.dr_session_create.argtypes=[C.POINTER(Host),C.c_int32];lib.dr_session_create.restype=C.c_void_p
    lib.dr_session_objects.argtypes=[C.c_void_p];lib.dr_session_objects.restype=Objects
    lib.dr_session_queue_tile_sound.argtypes=[C.c_void_p,C.c_int32];lib.dr_session_queue_tile_sound.restype=None
    lib.dr_session_next_sound.argtypes=[C.c_void_p,C.POINTER(I32),C.POINTER(I32)];lib.dr_session_next_sound.restype=C.c_bool
    host=Host();session=lib.dr_session_create(C.byref(host),1);o=lib.dr_session_objects(session)
    st=Stroke.from_address(o.stroke);potions=(U8*108).from_address(o.preview+POTIONS);settings=(U8*12).from_address(o.settings)
    def native_sounds():
        out=[];sound=I32();variant=I32()
        while lib.dr_session_next_sound(session,C.byref(sound),C.byref(variant)):out.append(sound.value)
        return out
    rng=random.Random(0x9094);counts={}
    for draw in range(3000):
        i=rng.randrange(36);kind=rng.randrange(-1,9);flags=[int(rng.random()<.4) for _ in range(3)];on=int(rng.random()<.8)
        T=tile(G,i);old.write(T+0x9c,kind);u.mem_write(T+0x232,bytes(flags));u.mem_write(G+SETTINGS_BYTES,bytes([on]))
        old.sounds=[];old.call(QUEUE_TILE_SOUND,[G,T])
        st.selection.tiles[i].rule.type=kind;potions[3*i:3*i+3]=flags;settings[SETTINGS_NATIVE[0]]=on
        native_sounds();lib.dr_session_queue_tile_sound(session,i);n=native_sounds()
        if old.sounds!=n:
            (HERE/'tile_sound_failure.json').write_text(json.dumps(dict(draw=draw,tile=i,type=kind,flags=flags,sound_on=on,original=old.sounds,native=n),indent=2))
            raise AssertionError('tile_sound_failure.json')
        key=f'{kind}:{"".join(map(str,flags))}' if kind==0 else str(kind);key=key if on else 'off'
        counts[key]=counts.get(key,0)+1
    assert all(counts.get(f'0:{a}{b}{c}') for a in '01' for b in '01' for c in '01') and counts.get('off'),counts
    print(json.dumps(dict(status='passed',draws=3000,cases=dict(sorted(counts.items())),function='Game::QueueTileSound 0x9094',
                          native='dr_session_queue_tile_sound (queue_tile_sound)',original='Actual function from its entry',
                          boundaries=['Game::QueueSound recorded as verify_session.py (the sound switch gate)'])))

if __name__=='__main__':main()
