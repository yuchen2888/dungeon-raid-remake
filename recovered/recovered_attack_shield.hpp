#pragma once
#include "recovered_resources.hpp"
namespace dungeonraid {
enum class AttackShieldEventKind : std::int32_t { Random=1, ShieldValue, ShieldShatter, Sound };
struct AttackShieldEvent { AttackShieldEventKind kind; std::int32_t a,b,c,d; };
struct AttackShieldHooks { void* context; void (*event)(void*,const AttackShieldEvent*); };
}
extern "C" {
// ProcessAttack subsection [0x147e4,0x1487e), NOT the complete enemy phase.
// Caller supplies the preceding min(incoming damage, armour) value (R10).
// Valid gameplay domain: 0 <= absorbed_damage <= current armour.
// armour_loss_chance is the signed Game+0xbdc8 comparison threshold.
// Uses the shared board, preview armour, UI armour and six-stream RNG state.
std::int32_t dr_process_attack_shield_wear(dungeonraid::ResourceState*,
    std::int32_t absorbed_damage,std::int32_t armour_loss_chance,
    const dungeonraid::AttackShieldHooks*);
}
