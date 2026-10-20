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
// Attack label/flare animation fields not owned by another recovered module.
// The two phase timers are MatchState shake_progress_bd90 / shake_scale_bd94.
struct AttackAnimation {
    float label_progress;      // Game+0xbd58
    float label_y;             // Game+0xbd54
    float damage_label_alpha;  // Game+0xbd38
    float poison_label_alpha;  // Game+0x15520
    std::int32_t flare_count;  // Game+0xbd8c (flare list at Game+0xbd80, stride 0x70)
    std::uint8_t counterattack;// Game+0xbfba
    // Phase 5/6 label motion parameters, named by Game offset until their
    // meaning is confirmed by the phase-5/6 animation code.
    float bd30,bd34,bd5c,bd60,bd64,bd68,bd6c,bd70,bd74,bd78,bd7c;
};
// Sound: a=27. LabelNumber: a=label (0 damage Game+0xb9fc, 1 poison Game+0x151e4), b=number.
// LabelPosition: a=label, b=x bits, c=y bits. FlareAlpha: a=flare, b=alpha.
// FlareScale: a=flare, b=float bits stored to flare+0x64 and +0x68.
// SetAlpha: a=quad 2 (Game+0xb98c), b=alpha.
// LabelAlpha: a=label, b=alpha. HelpMenu: HelpMenu::Initialise(Game+0x10298, a=bd30 bits,
// b=bd34 bits, 0, 0, type c=16). Random: a=low bits, b=high bits, c=stream, (result in bd7c).
// SetAlpha quad 1 is Game+0xb8ac.
// AddLabel: Game::AddSimpleLabel(a=type, position &bd30, b=number, c=colour, scale 0.5).
enum class AttackAnimEventKind : std::int32_t { Sound=1, LabelNumber, LabelPosition, FlareAlpha, FlareScale, SetAlpha,
    LabelAlpha, HelpMenu, Random, AddLabel };
struct AttackAnimEvent { AttackAnimEventKind kind; std::int32_t a,b,c; };
// counterattack must run Game::DoCounterattack (dr_do_counterattack).
struct AttackAnimHooks {
    void* context;
    void (*event)(void*,const AttackAnimEvent*);
    void (*counterattack)(void*);
};
// Game fields read by ProcessAttack whose producers are outside it.
struct AttackProcessInputs {
    std::int32_t armour_loss_chance; // Game+0xbdc8
    std::int32_t weaken;             // Game+0xbe6c
    std::int32_t damage_all;         // Game+0xbe68
};
struct AttackProcessHooks {
    const AttackFlareHooks* flare;   // phase 1 + InitialiseFlares
    const AttackAnimHooks* anim;     // phases 2..6 animation, counterattack
    const AttackAbsorbHooks* absorb;
    const AttackShieldHooks* shield;
    const AttackWeakenHooks* weaken;
    const AttackAllHooks* all;       // damage-all: attack_skull, move_matched_tiles
    const AttackHealthHooks* health; // Vampires must run dr_process_vampires
    const AttackFadeHooks* fade;
};
}
extern "C" {
// Original Game::AddFlare 0x9f94, its game state: the flare's rotation Rand(0, 360, stream 0) (returned) and
// the flare count (Game+0xbd8c) + 1, which keeps input blocked until the flares fade. The flare quad itself
// (UV by type, position, size 0.08, colour; the list grows when full) is presentation: the caller passes
// type, position and colour to the renderer with the rotation.
float dr_add_flare(std::int32_t* flare_count,dungeonraid::RandomState*);
// Original Game::AddParticles 0xa914 (Particles::InitialiseFromTile), its game state: the particles' random
// spread draws Rand(..., stream 0) 33 times for particle type 0 (from the tile), 81 times for types 1..3 (at the
// tile's defence / health / attack label), none for other types. The particles are presentation.
void dr_add_particles(dungeonraid::RandomState*,std::int32_t type);
// Original SimpleLabel::Initialise 0x23078 (Game::AddSimpleLabel, both overloads -- the tile overload uses label
// type 0): label types 1, 8, 9, 10 (speed 0.1) and 3 (0.08) draw nothing, any other type Rand(0.1, 0.2, stream 0)
// once. The label is presentation.
void dr_add_simple_label(dungeonraid::RandomState*,std::int32_t type);
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
// Original Game::DoCounterattack 0x11214: clear matched_counts[0..4]; every
// type-1 tile without attack_flag, column-major, takes AttackSkull of its own
// Tile::GetAttack (effects false); Label event: tile, a=type 2, b=attack, c=11,
// d=0.5 bits, shown at the tile's resting position (Game+0xb400 table). Then
// MoveMatchedTiles and clear every attack_flag. Uses AttackAllHooks callbacks.
void dr_do_counterattack(dungeonraid::PathState*,const dungeonraid::AttackAllHooks*);
// ProcessAttack [0x141c6,0x143ca): phases 2..4 shared timers and flare
// animation, the phase-2 exit (to 3 with counterattack, else 4 with damage and
// poison labels) and phase 3 (label fade; when flares are done, phase 7 and
// DoCounterattack). Phase-4 work after 0x143ca is separate. dt finite, >= 0.
// Returns whether the flares finished this frame (the original's [sp,#0x2c]).
bool dr_process_attack_flares(dungeonraid::AttackDamageState*,dungeonraid::AttackAnimation*,
    float dt,const dungeonraid::AttackAnimHooks*);
// ProcessAttack [0x143ca,0x1457c): phase 4. progress += 8dt; above 1 with the
// flares done this frame (flares_done from dr_process_attack_flares): phase 5
// when armour > 0 else 6, motion parameters, Rand(float) on stream 0 into bd7c,
// HelpMenu. Then bd74 = damage-label alpha and three alphas from progress.
void dr_process_attack_phase4(dungeonraid::AttackDamageState*,dungeonraid::AttackAnimation*,
    bool flares_done,float dt,const dungeonraid::AttackAnimHooks*);
// ProcessAttack [0x1457c,0x146ce): phases 5/6 label motion. bd70 (speed)
// += 20dt; bd6c (progress) += bd70*dt, capped at 1 = completed. Label 0 at
// Interpolate((bd64,bd68),(bd5c,bd60),t) minus (0.25-(0.5-t)^2)*bd7c on x (phase 5)
// or y (phase 6); label 1 at that point + (0, 0.05); damage-label alpha (bd38)
// = Interpolate(bd78, bd74, powf(t,5)) = bd78*p + (1-p)*bd74, copied to +0x15520.
// Returns true when completed (original continues at 0x146ce, else 0x14ae4).
bool dr_process_attack_label_motion(dungeonraid::AttackDamageState*,dungeonraid::AttackAnimation*,
    float dt,const dungeonraid::AttackAnimHooks*);
// ProcessAttack [0x146ce,0x14790), reached when the label motion completes.
// Phase 6 continues at 0x14a14 (dr_process_attack_health_damage), nothing here.
// Phase 5: phase 6 and the next motion (to (0.8625,1.29375) from (bd30,bd34),
// alpha bd38 -> 0.2, arc Rand(0.4,0.8,stream 0)), label 2 showing
// -min(incoming damage, armour), HelpMenu type 17; then 0x14790 absorption
// (dr_process_attack_armour_absorb) follows in the same frame.
void dr_process_attack_phase5_done(dungeonraid::AttackDamageState*,dungeonraid::AttackAnimation*,
    const dungeonraid::AttackAnimHooks*);
// Whole Game::ProcessAttack 0x14118 for one frame, composed in the original's
// control-flow order from the recovered parts above: phase 1, phases 2..4,
// phase 4, phase 5/6 motion, then on completion either (phase 5) the completion
// block, absorption, shield wear, weakening and damage-all, or (phase 6) health
// damage; finally the phase-7 fade. a->counterattack (Game+0xbfba) is also the
// fade's alternate-quad flag. overlay_alpha is Game+0xb92b.
void dr_process_attack(dungeonraid::AttackDamageState*,dungeonraid::PathState*,dungeonraid::AttackAnimation*,
    std::uint8_t* overlay_alpha,float dt,const dungeonraid::AttackProcessInputs*,const dungeonraid::AttackProcessHooks*);
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
