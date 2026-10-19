#pragma once
#include "recovered_path.hpp"
namespace dungeonraid {
// Sound: a=sound. Text: Tile::UpdateText(a,b,c). Label: Game::AddSimpleLabel at the tile
// center, a=type, b=number, c=colour, d=scale bits. Flare: Game::AddFlare at the tile
// center, a=type, b=RGBA bytes. Achievement: a=id, b=float bits.
enum class TurnEventKind : std::int32_t { Sound=1, Text, Label, Flare, Achievement };
struct TurnEvent { TurnEventKind kind; std::int32_t tile,a,b,c,d; };
// match_tile is a synchronous gameplay dependency: wire it to dr_match_tile.
struct TurnHooks {
    void* context;
    void (*event)(void*,const TurnEvent*);
    void (*match_tile)(void*,std::int32_t tile,std::int32_t reward);
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
}
