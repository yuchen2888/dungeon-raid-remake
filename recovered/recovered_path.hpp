#pragma once
#include "recovered_tokens.hpp"
namespace dungeonraid {
// Persistent combat-only fields. Tile identity, geometry and match/freeze flags
// belong to MatchState::stroke; no second authoritative board is stored here.
struct PathCombatTile {
    std::int32_t attack,defence,health;
    PoisonState poison;
    std::uint8_t overlay,flag_25e,attack_flag;
};
struct PathBattle {
    std::int32_t kill_count_165b4,kill_count_15548,killed_attack_164ac,armour_break_chance,poison_amount;
    std::uint8_t grant_coin_on_attack,poison_sound_queued;
};
struct PathState {
    MatchState* match;
    TokenQueue* queue;
    PathBattle battle;
    PathCombatTile combat[36];
    std::int32_t turn;
    std::uint8_t input_ready;
    std::int32_t crossing_best,crossing_average,crossing_samples,total;
};
struct PathHooks {
    void* context;
    // Observes Round events, including MatchTile/Token calls before dispatch.
    // kind 0 is RNG: a=low,b=high,c=stream,d=result.
    void (*event)(void*,const RoundEvent*);
    const MatchHooks* match;
    const TokenHooks* tokens;
};
}
extern "C" {
// Integration adapter, NOT an additional recovered original function.
// Uses a temporary RoundState view and synchronizes before/after every external
// call; persistent identity/flags remain in the shared StrokeState board.
// MoveMatchedTiles remains an observed boundary. Valid path indices required.
void dr_commit_path(dungeonraid::PathState*,const std::uint8_t*,std::size_t,
    const std::uint8_t* excluded,std::size_t,const dungeonraid::PathHooks*);
// Integration adapter, NOT an additional recovered original function: one
// original Game::AttackSkull (dr_attack_skull) on tile index through the same
// synchronized RoundState view and hooks as dr_commit_path. Returns its result.
bool dr_path_attack_skull(dungeonraid::PathState*,std::uint32_t index,std::int32_t amount,
    bool effects,const dungeonraid::PathHooks*);
}
