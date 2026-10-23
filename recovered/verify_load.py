#!/usr/bin/env python3
"""Actual Game::DeserialiseState 0x15c18 vs the native session's (dr_session_deserialise: dr_deserialise_state,
recovered_save) on carried states of verify_save.py (T030-N5).

Each case saves one state with the original Game::SerialiseState (verify_save.py checks those bytes), then loads a
different state into both sides and the saved bytes into their save buffers, and runs DeserialiseState over it. The
original runs from its entry to its return: DeserialiseState2, Tile::SetType (with the generation harness: colours,
UVs, texts, countdowns and enemy UVs recorded), Tile::Deserialise2 and the Make* / Set*Visibility / SetSpecialType /
UpdateValues functions, Item::Deserialise2 and ClearStats, Game::UpdateStats (as verify_session.py), Skill::Deserialise,
CharacterClass::DeserialiseGameState, SetRandSeed, HelpMenu::Deserialise, Game::SetHelpState and SetDifficulty are
original code; the interface updates, Upgrade::SetIcon, texts (Label::SetText, sprintf, strcpy, Item::MakeStats),
PositionSkill, UpdateSkills and GameMenu::SetHelpState are skipped. Some cases take older format versions (0..2: no
record mode / class / kill count, no broken-shield byte without a header) by rewriting the version byte. Compared:
the game state of verify_session.py (board, combat, resources, items, skills, stats, seeds ...) plus the resource values,
chances and stat counts, the current class record (race, perks, flaws, class type and level views), the name, the help
switch and the difficulty flag, and every random draw and tile event (colour, UV, text, countdown, enemy UV) of the load.
Each case also saves one state's class records with the original Game::SerialiseClasses (random replacement skills,
levels and progress; sometimes a count byte that is not 10) and restores them into another state: the original
Game::DeserialiseClasses and then Game::Start's SetCurrentClass(Game+0x1648c) vs dr_session_restore_classes, comparing
the ten records and the current class's views.
"""
import ctypes as C
import json
import random
from verify_session import SET_CURRENT, CarriedSessionOriginal, CarriedSession, SERIALISE, SAVE_BUFFER, NAME, I32, U8, DESERIALISE, HELP_SWITCH as HELP, DIFFICULTY_CHANGED, SERIALISE_CLASSES, CLASS_SAVE
from verify_release import CLASSES, CLASS_STRIDE, CLASS_INDEX_ADDR
from verify_save import case as save_case
from verify_stroke import HERE

# resource and stat fields DeserialiseState writes (beyond verify_session.py's game state)
VALUES=dict(level=0xbe4c,xp=0xbdb0,up=0xbdb4,gold=0xbdb8,total_xp=0xbe50,total_up=0xbe58,total_gold=0xbe54,ui_xp=0x599c,ui_up=0x59a0,
            ui_gold=0x59a4,poison=0x15540,shield_value=0xbe10,healing_value=0xbe08,base_damage=0xbdc0,be18=0xbe18,be20=0xbe20,be28=0xbe28,
            be30=0xbe30,bde8=0xbde8,bdf0=0xbdf0,bdf8=0xbdf8,be00=0xbe00)

class Original(CarriedSessionOriginal):
    def load(self,c):
        super().load(c);G=self.GAME;cur=self.read(G+CLASS_INDEX_ADDR)
        for i in range(10):   # only the current record holds the class's race / perks / flaws (the native records are fresh)
            if i!=cur:self.u.mem_write(G+CLASSES+CLASS_STRIDE*i+8,bytes(4));self.u.mem_write(G+CLASSES+CLASS_STRIDE*i+0x10,bytes(32))
    def extra_state(self):
        G=self.GAME;cur=self.read(G+CLASS_INDEX_ADDR);rec=G+CLASSES+CLASS_STRIDE*cur;i32=lambda a:C.c_int32(self.read(a)).value
        return dict(current=cur,race=i32(rec+8),perks=[i32(rec+0x10+4*k) for k in range(4)],flaws=[i32(rec+0x20+4*k) for k in range(4)],
                    name=bytes(self.u.mem_read(G+NAME,17)).hex(),help=self.u.mem_read(G+HELP,1)[0],changed=self.u.mem_read(G+DIFFICULTY_CHANGED,1)[0],
                    values={k:i32(G+a) for k,a in VALUES.items()})

DESERIALISE_CLASSES=0x8ea0
RECORD=dict(class_type=4,race=8,base_race=0xc,level=0x54,games_played=0x58,enemies_killed=0x5c,normal_score=0x60,hard_score=0x64,harder_score=0x68)
def records_original(old):
    G=old.GAME;out=[]
    for i in range(10):
        rec=G+CLASSES+CLASS_STRIDE*i;i32=lambda a:C.c_int32(old.read(a)).value
        r={k:(old.u.mem_read(rec+o,1)[0] if k=='level' else old.read(rec+o) if o>=0x58 else i32(rec+o)) for k,o in RECORD.items()}   # progress: unsigned
        r.update(perks=[i32(rec+0x10+4*k) for k in range(4)],flaws=[i32(rec+0x20+4*k) for k in range(4)],
                 replacement=[i32(old.read(rec+0x48)+4*k) for k in range(20)])
        out.append(r)
    return out
def records_native(new):
    out=[]
    for c in new.classes:
        r={k:getattr(c,k) for k in RECORD};r.update(perks=list(c.perks),flaws=list(c.flaws),replacement=list(c.replacement_skills[:20]))
        out.append(r)
    return out

class Native(CarriedSession):
    def load(self,c):
        super().load(c);self.lists=[(I32*20)(*([255]*20)) for _ in range(10)]   # replacement lists, as the original's (all 255)
        for cls,l in zip(self.classes,self.lists):cls.replacement_skills=C.cast(l,C.POINTER(I32));cls.replacement_skill_count=20
    def extra_state(self):
        o=self.session_lib.dr_session_objects(self.session);cur=self.scroll_state.current;c=self.classes[cur]
        settings=(U8*2).from_address(o.settings);sel=self.state.selection
        assert c.race==sel.character.race and list(c.perks)==list(self.m.perks) and list(c.flaws)==list(sel.character.flaws)
        return dict(current=cur,race=c.race,perks=list(self.m.perks),flaws=list(sel.character.flaws),
                    name=bytes((U8*17).from_address(o.name)).hex(),help=settings[0],changed=settings[1],
                    values={k:getattr(*self.value_targets()[k]) for k in VALUES})
    def value_targets(self):
        r,m,p,sel,x=self.r,self.m,self.p,self.state.selection,self.extra
        t={k:(r,k) for k in ('level','xp','up','gold','total_xp','total_up','total_gold','ui_xp','ui_up','ui_gold','poison')}
        t.update(shield_value=(p,'shield_value'),healing_value=(p,'healing_value'),base_damage=(sel,'base_damage'))
        class Item:
            def __init__(self,array,i):self.array,self.i=array,i
            def __getattr__(self,_):return self.array[self.i]
        for i,k in enumerate(('be20','be28','be18','be30')):t[k]=(Item(m.bonus_chance,i),'v')
        for i,k in enumerate(('bde8','bdf0','bdf8','be00')):t[k]=(Item(x.base_bde8,i),'v')
        return t

def older(saved,version):
    """The version-3 bytes in an older format: version < 3 lacks the record mode, total and crossing values; version < 2
    also the class, its game state, spawn_count_1555c and kill_count_165b4; version 0 (no header flag) the broken-shield
    byte of shield tiles."""
    b=bytes(saved);p=2;head=b[:2]
    record=b[p:p+11];p+=11;cls=b[p:p+28];p+=28
    types=[];nibbles=b[p:p+18];p+=18
    for x in nibbles:types+=[x>>4,x&15]
    tiles=[]
    for t in types:
        q=p;kind=b''
        if t in (0,4,3,6):kind=b[p:p+1];p+=1
        state=b[p];p+=1
        rest_start=p
        if state==2:p+=1
        if t==1:
            p+=19
            for k in range(3):
                v=b[p];p+=1
                if not v:break
        tiles.append((t,kind,b[q+len(kind):rest_start],b[rest_start:p]))
    turn=b[p:p+4];kills=b[p+4:p+8];p+=8;rest=b[p:]
    out=bytearray([0xff,version])
    if version>2:out+=record
    if version>1:out+=cls
    out+=nibbles
    for t,kind,state,tail in tiles:out+=(b'' if version==0 and t==3 else kind)+state+tail
    out+=turn+(kills if version>1 else b'')+rest
    return bytes(out)+bytes(0x800-len(out))

def case(rng):
    """verify_save.py's cases without tiles both frozen and burning: in play each clears the other, and such a tile's save
    has the flame byte that DeserialiseState does not read (it freezes the tile first), so the rest would be misread."""
    c=save_case(rng)
    for t,cb in zip(c['board'],c['combat']):
        if t['flag255']:t['flaming']=0;cb['flag256']=0
    return c

def main():
    old,new=Original(),Native();rng=random.Random(0x15c18);versions={}
    lib=new.session_lib;lib.dr_session_deserialise.argtypes=[C.c_void_p];lib.dr_session_deserialise.restype=C.c_bool
    lib.dr_session_restore_classes.argtypes=[C.c_void_p,C.c_char_p,C.c_uint32];lib.dr_session_restore_classes.restype=C.c_bool
    lib.dr_session_save_classes.argtypes=[C.c_void_p];lib.dr_session_save_classes.restype=None
    for n in range(300):
        a=case(rng);old.load(a);old.u.mem_write(old.GAME+SAVE_BUFFER,bytes(0x800))
        old.run_entry(SERIALISE,['saving']);saved=bytearray(old.u.mem_read(old.GAME+SAVE_BUFFER,0x800))
        version=rng.choice([3,3,3,3,2,1,0]);saved=bytearray(older(saved,version)) if version<3 else saved;versions[version]=versions.get(version,0)+1
        b=case(rng);old.load(b);new.load(b)
        old.u.mem_write(old.GAME+SAVE_BUFFER,bytes(saved));C.memmove(C.addressof(new.save),bytes(saved),0x800)
        old.gen_events=[];new.gen_events=[]
        old.run_entry(DESERIALISE,['loading','gen_active']);ok=lib.dr_session_deserialise(new.session);new.sync()
        old.class_current=True   # the loaded class (Game+0x1648c) is the current one: read its record (verify_session's match_status)
        x=[old.game_state(),old.extra_state(),old.gen_events];y=[new.game_state(),new.extra_state(),new.gen_events]   # with the draws and tile events
        if not ok or x!=y:
            (HERE/'load_failure.json').write_text(json.dumps(dict(version=version,original=x,native=y,ok=ok),indent=2,default=str))
            raise AssertionError('load_failure.json')
        # the class records' save of one state (with replacement skills, levels and progress changed): the original's and
        # the native's (dr_session_save_classes), then restored into another state
        a=case(rng);old.load(a);new.load(a)
        for i,cls in enumerate(new.classes):
            rec=old.GAME+CLASSES+CLASS_STRIDE*i;arr=old.read(rec+0x48)
            for k in range(20):v=rng.choice([255,255,rng.randrange(40)]);old.write(arr+4*k,v);cls.replacement_skills[k]=v
            for o,key in zip(range(0x58,0x6c,4),('games_played','enemies_killed','normal_score','hard_score','harder_score')):
                v=rng.randrange(0,1<<32);old.write(rec+o,v);setattr(cls,key,v)
            v=rng.randrange(11);old.u.mem_write(rec+0x54,bytes([v]));cls.level=v
        if rng.random()<.6:   # the units' race / perks / flaws changed in play (a Shapeshift): the native views only, the original's record
            cur=new.scroll_state.current;rec=old.GAME+CLASSES+CLASS_STRIDE*cur;sel=new.state.selection
            race=rng.randrange(10);old.write(rec+8,race);sel.character.race=race
            perks=[rng.choice([255,1,4,7,9]) for _ in range(4)];flaws=[rng.choice([255,1,4,8]) for _ in range(4)]
            for k in range(4):old.write(rec+0x10+4*k,perks[k]&0xffffffff);old.write(rec+0x20+4*k,flaws[k]&0xffffffff)
            new.m.perks=(I32*4)(*perks);sel.character.flaws=(I32*4)(*flaws)
        old.run_entry(SERIALISE_CLASSES,['classing']);classes=bytes(old.u.mem_read(old.GAME+CLASS_SAVE,472))
        lib.dr_session_save_classes(new.session);new.sync()
        x=[old.save_state()[3:],records_original(old),old.extra_state(),old.game_state()];y=[new.save_state()[3:],records_native(new),new.extra_state(),new.game_state()]
        if x!=y:
            (HERE/'load_failure.json').write_text(json.dumps(dict(stage='serialise classes',original=x,native=y),indent=2,default=str))
            raise AssertionError('load_failure.json (serialise classes)')
        if rng.random()<.1:classes=classes[:1]+bytes([9])+classes[2:]   # not ten records: nothing read
        b=case(rng);old.load(b);new.load(b);old.u.mem_write(old.GAME+CLASS_SAVE,classes)
        old.run_entry(DESERIALISE_CLASSES,[]);ok=lib.dr_session_restore_classes(new.session,classes,472);new.sync()
        if classes[1]==10:   # then Game::Start's SetCurrentClass(Game+0x1648c) (T040-N1: the native restore makes it too)
            old.u.reg_write(old.regs[1],old.read(old.GAME+CLASS_INDEX_ADDR));old.run_entry(SET_CURRENT[0],[])
        x=[records_original(old),old.extra_state()];y=[records_native(new),new.extra_state()]
        if ok!=(classes[1]==10) or x!=y:
            (HERE/'load_failure.json').write_text(json.dumps(dict(stage='classes',original=x,native=y,ok=ok),indent=2,default=str))
            raise AssertionError('load_failure.json (classes)')
    report=dict(status='passed',cases=300,versions={str(k):v for k,v in sorted(versions.items())},
                function=dict(symbol='__ZN4Game16DeserialiseStateEv',address=hex(DESERIALISE),native='dr_deserialise_state (dr_session_deserialise)'),
                original='Actual Game::DeserialiseState from its entry over a different loaded state, with the saved bytes of Game::SerialiseState',
                classes='Actual Game::DeserialiseClasses with the bytes of Game::SerialiseClasses, every case',
                boundaries=['interface updates, icons and texts skipped; the generation harness records tile colours / UVs / texts'])
    print(json.dumps(report))

if __name__=='__main__':main()
