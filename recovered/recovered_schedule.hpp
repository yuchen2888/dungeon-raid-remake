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
// Game fields reset by Game::InitNewGame that no other recovered state owns (named by offset).
struct NewGameExtra {
    std::int32_t tokens_type0_165d8, tokens_type4_165e8;   // ends of the 5-wide token counters around
    std::int32_t bonus_type0_165ec, bonus_type4_165fc;     // TokenQueueCounters.normal[3] / bonus[3]
    std::int32_t value_164d4, tokens_b53c, tokens_b54c;
    std::int32_t base_bde8[4];          // Game+0xbde8/0xbdf0/0xbdf8/0xbe00 (each before PlayerStats.base_*)
    std::uint8_t flag_bf88;
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
}
extern "C" {
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
