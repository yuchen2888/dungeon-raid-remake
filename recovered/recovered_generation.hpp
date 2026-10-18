#pragma once
#include "recovered_refill.hpp"
#include "recovered_resources.hpp"
namespace dungeonraid {
struct GeneratedTile {
    std::int32_t variant, max_health;
    float label_offset;
    std::uint8_t flag_224;
};
struct GenerationState {
    RefillState* refill;
    ResourceState* resources;
    GeneratedTile tiles[36];
    std::int32_t time_to_promotion, generated_count, generated_enemies;
    std::uint8_t promotion_enabled, force_coins, inhibit_force_coins, one_health;
    // Original +bfb8/+bfb9: following the five matched counters, not counters.
    std::uint8_t filter_enabled, filter_swords;
};
enum class GenerationEventKind : std::int32_t {
    Random=1, Colour, UV, Text, Countdown, EnemyUV, Sound, Achievement,
    ShieldValue, ShieldShatter, JumpDown
};
struct GenerationEvent {GenerationEventKind kind;std::int32_t tile,a,b,c,d;};
struct GenerationHooks {void* context;void (*event)(void*,const GenerationEvent*);};
}
extern "C" {
bool dr_time_to_promote(dungeonraid::GenerationState*);
void dr_set_time_to_promotion(dungeonraid::GenerationState*,int,const dungeonraid::GenerationHooks*);
int dr_generation_total_xp(const dungeonraid::GenerationState*);
void dr_generate_stats(dungeonraid::GenerationState*,std::uint32_t,int turn,int difficulty,const dungeonraid::GenerationHooks*);
void dr_promote_tile(dungeonraid::GenerationState*,std::uint32_t,int turn,int difficulty,bool flag,const dungeonraid::GenerationHooks*);
void dr_set_tile_type(dungeonraid::GenerationState*,std::uint32_t,int type,int turn,int difficulty,const dungeonraid::GenerationHooks*);
void dr_randomise_tile(dungeonraid::GenerationState*,std::uint32_t,const dungeonraid::GenerationHooks*);
void dr_make_arrow(dungeonraid::GenerationState*,std::uint32_t,const dungeonraid::GenerationHooks*);
void dr_make_mana_potion(dungeonraid::GenerationState*,std::uint32_t,const dungeonraid::GenerationHooks*);
void dr_make_broken(dungeonraid::GenerationState*,std::uint32_t,const dungeonraid::GenerationHooks*);
void dr_update_generated_values(dungeonraid::GenerationState*,std::uint32_t,const dungeonraid::GenerationHooks*);
}
