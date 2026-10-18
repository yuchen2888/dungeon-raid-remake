#pragma once
#include "recovered_resources.hpp"
namespace dungeonraid {
enum class AttackShieldEventKind : std::int32_t { Random=1, ShieldValue, ShieldShatter, Sound };
struct AttackShieldEvent { AttackShieldEventKind kind; std::int32_t a,b,c,d; };
struct AttackShieldHooks { void* context; void (*event)(void*,const AttackShieldEvent*); };
// Enemy-phase damage fields not yet owned by another recovered module.
struct AttackDamageState {
    ResourceState* resources;      // armour: resources->match->preview->armour_current (+0xbda4)
    std::int32_t phase;            // Game+0xb8a8 ProcessAttack phase (1..7)
    std::int32_t incoming_damage;  // Game+0xbe84 attacker GetAttack sum (InitialiseFlares)
    std::int32_t enemy9_damage;    // Game+0x1553c part of that sum from enemy type 9
};
// DamageNumber: a=remaining damage (SimpleLabel::SetNumber on the attack label).
// Label: a=label type 7,b=number,c=colour 15,d=scale float bits; position Game+0x15518.
enum class AttackAbsorbEventKind : std::int32_t { DamageNumber=1, Label };
struct AttackAbsorbEvent { AttackAbsorbEventKind kind; std::int32_t a,b,c,d; };
struct AttackAbsorbHooks { void* context; void (*event)(void*,const AttackAbsorbEvent*); };
}
extern "C" {
// ProcessAttack subsection [0x14790,0x147e4), phase-5 armour absorption only.
// Returns min(incoming_damage, armour), the R10 input of shield wear below.
// Stores incoming_damage-armour back (may be negative, as original); when
// nothing gets through, sets phase 7 and flushes a positive enemy9_damage label.
std::int32_t dr_process_attack_armour_absorb(dungeonraid::AttackDamageState*,
    const dungeonraid::AttackAbsorbHooks*);
// ProcessAttack subsection [0x147e4,0x1487e), NOT the complete enemy phase.
// Caller supplies the preceding min(incoming damage, armour) value (R10).
// Valid gameplay domain: 0 <= absorbed_damage <= current armour.
// armour_loss_chance is the signed Game+0xbdc8 comparison threshold.
// Uses the shared board, preview armour, UI armour and six-stream RNG state.
std::int32_t dr_process_attack_shield_wear(dungeonraid::ResourceState*,
    std::int32_t absorbed_damage,std::int32_t armour_loss_chance,
    const dungeonraid::AttackShieldHooks*);
}
