#!/usr/bin/env python3
"""Actual Game::SerialiseState 0x91c4 vs the native session's save (dr_session_save: dr_serialise_state, recovered_save)
on carried states of verify_session.py (T030-N5).

The original runs from its entry to its return with R0 = Game: CharacterClass::SerialiseGameState, Tile::Serialise,
Item::Serialise, Skill::Serialise, HelpMenu::Serialise, GetRandSeed and the Item** vector's size are original code;
Item::Serialise's QueueAchievement is recorded. Cases widen verify_session's carried states to every branch: tiles of
every type with their kind bytes (explosive / mana / acid potions, magic / broken swords and arrows, broken shields,
scroll special types), frozen and burning tiles with flame damage, skulls with enemy types and states, flag_25d and
poison lists of every length; record modes, the current class, the class's race / perks / flaws, items with up to 20
stats, 0..4 skills, names of every length, the save buffer's earlier content (the byte SerialiseState skips keeps it).
Compared: the save length, changed flag and bytes, and the achievements.
"""
import ctypes as C
import json
import random
from verify_session import CarriedSessionOriginal, CarriedSession, with_items, with_class, turn_case, SERIALISE, SAVE_BUFFER
from verify_stroke import HERE

SOURCE_SAVE=34

def case(rng):
    c=with_class(with_items(turn_case(rng),rng),rng)
    c['record']=rng.choice([0,0,1]);c['mode']=rng.randrange(3)
    for i,t in enumerate(c['board']):
        t['type']=rng.choice([0,0,1,1,1,2,3,3,4,4,5,6])
        t.update(magic_sword=0,broken=0,flag231=0,flag255=int(rng.random()<.15),flaming=int(rng.random()<.15),
                 flame_damage=rng.choice([0,3,40,255,300]),special=rng.randrange(6),enemy=rng.randrange(33) if t['type']==1 else 0,
                 enemy_state=rng.randrange(4))
        if t['type']==4:t.update(**{k:int(rng.random()<.3) for k in ('magic_sword','broken','flag231')})
        if t['type']==3:t['broken']=int(rng.random()<.3)
        c['preview']['potions'][i]=[int(rng.random()<.25) for _ in range(3)]
        cb=c['combat'][i];cb.update(attack=rng.randrange(-2,60),defence=rng.randrange(0,30),health=rng.randrange(-5,400),flag256=t['flaming'])
        n=rng.randrange(4);cb['poison'][:3]=[rng.randrange(1,40) for _ in range(n)]+[0]*(3-n)
        if rng.random()<.1:cb['poison'][:3]=[rng.randrange(0,40) for _ in range(3)]   # a zero before later values
        c['extras'][i]['max_health']=rng.randrange(0,500);c['match']['flag_25d'][i]=int(rng.random()<.3)
    m=c['match'];m['bonus_chance']=[rng.randrange(256) for _ in range(4)];m['perks']=[rng.choice([255,1,4,7,9]) for _ in range(4)]
    m['spawn_count_1555c']=rng.randrange(6);m['spawn_enabled_14ae0']=rng.randrange(4)
    c['game'].update(race=rng.randrange(10),flaws=[rng.choice([255,1,4,8]) for _ in range(4)])
    for it in c['k5']['items']:
        if rng.random()<.3:it['stats']=[rng.choice([0,1,5,-3,1000]) if rng.random()<.6 else 0 for _ in range(20)]
    r=c['resources'];r['skill_count']=rng.randrange(5)
    c['skill_id']=[rng.randrange(40) for _ in range(4)];c['skill_level']=[rng.randrange(4) for _ in range(4)]
    r['skill_max']=[rng.randrange(1,9) for _ in range(4)];r['skill_current']=[rng.randrange(0,9) for _ in range(4)]
    for k in range(4):
        if rng.random()<.15:r['skill_max'][k]=r['skill_current'][k]=-1   # no cooldown (saved as 255, loaded back as -1)
    r.update(xp=rng.randrange(100),total_xp=100*rng.randrange(40),up=rng.randrange(100),total_up=100*rng.randrange(40),
             gold=rng.randrange(100),total_gold=100*rng.randrange(40),poison=rng.randrange(256))
    c['path_state'].update(turn=rng.randrange(1000),total=rng.randrange(100000),crossing_samples=rng.randrange(500),
                           crossing_average=rng.randrange(50),crossing_best=rng.randrange(50))
    c['generation']['time_to_promotion']=rng.randrange(0,60)
    n=rng.choice([0,1,5,16,17]);c['name']=[rng.randrange(32,127) for _ in range(n)]
    c['previous_save']=bytes(rng.randrange(256) for _ in range(0x800)) if rng.random()<.5 else bytes(0x800)
    return c

def main():
    old,new=CarriedSessionOriginal(),CarriedSession();rng=random.Random(0x91c4);seen={};lengths=set();achievements=0
    lib=new.session_lib;lib.dr_session_save.argtypes=[C.c_void_p];lib.dr_session_save.restype=None
    for n in range(400):
        c=case(rng);old.load(c);new.load(c)
        old.u.mem_write(old.GAME+SAVE_BUFFER,c['previous_save']);C.memmove(C.addressof(new.save),c['previous_save'],0x800)
        u=old.u;old.save_achievements=[];u.reg_write(old.regs[0],old.GAME);u.reg_write(old.SP,0x140fe00);u.reg_write(old.LR,old.STOP|1)
        old.saving=True
        try:u.emu_start(SERIALISE|1,old.STOP,timeout=0,count=2000000);assert u.reg_read(old.PC)==old.STOP,hex(u.reg_read(old.PC))
        finally:old.saving=False
        new.sources={};lib.dr_session_save(new.session)
        a=[old.save_state(),old.save_achievements];b=[new.save_state(),[72]*new.sources.get((SOURCE_SAVE,1),0)]
        if a!=b:
            (HERE/'save_failure.json').write_text(json.dumps(dict(case=c,original=a,native=b),indent=2,default=lambda x:x.hex()))
            raise AssertionError('save_failure.json')
        lengths.add(a[0][0]);achievements+=len(a[1])
        for t in c['board']:seen[t['type']]=seen.get(t['type'],0)+1
    assert achievements>0 and len(lengths)>50,(achievements,len(lengths))
    report=dict(status='passed',cases=400,lengths=[min(lengths),max(lengths)],distinct_lengths=len(lengths),achievements=achievements,
                function=dict(symbol='__ZN4Game14SerialiseStateEv',address=hex(SERIALISE),native='dr_serialise_state (dr_session_save)'),
                original='Actual Game::SerialiseState from its entry with Tile / Item / Skill / HelpMenu / CharacterClass serialisers',
                boundaries=['QueueAchievement recorded'])
    print(json.dumps(report))

if __name__=='__main__':main()
