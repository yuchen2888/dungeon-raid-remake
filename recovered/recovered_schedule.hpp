#pragma once
#include "recovered_attack_shield.hpp"
#include "recovered_rune.hpp"
#include "recovered_turn.hpp"
#include "recovered_stats.hpp"
namespace dungeonraid {
// Inputs of the ProcessInput gate owned outside the recovered states.
struct InputGateInputs {
    std::uint32_t falling_count;   // Game+0xb3f8 std::list<Tile*> size (moving tiles, embedding-owned)
    std::int32_t tokens_pending;   // Game+0xb52c (TokenQueueCounters.pending)
    std::int32_t flare_count;      // Game+0xbd8c (AttackAnimation.flare_count)
    std::int32_t touch_phase;      // Game+0x10
    std::int32_t input_target;     // Game+0x58ac: active skill/menu input target, -1 = none
};
// Blocked: returned before any state change. Idle: gate passed (phase 0, input ready) with no touch
// to dispatch. Dispatch: gate passed and the touch must be dispatched.
enum class InputGate : std::int32_t { Blocked=0, AttackStarted, Idle, Dispatch };
struct ScheduleHooks {
    void* context;
    // Game::EndOfTurn: wire to dr_end_of_turn.
    void (*end_of_turn)(void*);
};
// A damage label flying to its target after release (advanced by Game::Process: speed += 10dt,
// progress += speed*dt up to 1, arc lifts the interpolated path).
struct LabelFlight { float arc; Point start; float progress, speed; };
// Release state not owned by another recovered module.
struct ReleaseFlights {
    LabelFlight flame;   // Game+0x14e5c
    LabelFlight spike;   // Game+0x151d0
    LabelFlight leech;   // Game+0xc31c
};
// Renderer-owned positions read on release.
struct ReleaseInputs {
    Point flame_label;     // flame damage label position, Game+0x14e30
    Point spike_label;     // spike damage label position, Game+0x151a4
    Point leech_label;     // leech label position, Game+0xc2f4
    Point health_target;   // Interface::GetTarget(0)
};
struct ReleaseState {
    PathState* path;               // match->stroke selection; battle kill/killed counters; combat attack
    GenerationState* generation;   // generated_count / generated_enemies
    ResourceState* resources;      // health, health_max, health_bonus, ui_health
    TurnFlags* flags;              // prev_164a7, b165b8[0]
    TurnFinishFlags* finish;       // flag_1554c, help_flags_102d0
    ReleaseFlights* flights;
};
// Sound: a=sound. Help: HelpMenu::Initialise(Game+0x10298, x, y, d=size bits, size, a=type).
// MatchTiles: Game::MatchTiles (wire to dr_commit_path). Achievement: a=id, b=float bits.
// Label: Game::AddSimpleLabel(a=type, (x, y), b=number, c=colour, d=scale bits). Text:
// Tile::UpdateText(a, b, c). IncreaseStat: Item::IncreaseStat(a) on the item at Game+0xbe90 (wire to
// dr_item_increase_stat).
// UpdateStats: Game::UpdateStats (wire to dr_update_stats). HealthBar: a=value.
// CrossVisibility: Game::UpdateCrossVisibility (still a boundary). UnlockMenu: UnlockMenu::Show(a=class
// type, b=level). MatchTile: Game::MatchTile(tile, a=reward) (wire to dr_match_tile). MoveMatchedTiles
// (wire to the refill). SerialiseState / SerialiseClasses: persistence (boundaries).
enum class ReleaseEventKind : std::int32_t { Sound=1, Help, MatchTiles, Achievement, Label, Text, IncreaseStat,
    UpdateStats, HealthBar, CrossVisibility, UnlockMenu, MatchTile, MoveMatchedTiles, SerialiseState, SerialiseClasses };
struct ReleaseEvent { ReleaseEventKind kind; std::int32_t tile,a,b,c,d; float x,y; };
struct ReleaseHooks {
    void* context;
    void (*event)(void*,const ReleaseEvent*);
    bool (*check_end_game)(void*);   // Game::CheckEndGame (wire to dr_check_end_game)
};
// The class roster (10 CharacterClass records at Game+0x15564, 388 bytes each) and the active class
// (Game+0x1648c). MatchState.class_type / class_level / unlocked[] are views of the same records
// (active class type and level, levels of classes 1..9); dr_release_class_scroll keeps them equal.
struct ClassScrollState {
    ClassProfile* classes;
    std::size_t current;
    std::int32_t difficulty;   // Game::QueueAchievement gate (dr_class_level_up)
};
// The shield shatter animation started by Game::InialiseShieldShatter (generation ShieldShatter event).
struct ShieldShatterState {
    std::uint8_t active;   // Game+0xbf88
    float progress;        // Game+0xbf8c, += 2dt
};
// Game fields reset by Game::InitNewGame that no other recovered state owns (named by offset).
struct NewGameExtra {
    std::int32_t tokens_type0_165d8, tokens_type4_165e8;   // ends of the 5-wide token counters around
    std::int32_t bonus_type0_165ec, bonus_type4_165fc;     // TokenQueueCounters.normal[3] / bonus[3]
    std::int32_t value_164d4;
    std::int32_t particles_b53c, labels_b54c;   // active Particles / SimpleLabel pool sizes (Game+0xb530 / 0xb540)
    std::int32_t base_bde8[4];          // Game+0xbde8/0xbdf0/0xbdf8/0xbe00 (each before PlayerStats.base_*)
    std::uint8_t label_active[4];       // SimpleLabel active bytes: leech 0xbfc0, flame 0x14afc, spike 0x14e70, 0x151e4
    std::uint8_t skill_ff[4][4];        // bytes +0x0f/+0x23/+0x37/+0x4b of the four skill objects (Game+0xbf90)
};
// Everything Game::InitNewGame resets. The active class is classes[0] (MatchState.perks and
// SelectionState.character.flaws are its perks and flaws).
struct NewGameState {
    MatchState* match;              // random, bonus chances, spawn_count_1555c; ->stroke selection
    ResourcePreviewState* preview;
    ResourceState* resources;
    PathState* path;
    GenerationState* generation;    // ->refill for PositionTile
    TokenQueue* tokens;
    TurnFlags* flags;
    TurnFinishFlags* finish;
    RuneState* rune;
    EndGameState* end;
    std::uint8_t* counterattack;    // Game+0xbfba
    AttackDamageState* attack;
    PlayerStats* player;
    ClassProfile* classes;          // the 10 class records (UnlockAchievement)
    std::int32_t difficulty;        // Game::QueueAchievement gate
    ShieldShatterState* shatter;
    NewGameExtra* extra;
};
// Achievement: a=id, b=float bits. SetSize: Quad::SetSize(tile, (a, b) float bits). Labels:
// Tile::InitialiseLabels(tile). TurnLabel: Label::SetText / UpdateColour on Game+0x5e18 (presentation).
// SkullValue: Interface::UpdateSkullValue. HealthBar / XPBar / UPBar / GoldBar: Interface bar update with
// a=value. Item: the item in slot a (Game+0xbe88+4a) is deleted and Item(Game, type b) constructed
// (Item::Initialise / GenerateName / GenerateStats / MakeStats, boundary). UpdateStats: wire to
// dr_update_stats. InterfaceReset: Interface::Reset.
enum class NewGameEventKind : std::int32_t { Achievement=1, SetSize, Labels, TurnLabel, SkullValue, HealthBar, XPBar,
    UPBar, GoldBar, Item, UpdateStats, InterfaceReset };
struct NewGameEvent { NewGameEventKind kind; std::int32_t tile,a,b; };
struct NewGameHooks {
    void* context;
    void (*event)(void*,const NewGameEvent*);
    const GenerationHooks* generation;   // RandomiseTile events
};
// The leech, flame and spike damage labels (SimpleLabel at Game+0xbfc0 / 0x14afc / 0x14e70): shown at the
// touch while a path is drawn, then flown to the health bar (Game::Process).
struct DamageLabelState {
    SelectionState* selection;   // current damage / leech / flame / spike, label moving flags, skull_counted
    ResourceState* resources;    // health, health_max, health_bonus, ui_health
    ReleaseFlights* flights;
    std::uint8_t* active;        // SimpleLabel active bytes: NewGameExtra.label_active[0..2] (renderer-maintained)
};
// The part of Game::Process between the screen gates and the falling list.
struct BoardEffectsState {
    PathState* path;               // combat poison effect (Tile+0x244/0x245/0x248)
    GenerationState* generation;   // tiles[i].flag_224 (spin; never set by the game)
    TurnFinishFlags* finish;       // help_flags_102d0 bit 0: first-game help
    ShieldShatterState* shatter;
};
// Help: HelpMenu::Initialise(Game+0x10298, (x, y) = resting position of tile, 0, 0, type a=0).
// ShatterInitialise: chunk quads reset (presentation). ShieldChunk: Game::ProcessShieldChunk for chunk a
// (0: quad Game+0xbea8, direction -1, target (0.485938, 1.29375); 1: quad Game+0xbf18, direction 1,
// target (0.507812, 1.29375)) at the current progress (presentation). Spin: Tile+0x220 += dt * Tile+0x228
// (renderer-owned floats). Colour: Quad::SetColour(tile, a=r, b=g, c=b; alpha unchanged). Text:
// Tile::UpdateText(1, 0, 0).
enum class BoardEffectEventKind : std::int32_t { Help=1, ShatterInitialise, ShieldChunk, Spin, Colour, Text };
struct BoardEffectEvent { BoardEffectEventKind kind; std::int32_t tile,a,b,c; float x,y; };
struct BoardEffectHooks { void* context; void (*event)(void*,const BoardEffectEvent*); };
// Other per-frame parts of Game::Process.
struct FrameState {
    PathState* path;              // ->match: shake_progress_bd90 / shake_scale_bd94 (flare size / alpha); selection
    ResourcePreviewState* preview;// total_165d0
    TokenQueue* tokens;           // bonus_total_165d4, normal / bonus counters
    NewGameExtra* extra;          // ends of the 5-wide token counters
    AttackAnimation* animation;   // flare_count
    AttackDamageState* attack;    // phase
    TurnFinishFlags* finish;      // help_flags_102d0
    TouchState* touch;            // Game+0x10 phase / +0x14 position
};
// FlareAlpha: SetAlpha(flare a, b) and flare size (quad +0x64/+0x68) = shake_progress_bd90 (c bits).
// Process / Initialise / Position / Number: the current-damage SimpleLabel (Game+0xb550): Process(a=dt
// bits); Initialise(type 1, (x, y), b=number, scale 1); SetPosition((x, y)); SetNumber(a). Help:
// HelpMenu::Initialise((x, y), 0.05, 0, type 8). BaseDamageHelp / WeaponDamageHelp: Interface::ShowHelpBaseDmg /
// ShowHelpWeaponDmg (they may change help_flags_102d0). ProcessInput: Game::ProcessInput (here with touch
// phase 3: the stroke is cancelled).
enum class FrameEventKind : std::int32_t { FlareAlpha=1, Process, Initialise, Position, Number, Help, BaseDamageHelp,
    WeaponDamageHelp, ProcessInput };
struct FrameEvent { FrameEventKind kind; std::int32_t a,b,c; float x,y; };
struct FrameHooks { void* context; void (*event)(void*,const FrameEvent*); };
// Label index 0 leech, 1 flame, 2 spike. Process: SimpleLabel::Process(dt) (fade, a=dt bits). Initialise:
// SimpleLabel::Initialise(a=type 8/9/10, (x, y), b=number, scale 1). Position: SetPosition((x, y)). Number:
// SetNumber(a). Alpha: SetAlpha(a). Scale: label scale (SimpleLabel+0x33c) = a float bits. HealthBar: a=value.
// Sound: a. Achievement: a=id, b=float bits.
enum class LabelEventKind : std::int32_t { Process=1, Initialise, Position, Number, Alpha, Scale, HealthBar, Sound, Achievement };
struct LabelEvent { LabelEventKind kind; std::int32_t label,a,b; float x,y; };
struct LabelHooks {
    void* context;
    void (*event)(void*,const LabelEvent*);
    bool (*check_end_game)(void*);   // Game::CheckEndGame (wire to dr_check_end_game)
};
}
extern "C" {
// Original Game::Process [0x176fc,0x17cda) with [0x17d74,0x17da4): for each damage label in turn, a
// shown label whose value is 0 fades (Process); a positive value is shown at the touch (y - 0.1 for leech
// while the path deals damage; flame 0.06 below a leech label, spike another 0.04 below a flame label)
// until released, then flies (speed += 10dt, progress += speed*dt, at most 1) from its start towards
// (0.8625, 1.29375) along an arc, its scale shrinking from 1 to 0.1 with progress^5. On arrival leech
// heals (up to health_max + health_bonus, sound 4); flame and spike hurt the player (floor 0 with
// achievement 35 / 34, sounds 17 / 25) and CheckEndGame runs: true returns true (the original leaves
// Game::Process before ProcessAttack).
bool dr_process_damage_labels(dungeonraid::DamageLabelState*,float dt,dungeonraid::Point touch,const dungeonraid::LabelHooks*);
// Original Game::InialiseShieldShatter 0x9810: active, progress 0 (the chunk quads are presentation).
void dr_initialise_shield_shatter(dungeonraid::ShieldShatterState*,const dungeonraid::BoardEffectHooks*);
// Original Game::Process [0x17d22,0x17d32)+[0x1733a,0x173c8)+[0x17d32,0x17d56) with
// Game::ProcessShieldShatter 0x9784 and Tile::ProcessEffects 0x3dcfc: first-game help (help flag bit 0:
// RandI(0,5,0) twice picks tile a*6+b, help 0 at its resting position); the shield shatter advances
// (progress += 2dt; past 1 it ends, else both chunks are drawn); then column-major every tile's effects:
// spin (flag_224), and the poison effect (active or clearing): progress += 3dt up to 1, colour interpolated
// between (255,255,255) and (169,76,202) (towards green while active, back while clearing), and at 1 the
// effect ends with UpdateText(1,0,0).
void dr_process_board_effects(dungeonraid::BoardEffectsState*,float dt,const dungeonraid::BoardEffectHooks*);
// Original Game::Process [0x17400,0x1744c): with no falling tile and no path, a positive round total
// (preview total_165d0) or token bonus total ends the round: both, and the 5-wide token counters, become 0.
void dr_reset_round_counters(dungeonraid::FrameState*,std::uint32_t falling_count);
// Original Game::Process [0x17570,0x17622): outside attack phases 2..4, remaining attack flares grow
// (shake_progress_bd90 += 2dt) and fade (shake_scale_bd94 -= 3.5dt; below 0 it is 0 and the flares end).
void dr_process_flare_fade(dungeonraid::FrameState*,float dt,const dungeonraid::FrameHooks*);
// Original Game::Process [0x17622,0x176fc)+[0x17d64,0x17d74): the current-damage label fades when shown
// with no damage; with positive damage it is shown 0.14 above the touch; with a counted skull help 8
// is shown and, when ShowHelpWeaponDmg clears help flag 0x400 that was set before, the stroke is cancelled
// (current damage 0, touch phase 3, ProcessInput). label_active: SimpleLabel active byte (renderer).
void dr_process_damage_label(dungeonraid::FrameState*,std::uint8_t label_active,float dt,const dungeonraid::FrameHooks*);
// Original Game::CalculateTilePositions 0xb264: vertical offset 0.015625 in record mode (else 0);
// tile y*6+x rests at ((x+0.5)*pitch+0.003125, (y+0.5)*pitch+0.246875+offset), its centre is
// placed there with size pitch (half pitch), SetSize and InitialiseLabels events.
void dr_calculate_tile_positions(dungeonraid::StrokeState*,const dungeonraid::NewGameHooks*);
// Original Game::InitNewGame 0x15c50: seeds all random streams with time (SetRandSeed(time, 6),
// FlushRandSeeds), CalculateTilePositions, class achievements (class 0, then 1..9), resets the turn,
// path, battle, token, label and flag state, time to promotion (200 in record mode 0, else 50, 49
// with flaw 8), generates the board row by row (PositionTile + RandomiseTile with filter_enabled set),
// starting stats (base damage 3, +1 perk 4; health 40, 100 in record mode 1, +10 perk 9, -10 flaw 1;
// bonus chances 20, +10 perk 7 on Game+0xbe18, -10 flaw 4 on Game+0xbe30), new items of types 0..4,
// UpdateStats, then the phase/input/list/level resets and Interface::Reset.
void dr_init_new_game(dungeonraid::NewGameState*,std::uint32_t time,const dungeonraid::NewGameHooks*);
// Original Game::CountAttackers 0x8fb0: enemies (type 1) without attack flag, not frozen, with
// GetAttack > 0 (row-major).
std::int32_t dr_count_attackers(const dungeonraid::PathState*);
// Original Game::ProcessInput gate [0x16638,0x16748): blocked while tiles fall, tokens are
// pending or attack flares exist. When input is not ready and no attack runs, the enemy phase
// starts (phase 1) if CountAttackers > 0, unless it is skipped (turn <= 4 with perk 0); skipped or
// no attackers: phase 8. Phases 1..7 block; phase 8 runs EndOfTurn. Then phase 0, input ready;
// with a touch (phase != 0) and no active input target the rune preview is reset and the touch
// is dispatched (Dispatch), otherwise Idle. The dispatch itself is not part of this gate.
dungeonraid::InputGate dr_input_gate(dungeonraid::PathState*,dungeonraid::AttackDamageState*,dungeonraid::RuneState*,
    const dungeonraid::InputGateInputs*,const dungeonraid::ScheduleHooks*);
// Original Game::AddRevengeHealth 0xce7c: column-major, every unmatched enemy (type 1) with enemy
// type 21 gains kill_count_15548 attack (UpdateText(1,0,0), label 27 at its centre with that
// number, colour 35, scale 1, sound 14).
void dr_add_revenge_health(dungeonraid::PathState*,const dungeonraid::ReleaseHooks*);
// Original Game::ProcessInput release after dr_prepare_release [0x16890,0x16e10). MatchPath
// (path minus fake tiles > 2): flag_1554c, sound 27 (enemy in the path) or 26 (sword; help 4
// at the first tile when help flag 0x10), the kill/generation counters reset, MatchTiles, the
// all-enemies refill achievement 74, flame/spike label flights, revenge health and the race-6
// armour upgrade (kill_count_15548 > 14), healing from killed attack (prev_164a7), the leech
// label flight (or current_leech = 0 without a counted skull). Otherwise current_leech = 0 and a
// one-tile class scroll returns ClassScroll before any further change (continue with
// dr_release_class_scroll). Every other route ends with dr_release_clear.
dungeonraid::ReleaseRoute dr_release_path(dungeonraid::ReleaseState*,const dungeonraid::ReleaseInputs*,
    const dungeonraid::ReleaseHooks*);
// Original ProcessInput class scroll [0x16c1c,0x16d88) (after dr_release_path returned ClassScroll):
// when the active class is below level 10 and not class type 0, RandI(0,1,stream 5) chooses between
// levelling it up and unlocking; unlocking levels up a random (RandI(0,n-1,5)) class still at level 0
// and shows UnlockMenu(index, 1); with none left (or after the choice) the active class, if below 10,
// levels up and shows UnlockMenu(type, level). CharacterClass::LevelUp is dr_class_level_up. Then the
// scroll tile is matched (reward 7), MoveMatchedTiles, CheckEndGame: true returns true at once (the
// original leaves ProcessInput without the tail); otherwise SerialiseState, SerialiseClasses and
// dr_release_clear.
bool dr_release_class_scroll(dungeonraid::PathState*,dungeonraid::ClassScrollState*,const dungeonraid::ReleaseHooks*);
// ProcessInput common release tail [0x16d88,0x16e10): the path and fake set are emptied,
// current damage cleared, flame/spike damage cleared unless their label is still moving, then
// UpdateCrossVisibility.
void dr_release_clear(dungeonraid::SelectionState*,const dungeonraid::ReleaseHooks*);
}
