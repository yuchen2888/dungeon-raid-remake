#pragma once
#include "recovered_path.hpp"
#include "recovered_resources.hpp"
#include "recovered_attack_shield.hpp"
namespace dungeonraid {
// Item::stats (Item+0x94), indexed by UpgradeType 0..19.
struct ItemStats { std::int32_t upgrade[20]; };
// Player stat fields written only by Game::UpdateStats (named by Game offset; meanings of the
// base_* fields beyond their use below are not yet confirmed).
struct PlayerStats {
    std::int32_t base_bdec,base_bdf4,base_bdfc,base_be04;   // sums of upgrades 8, 18, 19, 9
    std::int32_t chance_be1c,chance_be24,chance_be2c,chance_be34;
    std::uint8_t skill_cooldown_be64;                       // any item with upgrade 5 > 0
    std::int32_t ui_health_ceiling_5998,ui_sword_59bc,ui_armour_max_59c4,ui_skull_59c8;
};
// Destinations of Game::UpdateStats owned by other recovered states.
struct StatsTargets {
    ResourceState* resources;        // health, health_max (read), health_bonus, ui_health, ui_armour, skills
    ResourcePreviewState* preview;   // armour_current/max, xp/gold/upgrade bonus, healing/shield bonus
    StrokeState* stroke;             // selection weapon/base/bonus damage, leech, character; record/mode
    PathBattle* battle;              // armour_break_chance, poison_amount
    AttackProcessInputs* attack;     // armour_loss_chance, weaken, damage_all
    std::int32_t* regen;             // Game+0xbe70 (EndOfTurnState.regen)
    PlayerStats* player;
};
// HealthBar: a=value. ItemText: Item::MakeStats (item description text) for item a. Achievement:
// a=id, b=float bits. Label: Game::AddSimpleLabel at the tile centre, a=type, b=number, c=colour,
// d=scale bits. Sound: a=sound.
enum class StatsEventKind : std::int32_t { HealthBar=1, SwordValue, SkullValue, ShieldValue, UpdateSkills,
    ItemText, Achievement, Label, Sound };
struct StatsEvent { StatsEventKind kind; std::int32_t tile,a,b,c,d; };
struct StatsHooks { void* context; void (*event)(void*,const StatsEvent*); };
}
extern "C" {
// Original Game::UpdateStats 0x14c04: recomputes the player's stats from the equipped items
// (Item** vector, Game+0xbe9c) and skill stat multipliers, then adjusts health and armour to the
// new maxima, refreshes the interface values and moves skill cooldowns when the cooldown item
// flag changes.
void dr_update_stats(dungeonraid::StatsTargets*,const dungeonraid::ItemStats* const* items,std::uint32_t count,
    const dungeonraid::StatsHooks*);
// Original ItemUpgrade::GetStatUpgrade 0x2d774 / GetStatDowngrade 0x2d8a4: how much one upgrade
// adds to / removes from an item stat; leech (2) and armour loss chance (14) are graded by the
// player's current value, 10 (health bonus) is 0 in record mode 1, 17 depends on perk 5.
std::int32_t dr_stat_upgrade(const dungeonraid::StatsTargets*,std::int32_t type);
std::int32_t dr_stat_downgrade(const dungeonraid::StatsTargets*,std::int32_t type);
// Original Game::DestroyUpgrade 0x1515c (enemy ability 28): RandI picks an equipped item, then
// one of its positive stats (UpgradeType order); Item::ReduceStat lowers it by the downgrade
// (floor 0; the item text is redone, ItemText event) and achievement 39; then label 32 (colour
// 40) at the tile, sound 22 and UpdateStats. count must be > 0 (the original indexes the
// empty item vector otherwise).
void dr_destroy_upgrade(dungeonraid::StatsTargets*,dungeonraid::ItemStats* const* items,std::uint32_t count,
    std::uint32_t tile,const dungeonraid::StatsHooks*);
}
