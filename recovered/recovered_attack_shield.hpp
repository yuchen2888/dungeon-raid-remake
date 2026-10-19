#pragma once
#include "recovered_resources.hpp"
#include "recovered_path.hpp"
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
// Label: a=type,b=number,c=colour,d=scale bits; type 2 at Game+0xbd30, type 7 at Game+0x15518.
// Vampires: the caller must run Game::ProcessVampires at this point
// (dr_process_vampires in recovered_encounters; it only heals vampire tiles).
enum class AttackHealthEventKind : std::int32_t { Sound=1, Label, Poison, Vampires, HelpHealth, HealthBar };
struct AttackHealthEvent { AttackHealthEventKind kind; std::int32_t a,b,c,d; };
struct AttackHealthHooks { void* context; void (*event)(void*,const AttackHealthEvent*); };
// Sound: a=sound. Text: Tile::UpdateText(a,b,c). Label: a=type 4,b=number,
// c=colour 14,d=scale bits at Tile::GetAttackLabelPosition. Particles: a=type 3.
enum class AttackWeakenEventKind : std::int32_t { Sound=1, Text, Label, Particles };
struct AttackWeakenEvent { AttackWeakenEventKind kind; std::int32_t tile,a,b,c,d; };
struct AttackWeakenHooks { void* context; void (*event)(void*,const AttackWeakenEvent*); };
// SetAlpha: a=quad (0 overlay Game+0xb91c, 1 Game+0xb8ac, 2 Game+0xb98c), b=alpha.
// The original Quad::SetAlpha writes that byte to all four vertices.
enum class AttackFadeEventKind : std::int32_t { SetAlpha=1 };
struct AttackFadeEvent { AttackFadeEventKind kind; std::int32_t a,b; };
struct AttackFadeHooks { void* context; void (*event)(void*,const AttackFadeEvent*); };
// Sound: a=sound. Flare: tile, a=eye (Tile::GetEyePosition arg), b=flare type 0,
// c=colour bits 0xffffffff; the original Game::AddFlare also appends to the flare
// list and maintains its count, which the caller must do. SetAlpha: a=quad 0, b=alpha.
// Shadow: a=0 health,1 XP,2 UP,3 gold; b=-1 (Interface::Set*Shadow).
enum class AttackFlareEventKind : std::int32_t { Sound=1, Flare, SetAlpha, Shadow };
struct AttackFlareEvent { AttackFlareEventKind kind; std::int32_t tile,a,b,c; };
struct AttackFlareHooks { void* context; void (*event)(void*,const AttackFlareEvent*); };
// Sound: a=sound 3. Label: tile, a=type 5, b=amount, c=colour 16, d=scale bits.
// Achievement: a=43, b=float bits 100.
enum class AttackAllEventKind : std::int32_t { Sound=1, Label, Achievement };
struct AttackAllEvent { AttackAllEventKind kind; std::int32_t tile,a,b,c,d; };
// attack_skull and move_matched_tiles are synchronous gameplay dependencies:
// wire them to dr_path_attack_skull and dr_move_matched_tiles (both recovered).
struct AttackAllHooks {
    void* context;
    void (*event)(void*,const AttackAllEvent*);
    bool (*attack_skull)(void*,std::int32_t tile,std::int32_t amount,bool effects);
    void (*move_matched_tiles)(void*);
};
}
extern "C" {
// ProcessAttack subsection [0x14790,0x147e4), phase-5 armour absorption only.
// Returns min(incoming_damage, armour), the R10 input of shield wear below.
// Stores incoming_damage-armour back (may be negative, as original); when
// nothing gets through, sets phase 7 and flushes a positive enemy9_damage label.
std::int32_t dr_process_attack_armour_absorb(dungeonraid::AttackDamageState*,
    const dungeonraid::AttackAbsorbHooks*);
// Original Game::InitialiseFlares 0xd9b0: zero flare count (Game+0xbd8c),
// incoming damage and enemy-9 damage, then row-major sum Tile::GetAttack of every
// type-1 tile that has not attacked and is not frozen; eye flares for each except
// an enemy 32 with nonzero state.
void dr_initialise_flares(dungeonraid::AttackDamageState*,dungeonraid::PathState*,
    std::int32_t* flare_count,const dungeonraid::AttackFlareHooks*);
// ProcessAttack [0x14126,0x141c6): phase-1 overlay fade-in. alpha += dt*800
// (truncated); above 200: sound 14, phase 2, shake fields reset, InitialiseFlares,
// alpha 200. Then SetAlpha and the four interface shadows set to -1.
// Valid domain: finite 0 <= dt <= 10.
void dr_process_attack_fade_in(dungeonraid::AttackDamageState*,dungeonraid::PathState*,
    std::int32_t* flare_count,std::uint8_t* overlay_alpha,float dt,const dungeonraid::AttackFlareHooks*);
// ProcessAttack [0x14938,0x14a14) plus blocks [0x14b5e,0x14b9c) and
// [0x14bbe,0x14be0): when amount (Game+0xbe68) > 0, clear matched_counts[0..4],
// AttackSkull(amount, no effects) every type-1 tile without attack_flag in
// column-major order (sound 3 before the first, label 5 each, achievement 43 when
// an enemy 2 dies), then MoveMatchedTiles and clear every attack_flag.
void dr_process_attack_damage_all(dungeonraid::PathState*,std::int32_t amount,
    const dungeonraid::AttackAllHooks*);
// ProcessAttack [0x14ae4,0x14b56): phase-7 overlay fade. *overlay_alpha is the
// overlay Quad's vertex-0 alpha (Game+0xb92b), which doubles as the phase timer:
// alpha += dt*-900 (truncated); below 0 it becomes 0 and phase becomes 8.
// alternate_quad is Game+0xbfba. Valid domain: finite 0 <= dt <= 10.
void dr_process_attack_fade(dungeonraid::AttackDamageState*,std::uint8_t* overlay_alpha,
    float dt,bool alternate_quad,const dungeonraid::AttackFadeHooks*);
// ProcessAttack [0x1487e,0x14938) plus loop blocks 0x14b56..0x14b5d and
// 0x14b9c..0x14bbd: when weaken (Game+0xbe6c) > 0, every enemy tile that has
// not attacked and has attack > 1 loses weaken attack (floor 1), column-major.
void dr_process_attack_weaken(dungeonraid::PathState*,std::int32_t weaken,
    const dungeonraid::AttackWeakenHooks*);
// ProcessAttack subsection [0x14a14,0x14ae4): phase-6 completion only.
// Applies remaining incoming_damage to health (floored at 0), raises poison to
// enemy9_damage, sets phase 7. Does not schedule phases or check game over.
void dr_process_attack_health_damage(dungeonraid::AttackDamageState*,
    const dungeonraid::AttackHealthHooks*);
// ProcessAttack subsection [0x147e4,0x1487e), NOT the complete enemy phase.
// Caller supplies the preceding min(incoming damage, armour) value (R10).
// Valid gameplay domain: 0 <= absorbed_damage <= current armour.
// armour_loss_chance is the signed Game+0xbdc8 comparison threshold.
// Uses the shared board, preview armour, UI armour and six-stream RNG state.
std::int32_t dr_process_attack_shield_wear(dungeonraid::ResourceState*,
    std::int32_t absorbed_damage,std::int32_t armour_loss_chance,
    const dungeonraid::AttackShieldHooks*);
}
