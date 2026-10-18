#pragma once
#include "recovered_stroke.hpp"

namespace dungeonraid {
struct PotionFlags { std::uint8_t flag_232, flag_233, flag_234; };
struct ResourcePreviewState {
    std::int32_t armour_current, armour_max, shield_value, shield_bonus;
    std::int32_t healing_value, healing_bonus;
    float xp_bonus, upgrade_bonus, gold_bonus;
    std::uint8_t double_upgrade, double_healing, double_gold;
    std::int32_t total_165d0;
    PotionFlags potions[36];
};
}
extern "C" {
// ProcessResourceShadows: mutates resource counts and special-mode total;
// emits computed UI preview values. Does NOT apply actual rewards to a player.
// The original increments existing counts; the stroke controller clears them
// before calling. Potion flag values follow the original boolean domain.
void dr_preview_resources(dungeonraid::StrokeState*, dungeonraid::ResourcePreviewState*,
                           const dungeonraid::SelectionHooks*);
}
