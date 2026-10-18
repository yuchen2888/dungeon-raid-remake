#include "recovered_preview.hpp"
#include <cmath>
#include <limits>
using namespace dungeonraid;
namespace {
std::int32_t add(std::int32_t a,std::int32_t b) {
    return static_cast<std::int32_t>(static_cast<std::uint32_t>(a)+static_cast<std::uint32_t>(b));
}
std::int32_t sub(std::int32_t a,std::int32_t b) {
    return static_cast<std::int32_t>(static_cast<std::uint32_t>(a)-static_cast<std::uint32_t>(b));
}
std::int32_t mul(std::int32_t a,std::int32_t b) {
    return static_cast<std::int32_t>(static_cast<std::uint32_t>(a)*static_cast<std::uint32_t>(b));
}
// ARM VCVT-to-signed semantics, including invalid and out-of-range values.
std::int32_t integer(double value) {
    if(std::isnan(value))return 0;
    if(value>=2147483647.0)return std::numeric_limits<std::int32_t>::max();
    if(value<=-2147483648.0)return std::numeric_limits<std::int32_t>::min();
    return static_cast<std::int32_t>(value);
}
void emit(const SelectionHooks* hooks,SelectionEvent event,std::int32_t value) {
    if(hooks && hooks->event)hooks->event(hooks->context,event,-1,value,0);
}
}
extern "C" void dr_preview_resources(StrokeState* state,ResourcePreviewState* p,
                                       const SelectionHooks* hooks) {
    // Game::ProcessResourceShadows, VA 0xefe0..0xf2fe, including its literal pool.
    auto& s=state->selection;auto* counts=state->resource_counts_164b0;
    const bool no_reward=s.path_length<=3 && dr_have_flaw(&s.character,2);
    for(std::size_t i=0;i<s.path_length;++i) {
        const auto index=s.path[i];if(s.fake[index])continue;
        const auto& tile=s.tiles[index];
        switch(tile.rule.type) {
        case 0: {
            const auto& flags=p->potions[index];
            if(!no_reward && !flags.flag_234 && !flags.flag_232 && (flags.flag_233^1))
                counts[0]=add(counts[0],1);
            break;
        }
        case 1: if(tile.cross_visibility)counts[1]=add(counts[1],1);break;
        case 2: if(!no_reward)counts[2]=add(counts[2],1);break;
        case 3: if(!no_reward && !tile.broken)counts[3]=add(counts[3],1);break;
        default: break;
        }
    }
    const float missing=static_cast<float>(sub(p->armour_max,p->armour_current));
    const float per_shield=static_cast<float>(mul(add(p->shield_value,p->shield_bonus),p->double_upgrade?2:1));
    const float needed=std::ceil(missing/per_shield);
    // Original converts the count to f64 BEFORE subtracting ceilf's f32 result.
    counts[3]=integer(static_cast<double>(counts[3])-static_cast<double>(needed));
    if(counts[3]<0)counts[3]=0;
    const auto mode_multiplier=state->record_14aed && state->mode_14ae8==0 ? 2:1;
    emit(hooks,SelectionEvent::HealthShadow,
         mul(mul(counts[0],add(p->healing_value,p->healing_bonus)),p->double_healing?2:1));
    const float xp=static_cast<float>(mul(counts[1],mode_multiplier))*(p->xp_bonus+2.0f);
    emit(hooks,SelectionEvent::XPShadow,integer(xp));
    const float up_base=static_cast<float>(mul(counts[3],mode_multiplier))*(p->upgrade_bonus+2.0f);
    const float upgrades=up_base*(p->double_upgrade?2.0f:1.0f);
    emit(hooks,SelectionEvent::UPShadow,integer(upgrades));
    const float gold_base=static_cast<float>(mul(counts[2],mode_multiplier))*(p->gold_bonus+2.0f);
    const float gold=gold_base*(p->double_gold?2.0f:1.0f);
    emit(hooks,SelectionEvent::GoldShadow,integer(gold));
    if(state->record_14aed && state->mode_14ae8==0) {
        const float base_xp=static_cast<float>(counts[1])*(p->xp_bonus+1.0f);
        const float base_up=static_cast<float>(counts[3])*(p->upgrade_bonus+1.0f);
        const float base_gold=static_cast<float>(counts[2])*(p->gold_bonus+1.0f);
        const float sum=base_xp+base_up*(p->double_upgrade?2.0f:1.0f);
        p->total_165d0=integer(sum+base_gold*(p->double_gold?2.0f:1.0f));
    }
}
