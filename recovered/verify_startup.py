#!/usr/bin/env python3
"""Start-up (T040-N1): actual Game::Game 0xdd9c and Game::Start(true) 0xb880 vs the native dr_session_create.

The original runs from Game::Game's entry over zeroed memory, then Game::Start(true), with every called function as
original code except Game::SetupRenderer (OpenGL) and the library stubs: operator new is a bump allocator, memset /
memcpy / memmove are performed, time() is fixed, the rest return 0 (Objective-C, OpenGL, sound, files). The native is a
new session. Compared: what the rules read after start-up -- the difficulty, the settings bytes and the saved score page,
the board geometry (pitch, half spacing, every tile's index, centre, resting place, size and half size) and the tiles'
falling speed and acceleration, the attack dimming's alpha, the damage number's place and the two attack numbers'
scale, the shown values (health, XP, UP, gold, armour, health ceiling, sword, armour maximum, skull), the equipped
skills' and the level-up menu's skill types, the current class and its views (type, level, race, perks, flaws), and the
six random streams (Game::Start seeds them from time(); the native dr_session_seed with the same time). Presentation
is not compared.
"""
import ctypes as C
import json
import re
import struct
import sys
from verify_stroke import HERE
import verify_original as VO
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_LITTLE_ENDIAN, UC_HOOK_CODE
from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC,
                               UC_ARM_REG_C1_C0_2, UC_ARM_REG_FPEXC, UC_ARM_REG_FPSCR)
from verify_session import Objects, Host, U8, I32, SETTINGS_BYTES, SETTINGS_NATIVE, FM
from verify_stroke import State as Stroke
from verify_refill import Refill
from verify_match import Match
from verify_resources import Resource
from verify_stats import PlayerStats
from verify_turn_begin import SkillSlots
from verify_menu_level import MenuState

TEXT=(HERE.parent/'armv7-disassembly.txt').read_text()
def addr(symbol):return int(re.search(r'^'+re.escape(symbol)+r':\n\s*([0-9a-f]+):',TEXT,re.M)[1],16)
STUBS={int(a,16):n for a,n in re.findall(r'blx\s+0x([0-9a-f]+) @ symbol stub for: (\S+)',TEXT)}
GAME,STOP,HEAP,STACK=0x1100000,0x1200000,0x2000000,0x1400000
TIME=1792000000   # time() at start-up (the native: dr_session_seed)
from verify_session import SEEDS
SKIP={addr('__ZN4Game13SetupRendererEv')}

def original():
    binary=VO.armv7_slice((HERE.parent/'DungeonRaid-original').read_bytes())
    u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_LITTLE_ENDIAN)
    for _n,vm,vs,fo,fs in VO.segments(binary):
        s,e=vm&~4095,(vm+vs+4095)&~4095;u.mem_map(s,e-s);u.mem_write(vm,binary[fo:fo+fs])
    u.mem_map(GAME,0x20000);u.mem_map(STOP,0x1000);u.mem_map(HEAP,0x1000000);u.mem_map(STACK-0x100000,0x100000)
    u.reg_write(UC_ARM_REG_C1_C0_2,u.reg_read(UC_ARM_REG_C1_C0_2)|(15<<20));u.reg_write(UC_ARM_REG_FPEXC,0x40000000);u.reg_write(UC_ARM_REG_FPSCR,0)
    heap=[HEAP];stubbed={}
    def hook(uc,a,size,ud):
        if not (0x194000<=a<0x196000 or a in SKIP):return
        r=[uc.reg_read(x) for x in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)];n=STUBS.get(a,hex(a));res=0
        if n in ('__Znwm','__Znam'):res=heap[0];heap[0]+=(r[0]+15)&~15
        elif n=='_memset':uc.mem_write(r[0],bytes([r[1]&0xff])*r[2]);res=r[0]
        elif n in ('_memcpy','_memmove'):uc.mem_write(r[0],bytes(uc.mem_read(r[1],r[2])));res=r[0]
        elif n=='_time':res=TIME
        stubbed[n]=stubbed.get(n,0)+1
        uc.reg_write(UC_ARM_REG_R0,res);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR)|1)
    u.hook_add(UC_HOOK_CODE,hook)
    def call(entry,*args):
        for reg,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1),args):u.reg_write(reg,v)
        u.reg_write(UC_ARM_REG_SP,STACK-0x100);u.reg_write(UC_ARM_REG_LR,STOP|1)
        u.emu_start(entry|1,STOP,timeout=0,count=50000000);assert u.reg_read(UC_ARM_REG_PC)==STOP,hex(u.reg_read(UC_ARM_REG_PC))
    call(addr('__ZN4GameC2Ev'),GAME);call(addr('__ZN4Game5StartEb'),GAME,1)
    return u,stubbed

def main():
    u,stubbed=original()
    rd=lambda a:struct.unpack('<I',u.mem_read(a,4))[0];i32=lambda a:C.c_int32(rd(a)).value;b=lambda a:u.mem_read(a,1)[0]
    G=GAME;tile=lambda i:G+0x5e58+608*i
    skill=lambda p:i32(p+0x84)
    current=i32(G+0x1648c);rec=G+0x15564+388*current
    a=dict(difficulty=i32(G+0x14ae0),settings=list(u.mem_read(G+SETTINGS_BYTES,9)),score_page=[i32(G+0x1660c),b(G+0x16610)],
           geometry=[rd(G+0x5e50),rd(G+0x5e54)],
           tiles=[[i32(tile(i)+0x74),i32(tile(i)+0x78),rd(tile(i)+0x54),rd(tile(i)+0x58),rd(G+0xb400+8*i),rd(G+0xb404+8*i),rd(tile(i)+0x7c),
                   rd(tile(i)+0x80),rd(tile(i)+0x94),rd(tile(i)+0x98)] for i in range(36)],
           dimming=b(G+0xb92b),labels=[rd(G+0xbd54),rd(G+0xbd30),rd(G+0xbd34),rd(G+0xbd38),rd(G+0x15520)],
           shown=[i32(G+o) for o in (0x5994,0x599c,0x59a0,0x59a4,0x59c0,0x5998,0x59bc,0x59c4,0x59c8)],
           skills=[skill(rd(G+0xbf90+4*k)) for k in range(4)],menu=[skill(rd(G+FM+0x48+4*k)) for k in range(4)]+[skill(rd(G+FM+0x110))],
           current=[current,i32(rec+4),b(rec+0x54),i32(rec+8),[i32(rec+0x10+4*k) for k in range(4)],[i32(rec+0x20+4*k) for k in range(4)]],
           seeds=list(struct.unpack('<6I',u.mem_read(SEEDS,24))),heartbeat=[rd(G+0x4cdc+o) for o in (0x109c,0x10a0,0x10a4)])
    lib=C.CDLL(str(HERE/'recovered_session_native.dylib'))
    lib.dr_session_create.argtypes=[C.POINTER(Host),C.c_int32];lib.dr_session_create.restype=C.c_void_p
    lib.dr_session_objects.argtypes=[C.c_void_p];lib.dr_session_objects.restype=Objects
    lib.dr_session_seed.argtypes=[C.c_void_p,C.c_uint32];lib.dr_session_seed.restype=None
    host=Host();session=lib.dr_session_create(C.byref(host),1);lib.dr_session_seed(session,TIME);o=lib.dr_session_objects(session)
    st=Stroke.from_address(o.stroke);sel=st.selection;falling=Refill.from_address(o.refill).falling
    m=Match.from_address(o.match);r=Resource.from_address(o.resources);p=PlayerStats.from_address(o.player)
    settings=(U8*20).from_address(o.settings);anim=(C.c_float*8).from_address(o.animation);k=SkillSlots.from_address(o.skills)
    menu=MenuState.from_address(o.menu);bits=lambda x:struct.unpack('<I',struct.pack('<f',x))[0]
    scroll=C.c_uint64.from_address(o.scroll+8).value   # ClassScrollState.current
    n=dict(difficulty=m.spawn_enabled_14ae0,settings=[settings[i] for i in SETTINGS_NATIVE],score_page=[C.c_int32.from_address(o.settings+12).value,settings[16]],
           geometry=[bits(sel.geometry.pitch),bits(sel.half_spacing)],
           tiles=[[t.rule.x,t.rule.y,bits(t.geometry.center.x),bits(t.geometry.center.y),bits(t.resting.x),bits(t.resting.y),bits(t.size),
                   bits(t.geometry.size),bits(falling[i].speed),bits(falling[i].acceleration)] for i,t in enumerate(sel.tiles)],
           dimming=C.c_uint8.from_address(o.overlay_alpha).value,labels=[bits(anim[1]),bits(anim[6]),bits(anim[7]),bits(anim[2]),bits(anim[3])],
           shown=[r.ui_health,r.ui_xp,r.ui_up,r.ui_gold,r.ui_armour,p.ui_health_ceiling_5998,p.ui_sword_59bc,p.ui_armour_max_59c4,p.ui_skull_59c8],
           skills=list(k.id),menu=[t.type for t in menu.options]+[menu.scroll.type],
           current=[scroll,m.class_type,m.class_level,sel.character.race,list(m.perks),list(sel.character.flaws)],seeds=list(m.random.seeds),
           heartbeat=[bits(x) for x in (C.c_float*3).from_address(o.heartbeat)])
    if a!=n:
        (HERE/'startup_failure.json').write_text(json.dumps(dict(original=a,native=n),indent=2));raise AssertionError('startup_failure.json')
    print(json.dumps(dict(status='passed',function='Game::Game 0xdd9c, Game::Start(true) 0xb880',native='dr_session_create, dr_session_seed',
                          compared=sorted(a),stubbed=len(stubbed),original='Actual functions from their entries',
                          boundaries=['Game::SetupRenderer skipped','library stubs: new as a bump allocator, memset / memcpy / memmove performed, time() fixed, others return 0'])))

if __name__=='__main__':main()
