#pragma once
#include "recovered_path.hpp"
#include "recovered_resources.hpp"
#include "recovered_generation.hpp"
namespace dungeonraid {
// Sound: a=sound. Text: Tile::UpdateText(a,b,c). Label: Game::AddSimpleLabel at the tile
// center, a=type, b=number, c=colour, d=scale bits. Flare: Game::AddFlare at the tile
// center, a=type, b=RGBA bytes. Achievement: a=id, b=float bits.
// LabelRest / FlareRest: as Label / Flare but at the tile's resting position (Game+0xb400).
// Freeze: Tile::SetFreezeVisibility(a) render part. FlameOverlay: the burning overlay quad
// (UV, size, alpha 200) of SetFlameVisibility(true). Particles: a=type.
// HealthBar: a=health. LabelTarget: AddSimpleLabel at Interface::GetTarget(0), a=type,
// b=number, c=colour, d=scale. LabelPoison: the same at Interface::GetPoisonPosition().
enum class TurnEventKind : std::int32_t { Sound=1, Text, Label, Flare, Achievement,
    LabelRest, FlareRest, Freeze, FlameOverlay, Particles, HealthBar, LabelTarget, LabelPoison,
    UpdateSkills, ArrowColour,     // ArrowColour: Arrow::SetColour(a,b,c) on Game+0x3658
    Help, SerialiseState };        // Help: HelpMenu::Initialise (Game+0x10298) at the tile center,
                                   // a=HelpType, b=c=size float bits. SerialiseState: Game::SerialiseState
struct TurnEvent { TurnEventKind kind; std::int32_t tile,a,b,c,d; };
// match_tile is a synchronous gameplay dependency: wire it to dr_match_tile.
struct TurnHooks {
    void* context;
    void (*event)(void*,const TurnEvent*);
    void (*match_tile)(void*,std::int32_t tile,std::int32_t reward);
    // Game::AttackSkull: wire to dr_path_attack_skull.
    bool (*attack_skull)(void*,std::int32_t tile,std::int32_t amount,bool effects);
    // Game::CheckEndGame (not yet recovered): true ends EndOfTurn early.
    bool (*check_end_game)(void*);
    // Game::MoveMatchedTiles: wire to dr_move_matched_tiles.
    void (*move_matched_tiles)(void*);
};
}
namespace dungeonraid {
// CheckEndGame flags not owned by another recovered module.
struct EndGameState {
    std::uint8_t game_over_screen; // Game+0xcac4 (GameOverScreen at +0xcac0 is showing)
    std::uint8_t victory;          // Game+0x16611 (record-mode win)
    std::uint8_t revive_second;    // Game+0x164a5 (cleared with ResourceState.guard_164a4)
    // Written when the game ends (meaning not yet confirmed).
    std::int32_t flag_146d0;       // Game+0x146d0 = 0
    std::uint8_t flag_146d4;       // Game+0x146d4 = 1
    std::uint8_t flag_15546;       // Game+0x15546 = 1
};
// Skill objects (pointers at Game+0xbf90): +0x84 id, +0x88 level.
struct SkillSlots { std::int32_t id[4], level[4]; std::uint8_t active[4]; };   // +0x80 active
// EndOfTurn per-turn flags (meanings not yet confirmed; named by Game offset).
struct TurnFlags {
    std::uint8_t b15561,b15562;     // cleared
    std::uint8_t b165b8[5];         // Game+0x165b8..0x165bc cleared
    std::uint8_t arrow_pending_16491,arrow_hold_16492;
    std::uint8_t prev_164a7,next_164a8;
    std::uint8_t prev_be74[4],next_be78[4];
    std::uint8_t next_coin_bfbc;    // becomes PathBattle.grant_coin_on_attack (Game+0xbfbb)
};
// EndOfTurn closing flags (meanings not yet confirmed; named by Game offset).
struct TurnFinishFlags {
    std::uint8_t next_one_health_14af7;   // becomes GenerationState.one_health (+0x14af5)
    std::uint8_t next_force_coins_14af8;  // becomes GenerationState.force_coins (+0x14af6)
    std::uint8_t flag_1554c;              // cleared
    std::uint32_t help_flags_102d0;       // bit 0x8000: help 15, bit 0x200000: help 21
};
// ScoreScreen::AddScore: variant 0 = (name, turn, xp, gold, up, score, Difficulty),
// variant 1 = (name, turn, a, b, c, score, GameMode); name is Game+0xbe38.
struct ScoreEntry { std::int32_t variant, turn, a, b, c, score, mode; };
// game_over is the end-of-game bookkeeping [0x10c04,...) (scores, class stats,
// screens), still a boundary: called with win=true for a record-mode victory.
struct EndGameHooks {
    void* context;
    void (*event)(void*,const TurnEvent*);
    void (*game_over)(void*,bool win);
};
// SetSkills: ScoreScreen::SetSkills(a,b,c,d). SerialiseClasses: Game::SerialiseClasses
// (class roster persistence, boundary). GameOverScreen: Initialise(a=win).
enum class EndGameEventKind : std::int32_t { SetSkills=100, SerialiseClasses, GameOverScreen };
struct GameOverHooks {
    void* context;
    void (*event)(void*,const TurnEvent*);   // Achievement and EndGameEventKind values
    void (*add_score)(void*,const ScoreEntry*);
};
}
extern "C" {
// Original Game::MimicDefence 0xbd20: the tile's defence becomes the current armour.
void dr_mimic_defence(dungeonraid::PathState*,std::uint32_t tile,const dungeonraid::TurnHooks*);
// Original Game::Resurrect 0xaf68: effects only (sounds, flare, label) and the
// attack timers reset (shake_scale_bd94=1.0, shake_progress_bd90=0).
void dr_resurrect(dungeonraid::MatchState*,std::uint32_t tile,const dungeonraid::TurnHooks*);
// Original Game::ProcessCripples 0xcae0: only when the class race is 7, every
// unmatched plain skull (type 1, enemy 0) with health < defence is MatchTile'd
// as reward 5, row-major, with label 36 and achievement 53 (2.0).
void dr_process_cripples(dungeonraid::PathState*,const dungeonraid::TurnHooks*);
// Original Tile::SetFlameVisibility 0x3d89c. on: damage += flame_damage when
// already burning; self_flame, unfreeze, flame_damage, overlay and flaming set.
// off: overlay and flaming cleared, self_flame stored.
void dr_set_flame_visibility(dungeonraid::PathState*,std::uint32_t tile,bool on,std::int32_t damage,
    bool self_flame,const dungeonraid::TurnHooks*);
// EndOfTurn [0x13710,0x13910) with loop head [0x13d64,0x13d88): column-major
// over the board, frozen tiles thaw (flare, SetFreezeVisibility(false), sound 22
// once); burning tiles flare, burning enemies take their flame damage (label 9,
// dying ones get AttackSkull(0) and achievement 54 for race 8), then the fire
// is put out with SetFlameVisibility(false).
void dr_end_turn_burn_freeze(dungeonraid::PathState*,const dungeonraid::TurnHooks*);
// EndOfTurn [0x13910,0x13a1c): regeneration (Game+0xbe70) up to health_max +
// health_bonus, then poison (ResourceState.poison) damage to the player and
// CheckEndGame. Returns true when CheckEndGame ends the turn (original 0x13e04).
bool dr_end_turn_regen_poison(dungeonraid::ResourceState*,std::int32_t regen,const dungeonraid::TurnHooks*);
// EndOfTurn loop B [0x13a1c,0x13af0) + head [0x13d88,0x13daa): column-major over
// enemies (type 1); Tile::GetPoison ticks the poison queue; poisoned enemies get
// label 7 and lose that much health; survivors get UpdateText and particles 2,
// others are matched (MatchTile reward 5, achievement 47 for race 1).
void dr_end_turn_poison_enemies(dungeonraid::PathState*,const dungeonraid::TurnHooks*);
// EndOfTurn tail [0x13b3c,0x13cda) + [0x13d12,0x13d64) + [0x13dc8,0x13e04): revive
// guard rotation (164a6<-164a4<-revive_second<-0), CheckEndGame (true: return),
// MoveMatchedTiles, attack_flag cleared, pending generation flags applied, the
// generation filter cleared, time_to_promotion-1 (floored at 0), per-column help
// popups, record-mode victory at turn 100, CheckEndGame, then SerialiseState.
// Returns true when a CheckEndGame ended the turn (SerialiseState not reached).
bool dr_end_turn_finish(dungeonraid::ResourceState*,dungeonraid::PathState*,dungeonraid::GenerationState*,
    dungeonraid::EndGameState*,dungeonraid::TurnFinishFlags*,const dungeonraid::TurnHooks*);
// EndOfTurn [0x13574,0x13710): turn++, CheckEndGame (true: return), skill cooldowns
// (+1 up to max unless enemy 15 is on the board; sound 10 when reaching max-1 -> max;
// every skill deactivated), interface update, per-turn flag reset and rotation,
// counterattack flag, matched_counts and attack timers reset.
bool dr_end_turn_begin(dungeonraid::ResourceState*,dungeonraid::PathState*,dungeonraid::SkillSlots*,
    dungeonraid::TurnFlags*,std::uint8_t* counterattack,const dungeonraid::TurnHooks*);
// Original Game::CheckEndGame 0x10b18, decision part [0x10b18,0x10c04): true when
// the game is (already) over. Record-mode victory -> achievement 76 and game over;
// health > 0 -> false; otherwise achievement 40 when the class's mortal enemy is on
// the board, then either the one-time revive (guard_164a4: full health, sound 19,
// label 28, achievement 61, false) or game_over(false).
bool dr_check_end_game(dungeonraid::ResourceState*,dungeonraid::EndGameState*,const dungeonraid::EndGameHooks*);
// Original Game::GetTotalGold 0x18a2c / GetTotalUP 0x18a5c: current + total,
// divided by 4 (toward zero) in record mode 0. (GetTotalXP 0x189fc is the same
// formula, recovered earlier as dr_generation_total_xp; dr_total_xp is its
// ResourceState form.)
std::int32_t dr_total_gold(const dungeonraid::ResourceState*);
std::int32_t dr_total_up(const dungeonraid::ResourceState*);
std::int32_t dr_total_xp(const dungeonraid::ResourceState*);
// Original Game::GetScore 0x8c18. record mode 1: PathState.total; record mode 0:
// gold+xp+up, doubled on victory (Game+0x16611); otherwise gold+xp+up+turn+
// 100*level of every active skill slot.
std::int32_t dr_get_score(const dungeonraid::ResourceState*,const dungeonraid::PathState*,
    const dungeonraid::SkillSlots*,bool victory);
// CheckEndGame end-of-game bookkeeping [0x10c04,0x10dd6): class games/kills,
// score entry and per-difficulty best score (unsigned), skills, class
// persistence, game-over screen, end flags, achievement 67.
void dr_game_over(dungeonraid::ResourceState*,dungeonraid::PathState*,dungeonraid::ClassProfile*,
    const dungeonraid::SkillSlots*,dungeonraid::EndGameState*,bool win,const dungeonraid::GameOverHooks*);
}
