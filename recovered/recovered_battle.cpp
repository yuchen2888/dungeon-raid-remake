#include "recovered_core.hpp"
#include <algorithm>
using namespace dungeonraid;

namespace {
std::int32_t add32(std::int32_t a, std::int32_t b) {
    return static_cast<std::int32_t>(static_cast<std::uint32_t>(a) + static_cast<std::uint32_t>(b));
}
std::int32_t sub32(std::int32_t a, std::int32_t b) {
    return static_cast<std::int32_t>(static_cast<std::uint32_t>(a) - static_cast<std::uint32_t>(b));
}
void emit(const BattleHooks* hooks, BattleEvent event, std::int32_t a = 0,
          std::int32_t b = 0, std::int32_t c = 0, std::int32_t d = 0) {
    hooks->event(hooks->context, event, a, b, c, d);
}
std::int32_t random(const BattleHooks* hooks, std::int32_t low,
                    std::int32_t high, std::int32_t stream) {
    return hooks->random(hooks->context, low, high, stream);
}
}

extern "C" void dr_make_phylactery(BattleTile* tile, const BattleHooks* hooks) {
    // Original Tile::MakePhylactery, VA 0x1a110.
    tile->enemy_state = 1;
    emit(hooks, BattleEvent::UpdateEnemyUV);
    tile->flag_25e = 1;
    tile->combat.base_attack = tile->defence = 0;
    tile->health = 1;
    tile->combat.poison.current = tile->combat.poison.next = tile->combat.poison.following = 0;
}

extern "C" void dr_set_freeze(BattleTile* tile, bool visible, const BattleHooks* hooks) {
    // Original Tile::SetFreezeVisibility, VA 0x3d934. Rendering is an event boundary.
    emit(hooks, BattleEvent::Freeze, visible);
    tile->freeze_overlay_visible = tile->frozen = visible;
    if (visible) tile->flag_256 = 0;
}

extern "C" bool dr_attack_skull(BattleGame* game, BattleTile* tile,
                                 std::int32_t incoming_attack, bool effects,
                                 const BattleHooks* hooks) {
    // Full control flow of Game::AttackSkull, VA 0xd788.
    // MatchTile is deliberately a subsystem callback, not silently approximated.
    if (tile->enemy_type == 32 && tile->type == 1 && tile->enemy_state != 0) return false;
    if (effects && game->grant_coin_on_attack) emit(hooks, BattleEvent::Token, 2, 0, 0);
    const auto damage = std::max<std::int32_t>(0, sub32(incoming_attack, tile->defence));
    const auto remaining_health = sub32(tile->health, damage);
    if (remaining_health <= 0) {
        if (tile->enemy_type == 32) {
            dr_make_phylactery(tile, hooks);
            emit(hooks, BattleEvent::Flare, 1, static_cast<std::int32_t>(0xff00ffffU));
            game->lich_progress_bits = 0;
            game->lich_transition_bits = 0x3f800000;
            return false;
        }
        game->kill_count_165b4 = add32(game->kill_count_165b4, 1);
        game->kill_count_15548 = add32(game->kill_count_15548, 1);
        game->killed_attack_164ac = add32(game->killed_attack_164ac, dr_get_attack(&tile->combat));
        emit(hooks, BattleEvent::MatchTile, 5);
        return true;
    }
    if (tile->health != remaining_health) {
        emit(hooks, BattleEvent::Particles, 2);
        tile->health = remaining_health;
        emit(hooks, BattleEvent::UpdateText, 0, 0, 1);
    }
    std::int32_t broken = 0;
    const auto blocked = std::min(tile->defence, incoming_attack);
    for (std::int32_t i = 0; i < blocked; ++i)
        if (random(hooks, 0, 100, 5) < game->armour_break_chance) ++broken;
    if (broken > 0) {
        emit(hooks, BattleEvent::Particles, 1);
        tile->defence = sub32(tile->defence, broken);
        emit(hooks, BattleEvent::UpdateText, 0, 1, 0);
    }
    if (!effects) return false;
    if (game->poison_amount > 0 && tile->enemy_type != 9) {
        if (!game->poison_sound_queued) {
            emit(hooks, BattleEvent::Sound, 29);
            game->poison_sound_queued = 1;
        }
        dr_add_poison(&tile->combat, game->poison_amount);
        emit(hooks, BattleEvent::Label, 6, 0, 15, 0x3f800000);
    }
    if (game->context.active_class->race_selector == 5 && random(hooks, 1, 100, 5) <= 10) {
        dr_set_freeze(tile, true, hooks);
        emit(hooks, BattleEvent::Achievement, 51, 0x40000000);
    }
    return false;
}

extern "C" void dr_get_rewards(std::int32_t enemy_type, const BattleHooks* hooks) {
    // Tile::GetRewards, VA 0x3d4d0. Keep original call order, including descending
    // random bounds; an eventual random backend must implement the original API.
    const auto total = random(hooks, 15, 25, 1);
    auto output = [&](std::int32_t type, std::int32_t count) {
        for (std::int32_t i = 0; i < count; ++i) emit(hooks, BattleEvent::Reward, type);
    };
    if (enemy_type == 3) { output(2, total); return; }
    if (enemy_type == 4 || enemy_type == 27) {
        const auto first = random(hooks, total / 4, total / 3, 1);
        const auto remainder = total - first;
        const auto second = random(hooks, remainder * 3 / 4, remainder / 4, 1);
        output(enemy_type == 4 ? 0 : 3, first);
        output(2, second);
        output(1, remainder - second);
        return;
    }
    const auto gold = random(hooks, total * 3 / 4,
                              enemy_type == 13 ? total / 2 : total / 3, 1);
    output(2, gold);
    output(1, total - gold);
}
