#pragma once
#include "recovered_path.hpp"
#include "recovered_resources.hpp"
#include "recovered_generation.hpp"
#include "recovered_rune.hpp"
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
    Help, SerialiseState,          // Help: HelpMenu::Initialise (Game+0x10298) at the tile center,
                                   // a=HelpType, b=c=size float bits. SerialiseState: Game::SerialiseState
    FlareTarget };                 // FlareTarget: AddFlare at Interface::GetTarget(0), a=type, b=RGBA bytes
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
    // An enemy ability not yet recovered (Game::HealOrBless, MakeAcidPotion, FreezeTiles,
    // StealGold, JumpEnemy, ConvertRandomTiles, BreakRandomShieldSword, AttractSkulls,
    // AttractShieldsSwords, ThrowSkull, DestroyUpgrade), keyed by enemy_type.
    void (*ability)(void*,std::int32_t enemy_type,std::int32_t tile);
    // Game::SwapTiles(x1,y1,x2,y2): wire to dr_swap_tiles.
    void (*swap_tiles)(void*,std::int32_t x1,std::int32_t y1,std::int32_t x2,std::int32_t y2);
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
// EndOfTurn per-turn flags (meanings not yet confirmed; named by Game offset). Flags owned by
// other recovered states are written there: Game+0x16491 is RuneState.enabled_16491 and
// Game+0xbe74..0xbe77 are SelectionState.double_damage and ResourcePreviewState.double_upgrade/
// double_healing/double_gold.
struct TurnFlags {
    std::uint8_t b15561,b15562;     // cleared
    std::uint8_t b165b8[5];         // Game+0x165b8..0x165bc cleared
    std::uint8_t arrow_hold_16492;
    std::uint8_t prev_164a7,next_164a8;
    std::uint8_t next_be78[4];      // next turn's double_damage/upgrade/healing/gold (Game+0xbe78..0xbe7b)
    std::uint8_t next_coin_bfbc;    // becomes PathBattle.grant_coin_on_attack (Game+0xbfbb)
};
// EndOfTurn closing flags (meanings not yet confirmed; named by Game offset).
struct TurnFinishFlags {
    std::uint8_t next_one_health_14af7;   // becomes GenerationState.one_health (+0x14af5)
    std::uint8_t next_force_coins_14af8;  // becomes GenerationState.force_coins (+0x14af6)
    std::uint8_t flag_1554c;              // cleared
    std::uint32_t help_flags_102d0;       // bit 0x8000: help 15, bit 0x200000: help 21
};
// Game::EndOfTurn state not owned by another recovered module.
struct EndOfTurnState {
    SkillSlots* skills;
    TurnFlags* flags;
    RuneState* rune;               // RuneState.enabled_16491 (Game+0x16491)
    std::uint8_t* counterattack;   // Game+0xbfba
    EndGameState* end;
    TurnFinishFlags* finish;
    std::uint8_t* activated;       // Tile+0x254 for the 36 tiles; per-tile: swap it on RefillHooks Swap
    std::int32_t regen;            // Game+0xbe70
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
// Enemy abilities (Game member functions called by Tile::ActivateAbility).
// Game::RunAwayEnemy 0x11170: flare at the tile (RGBA 255,255,0,255), sound 35, MatchTile(7),
// MoveMatchedTiles, attack flags cleared, attack timers reset.
void dr_run_away_enemy(dungeonraid::PathState*,std::uint32_t tile,const dungeonraid::TurnHooks*);
// Game::ExplodeEnemy 0x12da8: matched_counts and sound_13ec4 cleared, MatchTile(7), flare at the
// interface target (RGBA 255,0,0,255), player health halved (toward zero; at least 1) with
// the health bar updated, attack timers reset.
void dr_explode_enemy(dungeonraid::ResourceState*,dungeonraid::PathState*,std::uint32_t tile,const dungeonraid::TurnHooks*);
// Game::TeleportEnemy 0xf4c8: every unmatched tile (column-major) is marked matched with a
// flare at its resting position (RGBA 0,100,255,255); the generation filter is enabled
// (swords filter when the class's mortal enemy is 19, then achievement 38), attack timers
// reset, sound 21. MoveMatchedTiles later replaces the board.
void dr_teleport_enemy(dungeonraid::PathState*,dungeonraid::GenerationState*,const dungeonraid::TurnHooks*);
// Game::LowerSkulls 0xc9e0: in every column (scanning up from row 4) the lowest enemy whose
// tile below is not an enemy (other than this tile) gets the tile below matched (MatchTile 7,
// resting flare RGBA 115,60,20,255); then label 23 (colour 31) at this tile, sound 5, timers reset.
void dr_lower_skulls(dungeonraid::PathState*,std::uint32_t tile,const dungeonraid::TurnHooks*);
// Game::FleeUp 0xc664: label 37 (colour 45) at the resting position; on row 0 the tile is
// matched (MatchTile 7, white resting flare) and nothing else happens; otherwise it swaps with
// the tile above (SwapTiles), white flares at both resting positions, sound 35, timers reset.
void dr_flee_up(dungeonraid::PathState*,std::uint32_t tile,const dungeonraid::TurnHooks*);
// Game::IgniteTiles 0xa150: the eight neighbours (column-major), except matched tiles and
// enemy 7, get a resting flare (RGBA 240,150,10,255) and SetFlameVisibility(true, this
// tile's GetAttack, false); timers reset.
void dr_ignite_tiles(dungeonraid::PathState*,std::uint32_t tile,const dungeonraid::TurnHooks*);
// Game::StabAttack 0x127a8: when the class's mortal enemy is 16 and the tile is not on row 5,
// the tile below is matched (MatchTile 7) unless it is an enemy with an ability; otherwise,
// on row 5 only: sounds 27 and 17, label 19 (colour 27), player health -= 2*GetAttack
// (floored at 0, health bar), label 2 (2*GetAttack, colour 11, scale 0.5) at the poison position.
void dr_stab_attack(dungeonraid::ResourceState*,dungeonraid::PathState*,std::uint32_t tile,const dungeonraid::TurnHooks*);
// Game::ConvertSwordToSkull 0xdc38: RandI(0, swords-1, stream 5) picks a sword (type 4,
// column-major); label 18 (colour 26) and sound 14 when there are swords; the picked sword
// becomes an enemy (Tile::SetType(1, turn, difficulty); health 1 with UpdateText when
// GenerationState.one_health), resting flare RGBA 240,150,10,255 and label 18; timers reset.
void dr_convert_sword_to_skull(dungeonraid::GenerationState*,std::uint32_t tile,const dungeonraid::TurnHooks*,
    const dungeonraid::GenerationHooks*);
// Game::MakeAcidPotion 0xafdc: as ConvertSwordToSkull for normal potions (type 0 without
// potion flags; GetNormalPotionCount, RandI stream 5, column-major pick): label 14 (colour 23)
// and sound 24 when there are any; the pick becomes an acid potion (Tile::MakeAcidPotion: UV
// row type*0.0517578125+0.552734375, Tile+0x233 set) with a green resting flare; timers reset.
void dr_make_acid_potion(dungeonraid::GenerationState*,std::uint32_t tile,const dungeonraid::TurnHooks*,
    const dungeonraid::GenerationHooks*);
// Game::FreezeTiles 0x103d8: candidates are tiles that are not matched, not frozen and not an
// enemy with an ability (a std::set<Tile*>, i.e. index order); twice (while any remain) RandI(0,
// n-1, stream 5) picks one: SetFreezeVisibility(true), flare RGBA 100,230,255,255 at its centre,
// removed from the set. Then label 17 (colour 25), sound 20, timers reset.
void dr_freeze_tiles(dungeonraid::PathState*,std::uint32_t tile,const dungeonraid::TurnHooks*);
// Game::BreakRandomShieldSword 0x181d8: candidates are unmatched, unbroken shields and
// non-magic swords (std::set<Tile*>, index order); none: nothing happens at all. Otherwise
// RandI(0, n-1, stream 5) picks one: Tile::MakeBroken, white flare at its centre; label 22
// (colour 30), sound 16, timers reset.
void dr_break_random_shield_sword(dungeonraid::GenerationState*,std::uint32_t tile,const dungeonraid::TurnHooks*,
    const dungeonraid::GenerationHooks*);
// Original Tile::ActivateAbility 0x3f09c. Once per turn per tile (activated[] is
// Tile+0x254, cleared by EndOfTurn). Dispatches on enemy_type: countdown abilities
// (3 RunAwayEnemy, 10 ExplodeEnemy, 19 TeleportEnemy: enemy_state-1, Countdown event,
// ability at 0; 28: ability at 0 then enemy_state=5, Countdown always), recovered abilities
// (7 IgniteTiles, 11 ConvertSwordToSkull, 16 StabAttack, 17 MimicDefence, 23 LowerSkulls,
// 31 FleeUp), resurrection (32: unless enemy_state is 0 or flag_25e (which is consumed),
// GenerateStats(turn, difficulty), EnemyUV, UpdateValues, Resurrect) and the abilities not
// yet recovered via TurnHooks.ability. Countdown/EnemyUV go to the generation hooks.
void dr_activate_ability(dungeonraid::PathState*,dungeonraid::GenerationState*,std::uint8_t* activated,std::uint32_t tile,
    const dungeonraid::TurnHooks*,const dungeonraid::GenerationHooks*);
// EndOfTurn [0x13cda,0x13d12) + [0x13af2,0x13b3c) + head [0x13daa,0x13dc8): clears
// activated[] (Tile+0x254), ProcessCripples, then column-major ActivateAbility for
// every enemy (type 1) with enemy_type != 0.
void dr_end_turn_abilities(dungeonraid::PathState*,dungeonraid::GenerationState*,std::uint8_t* activated,
    const dungeonraid::TurnHooks*,const dungeonraid::GenerationHooks*);
// Original Game::EndOfTurn 0x13574 (whole function): dr_end_turn_begin, burn/freeze,
// regeneration/poison, poisoned enemies, abilities and dr_end_turn_finish, returning
// early wherever CheckEndGame ends the game.
void dr_end_of_turn(dungeonraid::ResourceState*,dungeonraid::PathState*,dungeonraid::GenerationState*,
    dungeonraid::EndOfTurnState*,const dungeonraid::TurnHooks*,const dungeonraid::GenerationHooks*);
// EndOfTurn [0x13574,0x13710): turn++, CheckEndGame (true: return), skill cooldowns
// (+1 up to max unless enemy 15 is on the board; sound 10 when reaching max-1 -> max;
// every skill deactivated), interface update, per-turn flag reset and rotation,
// counterattack flag, matched_counts and attack timers reset.
bool dr_end_turn_begin(dungeonraid::ResourceState*,dungeonraid::PathState*,dungeonraid::SkillSlots*,
    dungeonraid::TurnFlags*,dungeonraid::RuneState*,std::uint8_t* counterattack,const dungeonraid::TurnHooks*);
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
