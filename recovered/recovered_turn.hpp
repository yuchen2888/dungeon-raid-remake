#pragma once
#include "recovered_path.hpp"
#include "recovered_resources.hpp"
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
    LabelRest, FlareRest, Freeze, FlameOverlay, Particles, HealthBar, LabelTarget, LabelPoison };
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
};
}
namespace dungeonraid {
// CheckEndGame flags not owned by another recovered module.
struct EndGameState {
    std::uint8_t game_over_screen; // Game+0xcac4 (GameOverScreen at +0xcac0 is showing)
    std::uint8_t victory;          // Game+0x16611 (record-mode win)
    std::uint8_t revive_second;    // Game+0x164a5 (cleared with ResourceState.guard_164a4)
};
// game_over is the end-of-game bookkeeping [0x10c04,...) (scores, class stats,
// screens), still a boundary: called with win=true for a record-mode victory.
struct EndGameHooks {
    void* context;
    void (*event)(void*,const TurnEvent*);
    void (*game_over)(void*,bool win);
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
// Original Game::CheckEndGame 0x10b18, decision part [0x10b18,0x10c04): true when
// the game is (already) over. Record-mode victory -> achievement 76 and game over;
// health > 0 -> false; otherwise achievement 40 when the class's mortal enemy is on
// the board, then either the one-time revive (guard_164a4: full health, sound 19,
// label 28, achievement 61, false) or game_over(false).
bool dr_check_end_game(dungeonraid::ResourceState*,dungeonraid::EndGameState*,const dungeonraid::EndGameHooks*);
}
