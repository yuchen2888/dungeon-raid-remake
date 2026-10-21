#!/usr/bin/env python3
"""The native session (recovered_session) against the original, frame by frame (T040-G2).

The native side is one C++ session: its objects are loaded with the case (the harness loaders fill ctypes
objects, which are copied into the session's objects and linked), then dr_session_new_game and one
dr_session_frame per frame run every unit with the session's own wiring -- no Python callback takes part in
the play. The harness reads the state from the session's memory. Four phases:
- new games as verify_new_game_play.py (T040-F4): original InitNewGame, then the whole original
  Game::Process every frame; some games weakened (they end early), some strengthened (long games);
- carried mid-game states as verify_game_frames.py (T040-F3): random boards with every enemy type, flags,
  poison and abilities, a few turns each;
- skills (T040-H6): carried states with equipped skills (every type; the last games PromoteNormalEnemy in every slot), where most turns press a skill button (touch down, then
  release on it or elsewhere) and some path turns press one while the turn still runs (input not ready).
  The original runs Interface::Process's Interface::ProcessInput (input ready, no menu open) with Skill::
  Activate, FireBreath and the Game skill functions as original code: Interface::CursorInButton answers the
  frame's button, Quad::ContainsPoint (menu buttons) no; sounds, achievements, button colours, tooltips,
  UpdateSkills, PositionSkill, arrow colour, enemy UV and text skipped; AddFlare / AddParticles /
  AddSimpleLabel apply their stream-0 draws; SetType, the generation skills, SwapTiles / MoveMatchedTiles,
  JumpDown and ExplodeArmour with the harnesses of verify_skill_board*.py / verify_abilities.py /
  verify_encounters.py. The equipped skills (type, level, active, cooldowns, in slot order) are compared too.
- items (T040-K5): carried states where race 6 draws a path of 15+ plain skulls (Item::IncreaseStat) or enemies
  28 are one turn from their ability (Game::DestroyUpgrade).
Every case has five equipped items (Game+0xbe88.., the Item** vector Game+0xbe9c) and the fields Game::UpdateStats
writes; InitNewGame's Item(Game, type) (Item::InitialiseNames run once beforehand), UpdateStats, IncreaseStat and
DestroyUpgrade run as original code (their interface refreshes, item text, icons and sounds skipped, std::vector<int>
modelled, DestroyUpgrade's label applying its stream-0 draw); the items and those fields are compared too.
Menus (T040-K5b): Interface::ShowMenu runs FoldoutMenu::Initialise as original code (std::set<int> / std::set<ItemType>
/ std::vector<int> modelled, the ten classes' base and replacement skill arrays written to the class objects; interface,
text and tooltips skipped); while it is open Interface::Process runs FoldoutMenu::Process instead (CursorInButton /
CursorInQuad answer the frame's menu button; SetSkill, SetItem, Item::AddUpgrade and UpdateStats as original code, the
bought scroll's Skill::Activate as for the skill buttons). In play a menu waits for its opening animation, takes a few
random taps, then a choice (two on the level-up menu) and the confirm until the closing animation ends; the menu state
is compared too (the upgrade plans only while the upgrade menu is the current one). The item and skill phases draw the
current class (Game+0x1648c) from 0..9 (with_class): the menus' skill pools and the class fields Game::MatchTile reads
(type, level, race) follow it.
The original side is the F4 / F3 harness, except that the functions the session wires itself from unit events
(SetSpecialType, Shapeshift, Healing, ProcessPretzels, CheckEndGame in the units, InialiseShieldShatter) run as
original code instead of the unit harnesses' adapters (OriginalMixin); carried-state variants make them occur.

Compared after the start and after every frame: the game state of verify_game_frames.py plus the stroke's
resource counts (Game+0x164b0), without the event
lists (the units' events are compared by the unit tests; the session forwards them unchanged) and without
the flare / quad alpha mirrors (presentation the renderer keeps from those events).
"""
import ctypes as C
import json
import random
import re
import struct
import verify_original
from verify_new_game_play import Original as NewGameOriginal, Native as NewGameNative, case
from verify_game_frames import Original as FramesOriginal, Native as FramesNative
from verify_full_turn import case as turn_case
from verify_full_turn import f32
from verify_stroke import HERE, I32, U8, Point, State as Stroke
from verify_motion import Motion, target as motion_target
from verify_abilities import TARGET_POINT
from verify_tokens import Counters
from verify_resources import INTS as RESOURCE_INTS
from verify_match import RandomState
from verify_release import CLASSES,CLASS_STRIDE,CLASS_INDEX_ADDR

GAMES,TURNS,LONG_TURNS=9,12,40
CARRIED_GAMES,CARRIED_TURNS=15,5
ITEM_GAMES=10
SKILL_GAMES,SKILL_TURNS,PROMOTE_GAMES=62,6,12   # the last games: PromoteNormalEnemy in every slot (an enemy 31 jumps down)
BUTTON_TOUCH=[5.0,5.0]   # a skill button: no tile under the touch
# carried-state variants that reach the functions the session wires from unit events (and checks below)
def variant(c,game):
    kind=game%5
    if kind==0:c['game']['race']=9                                         # killing a special enemy: Shapeshift
    elif kind==1:c['game']['race']=4;c['resources'].update(xp=99,ui_xp=99,health=3,ui_health=3,health_max=400)  # level up: Healing (raises low health)
    elif kind==2:c['record']=1;c['mode']=1                                  # record mode 1: ProcessPretzels
    elif kind==3:c['match'].update(spawn_enabled_14ae0=max(1,c['match']['spawn_enabled_14ae0']),spawn_remaining_15558=1,spawn_count_1555c=0)  # class scroll: SetSpecialType
    else:c['game']['race']=5                                                 # mortal enemy 12 generated: InialiseShieldShatter
    return c
def with_class(c,rng):
    """T040-K5b: a current class drawn from 0..9 (the menus' skill pools). The harness loaders write the current class's
    record (race, perks, flaws) at index 0: the roster's class 0 moves to the drawn index and class 0 becomes another
    class; the original's record 0 is copied there after loading (OriginalMixin.load)."""
    sc=c['release']['scroll'];k=rng.randrange(10)
    if k:
        roster=sc['classes'];roster[k]=list(roster[0])
        roster[0]=[(roster[k][0]+rng.randrange(1,10))%10,rng.randrange(10),rng.choice([0,1,5,10])]
    sc['current']=k;return c
def skill_variant(c,rng,game):
    """Equipped skills, every type in turn (four per game; the slot order rotates every ten games, so each type also
    sits in the slots only reached with three or four skills), most cooldowns ready."""
    count=rng.choice([2,3,4,4,4]);r=c['resources'];r['skill_count']=count
    c['skill_id']=[SKILL_TYPES[(4*game+(i+game//10)%4)%len(SKILL_TYPES)] for i in range(4)];c['skill_level']=[rng.randrange(0,4) for _ in range(4)];c['skill_active']=[0]*4
    r['skill_max']=[rng.randrange(1,6) for _ in range(4)]
    r['skill_current']=[m if rng.random()<.85 else rng.randrange(0,m) for m in r['skill_max']]
    if game>=SKILL_GAMES-PROMOTE_GAMES:r['skill_count']=4;c['skill_id']=[23]*4;r['skill_max']=r['skill_current']=[1]*4
    return c
# (unit, event kind) the session acts on, required to occur: Selection ProcessPretzels, Match SetSpecialType / Shapeshift,
# Resource Healing (the Stab / thrown-skull CheckEndGame and ShieldShatter depend on chance: see events_by_unit_kind)
REQUIRED={(1,15),(2,8),(2,9),(5,11)}
NAMES=('stroke','preview','match','rune','tokens','resources','path','refill','generation','damage','animation','overlay_alpha',
       'attack_inputs','skills','turn_flags','finish','end','activated','end_of_turn','flights','release_inputs','classes','scroll',
       'player','extra','shatter','touch','screens','input_target','current_label_active','motions')
class Objects(C.Structure):
    _fields_=[(k,C.c_void_p) for k in NAMES]+[('motion_count',C.c_uint32),('falling',C.c_void_p),('falling_count',C.c_uint32),
              ('skill_button',C.c_void_p),('skill_input',C.c_void_p),('items',C.c_void_p),('menu',C.c_void_p),('menu_button',C.c_void_p),('dimmed',C.c_void_p)]
EVENT=C.CFUNCTYPE(None,C.c_void_p,I32,C.c_void_p)
TARGET=C.CFUNCTYPE(None,C.c_void_p,I32,I32,C.POINTER(Point))
CHOOSE=C.CFUNCTYPE(I32,C.c_void_p,C.POINTER(Motion))
START=C.CFUNCTYPE(None,C.c_void_p,I32,C.POINTER(Point))
class Host(C.Structure):_fields_=[('context',C.c_void_p),('event',EVENT),('target',TARGET),('choose',CHOOSE),('start',START)]
SOURCE_GENERATION,SOURCE_NEW_GAME,SOURCE_SKILL,SKILL_USED,SKILL_FLAME,SKILL_JUMP=8,28,31,17,16,13   # SkillEventKind UpdateSkills: a skill used; FlameVisibility: FireBreath; JumpDown

SCREEN_INIT=0x307f8   # GameOverScreen::Initialise
SPECIAL,SHAPESHIFT,SHAPESHIFT_END,HEALING,PRETZELS,CHECK_END=0x3f43c,0x918c,0x91c4,0x12e68,0xd03c,0x10b18
SHATTER_INIT,SHATTER_INIT_END=0x9810,0x9882
ADD_FLARE,FLARE_COUNT,SEEDS=0x9f94,0xbd8c,0x1eac20
ADD_PARTICLES,ADD_LABEL,ADD_TILE_LABEL=0xa914,0xae2c,0xb130
CROSS,CROSS_END,CROSS_POOL,CROSS_INDEX,CROSS_SCRATCH=0xaa24,0xae2c,0x164c8,0x164d4,0x3000000
# Interface::Process (from Game::Process): Interface::ProcessInput's skill buttons with input ready and no menu open
IFACE_PROCESS,IFACE_INPUT,IFACE_INPUT_END,INTERFACE,MENUS=0x20c64,0x209e4,0x20c4e,0x4cdc,(0x59f4,0x5b0c,0x5b9c)
PROCESS,PROCESS_END,SKILL_OBJECTS,SWAP_TILES,MOVE_MATCHED,JUMP_DOWN=0x1717c,0x17db8,0x1700000,0xb494,0x10ed8,0xb5c4
SKILL_SKIP=('__ZN4Game10QueueSoundE5Sound','__ZN4Game16QueueAchievementE11Achievementf','__ZN4Quad9SetColourERK9GLcolour4',
            '__ZN7Tooltip4ShowE9SkillTypeiiRK8GLfloat2','__ZN7Tooltip4HideEv','__ZN9Interface12UpdateSkillsEv','__ZN9Interface13PositionSkillEi',
            '__ZN5Arrow9SetColourEjjj','__ZN4Tile13UpdateEnemyUVEv','__ZN4Tile10UpdateTextEbbb')
# board skill functions run with the generation harness on (verify_skill_board*.py): FreezeSkulls, ConvertTiles,
# CreateManaPotions, CreateExplosivePotions, CreateArrows, CreateMagicSword, DemoteSpecialEnemy, PromoteNormalEnemy;
# ExplodeArmour with the path harness
GEN_SKILLS,PATH_SKILLS=(0xa470,0xa7f4,0xa548,0xa380,0xcdac,0xccc0,0xa6f4,0xb648),(0x115dc,)
SKILL_TYPES=list(range(40))   # 10 Upgrade opens the upgrade menu
CROSS_SKIP=('__ZNKSt6vectorI11SimpleLabelSaIS0_EE4sizeEv','__ZN11SimpleLabelC1Ev','__ZNSt6vectorI11SimpleLabelSaIS0_EE9push_backERKS0_',
            '__ZN11SimpleLabelD1Ev','__ZN11SimpleLabel15RegenerateLabelEv','__ZN11SimpleLabel9SetColourEi')
EFFECTS=C.CDLL(str(HERE/'recovered_attack_shield_native.dylib'))
for _f in (EFFECTS.dr_add_particles,EFFECTS.dr_add_simple_label):_f.argtypes=[C.POINTER(RandomState),I32];_f.restype=None
RANDOM=C.CDLL(str(HERE/'recovered_random_native.dylib'));RANDOM.dr_random_float.argtypes=[C.POINTER(RandomState),C.c_float,C.c_float,C.c_uint32]
RANDOM.dr_random_float.restype=C.c_float
# T040-K5: the equipped items and the fields Game::UpdateStats writes
from verify_stats import PlayerStats, PLAYER, UI, INTS as STATS_INTS, FLOATS as STATS_FLOATS
ITEM_SPACE,ITEM_OBJECTS,ITEM_ALLOC,VEC_DATA=0x3200000,0x32c0000,0x32d0000,0x32f0000
NAMES_FN,ITEM_CTOR,UPDATE_STATS,DESTROY,INCREASE=0x26acc,0x2a5ac,0x14c04,0x1515c,0x29d58
NEW_STUB,DELETE_STUB,MEMMOVE=0x194d54,0x194d4c,0x194ef4
ITEM_FIELDS=((0x80,'type'),(0x84,'icon'),(0x88,'prefix_level'),(0x8c,'prefix'),(0x90,'name'))
class ItemRecord(C.Structure):_fields_=[(k,I32) for _,k in ITEM_FIELDS]+[('stats',I32*20)]
STATS_SKIP=('__ZN9Interface15UpdateHealthBarER4Quadi','__ZN9Interface16UpdateSwordValueEv','__ZN9Interface16UpdateSkullValueEv',
            '__ZN9Interface17UpdateShieldValueEv','__ZN9Interface12UpdateSkillsEv','__ZN4Item9MakeStatsEv','__ZN4Game16QueueAchievementE11Achievementf',
            '__ZN4Game10QueueSoundE5Sound','__ZN7Upgrade7SetIconEiiii')
VECTOR_OPS={'__ZNSt6vectorIiSaIiEE9push_backERKi':'push','__ZNKSt6vectorIiSaIiEE4sizeEv':'size','__ZNSt6vectorIiSaIiEED2Ev':'free'}
def with_items(c,rng):
    """The equipped items and the UpdateStats fields of a case (new games make their own items)."""
    def item(t):
        st=[0]*20
        for j in rng.sample(range(20),rng.randrange(1,6)):st[j]=rng.choice([1,2,3,5,10,rng.randrange(0,20)])
        return dict(type=t,icon=rng.randrange(400),prefix_level=rng.choice([-1,0,5]),prefix=rng.randrange(-1,148),name=rng.randrange(20),stats=st)
    f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
    stats={k:rng.randrange(0,20) for k in STATS_INTS if k not in ('health','health_max','health_bonus','ui_health','ui_armour','armour_current','base_damage')}
    stats.update({k:f32(rng.choice([0,0.5,1.0])) for k in STATS_FLOATS},cooldown=0)
    c['k5']=dict(items=[item(i) for i in range(5)],stats=stats)
    return c
# T040-K5b: FoldoutMenu (Interface+0xd10) as original code
from verify_menu_level import MenuState, OPTION_INTS, OPTION_CHANCES, SET_OPS, SKIP as MENU_SKIP_SYMBOLS, BASE as CLASS_BASE
SHOW_MENU,FM_INIT,FM_PROCESS,FM=0x1eb20,0x24a54,0x23c44,0x4cdc+0xd10
MENU_OBJECTS,CLASS_ARRAYS,SET_NODES_K5=0x3280000,0x3290000,0x32a0000
ITEM_SET_OPS={'__ZNSt8_Rb_treeI8ItemTypeS0_St9_IdentityIS0_ESt4lessIS0_ESaIS0_EE13_Rb_tree_implIS4_Lb0EEC2ERKSaISt13_Rb_tree_nodeIS0_EERKS4_':'init',
              '__ZNSt3setI8ItemTypeSt4lessIS0_ESaIS0_EE6insertERKS0_':'insert',
              '__ZNSt8_Rb_treeI8ItemTypeS0_St9_IdentityIS0_ESt4lessIS0_ESaIS0_EE5eraseESt23_Rb_tree_const_iteratorIS0_E':'erase_node',
              '__ZNSt8_Rb_treeI8ItemTypeS0_St9_IdentityIS0_ESt4lessIS0_ESaIS0_EE8_M_eraseEPSt13_Rb_tree_nodeIS0_E':'clear'}
MENU_SKIP=MENU_SKIP_SYMBOLS+['__ZN11ItemUpgrade14WriteStatFloatEPKcP4Item','__ZN11ItemUpgrade16WriteStatPercentEPKcP4Item',
          '__ZN11ItemUpgrade12WriteStatIntEPKcP4Item','__ZN11ItemUpgrade14GetDescriptionEv','__ZN11ItemUpgrade8GetStatsEv',
          '__ZN11FoldoutMenu15HighlightButtonEiib','__ZN4Menu13SetQuadColourEihhhh','__ZN4Quad9SetColourERK9GLcolour4',
          '__ZN7Tooltip10ShowScrollE9SkillTypeRK8GLfloat2','__ZN9Interface13PositionSkillEi']
class OriginalMixin:
    """The F4 original, where the functions the session wires itself run as original code instead of the unit
    harnesses' adapters: SetSpecialType (with the generation harness on), Shapeshift, Healing, ProcessPretzels
    (std::set modelled by the path harness), CheckEndGame from the resource and encounter units (end-of-game
    harness on) and InialiseShieldShatter. Their presentation calls are skipped (UpdateSkills, chunk alphas)."""
    def __init__(self):
        super().__init__()
        self.match_calls={k:v for k,v in self.match_calls.items() if k not in (SPECIAL,SHAPESHIFT)}
        self.extra={k:v for k,v in self.extra.items() if k!=PRETZELS}
        self.resource_calls={k:v for k,v in self.resource_calls.items() if v not in ('end','healing')}
        self.enc_calls={k:v for k,v in self.enc_calls.items() if v!='end'}
        self.gen_calls={k:v for k,v in self.gen_calls.items() if v!='shatter'}
        text=(HERE.parent/'armv7-disassembly.txt').read_text()
        addr=lambda sym:int(re.search(r'^'+re.escape(sym)+r':\n\s*([0-9a-f]+):',text,re.M)[1],16)
        self.update_skills=addr('__ZN9Interface12UpdateSkillsEv');self.quad_alpha=addr('__ZN4Quad8SetAlphaEh');self.returns={}
        # Game::UpdateCrossVisibility runs as original code (verify_cross.py), its cross-label storage skipped
        self.boundaries={k:v for k,v in self.boundaries.items() if v!='cross'}
        self.release_calls={k:v for k,v in self.release_calls.items() if v!='cross'}
        self.u.mem_map(CROSS_SCRATCH,0x200000);self.cross_return=None
        self.cross_skip={addr(n):n for n in CROSS_SKIP};self.cross_skip.update({a:'stub' for a in (0x194cec,0x194cf0,0x194cf4)})
        self.skill_skip={addr(n) for n in SKILL_SKIP};self.skill_input=False;self.button=-1;self.set_type_return=None
        self.cursor=addr('__ZN9Interface14CursorInButtonEi');self.contains=addr('__ZN4Quad13ContainsPointERK8GLfloat2')
        self.set_type=addr('__ZN4Tile7SetTypeE8TileTypeii')
        self.overlay_quad={addr(q) for q in ('__ZN4Quad7SetSizeERK8GLfloat2','__ZN4Quad5SetUVERK8GLfloat2S2_','__ZN4Quad8SetAlphaEh')}
        # T040-K5: items, UpdateStats, Item::IncreaseStat and DestroyUpgrade run as original code
        self.u.mem_map(ITEM_SPACE,0x100000);self.heap=ITEM_SPACE;self.naming=False;self.names_ready=False;self.stats_running=False
        self.item_allocs=0;self.int_vectors_k5={}
        self.release_calls={k:v for k,v in self.release_calls.items() if v not in ('increase_stat','update_stats')}
        self.abilities={}   # Game::DestroyUpgrade (enemy 28)
        self.stats_skip={addr(n) for n in STATS_SKIP};self.vector_ops={addr(n):v for n,v in VECTOR_OPS.items()}
        # T040-K5b: the menus
        self.resource_calls={k:v for k,v in self.resource_calls.items() if v!='menu'}   # Interface::ShowMenu runs
        self.menu_running=False;self.menu_button=-1;self.k5_sets={}
        self.menu_skip={addr(n) for n in MENU_SKIP};self.string_vector_size=addr('__ZNKSt6vectorISsSaISsEE4sizeEv')
        self.menu_set_ops={addr(n):v for n,v in SET_OPS.items()};self.menu_set_ops.update({addr(n):v for n,v in ITEM_SET_OPS.items()})
        self.fm_cursor=addr('__ZN11FoldoutMenu14CursorInButtonEi');self.fm_quad=addr('__ZN11FoldoutMenu12CursorInQuadEi')
        self.skill_activate=addr('__ZN5Skill8ActivateEv')
        assert addr('__ZN9Interface8ShowMenuE8MenuType')==SHOW_MENU and addr('__ZN11FoldoutMenu7ProcessEf')==FM_PROCESS
        assert addr('__ZN4ItemC1EP4Game8ItemType')==0x2a6bc and addr('__ZN4Game11UpdateStatsEv')==UPDATE_STATS and addr('__ZN4Game14DestroyUpgradeEP4Tile')==DESTROY
        assert addr('__ZN9Interface7ProcessEfb')==IFACE_PROCESS and addr('__ZN9Interface12ProcessInputEv')==IFACE_INPUT
        assert addr('__ZN4Game15ProcessPretzelsEv')==PRETZELS and addr('__ZN4Game12CheckEndGameEv')==CHECK_END
    def until_return(self,u,flag,value=True):
        lr=u.reg_read(self.LR)&~1;old=getattr(self,flag,False);setattr(self,flag,value)
        self.returns.setdefault(lr,[]).append(lambda:setattr(self,flag,old))
    def hook(self,u,address,size,context):
        for undo in self.returns.pop(address,[]):undo()
        lr=u.reg_read(self.LR)&~1
        if self.naming:   # Item::InitialiseNames: its vectors on a bump heap
            if address==NEW_STUB:n=u.reg_read(self.regs[0]);u.reg_write(self.regs[0],self.heap);self.heap+=(n+15)&~15;u.reg_write(self.PC,lr|1);return
            if address==DELETE_STUB:u.reg_write(self.PC,lr|1);return
            if address==MEMMOVE:
                d,src,n=(u.reg_read(self.regs[i]) for i in range(3));u.mem_write(d,bytes(u.mem_read(src,n)));u.reg_write(self.PC,lr|1);return
            return
        if address in (0x2a6bc,UPDATE_STATS) and getattr(self,'initialising',False):   # InitNewGame's items and stats: recorded, then run
            r=[u.reg_read(v) for v in self.regs]
            if address==0x2a6bc:self.new_events.append([10,-1,self.items_made,C.c_int32(r[2]).value]);self.items_made+=1
            else:self.new_events.append([11,-1,0,0])
            self.until_return(u,'stats_running');self.until_return(u,'gen_active',False);return   # not the generation harness's draws
        if address==NEW_STUB and getattr(self,'initialising',False):   # the new items' memory
            u.reg_write(self.regs[0],ITEM_ALLOC+0x200*self.item_allocs);self.item_allocs+=1;u.reg_write(self.PC,lr|1);return
        if address in (UPDATE_STATS,DESTROY,INCREASE) and not self.stats_running:self.until_return(u,'stats_running')
        if self.stats_running:
            r=[u.reg_read(v) for v in self.regs]
            if address in self.stats_skip or address in (0x194fb0,0x194f60):u.reg_write(self.PC,lr|1);return
            vop=self.vector_ops.get(address)
            if vop:
                if vop=='push':
                    vals=self.int_vectors_k5.setdefault(r[0],[]);vals.append(C.c_int32(self.read(r[1])).value)
                    base=VEC_DATA+0x400*list(self.int_vectors_k5).index(r[0])
                    for k,v in enumerate(vals):self.write(base+4*k,v&0xffffffff)
                    self.write(r[0],base);self.write(r[0]+4,base+4*len(vals));self.write(r[0]+8,base+0x400)
                elif vop=='size':u.reg_write(self.regs[0],len(self.int_vectors_k5.get(r[0],[])))
                else:self.int_vectors_k5.pop(r[0],None)
                u.reg_write(self.PC,lr|1);return
            if address==ADD_LABEL:   # DestroyUpgrade's label: its stream-0 draw
                seeds=RandomState((C.c_uint32*6)(*struct.unpack('<6I',u.mem_read(SEEDS,24))))
                EFFECTS.dr_add_simple_label(C.byref(seeds),C.c_int32(r[1]).value);u.mem_write(SEEDS,struct.pack('<6I',*seeds.seeds))
                u.reg_write(self.PC,lr|1);return
            if address in (0x194cec,0x194cf0,0x194cf4):u.reg_write(self.PC,lr|1);return
        if address==SPECIAL:self.until_return(u,'gen_active')
        elif address==PRETZELS:self.int_sets={};self.until_return(u,'path_active')
        elif address==CHECK_END and not self.recording:self.until_return(u,'recording')
        elif address==self.update_skills and SHAPESHIFT<lr<SHAPESHIFT_END:u.reg_write(self.PC,lr|1);return
        elif address==self.quad_alpha and SHATTER_INIT<lr<SHATTER_INIT_END:u.reg_write(self.PC,lr|1);return
        if address==SHOW_MENU and not self.menu_running:self.until_return(u,'menu_running');self.until_return(u,'skill_input',False)   # (Game::Upgrade from a skill)
        if address==IFACE_PROCESS and PROCESS<=lr<PROCESS_END and u.mem_read(self.GAME+0x59f4,1)[0]:   # an open FoldoutMenu: its Process
            u.reg_write(self.regs[0],self.GAME+FM);self.until_return(u,'menu_running');u.reg_write(self.PC,FM_PROCESS|1);return
        if self.menu_running and not self.skill_input:
            r=[u.reg_read(v) for v in self.regs];s=lambda v:C.c_int32(v).value
            op=self.menu_set_ops.get(address)
            if op:
                if op=='init':self.k5_sets[r[0]]=set();self.k5_write_set(r[0])
                elif op=='insert':self.k5_sets.setdefault(r[1],set()).add(s(self.read(r[2])));self.k5_write_set(r[1])
                elif op=='erase':
                    k=s(self.read(r[1]));had=k in self.k5_sets.setdefault(r[0],set());self.k5_sets[r[0]].discard(k);self.k5_write_set(r[0]);u.reg_write(self.regs[0],int(had))
                elif op=='erase_node':self.k5_sets.setdefault(r[0],set()).discard(s(self.read(r[1]+16)));self.k5_write_set(r[0])
                elif op=='clear':self.k5_sets[r[0]]=set();self.k5_write_set(r[0])
                else:self.k5_sets[r[0]]=set(self.k5_sets.get(r[1],set()));self.k5_write_set(r[0])
                u.reg_write(self.PC,lr|1);return
            if address==0x194d30:u.reg_write(self.regs[0],self.read(r[0]));u.reg_write(self.PC,lr|1);return   # _Rb_tree_increment: the node list
            if address==self.string_vector_size:u.reg_write(self.regs[0],0);u.reg_write(self.PC,lr|1);return   # the option text lines
            if address==self.fm_cursor:u.reg_write(self.regs[0],int(s(r[1])==self.menu_button));u.reg_write(self.PC,lr|1);return
            if address==self.fm_quad:u.reg_write(self.regs[0],int(s(r[1])==7 and self.menu_button==7));u.reg_write(self.PC,lr|1);return
            if address in self.menu_skip or address in self.stats_skip or address in (0x194fb0,0x194f60,0x194cec,0x194cf0,0x194cf4):
                u.reg_write(self.PC,lr|1);return
            vop=self.vector_ops.get(address)
            if vop:
                if vop=='push':
                    vals=self.int_vectors_k5.setdefault(r[0],[]);vals.append(s(self.read(r[1])))
                    base=VEC_DATA+0x400*list(self.int_vectors_k5).index(r[0])
                    for k,v in enumerate(vals):self.write(base+4*k,v&0xffffffff)
                    self.write(r[0],base);self.write(r[0]+4,base+4*len(vals));self.write(r[0]+8,base+0x400)
                elif vop=='size':u.reg_write(self.regs[0],len(self.int_vectors_k5.get(r[0],[])))
                else:self.int_vectors_k5.pop(r[0],None)
                u.reg_write(self.PC,lr|1);return
            if address==self.skill_activate:   # the bought scroll: Skill::Activate with the skill hooks of the skill buttons
                self.write(r[0]+0x7c,self.GAME);self.until_return(u,'skill_input')
        if address==IFACE_PROCESS and PROCESS<=lr<PROCESS_END:   # the skill buttons run as original code (verify_skill_input.py)
            G=self.GAME
            if u.reg_read(self.regs[2])&0xff and not any(u.mem_read(G+a,1)[0] for a in MENUS):
                self.write(G+INTERFACE+0x1030,G);self.until_return(u,'skill_input');u.reg_write(self.PC,IFACE_INPUT|1);return
            u.reg_write(self.PC,lr|1);return
        if self.skill_input:
            r=[u.reg_read(v) for v in self.regs]
            if address==self.cursor:u.reg_write(self.regs[0],int(C.c_int32(r[1]).value==self.button));u.reg_write(self.PC,lr|1);return
            if address==self.contains and IFACE_INPUT<lr<IFACE_INPUT_END:u.reg_write(self.regs[0],0);u.reg_write(self.PC,lr|1);return   # menu buttons
            if address in self.skill_skip:u.reg_write(self.PC,lr|1);return
            if address==self.set_type and not self.gen_active:self.until_return(u,'gen_active')   # Tile::SetType with the generation harness
            if address in self.overlay_quad and (0x3d89c<=lr<0x3d9a4):return   # Set{Flame,Freeze}Visibility's overlay quads run as original code
            if address in GEN_SKILLS:self.until_return(u,'gen_active')
            elif address in PATH_SKILLS:self.until_return(u,'path_active')
            if address==JUMP_DOWN:   # a promoted enemy 31 jumps down: with the encounter harness (verify_encounters.py)
                for flag in ('enc_active','refill_active'):self.until_return(u,flag)
            if address in (SWAP_TILES,MOVE_MATCHED):   # SwapTiles / MoveMatchedTiles with the refill / generation / encounter harnesses (as verify_abilities.py)
                for flag in ('refill_active','gen_active','enc_active'):self.until_return(u,flag)
                self.until_return(u,'path_active',False)   # not ExplodeArmour's path harness
            if address==ADD_FLARE:self.effect_draw(0,0.0,360.0);self.write(self.GAME+FLARE_COUNT,self.read(self.GAME+FLARE_COUNT)+1);u.reg_write(self.PC,lr|1);return
            if address in (ADD_PARTICLES,ADD_LABEL,ADD_TILE_LABEL):
                seeds=RandomState((C.c_uint32*6)(*struct.unpack('<6I',u.mem_read(SEEDS,24))))
                if address==ADD_PARTICLES:EFFECTS.dr_add_particles(C.byref(seeds),C.c_int32(r[2]).value)
                else:EFFECTS.dr_add_simple_label(C.byref(seeds),C.c_int32(r[1]).value if address==ADD_LABEL else 0)
                u.mem_write(SEEDS,struct.pack('<6I',*seeds.seeds));u.reg_write(self.PC,lr|1);return
        if address==CROSS:   # the labels it initialises (pool + cursor * 0x358, the cursor wrapping) land in scratch pages until it returns
            G=self.GAME;self.cross_return=(u.reg_read(self.LR)&~1,self.read(G+CROSS_POOL));cursor=self.read(G+CROSS_INDEX);assert cursor<0x400,cursor
            self.write(G+CROSS_POOL,(CROSS_SCRATCH+0x100000-cursor*0x358)&0xffffffff)
        elif self.cross_return and address==self.cross_return[0]:self.write(self.GAME+CROSS_POOL,self.cross_return[1]);self.cross_return=None
        if address in self.cross_skip and CROSS<lr<CROSS_END:
            if 'size' in self.cross_skip[address]:u.reg_write(self.regs[0],0x7fffffff)   # the pool is never full
            u.reg_write(self.PC,u.reg_read(self.LR));return
        if address==ADD_FLARE:   # the harnesses adapt Game::AddFlare; its game state (verify_add_flare.py) is applied here
            G=self.GAME;count=self.read(G+FLARE_COUNT);result=super().hook(u,address,size,context)
            if (u.reg_read(self.PC)&~1)!=ADD_FLARE:
                seeds=RandomState((C.c_uint32*6)(*struct.unpack('<6I',u.mem_read(SEEDS,24))))
                RANDOM.dr_random_float(C.byref(seeds),0.0,360.0,0);u.mem_write(SEEDS,struct.pack('<6I',*seeds.seeds))
                if self.read(G+FLARE_COUNT)==count:self.write(G+FLARE_COUNT,count+1)   # the attack harness already counts
            return result
        if address in (ADD_PARTICLES,ADD_LABEL,ADD_TILE_LABEL):   # adapted by the harnesses; their stream-0 draws (verify_effect_draws.py)
            r=[u.reg_read(v) for v in self.regs];result=super().hook(u,address,size,context)
            if (u.reg_read(self.PC)&~1)!=address:
                seeds=RandomState((C.c_uint32*6)(*struct.unpack('<6I',u.mem_read(SEEDS,24))))
                if address==ADD_PARTICLES:EFFECTS.dr_add_particles(C.byref(seeds),C.c_int32(r[2]).value)
                else:EFFECTS.dr_add_simple_label(C.byref(seeds),C.c_int32(r[1]).value if address==ADD_LABEL else 0)
                u.mem_write(SEEDS,struct.pack('<6I',*seeds.seeds))
            return result
        if address==SCREEN_INIT and self.recording:   # recorded and skipped by the harness; its game state is written here
            u.mem_write(self.GAME+0xcac4,b'\x01');self.write(self.GAME+0xcc1c,0)
        return super().hook(u,address,size,context)
    def effect_draw(self,stream,lo,hi):
        seeds=RandomState((C.c_uint32*6)(*struct.unpack('<6I',self.u.mem_read(SEEDS,24))))
        RANDOM.dr_random_float(C.byref(seeds),lo,hi,stream);self.u.mem_write(SEEDS,struct.pack('<6I',*seeds.seeds))
    def load(self,c):
        super().load(c);G=self.GAME;I=G+INTERFACE
        sc=c.get('release',{}).get('scroll',{});self.class_current=sc.get('current',0)
        if self.class_current:   # with_class: record 0 (as the loaders wrote it) is the current class's
            rec=G+CLASSES+CLASS_STRIDE*self.class_current;self.u.mem_write(rec,bytes(self.u.mem_read(G+CLASSES,CLASS_STRIDE)))
            type_,base,level=sc['classes'][self.class_current];self.write(rec+4,type_);self.write(rec+0xc,base);self.u.mem_write(rec+0x54,bytes([level]))
            self.write(G+CLASS_INDEX_ADDR,self.class_current)
        if not self.names_ready:   # the item name tables, once
            u=self.u;self.naming=True;u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1)
            try:u.emu_start(NAMES_FN|1,self.STOP,timeout=0,count=5000000)
            finally:self.naming=False
            self.names_ready=True
        k=c['k5'];self.item_allocs=0;self.int_vectors_k5={}
        for i,rec in enumerate(k['items']):
            base=ITEM_OBJECTS+0x200*i;self.write(base+0x7c,G);self.write(G+0xbe88+4*i,base);self.write(VEC_DATA-0x100+4*i,G+0xbe88+4*i)
            for off,key in ITEM_FIELDS:self.write(base+off,rec[key]&0xffffffff)
            for j,v in enumerate(rec['stats']):self.write(base+0x94+4*j,v&0xffffffff)
        self.write(G+0xbe9c,VEC_DATA-0x100);self.write(G+0xbea0,VEC_DATA-0x100+20);self.write(G+0xbea4,VEC_DATA-0x100+20)
        for key,v in k['stats'].items():
            if key in STATS_INTS:self.write(G+STATS_INTS[key],v&0xffffffff)
            elif key in STATS_FLOATS:self.u.mem_write(G+STATS_FLOATS[key],struct.pack('<f',v))
        self.u.mem_write(G+0xbe64,bytes([k['stats']['cooldown']]))
        # the menu's objects (Skill / Item / ItemUpgrade -> Game) and the classes' skill lists
        self.k5_sets={}
        self.write(G+FM+0x10,G);self.write(G+FM+0x14,G+0x4cdc)
        for i in range(4):
            for base,slot in ((MENU_OBJECTS+0x200*i,0x48),(MENU_OBJECTS+0x800+0x200*i,0x38),(MENU_OBJECTS+0x1000+0x100*i,0x68)):
                self.u.mem_write(base,b'\0'*0x200 if slot!=0x68 else b'\0'*0x100);self.write(base+0x7c,G);self.write(G+FM+slot+4*i,base)
            self.write(G+FM+0x58+4*i,G and self.read(G+0xbe88))
        self.u.mem_write(MENU_OBJECTS+0x1400,b'\0'*0x200);self.write(MENU_OBJECTS+0x1400+0x7c,G);self.write(G+FM+0x110,MENU_OBJECTS+0x1400)
        for a in (0x78,0x10c,0x24,0x30,0x34,0x2c,0xc):self.write(G+FM+a,0)
        for a in (0x20,0x21,0x28):self.u.mem_write(G+FM+a,b'\0')
        for i in range(10):
            b=G+0x15564+388*i;arrays=CLASS_ARRAYS+0x100*i;type_=C.c_int32(self.read(b+4)).value;type_=type_ if 0<=type_<10 else 0
            for j in range(20):self.write(arrays+4*j,CLASS_BASE[type_][j]);self.write(arrays+0x80+4*j,255)
            self.write(b+0x30,arrays);self.write(b+0x34,arrays+80);self.write(b+0x48,arrays+0x80);self.write(b+0x4c,arrays+0x80+80)
        for i in range(4):self.write(SKILL_OBJECTS+0x100*i+0x7c,G)   # Skill -> Game
        self.write(I+0xbd0,0xffffffff);self.write(I+0x1034,0)       # no skill button pressed, previous touch phase 0
    def set_button(self,button):self.button=button
    def match_status(self):   # the current class's type, level and race (Game::MatchTile reads them at Game+0x1648c's index)
        r=super().match_status()
        if getattr(self,'class_current',0):
            rec=self.GAME+CLASSES+CLASS_STRIDE*self.read(self.GAME+CLASS_INDEX_ADDR)
            r.update(class_type=C.c_int32(self.read(rec+4)).value,class_level=self.u.mem_read(rec+0x54,1)[0],race=self.read(rec+8))
        return r
    def set_menu_button(self,button):self.menu_button=button
    def k5_write_set(self,tree):
        values=sorted(self.k5_sets[tree]);header=tree+4;base=SET_NODES_K5+0x400*list(self.k5_sets).index(tree)
        self.write(tree+0x14,len(values));self.write(tree+0xc,base if values else header);self.write(tree+8,base if values else 0)
        for i,v in enumerate(values):node=base+32*i;self.write(node,base+32*(i+1) if i+1<len(values) else header);self.write(node+16,v&0xffffffff)
    def menu_state(self):
        G=self.GAME;i32=lambda a:C.c_int32(self.read(a)).value;b=lambda a:self.u.mem_read(a,1)[0]
        opt=lambda o:[i32(o+0x84),i32(o+0x88),i32(o+0x8c),i32(o+0x90),b(o+0x80)]
        item=lambda o:[i32(o+off) for off,_ in ITEM_FIELDS]+[i32(o+0x94+4*j) for j in range(20)]
        slots=[self.read(G+0xbe88+4*j) for j in range(5)];sc=self.read(G+FM+0x110)
        return dict(type=i32(G+FM+0xc),first=i32(G+FM+0x30),second=i32(G+FM+0x34),ready=b(G+FM+0x20),pressed=b(G+FM+0x21),timer=self.read(G+FM+0x24),
                    opening=b(G+FM+0x28),previous=i32(G+FM+0x2c),n=i32(G+FM+0x78),options=[opt(self.read(G+FM+0x48+4*i)) for i in range(4)],
                    items=[item(self.read(G+FM+0x38+4*i)) for i in range(3)],scroll_slot=i32(G+FM+0x10c),scroll=opt(sc)[:4],
                    upgrades=[[slots.index(self.read(G+FM+0x58+4*i)) if self.read(G+FM+0x58+4*i) in slots else -1,
                               i32(self.read(G+FM+0x68+4*i)+0x80),i32(self.read(G+FM+0x68+4*i)+0x84)] for i in range(4)]
                             if i32(G+FM+0xc)==2 else [])   # left over from an upgrade menu: the shop's SetItem moves the objects, and Initialise(2) rewrites all four
    def game_state(self):   # plus the stroke's resource counts (Game+0x164b0, ProcessResourceShadows)
        G=self.GAME;i32=lambda a:C.c_int32(self.read(a)).value;slots=[]
        for i in range(4):   # the equipped skill objects in slot order (RemoveSkill reorders Game+0xbf90)
            o=self.read(G+0xbf90+4*i);slots.append([i32(o+0x84),i32(o+0x88),self.u.mem_read(o+0x80,1)[0],i32(o+0x8c),i32(o+0x90)])
        items=[]
        for i in range(5):
            o=self.read(G+0xbe88+4*i);items.append([i32(o+off) for off,_ in ITEM_FIELDS]+[i32(o+0x94+4*j) for j in range(20)])
        k5={key:i32(G+a) for key,a in STATS_INTS.items()};k5.update({key:self.read(G+a) for key,a in STATS_FLOATS.items()});k5['cooldown']=self.u.mem_read(G+0xbe64,1)[0]
        return dict(super().game_state(),counts=[C.c_int32(self.read(self.GAME+0x164b0+4*i)).value for i in range(6)],
                    game_over_state=C.c_int32(self.read(self.GAME+0xcc1c)).value,skill_slots=slots,skill_count=i32(G+0xbfa0),items=items,k5=k5,
                    menu=self.menu_state())
class NewGameSessionOriginal(OriginalMixin,NewGameOriginal):pass
class CarriedSessionOriginal(OriginalMixin,FramesOriginal):pass

class SessionMixin:
    def __init__(self):
        super().__init__();lib=self.session_lib=C.CDLL(str(HERE/'recovered_session_native.dylib'));self.session=None
        lib.dr_session_create.argtypes=[C.POINTER(Host),I32];lib.dr_session_create.restype=C.c_void_p
        lib.dr_session_destroy.argtypes=[C.c_void_p];lib.dr_session_destroy.restype=None
        lib.dr_session_objects.argtypes=[C.c_void_p];lib.dr_session_objects.restype=Objects
        lib.dr_session_link.argtypes=[C.c_void_p];lib.dr_session_link.restype=None
        lib.dr_session_set_falling.argtypes=[C.c_void_p,C.POINTER(I32),C.c_uint32];lib.dr_session_set_falling.restype=None
        lib.dr_session_set_motions.argtypes=[C.c_void_p,C.POINTER(Motion),C.c_uint32];lib.dr_session_set_motions.restype=None
        lib.dr_session_new_game.argtypes=[C.c_void_p,C.c_uint32];lib.dr_session_new_game.restype=None
        lib.dr_session_frame.argtypes=[C.c_void_p,C.c_float,I32,Point];lib.dr_session_frame.restype=I32
        self.sources={}
        def event(_,source,p):
            k=(source,C.cast(p,C.POINTER(I32))[1 if source==6 else 0]);self.sources[k]=self.sources.get(k,0)+1   # (unit, event kind) seen in play (RoundEvent: kind second)
            if source==SOURCE_NEW_GAME:
                e=C.cast(p,C.POINTER(I32*4)).contents;self.new_events.append(list(e))
            elif source==SOURCE_GENERATION:
                e=C.cast(p,C.POINTER(I32*6)).contents;self.gen_events.append(list(e))
        def get_target(_,kind,index,out):out[0]=Point(*motion_target(kind,index))
        def choose(_,p):p.contents.linked=self.case['special_link'];return self.case['special_choice']
        def start(_,kind,out):out[0]=Point(*TARGET_POINT)
        self.host_cb=(EVENT(event),TARGET(get_target),CHOOSE(choose),START(start));self.host=Host(None,*self.host_cb)
    def load(self,c):
        if self.session:self.q=self.own_queue   # the loaders replace the harness's own token queue, not the session's
        super().load(c);lib=self.session_lib;self.own_queue=self.q
        if self.session:lib.dr_session_destroy(self.session)
        self.session=lib.dr_session_create(C.byref(self.host),1);o=lib.dr_session_objects(self.session)
        # the case, as the harness loaders built it, becomes the session's state
        pairs=dict(stroke=self.state,preview=self.p,match=self.m,rune=self.rune,resources=self.r,path=self.path_state,refill=self.refill,
                   generation=self.gen,damage=self.damage,animation=self.anim,overlay_alpha=self.overlay,attack_inputs=self.inputs,
                   skills=self.skills,turn_flags=self.turn_flags,finish=self.fin_flags,end=self.flags,activated=self.flags_254,
                   end_of_turn=self.eot_state,flights=self.flights,release_inputs=self.release_inputs,classes=self.classes,
                   scroll=self.scroll_state,player=getattr(self,'player',None),extra=self.extra,shatter=self.shatter,touch=self.touch,
                   screens=self.screens)
        pairs={k:v for k,v in pairs.items() if v is not None}   # the carried harness has no PlayerStats (zero)
        for name,obj in pairs.items():C.memmove(getattr(o,name),C.addressof(obj),C.sizeof(obj))
        lib.dr_session_link(self.session)
        moving=(I32*max(1,len(self.moving_list)))(*self.moving_list);lib.dr_session_set_falling(self.session,moving,len(self.moving_list))
        motions=[t for _,t in sorted(self.motions.items())];array=(Motion*max(1,len(motions)))(*motions)
        lib.dr_session_set_motions(self.session,array,len(motions))
        counters=self.token_counters();q=C.c_void_p(o.tokens)
        fn=self.tokens_lib.dr_token_queue_restore;fn.argtypes=[C.c_void_p,C.POINTER(Counters)];fn.restype=None;fn(q,C.byref(counters))
        # from here on the harness reads the session's memory
        o=lib.dr_session_objects(self.session)
        for name,obj in pairs.items():setattr(self,{v:k for k,v in self.attribute_names().items()}.get(name,name),type(obj).from_address(getattr(o,name)))
        self.fin_flags=self.finish;self.counter=U8.from_address(o.animation+type(self.anim).counterattack.offset)
        self.label_active=(U8*4).from_address(o.extra+type(self.extra).label_active.offset)
        self.q=o.tokens;self.sync()
        self.menu=MenuState.from_address(o.menu);self.k5_items=(ItemRecord*5).from_address(o.items);self.k5_player=PlayerStats.from_address(o.player);k5=c['k5']
        for i,rec in enumerate(k5['items']):
            x=self.k5_items[i]
            for _,key in ITEM_FIELDS:setattr(x,key,rec[key])
            x.stats=(I32*20)(*rec['stats'])
        targets=self.k5_targets()
        for key,v in k5['stats'].items():obj,attr=targets[key];setattr(obj,attr,v)
        pl=self.k5_player;self.m.bonus_chance_extra=(I32*4)(pl.chance_be24,pl.chance_be2c,pl.chance_be1c,pl.chance_be34)   # one Game field each
    def attribute_names(self):
        return dict(state='stroke',p='preview',m='match',rune='rune',r='resources',path_state='path',refill='refill',gen='generation',
                    damage='damage',anim='animation',overlay='overlay_alpha',inputs='attack_inputs',skills='skills',turn_flags='turn_flags',
                    finish='finish',flags='end',flags_254='activated',eot_state='end_of_turn',flights='flights',release_inputs='release_inputs',
                    classes='classes',scroll_state='scroll',player='player',extra='extra',shatter='shatter',touch='touch',screens='screens')
    def sync(self):
        o=self.session_lib.dr_session_objects(self.session)
        self.moving_list=list((I32*o.falling_count).from_address(o.falling)) if o.falling_count else []
        self.motions={i:Motion.from_address(o.motions+i*C.sizeof(Motion)) for i in range(o.motion_count)}
    def game_state(self):
        k,r=self.skills,self.r
        slots=[[k.id[i],k.level[i],k.active[i],r.skill_max[i],r.skill_current[i]] for i in range(4)]
        items=[[getattr(x,key) for _,key in ITEM_FIELDS]+list(x.stats) for x in self.k5_items]
        return dict(super().game_state(),counts=list(self.state.counts),game_over_state=self.screens.game_over_state_cc1c,skill_slots=slots,
                    skill_count=r.skill_count,items=items,k5=self.k5_status(),menu=self.menu_state())
    def k5_targets(self):
        r,p,sel,b,a,pl=self.r,self.p,self.state.selection,self.path_state.battle,self.inputs,self.k5_player
        t=dict(health=(r,'health'),health_max=(r,'health_max'),health_bonus=(r,'health_bonus'),ui_health=(r,'ui_health'),ui_armour=(r,'ui_armour'),
               armour_current=(p,'armour_current'),armour_max=(p,'armour_max'),healing_bonus=(p,'healing_bonus'),shield_bonus=(p,'shield_bonus'),
               weapon_damage=(sel,'weapon_damage'),base_damage=(sel,'base_damage'),bonus_base_damage=(sel,'bonus_base_damage'),leech=(sel,'leech'),
               break_chance=(b,'break_chance'),poison_amount=(b,'poison_amount'),armour_loss_chance=(a,'armour_loss_chance'),weaken=(a,'weaken'),
               damage_all=(a,'damage_all'),regen=(self.eot_state,'regen'),xp_bonus=(p,'xp_bonus'),gold_bonus=(p,'gold_bonus'),upgrade_bonus=(p,'upgrade_bonus'),
               cooldown=(pl,'skill_cooldown_be64'))
        t.update({key:(pl,key) for key in PLAYER+UI})
        return t
    def k5_status(self):
        out={}
        for key,(obj,attr) in self.k5_targets().items():
            v=getattr(obj,attr);out[key]=struct.unpack('<I',struct.pack('<f',v))[0] if key in STATS_FLOATS else v
        return out
    def new_game(self,time):
        self.new_events=[];self.gen_events=[];self.session_lib.dr_session_new_game(self.session,time);self.sync()
    def set_button(self,button):
        o=self.session_lib.dr_session_objects(self.session);I32.from_address(o.skill_button).value=button
    def set_menu_button(self,button):
        o=self.session_lib.dr_session_objects(self.session);I32.from_address(o.menu_button).value=button
    def menu_state(self):
        m=self.menu
        return dict(type=m.type,first=m.first,second=m.second,ready=m.confirm_ready,pressed=m.confirm_pressed,timer=struct.unpack('<I',struct.pack('<f',m.timer))[0],
                    opening=m.opening,previous=m.previous_phase,n=m.skill_options,
                    options=[[t.type,t.level,t.max,t.current,t.active] for t in m.options],
                    items=[[getattr(x,key) for _,key in ITEM_FIELDS]+list(x.stats) for x in m.items],scroll_slot=m.scroll_slot,
                    scroll=[m.scroll.type,m.scroll.level,m.scroll.max,m.scroll.current],
                    upgrades=[[m.upgrade_items[i],m.upgrade_type[i],m.upgrade_amount[i]] for i in range(4)] if m.type==2 else [])
    def play_frame(self,phase,touch,dt):
        self.frame_route=self.session_lib.dr_session_frame(self.session,dt,phase,Point(*touch));self.sync()
        return dict(self.game_state(),reached_attack=self.frame_route==0)

class NewGameSession(SessionMixin,NewGameNative):pass
class CarriedSession(SessionMixin,FramesNative):pass

def state_only(x):
    """The game state without event lists and presentation mirrors."""
    if isinstance(x,dict):
        return {k:state_only(v) for k,v in x.items() if k not in ('events','encounters','end_events','flares','quads')}
    if isinstance(x,list):return [state_only(v) for v in x]
    return x

def set_health(old,new,health,maximum=None):
    old.write(old.GAME+RESOURCE_INTS['health'],health);new.r.health=health
    if maximum is not None:old.write(old.GAME+RESOURCE_INTS['health_max'],maximum);new.r.health_max=maximum

def main():
    menus_seen={};items_rng=random.Random(0x14c04);rng=random.Random(0x5e55);frames=turns=moves=ended=presses=busy_presses=busy_blocked=0;routes={};sources={};phases={};used={}
    def signed_states(x):
        if isinstance(x,dict):return {k:(C.c_int32(v).value if k=='enemy_state' and isinstance(v,int) else signed_states(v)) for k,v in x.items()}
        if isinstance(x,list):return [signed_states(v) for v in x]
        return x
    def compare(stage,a,b,**info):
        a,b=state_only(signed_states(a)),state_only(signed_states(b))
        if a!=b:
            (HERE/'session_failure.json').write_text(json.dumps(dict(stage=stage,info=info,original=a,native=b),indent=2,default=str))
            raise AssertionError(f'session_failure.json ({stage})')
    def play(old,new,game,count,skills=False,first_path=None):
        nonlocal frames,turns,moves,ended,presses,busy_presses,busy_blocked;ready_before=1
        for turn in range(count):
            count_=new.r.skill_count
            if skills and count_>0 and rng.random()<.75:   # a skill button pressed and released (sometimes released on another)
                button=turn%count_ if rng.random()<.9 else rng.randrange(count_);release=button if rng.random()<.92 else rng.randrange(-1,4)
                script=[(1,('button',button)),(2,('button',release))];presses+=1;path=[]
                pressed_type,used_before=new.skills.id[button],new.sources.get((SOURCE_SKILL,SKILL_USED),0)
            else:
                path=first_path if first_path and turn==0 else new.pick_path(rng);moves+=len(path)>=3
                script=[(1,i) for i in path]+[(2,path[-1])] if len(path)>=3 else []
            busy=len(script)+rng.randrange(1,12) if skills and count_>0 and len(path)>=3 and rng.random()<.6 else None   # a press while the turn runs
            menu_plan=[];menu_taps=0;menu_open=False
            for frame in range(3000):
                dt=f32(rng.choice([1/60,1/30]))
                button=-1
                if frame<len(script):
                    phase,i=script[frame]
                    if isinstance(i,tuple):button,touch=i[1],BUTTON_TOUCH
                    else:centre=new.state.selection.tiles[i].geometry.center;touch=[centre.x,centre.y]
                else:phase,touch=0,[0.5,0.5]
                if busy is not None and frame in (busy,busy+1):
                    phase,touch,button=1 if frame==busy else 2,BUTTON_TOUCH,turn%count_
                    if frame==busy:busy_presses+=1;busy_blocked+=not ready_before
                menu_button=-1
                if new.screens.menus[0]:   # the FoldoutMenu: wait for the animation, choose (two in the level-up menu), confirm
                    m=new.menu;touch=BUTTON_TOUCH;button=-1
                    if not menu_plan and m.timer<0:
                        if menu_taps<3 and rng.random()<.25:
                            b=rng.choice([14,15,16,17,7,-1]);menu_plan+=[(0,-1),(1,b),(2,rng.choice([b,b,-1,7]))];menu_taps+=1
                        elif m.first==-1 or (m.type==0 and m.second==-1):
                            b=rng.choice([x for x in (14,15,16,17) if x not in (m.first,m.second) and not (m.type==1 and x==17)])
                            menu_plan+=[(0,-1),(1,b),(2,b)]
                        else:menu_plan+=[(0,-1),(1,7),(2,7)]
                    phase,menu_button=menu_plan.pop(0) if menu_plan else (0,-1)
                    if not menu_open:menu_open=True;menus_seen[m.type]=menus_seen.get(m.type,0)+1
                else:menu_open=False;menu_plan=[];menu_taps=0
                old.set_menu_button(menu_button);new.set_menu_button(menu_button)
                old.set_button(button);new.set_button(button)
                if not script and frame==0:old.set_ready(0);new.set_ready(0)
                info=dict(game=game,turn=turn,frame=frame,phase=phase)
                if button>=0:info.update(button=button,skill=new.skills.id[button],skills=list(new.skills.id),count=new.r.skill_count)
                a,b=old.play_frame(phase,touch,dt),new.play_frame(phase,touch,dt);compare('frame',a,b,**info);frames+=1;ready_before=a['common']['input_ready']
                routes[new.frame_route]=routes.get(new.frame_route,0)+1
                if new.frame_route==11 or new.flags.game_over_screen:ended+=1;return
                if frame>=len(script) and a['common']['input_ready'] and a['common']['phase']==0 and not new.moving_list and not a['common']['pending'] and not new.screens.menus[0]:break
            else:raise AssertionError('turn did not finish')
            if script and isinstance(script[0][1],tuple) and new.sources.get((SOURCE_SKILL,SKILL_USED),0)>used_before:
                used[pressed_type]=used.get(pressed_type,0)+1
            turns+=1
    old,new=NewGameSessionOriginal(),NewGameSession()
    for game in range(GAMES):
        c=with_items(case(rng),items_rng);old.load(c);new.load(c)
        a=NewGameOriginal.run(old);new.new_game(c['new_game']['time'])
        compare('init events',[a['new_events'],a['events']],[new.new_events,new.gen_events],game=game)
        old.moving_list=[old.index(v) for v in old.list_values(old.GAME+0xb3f8)]
        if game%3==1:set_health(old,new,rng.choice([2,4,6]))   # weakened after the start: enemies end the game early
        elif game%3==2:set_health(old,new,1000,1000)            # strengthened: long games, later enemies
        compare('after init',old.game_state(),new.game_state(),game=game)
        play(old,new,game,LONG_TURNS if game%3==2 else TURNS)
    phases['new_games']=dict(games=GAMES,turns=turns,frames=frames,ended=ended);sources.update(new.sources)
    old,new=CarriedSessionOriginal(),CarriedSession()
    for game in range(CARRIED_GAMES):
        c=with_items(variant(turn_case(rng),game),items_rng);old.load(c);new.load(c)
        if game%2==0 and game%5!=1:set_health(old,new,5000,5000)   # most carried boards end the game within a turn
        compare('load',old.game_state(),new.game_state(),game=game)
        play(old,new,GAMES+game,CARRIED_TURNS)
    phases['carried']=dict(games=CARRIED_GAMES,turns=turns-phases['new_games']['turns'],frames=frames-phases['new_games']['frames'],
                           ended=ended-phases['new_games']['ended'])
    for k,v in new.sources.items():sources[k]=sources.get(k,0)+v
    class_rng=random.Random(0x25526)   # T040-K5b: the current class (the menus' skill pools) in the item and skill phases
    old,new=CarriedSessionOriginal(),CarriedSession();mark=dict(turns=turns,frames=frames,ended=ended)
    for game in range(ITEM_GAMES):   # T040-K5: Item::IncreaseStat (race 6, > 14 kills) and DestroyUpgrade (enemy 28)
        c=with_items(turn_case(rng),items_rng)
        long=None
        if game%2==0:   # race 6 and a path of 15+ plain skulls of health 1: Item::IncreaseStat
            c['game']['race']=6;n=rng.choice([15,16,20])
            long=[y*6+(x if y%2==0 else 5-x) for y in range(6) for x in range(6)][:n]
            for i in long:c['board'][i].update(type=1,enemy=0,enemy_state=0,selected=0);c['combat'][i].update(health=1,defence=0)
        else:   # enemies 28 one turn from their ability: Game::DestroyUpgrade
            for t in c['board']:
                if t['type']==1 and rng.random()<.5:t['enemy']=28;t['enemy_state']=1
        with_class(c,class_rng)
        old.load(c);new.load(c);set_health(old,new,5000,5000)
        compare('load',old.game_state(),new.game_state(),game=game)
        play(old,new,200+game,CARRIED_TURNS,first_path=long)
    phases['items']={k:v-mark[k] for k,v in dict(turns=turns,frames=frames,ended=ended).items()};mark=dict(turns=turns,frames=frames,ended=ended)
    for k,v in new.sources.items():sources[k]=sources.get(k,0)+v
    assert sources.get((23,7),0)>0 and sources.get((29,28),0)>0,(sources.get((23,7)),sources.get((29,28)))   # IncreaseStat, DestroyUpgrade
    rng=random.Random(0x2ad40)   # the skill phase's own sequence (independent of the phases before it)
    old,new=CarriedSessionOriginal(),CarriedSession();mark=dict(turns=turns,frames=frames,ended=ended)
    for game in range(SKILL_GAMES):
        c=with_class(with_items(skill_variant(turn_case(rng),rng,game),items_rng),class_rng);old.load(c);new.load(c);set_health(old,new,5000,5000)
        compare('load',old.game_state(),new.game_state(),game=game)
        play(old,new,100+game,SKILL_TURNS if game<SKILL_GAMES-PROMOTE_GAMES else 5*SKILL_TURNS,skills=True)
    phases['skills']=dict(games=SKILL_GAMES,presses=presses,presses_while_busy=busy_presses,presses_input_not_ready=busy_blocked,used={k:used[k] for k in sorted(used)},**{k:v-mark[k] for k,v in dict(turns=turns,frames=frames,ended=ended).items()})
    for k,v in new.sources.items():sources[k]=sources.get(k,0)+v
    assert phases['new_games']['ended'] and phases['carried']['ended'],phases
    assert REQUIRED<=set(sources),REQUIRED-set(sources)
    assert busy_blocked>20 and sources.get((SOURCE_SKILL,SKILL_JUMP),0)>0,(busy_blocked,sources.get((SOURCE_SKILL,SKILL_JUMP)))
    assert set(used)==set(SKILL_TYPES) and sources.get((SOURCE_SKILL,SKILL_FLAME),0)>3,(set(SKILL_TYPES)-set(used),sources.get((SOURCE_SKILL,SKILL_FLAME)))
    assert set(menus_seen)=={0,1,2},menus_seen
    report=dict(status='passed',phases=phases,menus=dict(sorted(menus_seen.items())),turns=turns,moves=moves,frames=frames,games_ended=ended,frame_routes=routes,
                events_by_unit_kind={f'{k[0]}:{k[1]}':v for k,v in sorted(sources.items())},
                original='Original InitNewGame (new games) or a loaded state (carried), then the whole original Game::Process every frame',
                native='One recovered_session: dr_session_new_game (new games), then dr_session_frame (the session wires every unit itself)',
                boundaries=['time() returns the case seed',
                            'the harness picks the paths, the skill button and the menu button under the touch; GameMenu / StatsMenu closed',
                            "the shop's scroll probe takes the leech label's type and vertices as 0 (T040-K6)",
                            'events and presentation mirrors not compared here (unit tests)'],
                scope='games from their start through many turns up to the end of the game, carried mid-game states, skill use, items and the three menus')
    (HERE/'session_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
