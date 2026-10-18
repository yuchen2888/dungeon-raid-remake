#pragma once
#include "recovered_core.hpp"

namespace dungeonraid {
struct SelectionTile {
    RuleTile rule;
    TileGeometry geometry;
    Point resting_position;
    float size;
    std::uint8_t selected, cross_visibility, magic_sword, broken, flaming, self_flame;
    std::int32_t flame_damage;
};
enum class SelectionEvent : std::int32_t {
    HideTooltip=1, Undim, SetSize, TileSound, HealthShadow, XPShadow,
    UPShadow, GoldShadow, CrossVisibility, Arrow,
    // Stroke controller boundaries. Wire ResourceShadows to dr_preview_resources.
    // Wire ProcessRune to dr_process_rune. ProcessPretzels is still unresolved.
    EnemyTooltip, UpdateDimming, ResourceShadows, ProcessRune, ProcessPretzels,
    RuneAllocateHighlight, RuneHighlight, RuneMatchTile, RuneAchievement
};
struct SelectionHooks {
    void* context;
    void (*event)(void*, SelectionEvent, std::int32_t, std::int32_t, std::int32_t);
};
struct SelectionState {
    BoardGeometry geometry;
    Point touch;
    float half_spacing;
    RuleClass character;
    SelectionTile tiles[36];
    std::uint8_t path[36], fake[36];
    std::size_t path_length;
    std::int32_t weapon_damage, base_damage, bonus_base_damage, leech;
    std::int32_t current_damage, current_leech, current_flame_damage, current_spike_damage;
    std::uint8_t double_damage, skull_counted, spiky_enemy_attacked;
    std::uint8_t flame_label_moving, spike_label_moving;
};
}
extern "C" {
void dr_select_tile(dungeonraid::SelectionTile*, std::int32_t, const dungeonraid::SelectionHooks*);
void dr_process_tile_selection(dungeonraid::SelectionState*, const dungeonraid::SelectionHooks*);
}
