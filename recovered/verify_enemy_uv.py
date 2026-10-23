#!/usr/bin/env python3
"""Tile::UpdateEnemyUV's rules (T040-N3): actual Tile::UpdateEnemyUV 0x3ef64 vs the native dr_session_update_enemy_uv.

4000 draws: a random tile, enemy type (none, any, the current class's mortal enemy), current class and race, and random
streams. The original runs from its entry with CharacterClass::GetMortalEnemyType and Rand as original code; the
picture (Tile::GetEnemyUV, Quad::SetUV) and the label colours (Label::UpdateColour) are skipped, the label is scratch
memory. Compared: the spin flag (Tile+0x224, GeneratedTile.flag_224) and the six random streams (Rand(30, 45, stream
0) for a mortal enemy); the drawn speed (Tile+0x228) is the renderer's.
"""
import ctypes as C
import json
import random
import re
import struct
from verify_skills import Original as SkillsOriginal, case as skills_case
from verify_stroke import HERE, State as Stroke
from verify_session import Objects, Host, U8
from verify_match import Match

TEXT=(HERE.parent/'armv7-disassembly.txt').read_text()
def addr(symbol):return int(re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',TEXT,re.M)[1],16)
UPDATE=addr('__ZN4Tile13UpdateEnemyUVEv')
SKIP={addr(n) for n in ('__ZN4Tile10GetEnemyUVE9EnemyTypeR8GLfloat2S2_','__ZN4Quad5SetUVERK8GLfloat2S2_','__ZN4Quad5SetUVEffff',
                        '__ZN5Label12UpdateColourEv')}
SEEDS,CLASSES,STRIDE,CURRENT,LABEL=0x1eac20,0x15564,388,0x1648c,0x3700000
def tile(G,i):return G+0x5e58+608*i

class Original(SkillsOriginal):
    def __init__(self):super().__init__();self.screening=False
    def hook(self,u,address,size,context):
        if self.screening and address in SKIP:u.reg_write(self.PC,u.reg_read(self.LR)|1);return
        return super().hook(u,address,size,context)
    def call(self,entry,args):
        u=self.u
        for r,v in zip(self.regs,args):u.reg_write(r,v&0xffffffff)
        u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1);self.screening=True
        try:u.emu_start(entry|1,self.STOP,timeout=0,count=200000)
        finally:self.screening=False
        assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))

def main():
    old=Original();old.load(skills_case(random.Random(1)));u=old.u;G=old.GAME
    u.mem_map(LABEL,0x1000)
    lib=C.CDLL(str(HERE/'recovered_session_native.dylib'))
    lib.dr_session_create.argtypes=[C.POINTER(Host),C.c_int32];lib.dr_session_create.restype=C.c_void_p
    lib.dr_session_objects.argtypes=[C.c_void_p];lib.dr_session_objects.restype=Objects
    lib.dr_session_update_enemy_uv.argtypes=[C.c_void_p,C.c_int32];lib.dr_session_update_enemy_uv.restype=None
    MORTAL=C.CDLL(str(HERE/'recovered_attack_shield_native.dylib'))   # (CharacterClass::GetMortalEnemyType for the draws)
    host=Host();session=lib.dr_session_create(C.byref(host),1);o=lib.dr_session_objects(session)
    st=Stroke.from_address(o.stroke);m=Match.from_address(o.match);flags=lambda i:U8.from_address(o.generation+16+16*i+12)
    rng=random.Random(0x3ef64);counts=dict(draws=0,mortal=0,cleared=0,none=0)
    for draw in range(4000):
        i=rng.randrange(36);cur=rng.randrange(10);race=rng.randrange(10);mortal=MORTAL.dr_mortal_enemy(race)
        enemy=rng.choice([0,mortal,mortal,rng.randrange(1,33)]);before=rng.randrange(2);seeds=[rng.randrange(1,2**31) for _ in range(6)]
        T=tile(G,i);old.write(T+0x24c,enemy);old.write(T+0x70,G);old.write(T+0xc8,LABEL);u.mem_write(T+0x224,bytes([before]))
        old.write(G+CURRENT,cur);old.write(G+CLASSES+STRIDE*cur+8,race);u.mem_write(SEEDS,struct.pack('<6I',*seeds))
        old.call(UPDATE,[T])
        st.selection.tiles[i].rule.enemy=enemy;st.selection.character.race=race;flags(i).value=before;m.random.seeds[:]=seeds
        lib.dr_session_update_enemy_uv(session,i)
        a=[u.mem_read(T+0x224,1)[0],list(struct.unpack('<6I',u.mem_read(SEEDS,24)))];n=[flags(i).value,list(m.random.seeds)]
        if a!=n:
            (HERE/'enemy_uv_failure.json').write_text(json.dumps(dict(draw=draw,tile=i,enemy=enemy,race=race,before=before,original=a,native=n),indent=2))
            raise AssertionError('enemy_uv_failure.json')
        counts['draws']+=1;counts['mortal' if a[0] else 'none' if not enemy else 'cleared']+=1
    assert counts['mortal'] and counts['cleared'] and counts['none'],counts
    print(json.dumps(dict(status='passed',**counts,function='Tile::UpdateEnemyUV 0x3ef64',native='dr_session_update_enemy_uv',
                          original='Actual function from its entry',boundaries=['the picture and label colours skipped','Tile+0x228 (the spin speed) the renderer\'s'])))

if __name__=='__main__':main()
