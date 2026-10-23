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
Interface::GetSpecialTarget(Token*), the skill slot a mana potion recharges (T040-L1), runs as original code
(std::set<int> modelled) instead of verify_motion.py's answer; the native session computes it (dr_special_target).
Saves (T030-N5): Game::SerialiseState (the turns' ends, ProcessInput's tail) and Game::SerialiseClasses (a game's end,
a class scroll's level-up) run as original code instead of the units' boundaries; the save buffer (length, changed flag,
bytes) and the class records' save are compared every frame. Every case has a player name (saved). In the new-game
phase some games quit midway and continue from their save (the original's InitNewGame, DeserialiseState and
CalculateTilePositions; the native dr_session_continue_game), then play on.
Damage labels (T040-K6): the leech, flame and spike SimpleLabels (Game+0xbfc0 / 0x14afc / 0x14e70) are set up by the
constructor and Game::Start's SetColour (17, 18, 19) and duration 0.2 as original code; Game::Process's SimpleLabel calls on
them (Initialise, SetPosition, SetNumber, SetAlpha, Process) run as original code (the digit tables filled by their static
initialiser, __divsi3 / __modsi3 modelled) instead of being skipped; the three labels' whole memory is compared every frame,
and the shop's scroll draw reads the leech label's type and vertices from it.
New games from the main menu (T040-M1): the new-game phase starts its games with the original Game::NewGame,
StartTutorial or StartChallenge from their entries (in turn; InitNewGame with the new-game harness, Game::SetHelpState,
MainMenu::SetActive and HelpMenu::ResetHelp / ClearHelp as original code; NameScreen::Show, StartCyclingGamesColour,
Interface::Process(0, false) and GameMenu's help button skipped), the main menu open and the help switch and queued help
random beforehand; the native dr_session_start_game. The record mode, difficulty, help switch and main menu are compared.
New-game setup (T040-M3): NameScreen::Show runs as original code from the start functions (its libc calls modelled,
its display calls -- UpdateName's width check included -- skipped); then a few setup presses run NameScreen::ProcessInput
as original code (touch down, QuadStrip::ContainsPoint answering the pressed button: random name, a class, a mode or a
difficulty, Start at the bottom; GenerateRandomName, SetMode, SetDifficulty, SetCurrentClass, SetName and InitNewGame as
original code, sprintf / strlen / strncpy / strcmp / memcpy modelled, IntroScreen::Initialise skipped with the fields
IntroScreen::Process reads written as it leaves them; Start's button counted as shown -- NameScreen::Process's fade-in
done -- with a name entered), and two IntroScreen::Process frames (fade-in, then Continue: the save); the native
dr_session_setup_* and dr_session_intro_done. The setup fields, name, mode, changed flags, screens, current class and
random streams are compared after every press.
Class screen (T040-M4b): before Start some games edit the current class as ClassScreen::Process does on its drops and
buttons, with its calls as original code in that order: a class icon (an unlocked class: Game::SetCurrentClass), a race
(Game::IsRaceUnlocked and CharacterClass::CanChooseRace, then the record's race +8), perk / flaw / skill slots
(CharacterClass::SetPerk / SetFlaw / SetReplacementSkill), a tab change (Game::SerialiseClasses) and Done
(CharacterClass::Validate, Game::SetCurrentClass(the record's type), Game::SerialiseClasses); the native
dr_session_class_*. The current record (race, perks, flaws, replacement list) and the class save are compared too.
Game and stats menus (T040-M5): some turns first press Interface's menu or stats button (BUTTON_TOUCH; released on it or
elsewhere, or cancelled: Interface::ProcessInput as original code, Quad::ContainsPoint answering the button, GameMenu::Show /
StatsMenu::Show as original code); while a menu is open Interface::Process runs GameMenu::Process / StatsMenu::Process as
original code (CursorInQuad / CursorOutsideMenu answering the frame's menu button; Game::UpdateHelpState, HelpMenu::Reset /
ClearHelp, Game::Set*State, MainMenu::FadeIn as original code; display calls skipped): after the fade a few taps (the
switches, the stats tabs, released on the button or elsewhere), then the close button / a tap outside. The first turn
of some continued games quits to the main menu from the game menu, then starts a new game from the main menu (InitNewGame runs
Interface::Reset as original code, display skipped: the game menu left open closes). Both menus, Interface's touched buttons, the nine switch bytes and the main menu's fade
are compared with the flow fields.
Help popups (T040-M6): HelpMenu (Game+0x10298) runs as original code wherever the game calls it -- HelpMenu::Initialise
(every unit's topics), Interface::ShowHelp* / UpdateSkills / ProcessHeartbeat (from every caller: the unit harnesses'
boundaries for them are bypassed; Interface::Process runs its dispatch as at 0x20c64 and then, with no FoldoutMenu open,
ProcessHeartbeat, also from the new games and ContinueGame), HelpMenu::QueueHelp (the setup screen's help button as
NameScreen::ProcessInput, the class screen's as ClassScreen::Process's calls for the shown tab) and HelpMenu::Process
(Game::Process's help route) -- with Show, Game::SetHelpState, Clamp and Interpolate as original code, std::string /
std::list<HelpItem> modelled and display calls skipped; Show's box is fixed (0.1, 0.5, 0.8 x 0.5) so that a touch can be
inside or outside it. While a popup is open the turn's script waits: after the fade the touch ends, sometimes a touch
outside the box, then one inside. The tutorial games and some carried games have topics queued. The
current-damage label (Game+0xb550, SetColour(10) and duration 0.2 as Game::Start leaves it) runs as original code too and
its active byte is given to the session as the renderer's (help 8 and ShowHelpBaseDmg / WeaponDmg need it shown). The popup (open, closing,
timer, previous phase, queued texts), the queued topics and the texts shown (topic or screen text, with position and size
where the game gives them) are compared with the flow fields.
High scores (T030-N5d): a game's end runs ScoreScreen::AddScore (the GameMode or Difficulty overload) and SetSkills as
original code (strcpy modelled); the whole table memory (ScoreScreen+0x1e0..+0x132e) is compared every frame. In the
skill phase a press mostly takes the equipped skill used least so far, so that every type gets used.
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
OVERLAY_CHANCE=.08       # T040-M5: a turn that opens the game menu or the stats menu first
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
def with_mana(c,rng):
    """T040-L1: some potions are mana potions (flag_232): their tokens recharge a skill (Interface::GetSpecialTarget)."""
    for i,t in enumerate(c['board']):
        if t['type']==0 and rng.random()<.3:c['preview']['potions'][i][0]=1
    return c
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
              ('skill_button',C.c_void_p),('skill_input',C.c_void_p),('items',C.c_void_p),('menu',C.c_void_p),('menu_button',C.c_void_p),('dimmed',C.c_void_p),
              ('save',C.c_void_p),('name',C.c_void_p),('settings',C.c_void_p),('class_save',C.c_void_p),('scores',C.c_void_p),
              ('damage_labels',C.c_void_p),('setup',C.c_void_p),('game_menu',C.c_void_p),('stats_menu',C.c_void_p),
              ('interface_buttons',C.c_void_p),('main_menu',C.c_void_p),('help',C.c_void_p)]
class Setup(C.Structure):_fields_=[('challenge',U8),('name',U8*19),('length',I32),('named',U8)]
class Overlay(C.Structure):_fields_=[('previous_phase',I32),('pressed',I32),('closing',U8),('timer',C.c_float)]
class MainMenuScreen(C.Structure):_fields_=[('timer',C.c_float),('fading',U8)]
class HelpPopup(C.Structure):_fields_=[('closing',U8),('timer',C.c_float),('previous_phase',I32),('text',I32),('at',Point),('width',C.c_float),
                                       ('height',C.c_float),('skill_slot',I32),('queued',C.c_uint32),('queue',I32*64)]
SOURCE_INTERFACE=35   # SessionSource::Interface
EVENT=C.CFUNCTYPE(None,C.c_void_p,I32,C.c_void_p)
TARGET=C.CFUNCTYPE(None,C.c_void_p,I32,I32,C.POINTER(Point))
START=C.CFUNCTYPE(None,C.c_void_p,I32,C.POINTER(Point))
class Host(C.Structure):_fields_=[('context',C.c_void_p),('event',EVENT),('target',TARGET),('start',START)]
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
    n=NAME_RNG.choice([0,1,5,16]);c['name']=[NAME_RNG.randrange(32,127) for _ in range(n)]   # the player's name (saved; Game::SetName: at most 16)
    return c
# T040-K5b: FoldoutMenu (Interface+0xd10) as original code
from verify_menu_level import MenuState, OPTION_INTS, OPTION_CHANCES, SET_OPS, SKIP as MENU_SKIP_SYMBOLS, BASE as CLASS_BASE
SHOW_MENU,FM_INIT,FM_PROCESS,FM=0x1eb20,0x24a54,0x23c44,0x4cdc+0xd10
GET_SPECIAL=0x20358   # Interface::GetSpecialTarget(Token*) (T040-L1): original code, std::set<int> modelled
SPECIAL_CALLS=[0]     # its calls in play (all phases)
SERIALISE,QUEUE_ACHIEVEMENT=0x91c4,0xbd68   # Game::SerialiseState (T030-N5): original code; its achievement recorded
SAVE_BUFFER,SAVE_LENGTH,SAVE_CHANGED,NAME=0x13ecf,0x146d0,0x146d4,0xbe38
SAVE_CALLS=[0]        # Game::SerialiseState calls in play (all phases)
SERIALISE_CLASSES,CLASS_SAVE,CLASS_SAVE_LENGTH,CLASS_SAVE_CHANGED=0x8ee8,0x146d5,0x14ad8,0x14adc   # Game::SerialiseClasses: original code
CLASS_SAVES=[0]
# ScoreScreen (Game+0xef68, T030-N5d): AddScore (all three overloads) and SetSkills as original code (strcpy modelled)
SCORE_SCREEN,SCORE_TABLES,SCORE_SIZE=0xef68,0x1e0,0x1328+6-0x1e0
SCORE_FUNCTIONS=('__ZN11ScoreScreen8AddScoreEPKciiiii9ScoreType','__ZN11ScoreScreen8AddScoreEPKciiiii8GameMode',
                 '__ZN11ScoreScreen8AddScoreEPKciiiii10Difficulty','__ZN11ScoreScreen9SetSkillsEiiii')
SCORE_CALLS={}         # by function: the GameMode / Difficulty overloads and SetSkills
NAME_RNG=random.Random(0xbe38)
# Game::DeserialiseState / ContinueGame / CalculateTilePositions (T030-N5): original code; the interface updates, icons
# and texts are skipped (sprintf, strcpy stubs too)
DESERIALISE,CONTINUE_GAME,TILE_POSITIONS=0x15c18,0x165f4,0xb264
LOAD_SKIP=['__ZN7Upgrade7SetIconEiiii','__ZN5Label7SetTextEPKci','__ZN4Item9MakeStatsEv','__ZN9Interface16UpdateSkullValueEv',
           '__ZN9Interface15UpdateHealthBarER4Quadi','__ZN9Interface17UpdateShieldValueEv','__ZN9Interface11UpdateXPBarER4Quadi',
           '__ZN9Interface11UpdateUPBarER4Quadi','__ZN9Interface13UpdateGoldBarERA2_4Quadi','__ZN9Interface9SetPoisonEi',
           '__ZN9Interface13PositionSkillEi','__ZN9Interface12UpdateSkillsEv','__ZN8GameMenu12SetHelpStateEb']
LOAD_STUBS=(0x194f60,0x194fb0)
HELP_SWITCH,DIFFICULTY_CHANGED=0x13ec8,0x14ae4
# The damage labels (T040-K6): leech, flame, spike SimpleLabel; their calls from Game::Process run as original code
DAMAGE_LABELS,LABEL_SIZE=(0xbfc0,0x14afc,0x14e70),0x358
CURRENT_LABEL=0xb550   # T040-M6: the current-damage label runs as original code too; its active byte is given to the session
LABEL_FUNCTIONS=('__ZN11SimpleLabel7ProcessEf','__ZN11SimpleLabel10InitialiseE15SimpleLabelTypeRK8GLfloat2if',
                 '__ZN11SimpleLabel11SetPositionERK8GLfloat2','__ZN11SimpleLabel9SetNumberEi','__ZN11SimpleLabel8SetAlphaEh')
LABEL_CTOR,LABEL_COLOUR,LABEL_DIGITS,DIVSI3,MODSI3=0x22194,0x221c4,0x313c,0x194d78,0x194d8c
LABEL_CALLS={}        # by function: the damage labels' calls in play
# The main menu's new games (T040-M1): Game::NewGame / StartTutorial / StartChallenge from their entries
START_ENTRIES,START_LO,START_HI,INIT_NEW_GAME,HELP_STATE_RETURN=(0x16590,0x164c0,0x1652c),0x164c0,0x165f4,0x15c50,0x95e8
START_SKIP=('__ZN8MainMenu23StartCyclingGamesColourEv','__ZN8GameMenu12SetHelpStateEb')
RECORD,DIFFICULTY,MAIN_MENU,HELP_QUEUE=0x14aed,0x14ae0,0xc400,0x102d0
STARTS={}             # new games by kind (0 NewGame, 1 StartTutorial, 2 StartChallenge)
# The new-game setup screen (NameScreen, Game+0x102dc) and the story screen (IntroScreen, Game+0xc330), T040-M3
NAME_SCREEN,INTRO,NAME_SHOW,NAME_INPUT,NAME_INPUT_END,INTRO_PROCESS,INTRO_INIT=0x102dc,0xc330,0x3bd60,0x3bff8,0x3cac0,0x2dd04,0x2de90
RANDOM_NAME,SET_NAME,SET_CURRENT,SET_MODE,SET_DIFFICULTY=(0x3882c,0x38920),(0x8470,0x84a4),(0x1a390,0x1a3ec),0x83e8,0x842c
STRLEN,STRNCPY,MEMCPY,SPRINTF,STRCMP=0x194fbc,0x194fc4,0x194ef0,0x194f60,0x194fac
SETUP_BUTTONS=dict(help=lambda a:0x868,random=lambda a:0x2e0,klass=lambda a:0x8ec+76*a,difficulty=lambda a:0x3e8+76*a,mode=lambda a:(0x6b4,0x700)[a])
NAME_NAME,NAME_LENGTH,NAME_NAMED,NAME_CHALLENGE,NAME_START_ALPHA,NAME_PREVIOUS=0x2935,0x2948,0x294c,0x3bbc,0x2993,0x2960
MODE,MODE_CHANGED,NAME_CHANGED,CURRENT_CLASS,NAME_OPEN,INTRO_OPEN=0x14ae8,0x14aec,0xbe49,0x1648c,0x12c09,0xc3f0
SETUPS={}             # setup presses by kind and result
VALIDATE,RACE_UNLOCKED,CAN_CHOOSE,SET_PERK,SET_FLAW,SET_SKILL=0x111870,0x8d88,0x110a54,0x1115e0,0x111628,0x111b80   # T040-M4b
CLASS_OPS={}          # class-screen edits by kind
CONTINUES=[0]         # games continued from their save (new-game phase)
# T040-M5: GameMenu (Game+0x5b00) and StatsMenu (Game+0x5b90) from Interface::Process, their Show from Interface::ProcessInput, and
# InitNewGame's Interface::Reset as original code (display skipped); MainMenu (Game+0xc3fc)
GM,SM,GM_PROCESS,SM_PROCESS,GM_SHOW,SM_SHOW,IFACE_RESET,MAIN_MENU_OBJ=0x5b00,0x5b90,0x32580,0x33c0c,0x31b88,0x3381c,0x204a4,0xc3fc
OVERLAY_RUN=('__ZN8GameMenu4ShowEv','__ZN9StatsMenu4ShowEv','__ZN4Game15UpdateHelpStateEv','__ZN8HelpMenu9ResetHelpEv','__ZN8HelpMenu9ClearHelpEv',
             '__ZN4Game13SetSoundStateEb','__ZN4Game12SetHelpStateEb','__ZN4Game13SetClockStateEb','__ZN4Game21SetAttackDimmingStateEb',
             '__ZN4Game16SetHighFramerateEb','__ZN8MainMenu6FadeInEv','__Z11Interpolatefff','__ZNKSt6vectorIP5LabelSaIS1_EE4sizeEv')
OVERLAY_COUNT={'__ZN8GameMenu4ShowEv':'game_menu','__ZN9StatsMenu4ShowEv':'stats_menu','__ZN4Game15UpdateHelpStateEv':'closed',
               '__ZN4Game13SetSoundStateEb':'sound','__ZN4Game12SetHelpStateEb':'help','__ZN4Game13SetClockStateEb':'clock',
               '__ZN4Game21SetAttackDimmingStateEb':'dimming','__ZN4Game16SetHighFramerateEb':'framerate','__ZN8MainMenu6FadeInEv':'quit'}
OVERLAY_SCRATCH,SETTINGS_BYTES=0x3400000,0x13ec6   # the stats menu's labels; Game+0x13ec6..0x13ece
SETTINGS_NATIVE=[4,5,0,6,8,10,7,9,11]   # the SaveSettings byte of each
# T040-M6: HelpMenu (Game+0x10298) as original code; the screen texts QueueHelp is given (setup 100..104, class tabs 105..122)
HELP_MENU,IFACE_TRAMP,HEARTBEAT,QUEUE_HELP=0x10298,0x20cb4,0x1e8e8,0x38268
HELP_ENTRIES=('__ZN8HelpMenu10InitialiseEffff8HelpType','__ZN8HelpMenu7ProcessEf','__ZN8HelpMenu9QueueHelpEPKcfff',
              '__ZN9Interface12ShowHelpGoldEv','__ZN9Interface14ShowHelpHealthEv','__ZN9Interface10ShowHelpXPEv','__ZN9Interface10ShowHelpUPEv',
              '__ZN9Interface17ShowHelpWeaponDmgEv','__ZN9Interface14ShowHelpArmourEv','__ZN9Interface15ShowHelpBaseDmgEv',
              '__ZN9Interface12UpdateSkillsEv','__ZN9Interface16ProcessHeartbeatEf')
HELP_RUN=HELP_ENTRIES+('__ZN8HelpMenu4ShowEPKcffff','__ZN4Game12SetHelpStateEb','__Z5Clampfff','__Z11Interpolatefff')
HELP_TEXTS=[0x155f9c,0x156008,0x1560d8,0x156184,0x1561d4,0x16e298,0x16e310,0x16e3b4,0x16e488,0x16e510,0x16e5b0,0x16e658,0x16e6ac,
            0x16e760,0x16e808,0x16e8a0,0x16e91c,0x16e97c,0x16ea3c,0x16eaa0,0x16eb40,0x16ebb0,0x16ec84]
HELP_TEXT_IDS={a:100+i for i,a in enumerate(HELP_TEXTS)};CLASS_HELP=[HELP_TEXTS[5:10],HELP_TEXTS[10:14],HELP_TEXTS[14:18],HELP_TEXTS[18:23]]
HELP_BOX=(0.1,0.5,0.8,0.5);HELP_IN,HELP_OUT=[0.5,0.75],[0.05,0.2]
STRING_CTOR,STRING_COPY,STRING_DTOR=0x194d10,0x194d18,0x194d1c
HELP={}               # popups shown by text, taps outside / inside, setup and class help presses
def help_show(s):   # a text shown as compared: a screen text's place is the renderer's, so are topics 19 / 20's positions
    return s[:1] if s[0]>=100 else [s[0],s[3],s[4]] if s[0] in (19,20) else s
OVERLAY={}            # in play: menus opened (from the buttons), closed (the close button), switches, tabs, quits; Interface::Reset runs
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
        self.load_skip={addr(n) for n in LOAD_SKIP}|set(LOAD_STUBS);self.loading=False
        self.score_functions={addr(n):n for n in SCORE_FUNCTIONS};self.scoring=False
        self.label_functions={addr(n):n for n in LABEL_FUNCTIONS};self.label_running=False;self.digits_ready=False
        self.start_skip={addr(n):n for n in START_SKIP};self.starting=False
        self.func_starts={int(a,16) for a in re.findall(r'^[^\s][^\n]*:\n\s+([0-9a-f]+):',text,re.M)};self.setting_up=False;self.setup_target=None
        self.strip_contains=addr('__ZN9QuadStrip13ContainsPointERK8GLfloat2')
        self.setup_run={RANDOM_NAME[0],SET_MODE,SET_DIFFICULTY,SET_CURRENT[0],SET_NAME[0],SERIALISE,addr('__Z11Interpolatefff')}
        assert [addr(n) for n in ('__ZN14CharacterClass8ValidateEv','__ZN4Game14IsRaceUnlockedE8RaceType','__ZN14CharacterClass13CanChooseRaceEv',
                                  '__ZN14CharacterClass7SetPerkEi8PerkType','__ZN14CharacterClass7SetFlawEi8FlawType',
                                  '__ZN14CharacterClass19SetReplacementSkillEi9SkillType')]==[VALIDATE,RACE_UNLOCKED,CAN_CHOOSE,SET_PERK,SET_FLAW,SET_SKILL]
        assert [addr(n) for n in ('__ZN10NameScreen4ShowEPKcb','__ZN10NameScreen12ProcessInputEf','__ZN11IntroScreen7ProcessEf',
                                  '__ZN11IntroScreen10InitialiseEv','__ZN10NameScreen18GenerateRandomNameEv','__ZN4Game7SetNameEPKc',
                                  '__ZN4Game15SetCurrentClassE9ClassType','__ZN4Game7SetModeEi','__ZN4Game13SetDifficultyEi')]==[
                                  NAME_SHOW,NAME_INPUT,INTRO_PROCESS,INTRO_INIT,RANDOM_NAME[0],SET_NAME[0],SET_CURRENT[0],SET_MODE,SET_DIFFICULTY]
        assert [addr(n) for n in ('__ZN4Game7NewGameEv','__ZN4Game13StartTutorialEv','__ZN4Game14StartChallengeEv')]==list(START_ENTRIES)
        assert addr('__ZN4Game16DeserialiseStateEv')==DESERIALISE and addr('__ZN4Game22CalculateTilePositionsEv')==TILE_POSITIONS
        # T040-K5: items, UpdateStats, Item::IncreaseStat and DestroyUpgrade run as original code
        self.u.mem_map(ITEM_SPACE,0x100000);self.heap=ITEM_SPACE;self.naming=False;self.names_ready=False;self.stats_running=False
        self.item_allocs=0;self.int_vectors_k5={}
        self.release_calls={k:v for k,v in self.release_calls.items() if v not in ('increase_stat','update_stats')}
        self.abilities={}   # Game::DestroyUpgrade (enemy 28)
        self.stats_skip={addr(n) for n in STATS_SKIP};self.vector_ops={addr(n):v for n,v in VECTOR_OPS.items()}
        # T040-K5b: the menus
        self.resource_calls={k:v for k,v in self.resource_calls.items() if v!='menu'}   # Interface::ShowMenu runs
        self.menu_running=False;self.menu_button=-1;self.k5_sets={};self.special_running=False;self.saving=False;self.save_achievements=[]
        self.menu_skip={addr(n) for n in MENU_SKIP};self.string_vector_size=addr('__ZNKSt6vectorISsSaISsEE4sizeEv')
        self.menu_set_ops={addr(n):v for n,v in SET_OPS.items()};self.menu_set_ops.update({addr(n):v for n,v in ITEM_SET_OPS.items()})
        self.fm_cursor=addr('__ZN11FoldoutMenu14CursorInButtonEi');self.fm_quad=addr('__ZN11FoldoutMenu12CursorInQuadEi')
        self.skill_activate=addr('__ZN5Skill8ActivateEv')
        self.overlay_running=self.resetting=False;self.overlay_run={addr(n) for n in OVERLAY_RUN}|{GM_PROCESS,SM_PROCESS};self.overlay_count={addr(n):v for n,v in OVERLAY_COUNT.items()}
        self.gm_cursor,self.sm_cursor=addr('__ZN8GameMenu12CursorInQuadEi'),addr('__ZN9StatsMenu12CursorInQuadEi')
        self.sm_outside,self.get_item=addr('__ZN9StatsMenu17CursorOutsideMenuEv'),addr('__ZN4Game7GetItemE8ItemType')
        self.u.mem_map(OVERLAY_SCRATCH,0x10000)
        self.helping=False;self.help_entries={addr(n) for n in HELP_ENTRIES};self.help_run={addr(n) for n in HELP_RUN};self.iface_return=None
        self.help_init,self.help_show=addr('__ZN8HelpMenu10InitialiseEffff8HelpType'),addr('__ZN8HelpMenu4ShowEPKcffff')
        self.list_push,self.list_pop=addr('__ZNSt4listI8HelpItemSaIS0_EE9push_backERKS0_'),addr('__ZNSt4listI8HelpItemSaIS0_EE9pop_frontEv')
        self.help_type=-1;self.help_shows=[];self.help_nodes=0
        assert [addr(n) for n in ('__ZN9Interface16ProcessHeartbeatEf','__ZN8HelpMenu9QueueHelpEPKcfff')]==[HEARTBEAT,QUEUE_HELP]
        assert [addr(n) for n in ('__ZN8GameMenu7ProcessEf','__ZN9StatsMenu7ProcessEf','__ZN8GameMenu4ShowEv','__ZN9StatsMenu4ShowEv','__ZN9Interface5ResetEv')]==[
            GM_PROCESS,SM_PROCESS,GM_SHOW,SM_SHOW,IFACE_RESET]
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
        if address in self.help_entries and not self.helping:self.until_return(u,'helping')   # T040-M6: HelpMenu as original code
        if self.helping:
            r=[u.reg_read(v) for v in self.regs];sp=u.reg_read(self.SP)
            if address==self.help_init:self.help_type=C.c_int32(self.read(sp+4)).value
            if address==self.help_show:   # the text shown (topic or screen text) with its position and size; the box fixed
                text=self.help_type if self.help_init<=lr<self.help_init+0x70 else HELP_TEXT_IDS.get(r[1],-1)
                self.help_shows.append([text,r[2],r[3],self.read(sp),self.read(sp+4)]);HELP[text]=HELP.get(text,0)+1
                def box(G=self.GAME):
                    for k,v in enumerate(HELP_BOX):self.write(G+HELP_MENU+0x14+4*k,struct.unpack('<I',struct.pack('<f',v))[0])
                self.returns.setdefault(lr,[]).append(box)
            if address in self.func_starts or 0x194000<=address<0x196000:
                if address in self.help_run:return
                if address==STRING_CTOR:self.write(r[0],r[1])
                elif address==STRING_COPY:self.write(r[0],self.read(r[1]))
                elif address==self.list_push:   # std::list<HelpItem>::push_back: a node {next, prev, text, x, y, size}
                    node=OVERLAY_SCRATCH+0x4000+0x20*self.help_nodes;self.help_nodes+=1;tail=self.read(r[0]+4)
                    for k,v in enumerate([r[0],tail,self.read(r[1]),self.read(r[1]+4),self.read(r[1]+8),self.read(r[1]+12)]):self.write(node+4*k,v)
                    self.write(tail,node);self.write(r[0]+4,node)
                elif address==self.list_pop:
                    first=self.read(r[0]);nxt=self.read(first);self.write(r[0],nxt);self.write(nxt+4,r[0])
                u.reg_write(self.PC,lr|1)
            return
        if address==IFACE_PROCESS:   # Interface::Process: its dispatch as at 0x20c64, then (no FoldoutMenu open) ProcessHeartbeat
            G=self.GAME;self.iface_return=(lr|1,u.reg_read(self.regs[1]));u.reg_write(self.LR,IFACE_TRAMP|1)   # via 0x20cb4
            if u.mem_read(G+0x59f4,1)[0]:   # an open FoldoutMenu: its Process
                u.reg_write(self.regs[0],G+FM);self.until_return(u,'menu_running');u.reg_write(self.PC,FM_PROCESS|1);return
            for menu,entry in ((GM,GM_PROCESS),(SM,SM_PROCESS)):   # T040-M5: an open game / stats menu
                if u.mem_read(G+menu+0xc,1)[0]:u.reg_write(self.regs[0],G+menu);self.until_return(u,'overlay_running');u.reg_write(self.PC,entry|1);return
            if u.reg_read(self.regs[2])&0xff:   # the skill buttons as original code (verify_skill_input.py)
                self.write(G+INTERFACE+0x1030,G);self.until_return(u,'skill_input');u.reg_write(self.PC,IFACE_INPUT|1);return
            u.reg_write(self.PC,IFACE_TRAMP|1);return
        if address==IFACE_TRAMP and self.iface_return:
            ret,dt=self.iface_return;self.iface_return=None;u.reg_write(self.LR,ret)
            if u.mem_read(self.GAME+0x59f4,1)[0]:u.reg_write(self.PC,ret);return
            u.reg_write(self.regs[0],self.GAME+INTERFACE);u.reg_write(self.regs[1],dt);u.reg_write(self.PC,HEARTBEAT|1);return
        if self.overlay_running or self.resetting:   # T040-M5: the menus and Interface::Reset; their display calls skipped
            if address in self.func_starts or 0x194000<=address<0x196000:
                if self.overlay_running and address in self.overlay_count:n=self.overlay_count[address];OVERLAY[n]=OVERLAY.get(n,0)+1
                if self.overlay_running and address in self.overlay_run:return
                r=[u.reg_read(v) for v in self.regs];res=None
                if address in (self.gm_cursor,self.sm_cursor):res=int(C.c_int32(r[1]).value==self.menu_button)
                elif address==self.sm_outside:res=int(self.menu_button==-1)
                elif address==self.get_item:res=OVERLAY_SCRATCH+0x8000
                elif address==self.string_vector_size:res=0
                if res is not None:u.reg_write(self.regs[0],res)
                u.reg_write(self.PC,lr|1)
            return
        if address==IFACE_RESET and getattr(self,'initialising',False):   # InitNewGame's Interface::Reset: original code (recorded as the harness does)
            assert u.reg_read(self.regs[0])==self.GAME+INTERFACE;self.new_events.append([12,-1,0,0]);OVERLAY['reset']=OVERLAY.get('reset',0)+1
            self.until_return(u,'resetting');return
        if address in self.label_functions and not self.label_running and u.reg_read(self.regs[0])-self.GAME in DAMAGE_LABELS+(CURRENT_LABEL,):
            assert PROCESS<=lr<PROCESS_END,hex(lr)   # the damage labels' calls (Game::Process): original code
            n=self.label_functions[address];LABEL_CALLS[n]=LABEL_CALLS.get(n,0)+1;self.until_return(u,'label_running');return
        if self.label_running:   # the runtime's __divsi3 / __modsi3 modelled
            if address in (DIVSI3,MODSI3):
                a,b=(C.c_int32(u.reg_read(r)).value for r in self.regs[:2]);q=abs(a)//abs(b)*(1 if (a<0)==(b<0) else -1)
                u.reg_write(self.regs[0],(q if address==DIVSI3 else a-q*b)&0xffffffff);u.reg_write(self.PC,lr|1)
            return
        if self.starting:   # a main-menu new game: InitNewGame with the new-game harness; NameScreen::Show with the setup harness
            if address==INIT_NEW_GAME and START_LO<=lr<START_HI:self.until_return(u,'initialising');self.until_return(u,'gen_active');return
            if address==NAME_SHOW and START_LO<=lr<START_HI:self.until_return(u,'setting_up');return
            if address in self.start_skip and (START_LO<=lr<START_HI or lr==HELP_STATE_RETURN):
                self.start_skipped.append(self.start_skip[address]);u.reg_write(self.PC,lr|1);return
        if self.setting_up:   # the setup and story screens (T040-M3)
            inside=lambda *ranges:any(a<=lr<b for a,b in ranges)
            if address in (STRLEN,STRNCPY,MEMCPY,SPRINTF,STRCMP) and inside((NAME_SHOW,NAME_INPUT),RANDOM_NAME,SET_NAME):self.libc(u,address,lr);return
            if address==self.strip_contains and inside((NAME_INPUT,NAME_INPUT_END)):   # the pressed button
                u.reg_write(self.regs[0],int(u.reg_read(self.regs[0])==self.setup_target));u.reg_write(self.PC,lr|1);return
            if address==self.contains and inside((NAME_INPUT,NAME_INPUT_END)):u.reg_write(self.regs[0],0);u.reg_write(self.PC,lr|1);return   # the keyboard's keys
            if address==INIT_NEW_GAME and inside((NAME_INPUT,NAME_INPUT_END)):self.until_return(u,'initialising');self.until_return(u,'gen_active');return
            if address==INTRO_INIT and inside((NAME_INPUT,NAME_INPUT_END)):   # presentation; the fields IntroScreen::Process reads, as it leaves them
                I=self.GAME+INTRO;u.mem_write(I+0xc0,b'\1\0');self.write(I+0xc4,0);self.write(I+0xc8,1);self.write(I+0xbc,0)
                self.setup_skipped.append(INTRO_INIT);u.reg_write(self.PC,lr|1);return
            if address in self.func_starts and address not in self.setup_run and inside((NAME_SHOW,NAME_INPUT_END),SET_CURRENT,(INTRO_PROCESS,INTRO_INIT)):
                self.setup_skipped.append(address);u.reg_write(self.PC,lr|1);return   # display, sounds, the ClassScreen / ModeScreen / MainMenu
        if address==SERIALISE:SAVE_CALLS[0]+=1;self.until_return(u,'saving');return   # the save: original code (not the units' boundary)
        if address==SERIALISE_CLASSES:CLASS_SAVES[0]+=1;self.until_return(u,'classing');return   # the class records' save: original code
        if getattr(self,'classing',False):return
        if address in self.score_functions and not self.scoring:   # the high scores: original code
            n=self.score_functions[address];SCORE_CALLS[n]=SCORE_CALLS.get(n,0)+1;self.until_return(u,'scoring');return
        if self.scoring:
            if address==0x194fb0:   # strcpy
                d,src=u.reg_read(self.regs[0]),u.reg_read(self.regs[1])
                while True:
                    b=u.mem_read(src,1);u.mem_write(d,bytes(b));src+=1;d+=1
                    if not b[0]:break
                u.reg_write(self.PC,lr|1)
            return
        if self.loading:   # DeserialiseState: its presentation skipped, Set*Visibility's overlay quads as original code
            if address in self.load_skip:u.reg_write(self.PC,lr|1);return
            if address in self.overlay_quad and 0x3d89c<=lr<0x3d9a4:return
        if self.saving:   # Item::Serialise's achievement 72; Tile / Item / Skill / HelpMenu::Serialise, GetRandSeed run
            if address==QUEUE_ACHIEVEMENT:self.save_achievements.append(C.c_int32(u.reg_read(self.regs[1])).value);u.reg_write(self.PC,lr|1)
            return
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
        if address==GET_SPECIAL:   # the mana potion's skill slot: original code (not verify_motion's answer)
            self.write(u.reg_read(self.regs[0])+0x1030,self.GAME);SPECIAL_CALLS[0]+=1;self.until_return(u,'special_running');return
        if self.special_running:
            r=[u.reg_read(v) for v in self.regs];op=self.menu_set_ops.get(address)
            if op in ('init','insert','clear'):
                if op=='insert':self.k5_sets.setdefault(r[1],set()).add(C.c_int32(self.read(r[2])).value);self.k5_write_set(r[1])
                else:self.k5_sets[r[0]]=set();self.k5_write_set(r[0])
                u.reg_write(self.PC,lr|1);return
            if address==0x194d30:u.reg_write(self.regs[0],self.read(r[0]));u.reg_write(self.PC,lr|1);return
            if address in (0x194cec,0x194cf0,0x194cf4):u.reg_write(self.PC,lr|1);return
        if address==SHOW_MENU:   # (Game::Upgrade from a skill button, or from a scroll bought in the shop: a menu opened inside the menu)
            if not self.menu_running:self.until_return(u,'menu_running')
            self.until_return(u,'skill_input',False)
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
        if self.skill_input:
            r=[u.reg_read(v) for v in self.regs]
            if address==self.cursor:u.reg_write(self.regs[0],int(C.c_int32(r[1]).value==self.button));u.reg_write(self.PC,lr|1);return
            if address==self.contains and IFACE_INPUT<lr<IFACE_INPUT_END:   # the menu button (4) and the stats button (5)
                I=self.GAME+INTERFACE;assert r[0] in (I+0xbd4,I+0xc44),hex(r[0])
                u.reg_write(self.regs[0],int(self.button==(4 if r[0]==I+0xbd4 else 5)));u.reg_write(self.PC,lr|1);return
            if address in (GM_SHOW,SM_SHOW) and IFACE_INPUT<lr<IFACE_INPUT_END:
                n=self.overlay_count[address];OVERLAY[n]=OVERLAY.get(n,0)+1;self.until_return(u,'overlay_running');return
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
        self.u.mem_write(G+SAVE_BUFFER,bytes(0x800));self.u.mem_write(G+NAME,bytes(c['name'])+bytes(17-len(c['name'])))   # no save yet; the name
        self.u.mem_write(G+HELP_SWITCH,b'\0')   # help off (a new session's setting)
        N=G+NAME_SCREEN;self.write(N,G);self.write(G+INTRO,G)   # NameScreen / IntroScreen -> Game; their fields as a new session's
        self.u.mem_write(N+NAME_NAME,bytes(19));self.write(N+NAME_LENGTH,0);self.u.mem_write(N+NAME_NAMED,b'\0');self.u.mem_write(N+NAME_CHALLENGE,b'\0')
        for a in (MODE_CHANGED,DIFFICULTY_CHANGED,NAME_CHANGED):self.u.mem_write(G+a,b'\0')
        sc=c.get('release',{}).get('scroll',{});self.class_current=sc.get('current',0)
        if self.class_current:   # with_class: record 0 (as the loaders wrote it) is the current class's
            rec=G+CLASSES+CLASS_STRIDE*self.class_current;self.u.mem_write(rec,bytes(self.u.mem_read(G+CLASSES,CLASS_STRIDE)))
            type_,base,level=sc['classes'][self.class_current];self.write(rec+4,type_);self.write(rec+0xc,base);self.u.mem_write(rec+0x54,bytes([level]))
            self.write(G+CLASS_INDEX_ADDR,self.class_current)
        S=G+SCORE_SCREEN;self.u.mem_write(S+SCORE_TABLES,bytes(SCORE_SIZE));self.write(S+0xf18,0xffffffff);self.write(S+0xf1c,0xffffffff)   # ScoreScreen's constructor
        self.u.mem_write(G+CLASS_SAVE,bytes(472));self.write(G+CLASS_SAVE_LENGTH,0);self.u.mem_write(G+CLASS_SAVE_CHANGED,b'\0')
        cur=self.read(G+CLASS_INDEX_ADDR)
        for i in range(10):   # the record fields no loader writes: zero, as the native records (the current class's are the case's)
            rec=G+CLASSES+CLASS_STRIDE*i
            if i!=cur:self.u.mem_write(rec+8,bytes(4));self.u.mem_write(rec+0x10,bytes(32));self.u.mem_write(rec+0x58,bytes(20))
        if not self.names_ready:   # the item name tables, once
            u=self.u;self.naming=True;u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1)
            try:u.emu_start(NAMES_FN|1,self.STOP,timeout=0,count=5000000)
            finally:self.naming=False
            self.names_ready=True
        if not self.digits_ready:self.run_label(LABEL_DIGITS,1,0xffff);self.digits_ready=True   # the label digit tables, once
        for i,a in enumerate(DAMAGE_LABELS):   # SimpleLabel::SimpleLabel, then Game::Start: SetColour(17, 18, 19), duration 0.2
            at=bytes(self.u.mem_read(G+a+0x334,8))   # the case's label position (the release harness wrote it)
            self.u.mem_write(G+a,bytes(LABEL_SIZE));self.run_label(LABEL_CTOR,G+a);self.run_label(LABEL_COLOUR,G+a,17+i)
            self.write(G+a+0x34c,0x3e4ccccd);self.u.mem_write(G+a+0x334,at)
        # T040-M6: the current-damage label as Game::Start leaves it (SetColour(10), duration 0.2), not shown
        self.u.mem_write(G+CURRENT_LABEL,bytes(LABEL_SIZE));self.run_label(LABEL_CTOR,G+CURRENT_LABEL);self.run_label(LABEL_COLOUR,G+CURRENT_LABEL,10)
        self.write(G+CURRENT_LABEL+0x34c,0x3e4ccccd)
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
        for base in (G+GM,G+SM):   # T040-M5: GameMenu / StatsMenu -> Game, closed; the stats menu's labels in scratch memory
            self.write(base+8,G);self.u.mem_write(base+0xc,b'\0');self.write(base+0x10,0);self.write(base+0x14,0xffffffff);self.u.mem_write(base+0x18,b'\0');self.write(base+0x1c,0)
        for k in range(24):self.write(OVERLAY_SCRATCH+0x800+4*k,OVERLAY_SCRATCH+0x1000+0x40*k)
        for v in (0xdc,0xe8,0xf4):self.write(G+SM+v,OVERLAY_SCRATCH+0x800);self.write(G+SM+v+4,OVERLAY_SCRATCH+0x800+16)
        H=G+HELP_MENU;self.write(H+4,OVERLAY_SCRATCH+0x2000);self.write(H+8,G);self.u.mem_write(H+0xc,b'\0\0');self.write(H+0x10,0)
        self.write(H+0x24,0);self.write(H+0x34,0);self.write(H+0x3c,H+0x3c);self.write(H+0x40,H+0x3c);self.help_nodes=0;self.help_shows=[]
        self.u.mem_write(I+0xcb4,b'\0\0');self.u.mem_write(G+SETTINGS_BYTES,bytes(9));self.write(G+MAIN_MENU_OBJ+8,0);self.u.mem_write(G+MAIN_MENU_OBJ+0xc,b'\0')
    def set_button(self,button):self.button=button
    def match_status(self):   # the current class's type, level and race (Game::MatchTile reads them at Game+0x1648c's index)
        r=super().match_status()   # (the unit harness reads record 0; the setup screen can change the current class)
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
                    menu=self.menu_state(),save=self.save_state(),scores=bytes(self.u.mem_read(G+SCORE_SCREEN+SCORE_TABLES,SCORE_SIZE)).hex(),
                    labels=[bytes(self.u.mem_read(G+a,LABEL_SIZE)).hex() for a in DAMAGE_LABELS],flow=self.flow_state())
    def start_game(self,kind):   # Game::NewGame / StartTutorial / StartChallenge from the entry (as NewGameOriginal.run for InitNewGame)
        self.new_events=[];self.items_made=0;self.gen_events=[];self.pending_gen=None;self.start_skipped=[];self.setup_skipped=[];u=self.u
        u.reg_write(self.regs[0],self.GAME);u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1);self.starting=True
        try:u.emu_start(START_ENTRIES[kind]|1,self.STOP,timeout=0,count=3000000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.starting=self.initialising=self.gen_active=False
        assert sorted(self.start_skipped)==sorted(START_SKIP),self.start_skipped
        return dict(new_events=self.new_events,**self.gen_status())
    def flow_state(self):   # the main-menu flow fields (T040-M1) and the setup screen's (T040-M3)
        G=self.GAME;N=G+NAME_SCREEN;b=lambda a:self.u.mem_read(G+a,1)[0];i32=lambda a:C.c_int32(self.read(a)).value
        return dict(record=b(RECORD),difficulty=i32(G+DIFFICULTY),help=b(HELP_SWITCH),main_menu=b(MAIN_MENU),mode=i32(G+MODE),
                    changed=[b(DIFFICULTY_CHANGED),b(MODE_CHANGED),b(NAME_CHANGED)],name=bytes(self.u.mem_read(G+NAME,17)).hex(),
                    screens=[b(NAME_OPEN),b(INTRO_OPEN)],current=i32(G+CURRENT_CLASS),seeds=list(struct.unpack('<6I',self.u.mem_read(SEEDS,24))),
                    setup=[self.u.mem_read(N+NAME_CHALLENGE,1)[0],bytes(self.u.mem_read(N+NAME_NAME,19)).hex(),i32(N+NAME_LENGTH),self.u.mem_read(N+NAME_NAMED,1)[0]],
                    overlay=self.overlay_state())
    def overlay_state(self):   # T040-M5: the game and stats menus, Interface's touched buttons, the switches, the main menu's fade
        G=self.GAME;b=lambda a:self.u.mem_read(G+a,1)[0];i32=lambda a:C.c_int32(self.read(G+a)).value
        menu=lambda m:[b(m+0xc),i32(m+0x10),i32(m+0x14),b(m+0x18),self.read(G+m+0x1c)]
        return [menu(GM),menu(SM),list(self.u.mem_read(G+INTERFACE+0xcb4,2)),list(self.u.mem_read(G+SETTINGS_BYTES,9)),[self.read(G+MAIN_MENU_OBJ+8),b(MAIN_MENU_OBJ+0xc)],
                self.help_state()]
    def help_state(self):   # T040-M6: the popup, its queued texts, the queued topics and the texts shown so far
        G=self.GAME;H=G+HELP_MENU;b=lambda a:self.u.mem_read(a,1)[0];queue=[];node=self.read(H+0x3c)
        while node!=H+0x3c and len(queue)<70:queue.append(HELP_TEXT_IDS.get(self.read(node+8),-1));node=self.read(node)
        return [b(H+0xc),b(H+0xd),self.read(H+0x10),C.c_int32(self.read(H+0x24)).value,queue,self.read(H+0x38),len(self.help_shows)]+[help_show(s) for s in self.help_shows[-3:]]
    def help_popup(self):return dict(timer=struct.unpack('<f',struct.pack('<I',self.read(self.GAME+HELP_MENU+0x10)))[0])
    def libc(self,u,address,lr):   # strlen / strncpy / memcpy / strcmp / sprintf (%s only) for the setup screen
        r=[u.reg_read(x) for x in self.regs];cstr=lambda a:bytes(u.mem_read(a,64)).split(b'\0')[0]
        if address==STRLEN:res=len(cstr(r[0]))
        elif address==STRNCPY:src=cstr(r[1])[:r[2]];u.mem_write(r[0],src+bytes(r[2]-len(src)));res=r[0]
        elif address==MEMCPY:u.mem_write(r[0],bytes(u.mem_read(r[1],r[2])));res=r[0]
        elif address==STRCMP:x,y=cstr(r[0]),cstr(r[1]);res=(x>y)-(x<y)
        else:
            sp=u.reg_read(self.SP);fmt=cstr(r[1]);args=[r[2],r[3],self.read(sp),self.read(sp+4)];out=b'';i=k=0
            while i<len(fmt):
                if fmt[i:i+2]==b'%s':out+=cstr(args[k]);k+=1;i+=2
                else:out+=fmt[i:i+1];i+=1
            u.mem_write(r[0],out+b'\0');res=len(out)
        u.reg_write(self.regs[0],res&0xffffffff);u.reg_write(self.PC,lr|1)
    def setup_press(self,kind,arg=0):   # a touch down on the setup screen: NameScreen::ProcessInput from its entry (T040-M3)
        G=self.GAME;N=G+NAME_SCREEN;u=self.u
        if kind=='type':   # a name typed on the keyboard (the renderer's): the box as the keyboard leaves it
            u.mem_write(N+NAME_NAME,arg+b'\0');self.write(N+NAME_LENGTH,len(arg));u.mem_write(N+NAME_NAMED,b'\1');return {}
        self.setup_target=None if kind=='start' else N+SETUP_BUTTONS[kind](arg)
        if kind=='start':   # Start is shown (alpha 255) once NameScreen::Process's fade-in ends with a name entered
            u.mem_write(N+NAME_START_ALPHA,bytes([0xff if u.mem_read(N+NAME_NAMED,1)[0] and C.c_int32(self.read(N+NAME_LENGTH)).value>0 else 0]))
        self.write(G+0x10,1);u.mem_write(G+0x14,struct.pack('<ff',0.5,1.4 if kind=='start' else 0.5));self.write(N+NAME_PREVIOUS,0)
        self.new_events=[];self.items_made=0;self.gen_events=[];self.pending_gen=None;self.setup_skipped=[]
        u.reg_write(self.regs[0],N);u.reg_write(self.regs[1],struct.unpack('<I',struct.pack('<f',1/60))[0])
        u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1);self.setting_up=True
        try:u.emu_start(NAME_INPUT|1,self.STOP,timeout=0,count=3000000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.setting_up=self.initialising=self.gen_active=False
        self.write(G+0x10,0);return dict(new_events=self.new_events,**self.gen_status())
    def call(self,entry,*args):   # an original function from its entry with the setup harness (NameScreen::SelectClass skipped)
        u=self.u
        for r,v in zip(self.regs,args):u.reg_write(r,v&0xffffffff)
        u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1);self.setting_up=True
        try:u.emu_start(entry|1,self.STOP,timeout=0,count=3000000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:
            self.setting_up=False
            for undo in self.returns.pop(self.STOP&~1,[]):undo()   # flags set until the return (it returned to STOP)
        return u.reg_read(self.regs[0])
    def class_op(self,kind,a=0,b=0):   # ClassScreen::Process's drops and buttons as their calls (T040-M4b)
        G=self.GAME;rec=G+CLASSES+CLASS_STRIDE*self.read(G+CURRENT_CLASS)
        if kind=='select':
            if self.u.mem_read(G+CLASSES+CLASS_STRIDE*a+0x54,1)[0]:self.call(SET_CURRENT[0],G,a)
        elif kind=='race':
            if self.call(RACE_UNLOCKED,G,a)&0xff and self.call(CAN_CHOOSE,rec)&0xff:self.write(rec+8,a)
        elif kind in ('perk','flaw','skill'):self.call({'perk':SET_PERK,'flaw':SET_FLAW,'skill':SET_SKILL}[kind],rec,a,b)
        elif kind=='tab':self.call(SERIALISE_CLASSES,G)
        elif kind=='help':
            for text in CLASS_HELP[a]:self.call(QUEUE_HELP,G+HELP_MENU,text,0,0)
        else:self.call(VALIDATE,rec);self.call(SET_CURRENT[0],G,C.c_int32(self.read(rec+4)).value);self.call(SERIALISE_CLASSES,G)
    def record_state(self):   # the current class record and the class save
        G=self.GAME;rec=G+CLASSES+CLASS_STRIDE*self.read(G+CURRENT_CLASS);i32=lambda a:C.c_int32(self.read(a)).value
        lst=self.read(rec+0x48)
        return [i32(rec+8),[i32(rec+0x10+4*k) for k in range(4)],[i32(rec+0x20+4*k) for k in range(4)],[i32(lst+4*k) for k in range(20)],self.save_state()[3:]]
    def intro_finish(self):   # IntroScreen::Process: a frame fading in, then Continue (its fade-out ends in that frame: the save)
        G=self.GAME;u=self.u;self.setup_skipped=[];self.setting_up=True
        try:
            for phase,y in ((0,0.5),(1,1.4)):
                self.write(G+0x10,phase);u.mem_write(G+0x14,struct.pack('<ff',0.5,y))
                u.reg_write(self.regs[0],G+INTRO);u.reg_write(self.regs[1],0x3f800000);u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1)
                u.emu_start(INTRO_PROCESS|1,self.STOP,timeout=0,count=3000000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.setting_up=False
        self.write(G+0x10,0);assert u.mem_read(G+INTRO_OPEN,1)[0]==0
    def set_flow(self,help_queue,help,main_menu):
        G=self.GAME;self.write(G+HELP_QUEUE,help_queue);self.u.mem_write(G+HELP_SWITCH,bytes([help]));self.u.mem_write(G+MAIN_MENU,bytes([main_menu]))
    def run_label(self,entry,*args):   # a SimpleLabel function (or the digit tables' initialiser) from its entry to its return
        u=self.u;u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1);self.label_running=True
        for r,v in zip(self.regs,args):u.reg_write(r,v&0xffffffff)
        try:u.emu_start(entry|1,self.STOP,timeout=0,count=200000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:self.label_running=False
    def run_entry(self,entry,flags):   # an original function from its entry to its return, with harness flags set
        u=self.u;u.reg_write(self.regs[0],self.GAME);u.reg_write(self.SP,0x140fe00);u.reg_write(self.LR,self.STOP|1)
        for f in flags:setattr(self,f,True)
        try:u.emu_start(entry|1,self.STOP,timeout=0,count=5000000);assert u.reg_read(self.PC)==self.STOP,hex(u.reg_read(self.PC))
        finally:
            for f in flags:setattr(self,f,False)
        return u.reg_read(self.regs[0])&0xff
    def continue_game(self):   # Game::ContinueGame: InitNewGame (the new-game harness), DeserialiseState, CalculateTilePositions
        NewGameOriginal.run(self);self.run_entry(DESERIALISE,['loading','gen_active']);self.run_entry(TILE_POSITIONS,['initialising','gen_active'])
        u=self.u;u.reg_write(self.regs[0],self.GAME+INTERFACE);u.reg_write(self.regs[1],0);u.reg_write(self.regs[2],0);u.reg_write(self.SP,0x140fe00)
        u.reg_write(self.LR,self.STOP|1);u.emu_start(IFACE_PROCESS|1,self.STOP,timeout=0,count=1000000);assert u.reg_read(self.PC)==self.STOP   # Interface::Process(0, false)
        for undo in self.returns.pop(self.STOP&~1,[]):undo()   # ProcessHeartbeat returned to STOP
        self.class_current=True;self.moving_list=[self.index(v) for v in self.list_values(self.GAME+0xb3f8)]
    def save_state(self):   # the saved game: length, changed flag and bytes
        G=self.GAME;n=C.c_int32(self.read(G+SAVE_LENGTH)).value
        k=C.c_int32(self.read(G+CLASS_SAVE_LENGTH)).value
        return [n,self.u.mem_read(G+SAVE_CHANGED,1)[0],bytes(self.u.mem_read(G+SAVE_BUFFER,max(0,min(n,0x800)))).hex(),
                k,self.u.mem_read(G+CLASS_SAVE_CHANGED,1)[0],bytes(self.u.mem_read(G+CLASS_SAVE,max(0,min(k,472)))).hex()]
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
        self.sources={};self.help_shows=[]
        def event(_,source,p):
            k=(source,C.cast(p,C.POINTER(I32))[1 if source==6 else 0]);self.sources[k]=self.sources.get(k,0)+1   # (unit, event kind) seen in play (RoundEvent: kind second)
            if source==SOURCE_NEW_GAME:
                e=C.cast(p,C.POINTER(I32*4)).contents;self.new_events.append(list(e))
            elif source==SOURCE_GENERATION:
                e=C.cast(p,C.POINTER(I32*6)).contents;self.gen_events.append(list(e))
            elif source==SOURCE_INTERFACE and C.cast(p,C.POINTER(I32))[0]==4:   # T040-M6: a text shown, with the popup's position and size
                h=HelpPopup.from_address(self.session_lib.dr_session_objects(self.session).help);bits=lambda x:struct.unpack('<I',struct.pack('<f',x))[0]
                self.help_shows.append([h.text,bits(h.at.x),bits(h.at.y),bits(h.width),bits(h.height)])
        def get_target(_,kind,index,out):out[0]=Point(*motion_target(kind,index))
        def start(_,kind,out):out[0]=Point(*TARGET_POINT)
        self.host_cb=(EVENT(event),TARGET(get_target),START(start));self.host=Host(None,*self.host_cb)
    def load(self,c):
        if self.session:self.q=self.own_queue   # the loaders replace the harness's own token queue, not the session's
        super().load(c);lib=self.session_lib;self.own_queue=self.q
        if self.session:lib.dr_session_destroy(self.session)
        self.session=lib.dr_session_create(C.byref(self.host),1);o=lib.dr_session_objects(self.session);self.help_shows=[]
        # the case, as the harness loaders built it, becomes the session's state
        pairs=dict(stroke=self.state,preview=self.p,match=self.m,rune=self.rune,resources=self.r,path=self.path_state,refill=self.refill,
                   generation=self.gen,damage=self.damage,animation=self.anim,overlay_alpha=self.overlay,attack_inputs=self.inputs,
                   skills=self.skills,turn_flags=self.turn_flags,finish=self.fin_flags,end=self.flags,activated=self.flags_254,
                   end_of_turn=self.eot_state,flights=self.flights,release_inputs=self.release_inputs,classes=self.classes,
                   scroll=self.scroll_state,player=getattr(self,'player',None),extra=self.extra,shatter=self.shatter,touch=self.touch,
                   screens=self.screens)
        pairs={k:v for k,v in pairs.items() if v is not None}   # the carried harness has no PlayerStats (zero)
        for name,obj in pairs.items():C.memmove(getattr(o,name),C.addressof(obj),C.sizeof(obj))
        ri=self.release_inputs   # the case's damage label positions are the labels' (SimpleLabel+0x334)
        for i,p in enumerate((ri.leech_label,ri.flame_label,ri.spike_label)):C.memmove(o.damage_labels+LABEL_SIZE*i+0x334,C.addressof(p),8)
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
        cls=self.classes[self.scroll_state.current];sel=self.state.selection   # the current class record is what the units read
        cls.race=sel.character.race;cls.perks=(I32*4)(*self.m.perks);cls.flaws=(I32*4)(*sel.character.flaws)
        for k,v in c.get('cls',{}).items():setattr(cls,k,v)   # its progress (Game::GameOver adds to it; SerialiseClasses saves it)
        self.save=(U8*0x800).from_address(o.save);C.memmove(o.name,bytes(c['name'])+bytes(17-len(c['name'])),17)
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
                    skill_count=r.skill_count,items=items,k5=self.k5_status(),menu=self.menu_state(),save=self.save_state(),
                    scores=bytes((U8*SCORE_SIZE).from_address(self.session_lib.dr_session_objects(self.session).scores)).hex(),
                    labels=[bytes((U8*LABEL_SIZE).from_address(self.session_lib.dr_session_objects(self.session).damage_labels+LABEL_SIZE*i)).hex() for i in range(3)],
                    flow=self.flow_state())
    def flow_state(self):
        o=self.session_lib.dr_session_objects(self.session);settings=(U8*4).from_address(o.settings);n=Setup.from_address(o.setup)
        return dict(record=self.state.record,difficulty=self.m.spawn_enabled_14ae0,help=settings[0],main_menu=self.screens.main_menu_c400,mode=self.state.mode,
                    changed=[settings[1],settings[2],settings[3]],name=bytes((U8*17).from_address(o.name)).hex(),
                    screens=[self.screens.name_12c09,self.screens.intro_c3f0],current=self.scroll_state.current,seeds=list(self.m.random.seeds),
                    setup=[n.challenge,bytes(n.name).hex(),n.length,n.named],overlay=self.overlay_state())
    def overlay_state(self):
        o=self.session_lib.dr_session_objects(self.session);settings=(U8*12).from_address(o.settings);bits=lambda x:struct.unpack('<I',struct.pack('<f',x))[0]
        menu=lambda m,k:[self.screens.menus[k],m.previous_phase,m.pressed,m.closing,bits(m.timer)];mm=MainMenuScreen.from_address(o.main_menu)
        return [menu(Overlay.from_address(o.game_menu),1),menu(Overlay.from_address(o.stats_menu),2),list((U8*2).from_address(o.interface_buttons)),
                [settings[i] for i in SETTINGS_NATIVE],[bits(mm.timer),mm.fading],self.help_state()]
    def help_state(self):
        o=self.session_lib.dr_session_objects(self.session);h=HelpPopup.from_address(o.help);bits=lambda x:struct.unpack('<I',struct.pack('<f',x))[0]
        return [self.screens.help_102a4,h.closing,bits(h.timer),h.previous_phase,list(h.queue[:h.queued]),self.fin_flags.help_flags_102d0,
                len(self.help_shows)]+[help_show(s) for s in self.help_shows[-3:]]
    def help_popup(self):
        o=self.session_lib.dr_session_objects(self.session);return HelpPopup.from_address(o.help)
    def overlay_menu(self,k):
        o=self.session_lib.dr_session_objects(self.session);return Overlay.from_address(o.game_menu if k==1 else o.stats_menu)
    def setup_press(self,kind,arg=0):
        lib=self.session_lib;s=self.session;self.new_events=[];self.gen_events=[]
        for f,a in (('dr_session_setup_random_name',[]),('dr_session_setup_select_class',[I32]),('dr_session_setup_mode',[I32]),
                    ('dr_session_setup_difficulty',[I32]),('dr_session_setup_start',[C.c_uint32])):
            getattr(lib,f).argtypes=[C.c_void_p,*a];getattr(lib,f).restype=C.c_bool if a else None
        if kind=='type':   # a name typed on the keyboard (the renderer's)
            n=Setup.from_address(lib.dr_session_objects(s).setup);C.memmove(n.name,arg+b'\0',len(arg)+1);n.length=len(arg);n.named=1;result=True
        elif kind=='random':lib.dr_session_setup_random_name(s);result=True
        elif kind=='help':lib.dr_session_setup_help.argtypes=[C.c_void_p];lib.dr_session_setup_help.restype=None;lib.dr_session_setup_help(s);result=True
        elif kind=='klass':result=lib.dr_session_setup_select_class(s,arg)
        elif kind=='mode':result=lib.dr_session_setup_mode(s,arg)
        elif kind=='difficulty':result=lib.dr_session_setup_difficulty(s,arg)
        else:result=lib.dr_session_setup_start(s,self.case_time)
        self.sync();return result
    def class_op(self,kind,a=0,b=0):
        lib=self.session_lib;s=self.session
        for f,n in (('dr_session_class_select',1),('dr_session_class_set_race',1),('dr_session_class_set_perk',2),('dr_session_class_set_flaw',2),
                    ('dr_session_class_set_skill',2),('dr_session_class_tab',0),('dr_session_class_done',0)):
            getattr(lib,f).argtypes=[C.c_void_p]+[I32]*n;getattr(lib,f).restype=C.c_bool if n==1 else None
        if kind=='help':lib.dr_session_class_help.argtypes=[C.c_void_p,I32];lib.dr_session_class_help.restype=C.c_bool;lib.dr_session_class_help(s,a)
        elif kind in ('select','race'):getattr(lib,'dr_session_class_'+('select' if kind=='select' else 'set_race'))(s,a)
        elif kind in ('perk','flaw','skill'):getattr(lib,'dr_session_class_set_'+kind)(s,a,b)
        else:getattr(lib,'dr_session_class_'+kind)(s)
        self.sync()
    def record_state(self):
        o=self.session_lib.dr_session_objects(self.session);c=self.classes[self.scroll_state.current];sel=self.state.selection
        return [sel.character.race,list(self.m.perks),list(sel.character.flaws),list(c.replacement_skills[:20]),self.save_state()[3:]]
    def intro_finish(self):
        lib=self.session_lib;lib.dr_session_intro_done.argtypes=[C.c_void_p];lib.dr_session_intro_done.restype=None
        lib.dr_session_intro_done(self.session);self.sync()
    def set_flow(self,help_queue,help,main_menu):
        settings=(U8*2).from_address(self.session_lib.dr_session_objects(self.session).settings)
        self.fin_flags.help_flags_102d0=help_queue;settings[0]=help;self.screens.main_menu_c400=main_menu
    def start_game(self,kind,time):
        lib=self.session_lib;lib.dr_session_start_game.argtypes=[C.c_void_p,I32,C.c_uint32];lib.dr_session_start_game.restype=None
        self.new_events=[];self.gen_events=[];lib.dr_session_start_game(self.session,kind,time);self.sync()
    def save_state(self):
        n=self.flags.flag_146d0;o=self.session_lib.dr_session_objects(self.session);cs=(U8*480).from_address(o.class_save)
        k=C.c_int32.from_address(o.class_save+472).value
        return [n,self.flags.flag_146d4,bytes(self.save[:max(0,min(n,0x800))]).hex(),k,cs[476],bytes(cs[:max(0,min(k,472))]).hex()]
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
    def continue_game(self,time):
        lib=self.session_lib;lib.dr_session_continue_game.argtypes=[C.c_void_p,C.c_uint32];lib.dr_session_continue_game.restype=C.c_bool
        self.new_events=[];self.gen_events=[];assert lib.dr_session_continue_game(self.session,time);self.sync()
    def set_button(self,button):
        o=self.session_lib.dr_session_objects(self.session);I32.from_address(o.skill_button).value=button
    def set_menu_button(self,button):
        o=self.session_lib.dr_session_objects(self.session);I32.from_address(o.menu_button).value=button
    def set_label_active(self,active):
        o=self.session_lib.dr_session_objects(self.session);U8.from_address(o.current_label_active).value=active
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
    menus_seen={};items_rng=random.Random(0x14c04);rng=random.Random(0x5e55);overlay_rng=random.Random(0x32580);frames=turns=moves=ended=presses=busy_presses=busy_blocked=0;routes={};sources={};phases={};used={}
    help_rng=random.Random(0x38128)
    def with_help(c,game):   # T040-M6: every topic queued in some carried games
        if game%3==0 and game<SKILL_GAMES-PROMOTE_GAMES:c['release']['help_flags']=c['finish']['help_flags_102d0']=0x7fffff   # (both loaders)
        return c
    def signed_states(x):
        if isinstance(x,dict):return {k:(C.c_int32(v).value if k=='enemy_state' and isinstance(v,int) else signed_states(v)) for k,v in x.items()}
        if isinstance(x,list):return [signed_states(v) for v in x]
        return x
    def compare(stage,a,b,**info):
        a,b=state_only(signed_states(a)),state_only(signed_states(b))
        if a!=b:
            (HERE/'session_failure.json').write_text(json.dumps(dict(stage=stage,info=info,original=a,native=b),indent=2,default=str))
            raise AssertionError(f'session_failure.json ({stage})')
    def play(old,new,game,count,skills=False,first_path=None,quit=False):
        nonlocal frames,turns,moves,ended,presses,busy_presses,busy_blocked;ready_before=1
        for turn in range(count):
            count_=new.r.skill_count;quitting=quit and turn==0
            if quitting or overlay_rng.random()<OVERLAY_CHANCE:   # T040-M5: the menu or stats button pressed and released (anywhere)
                which=4 if quitting or overlay_rng.random()<.6 else 5;path=[]
                script=[(1,('button',which)),(overlay_rng.choice([2,2,3]),('button',overlay_rng.choice([which,which,-1])))];pressed_type=None
            elif skills and count_>0 and rng.random()<.75:   # a skill button pressed and released (sometimes released on another)
                # mostly the equipped skill used least so far (then the turn's slot), so that every type gets used
                button=min(range(count_),key=lambda k:(used.get(new.skills.id[k],0),(k-turn)%count_)) if rng.random()<.9 else rng.randrange(count_)
                release=button if rng.random()<.92 else rng.randrange(-1,4)
                script=[(1,('button',button)),(2,('button',release))];presses+=1;path=[]
                pressed_type,used_before=new.skills.id[button],new.sources.get((SOURCE_SKILL,SKILL_USED),0)
            else:
                path=first_path if first_path and turn==0 else new.pick_path(rng);moves+=len(path)>=3
                script=[(1,i) for i in path]+[(2,path[-1])] if len(path)>=3 else []
            busy=len(script)+rng.randrange(1,12) if skills and count_>0 and len(path)>=3 and rng.random()<.6 else None   # a press while the turn runs
            menu_plan=[];menu_taps=0;menu_open=False;overlay_plan=[];overlay_taps=0;help_plan=[];step=0
            for frame in range(3000):
                dt=f32((help_rng if new.screens.help_102a4 else rng).choice([1/60,1/30]))   # (the help popup's frames: their own draws)
                button=-1;paused=False
                new.set_label_active(old.u.mem_read(old.GAME+CURRENT_LABEL,1)[0])   # T040-M6: the renderer's current-damage label
                if step<len(script):
                    phase,i=script[step]
                    if isinstance(i,tuple):button,touch=i[1],BUTTON_TOUCH
                    else:centre=new.state.selection.tiles[i].geometry.center;touch=[centre.x,centre.y]
                else:phase,touch=0,[0.5,0.5]
                if busy is not None and frame in (busy,busy+1):
                    phase,touch,button=1 if frame==busy else 2,BUTTON_TOUCH,turn%count_
                    if frame==busy:busy_presses+=1;busy_blocked+=not ready_before
                menu_button=-1
                if not new.screens.help_102a4:help_plan=[]
                if new.screens.help_102a4:   # T040-M6: the help popup (the game pauses, the script waits): after the fade the touch
                    h=new.help_popup();button=-1;paused=True   # ends, sometimes a touch outside the box, then one inside
                    if not help_plan and h.timer<=0 and not h.closing:
                        help_plan+=[(0,HELP_OUT,-1)]+([(1,HELP_OUT,-1),(0,HELP_OUT,-1)] if help_rng.random()<.25 else [])+[(1,HELP_IN,0)]
                    phase,touch,menu_button=help_plan.pop(0) if help_plan else (0,HELP_OUT,-1)
                    if phase==1:k='tap_in' if menu_button>=0 else 'tap_out';HELP[k]=HELP.get(k,0)+1
                elif new.screens.menus[0]:   # the FoldoutMenu: wait for the animation, choose (two in the level-up menu), confirm
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
                elif new.screens.menus[1] or new.screens.menus[2]:   # T040-M5: after the fade, taps (switches, tabs), then close
                    k=1 if new.screens.menus[1] else 2;m=new.overlay_menu(k);touch=BUTTON_TOUCH;button=-1;o=overlay_rng
                    if not overlay_plan and m.timer<=0:
                        if overlay_taps<4 and o.random()<.7:
                            b=o.choice([10,11,12,13,14,10,12,13,14,-1,o.randrange(9,15)]) if k==1 else o.choice([10,11,12,13,14,15,0,o.randrange(10,16)])
                            overlay_plan+=[(0,-1),(1,b),(o.choice([2,2,3]),o.choice([b,b,b,-1]))];overlay_taps+=1
                        else:b=(15 if quitting else 9) if k==1 else -1;overlay_plan+=[(0,-1),(1,b),(2,b)]
                    phase,menu_button=overlay_plan.pop(0) if overlay_plan else (0,-1)
                    if k==2 and phase==1 and menu_button>=10 and menu_button!=m.pressed:OVERLAY['tab']=OVERLAY.get('tab',0)+1
                else:
                    menu_open=False;menu_plan=[];menu_taps=0;overlay_plan=[];overlay_taps=0
                old.set_menu_button(menu_button);new.set_menu_button(menu_button)
                old.set_button(button);new.set_button(button)
                if not script and frame==0:old.set_ready(0);new.set_ready(0)
                info=dict(game=game,turn=turn,frame=frame,phase=phase)
                if 0<=button<4:info.update(button=button,skill=new.skills.id[button],skills=list(new.skills.id),count=new.r.skill_count)
                a,b=old.play_frame(phase,touch,dt),new.play_frame(phase,touch,dt);compare('frame',a,b,**info);frames+=1;ready_before=a['common']['input_ready']
                routes[new.frame_route]=routes.get(new.frame_route,0)+1
                if new.frame_route==11 or new.flags.game_over_screen:ended+=1;return
                if new.screens.main_menu_c400:assert quitting;return   # T040-M5: quit to the main menu (the game menu stays open beneath it)
                if not paused:step+=1
                if step>=len(script) and a['common']['input_ready'] and a['common']['phase']==0 and not new.moving_list and not a['common']['pending'] and not any(new.screens.menus) and not new.screens.help_102a4:break
            else:raise AssertionError('turn did not finish')
            if script and isinstance(script[0][1],tuple) and pressed_type is not None and new.sources.get((SOURCE_SKILL,SKILL_USED),0)>used_before:
                used[pressed_type]=used.get(pressed_type,0)+1
            turns+=1
    old,new=NewGameSessionOriginal(),NewGameSession()
    for game in range(GAMES):
        c=with_items(case(rng),items_rng);old.load(c);new.load(c)
        kind=(game//3)%3;flow=[rng.getrandbits(32),rng.randrange(2),1]   # from the main menu: queued help, help switch
        old.set_flow(*flow);new.set_flow(*flow);STARTS[kind]=STARTS.get(kind,0)+1
        a=old.start_game(kind);new.start_game(kind,c['new_game']['time'])
        compare('init events',[a['new_events'],a['events']],[new.new_events,new.gen_events],game=game)
        compare('setup',old.flow_state(),new.flow_state(),game=game)
        # T040-M3: the setup screen's buttons in some order (a wrong-kind or locked press does nothing), then Start
        naming=[('random',0)]*rng.choice([0,0,1,2])
        if rng.random()<.5 or game%3==0:   # a typed name (up to 17 characters: SetName keeps 16), last in some games
            naming.insert(len(naming) if game%3==0 else 0,('type',bytes(rng.randrange(65,91) for _ in range(17 if game%3==0 else rng.choice([1,8,16])))))
        unlocked=[i for i in range(1,10) if c['new_game']['classes'][i][2]]   # an unlocked class first, then any (a locked one: no change)
        classes=([('klass',rng.choice(unlocked))] if unlocked else [])+[('klass',rng.randrange(10)) for _ in range(rng.choice([1,2]))]
        others=[('mode',rng.randrange(2)) if kind==2 else ('difficulty',rng.randrange(4))]
        if rng.random()<.3:others.append(('difficulty',rng.randrange(4)) if kind==2 else ('mode',rng.randrange(2)))
        rng.shuffle(others);setup_presses=naming+classes+others
        if not c['name']:setup_presses=[('start',0)]+setup_presses+([] if any(k in ('random','type') for k,_ in setup_presses) else [('random',0)])   # Start without a name: nothing
        if rng.random()<.7:   # T040-M4b: the class screen (before Start)
            races=[k[1] for k in c['new_game']['classes'] if k[2]>=5]+[0]   # base races likely unlocked (a level-5 class)
            levels=[k[2] for k in c['new_game']['classes']];high=[i for i in range(1,10) if levels[i]>=5];locked=[i for i in range(1,10) if not levels[i]]
            ops=[('select',rng.choice(high or unlocked or [0]),0)]+([('select',rng.choice(locked),0)] if locked else [])+[rng.choice([('race',rng.choice(races+[rng.randrange(11)]),0),('select',rng.randrange(10),0),('perk',rng.randrange(-1,5),rng.choice([255,rng.randrange(10)])),
                 ('flaw',rng.randrange(-1,5),rng.choice([255,rng.randrange(10)])),('skill',rng.randrange(-1,21),rng.choice([255,rng.randrange(40)])),('tab',0,0)])
                 for _ in range(rng.randrange(2,8))]+[('done',0,0)]
            if high:ops.insert(2,('race_pick',0,0))   # a race the original unlocks, other than the class's own
            if help_rng.random()<.5:ops.insert(help_rng.randrange(1,len(ops)),('help',help_rng.randrange(4),0))   # T040-M6: a tab's help
            for op in ops:
                if op[0]=='race_pick':
                    G=old.GAME;rec=G+CLASSES+CLASS_STRIDE*old.read(G+CURRENT_CLASS);own=C.c_int32(old.read(rec+8)).value
                    picks=[r for r in rng.sample(range(10),10) if r!=own and old.call(RACE_UNLOCKED,G,r)&0xff]
                    if not picks:continue
                    op=('race',picks[0],0)
                old.class_op(*op);new.class_op(*op);CLASS_OPS[op[0]]=CLASS_OPS.get(op[0],0)+1
                compare('class screen',[old.flow_state(),old.record_state()],[new.flow_state(),new.record_state()],game=game,op=op)
        if help_rng.random()<.4:setup_presses.insert(help_rng.randrange(len(setup_presses)+1),('help',0))   # T040-M6: the help button
        for press in setup_presses+[('start',0)]:
            a=old.setup_press(*press);result=new.setup_press(*press);key=f'{press[0]}:{int(result)}';SETUPS[key]=SETUPS.get(key,0)+1
            compare('setup',old.flow_state(),new.flow_state(),game=game,press=press)
        assert result,'started'
        compare('init events',[a['new_events'],a['events']],[new.new_events,new.gen_events],game=game)
        old.intro_finish();new.intro_finish();compare('intro',old.flow_state(),new.flow_state(),game=game)
        old.moving_list=[old.index(v) for v in old.list_values(old.GAME+0xb3f8)]
        if game%3==1:set_health(old,new,rng.choice([2,4,6]))   # weakened after the start: enemies end the game early
        elif game%3==2:set_health(old,new,1000,1000)            # strengthened: long games, later enemies
        compare('after init',old.game_state(),new.game_state(),game=game)
        play(old,new,game,LONG_TURNS if game%3==2 else TURNS)
        if game%3!=1 and not old.read(old.GAME+0xcac4)&0xff:   # T030-N5: quit, then Continue from the saved game and play on
            assert old.read(old.GAME+SAVE_LENGTH),'no save'
            old.continue_game();new.continue_game(c['new_game']['time'])
            compare('continue',old.game_state(),new.game_state(),game=game);CONTINUES[0]+=1
            play(old,new,game,TURNS,quit=game%3==0)   # T040-M5: some quit to the main menu from the game menu at once
            if new.screens.main_menu_c400:   # then a new game from the main menu: InitNewGame's Interface::Reset closes the game menu
                assert new.screens.menus[1];a=old.start_game(kind);new.start_game(kind,c['new_game']['time']);OVERLAY['restart']=OVERLAY.get('restart',0)+1
                compare('restart',[a['new_events'],a['events'],old.flow_state()],[new.new_events,new.gen_events,new.flow_state()],game=game)
    phases['new_games']=dict(games=GAMES,turns=turns,frames=frames,ended=ended);sources.update(new.sources)
    old,new=CarriedSessionOriginal(),CarriedSession()
    for game in range(CARRIED_GAMES):
        c=with_items(variant(turn_case(rng),game),items_rng);old.load(c);new.load(c)
        if game%2==0 and game%5!=1:set_health(old,new,5000,5000)   # most carried boards end the game within a turn
        elif game%5==2:set_health(old,new,2)   # T030-N5d: a record-mode game that ends (ScoreScreen::AddScore, GameMode)
        compare('load',old.game_state(),new.game_state(),game=game)
        play(old,new,GAMES+game,CARRIED_TURNS)
    phases['carried']=dict(games=CARRIED_GAMES,turns=turns-phases['new_games']['turns'],frames=frames-phases['new_games']['frames'],
                           ended=ended-phases['new_games']['ended'])
    for k,v in new.sources.items():sources[k]=sources.get(k,0)+v
    class_rng=random.Random(0x25526)   # T040-K5b: the current class (the menus' skill pools) in the item and skill phases
    mana_rng=random.Random(0x20358)    # T040-L1: mana potions in the item and skill phases
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
        with_help(with_mana(with_class(c,class_rng),mana_rng),game+1)
        old.load(c);new.load(c);set_health(old,new,5000,5000)
        compare('load',old.game_state(),new.game_state(),game=game)
        play(old,new,200+game,CARRIED_TURNS,first_path=long)
    phases['items']={k:v-mark[k] for k,v in dict(turns=turns,frames=frames,ended=ended).items()};mark=dict(turns=turns,frames=frames,ended=ended)
    for k,v in new.sources.items():sources[k]=sources.get(k,0)+v
    assert sources.get((23,7),0)>0 and sources.get((29,28),0)>0,(sources.get((23,7)),sources.get((29,28)))   # IncreaseStat, DestroyUpgrade
    rng=random.Random(0x2ad40)   # the skill phase's own sequence (independent of the phases before it)
    old,new=CarriedSessionOriginal(),CarriedSession();mark=dict(turns=turns,frames=frames,ended=ended)
    for game in range(SKILL_GAMES):
        c=with_help(with_mana(with_class(with_items(skill_variant(turn_case(rng),rng,game),items_rng),class_rng),mana_rng),game);old.load(c);new.load(c);set_health(old,new,5000,5000)
        compare('load',old.game_state(),new.game_state(),game=game)
        play(old,new,100+game,SKILL_TURNS if game<SKILL_GAMES-PROMOTE_GAMES else 5*SKILL_TURNS,skills=True)
    phases['skills']=dict(games=SKILL_GAMES,presses=presses,presses_while_busy=busy_presses,presses_input_not_ready=busy_blocked,used={k:used[k] for k in sorted(used)},**{k:v-mark[k] for k,v in dict(turns=turns,frames=frames,ended=ended).items()})
    for k,v in new.sources.items():sources[k]=sources.get(k,0)+v
    assert phases['new_games']['ended'] and phases['carried']['ended'],phases
    assert REQUIRED<=set(sources),REQUIRED-set(sources)
    assert busy_blocked>20 and sources.get((SOURCE_SKILL,SKILL_JUMP),0)>0,(busy_blocked,sources.get((SOURCE_SKILL,SKILL_JUMP)))
    assert set(used)==set(SKILL_TYPES) and sources.get((SOURCE_SKILL,SKILL_FLAME),0)>3,(set(SKILL_TYPES)-set(used),sources.get((SOURCE_SKILL,SKILL_FLAME)))
    assert set(menus_seen)=={0,1,2},menus_seen
    assert all(OVERLAY.get(k,0) for k in ('game_menu','stats_menu','closed','sound','help','clock','dimming','framerate','quit','tab','reset','restart')),OVERLAY
    assert set(range(23))|set(range(100,105))|{'tap_in','tap_out'}<=set(HELP) and len([k for k in HELP if isinstance(k,int) and k>=105])>=8,HELP
    assert SPECIAL_CALLS[0]>0,SPECIAL_CALLS   # mana potion tokens: Interface::GetSpecialTarget
    assert all(LABEL_CALLS.get(n,0)>0 for n in LABEL_FUNCTIONS),LABEL_CALLS   # the damage labels shown, moved, renumbered, dimmed, faded
    assert SAVE_CALLS[0]>100 and CONTINUES[0]>0 and CLASS_SAVES[0]>0 and len(SCORE_CALLS)==3,(SAVE_CALLS,CONTINUES,CLASS_SAVES,SCORE_CALLS)   # saves; continued games; class saves; scores
    report=dict(status='passed',phases=phases,menus=dict(sorted(menus_seen.items())),special_targets=SPECIAL_CALLS[0],saves=SAVE_CALLS[0],continued=CONTINUES[0],class_saves=CLASS_SAVES[0],starts=STARTS,class_ops=dict(sorted(CLASS_OPS.items())),help={str(k):v for k,v in sorted(HELP.items(),key=lambda kv:str(kv[0]))},overlay=dict(sorted(OVERLAY.items())),setup_presses=dict(sorted(SETUPS.items())),label_calls={n.split('SimpleLabel')[1]:v for n,v in LABEL_CALLS.items()},score_calls={k.split('E')[-1] if 'AddScore' in k else 'SetSkills':v for k,v in SCORE_CALLS.items()},turns=turns,moves=moves,frames=frames,games_ended=ended,frame_routes=routes,
                events_by_unit_kind={f'{k[0]}:{k[1]}':v for k,v in sorted(sources.items())},
                original='Original InitNewGame (new games) or a loaded state (carried), then the whole original Game::Process every frame',
                native='One recovered_session: dr_session_new_game (new games), then dr_session_frame (the session wires every unit itself)',
                boundaries=['time() returns the case seed',
                            'the harness picks the paths, the skill button and the menu button under the touch; GameMenu / StatsMenu closed',
                            'the current-damage label (Game+0xb550) runs as original code (its active byte given to the session); the label pools stay presentation',
                            'events and presentation mirrors not compared here (unit tests)'],
                scope='games from their start through many turns up to the end of the game, carried mid-game states, skill use, items, the three menus, saves, continued games and high scores')
    (HERE/'session_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
