#pragma once
#include "recovered_attack_shield.hpp"
#include "recovered_rune.hpp"
namespace dungeonraid {
// Inputs of the ProcessInput gate owned outside the recovered states.
struct InputGateInputs {
    std::uint32_t falling_count;   // Game+0xb3f8 std::list<Tile*> size (moving tiles, embedding-owned)
    std::int32_t tokens_pending;   // Game+0xb52c (TokenQueueCounters.pending)
    std::int32_t flare_count;      // Game+0xbd8c (AttackAnimation.flare_count)
    std::int32_t touch_phase;      // Game+0x10
    std::int32_t input_target;     // Game+0x58ac: active skill/menu input target, -1 = none
};
// Blocked: returned before any state change. Idle: gate passed (phase 0, input ready) with no touch
// to dispatch. Dispatch: gate passed and the touch must be dispatched.
enum class InputGate : std::int32_t { Blocked=0, AttackStarted, Idle, Dispatch };
struct ScheduleHooks {
    void* context;
    // Game::EndOfTurn: wire to dr_end_of_turn.
    void (*end_of_turn)(void*);
};
}
extern "C" {
// Original Game::CountAttackers 0x8fb0: enemies (type 1) without attack flag, not frozen, with
// GetAttack > 0 (row-major).
std::int32_t dr_count_attackers(const dungeonraid::PathState*);
// Original Game::ProcessInput gate [0x16638,0x16748): blocked while tiles fall, tokens are
// pending or attack flares exist. When input is not ready and no attack runs, the enemy phase
// starts (phase 1) if CountAttackers > 0, unless it is skipped (turn <= 4 with perk 0); skipped or
// no attackers: phase 8. Phases 1..7 block; phase 8 runs EndOfTurn. Then phase 0, input ready;
// with a touch (phase != 0) and no active input target the rune preview is reset and the touch
// is dispatched (Dispatch), otherwise Idle. The dispatch itself is not part of this gate.
dungeonraid::InputGate dr_input_gate(dungeonraid::PathState*,dungeonraid::AttackDamageState*,dungeonraid::RuneState*,
    const dungeonraid::InputGateInputs*,const dungeonraid::ScheduleHooks*);
}
