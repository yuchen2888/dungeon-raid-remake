#pragma once
#include "recovered_match.hpp"
namespace dungeonraid {
enum class ResourceEventKind:std::int32_t {
    Sound=1,Skills,HealthBar,Poison,Target,Label,CheckEndGame,Help,Shadow,Menu,
    Healing,Achievement,XPBar,UPBar,GoldBar,Shield
};
struct ResourceEvent {ResourceEventKind kind;std::int32_t a,b,c,d;};
struct ResourceHooks {void* context;void (*event)(void*,const ResourceEvent*);};
struct ResourceState {
    MatchState* match;
    std::int32_t health,health_max,health_bonus,xp,up,gold;
    float xp_fraction,up_fraction,gold_fraction;
    std::int32_t level,total_xp,total_gold,total_up;
    std::int32_t ui_health,ui_xp,ui_up,ui_gold,ui_armour,poison;
    std::int32_t skill_count,skill_max[4],skill_current[4];
    std::uint8_t guard_164a6,guard_164a4;
};
}
extern "C" {
// Actual resource application once a token completes. Does not decide token
// completion timing. Healing / CheckEndGame and UI remain explicit callbacks.
// skill_count in 0..4; finite, ordinary gameplay bonus/fraction values.
void dr_add_resource(dungeonraid::ResourceState*,std::int32_t reward_type,
                     std::int32_t token_type,std::int32_t target_or_amount,
                     const dungeonraid::ResourceHooks*);
}
