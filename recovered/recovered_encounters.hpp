#pragma once
#include "recovered_generation.hpp"
namespace dungeonraid {
enum class EncounterEventKind : std::int32_t { Sound=1, Label, HealthBar, PoisonPosition, CheckEndGame, Flare, Text };
// Label: tile -1 uses the poison position returned by the renderer, otherwise
// the tile's current center. Fields a=label type,b=number,c=colour,d=float bits.
// Flare: tile is the fixed board cell; a=type,b=RGBA bits.
// Text: Tile::UpdateText(a,b,c) on that tile.
struct EncounterEvent {EncounterEventKind kind;std::int32_t tile,a,b,c,d;};
struct EncounterHooks {void* context;void (*event)(void*,const EncounterEvent*);const RefillHooks* refill;};
}
extern "C" {
void dr_stab(dungeonraid::GenerationState*,std::uint32_t,const dungeonraid::EncounterHooks*);
void dr_jump_down(dungeonraid::GenerationState*,std::uint32_t,const dungeonraid::EncounterHooks*);
// Original Tile::AddHealth: uncapped add, raises max_health when exceeded.
void dr_tile_add_health(dungeonraid::GenerationState*,std::uint32_t,std::int32_t,const dungeonraid::EncounterHooks*);
// Original Game::ProcessVampires: every unmatched enemy 20 heals by its attack
// (capped at max_health unless the class's mortal enemy is 20), column-major.
void dr_process_vampires(dungeonraid::GenerationState*,const dungeonraid::EncounterHooks*);
}
