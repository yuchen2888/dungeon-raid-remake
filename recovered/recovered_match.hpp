#pragma once
#include "recovered_preview.hpp"
#include "recovered_random.hpp"
namespace dungeonraid {
enum class MatchEventKind:std::int32_t {
    Particles=1,Achievement,Sound,Flare,Token,Help,Label,SetSpecialType,Shapeshift,Random
};
struct MatchEvent {MatchEventKind kind;std::int32_t tile,a,b,c,d;};
struct MatchHooks {void* context;void (*event)(void*,const MatchEvent*);};
struct MatchState {
    StrokeState* stroke;
    ResourcePreviewState* preview;
    RandomState random;
    std::int32_t matched_counts[8]; // Original +bfa4; valid reward arguments 0..7.
    std::int32_t bonus_chance[4], bonus_chance_extra[4]; // potion, XP, gold, shield
    std::int32_t perks[4];
    std::int32_t spawn_enabled_14ae0,spawn_remaining_15558,spawn_count_1555c;
    std::int32_t class_type;
    std::uint8_t class_level,unlocked[9],spawn_dirty_15555,sound_13ec4,flag_25d[36];
    std::uint32_t shake_progress_bd90,shake_scale_bd94;
};
}
extern "C" {
// Recursive MatchTile control flow with shared selection state and real RNG.
// Token, SetSpecialType and Shapeshift are subsystem callbacks, not silently
// simulated. Render/UI/achievement requests are also callbacks.
// Precondition: index < 36; reward_type 0..7; coordinates 0..5; valid pointers.
void dr_match_tile(dungeonraid::MatchState*,std::uint32_t index,std::int32_t reward_type,
                   const dungeonraid::MatchHooks*);
}
