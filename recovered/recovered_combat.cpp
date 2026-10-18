#include "recovered_core.hpp"
using namespace dungeonraid;

// Reconstructed from Dungeon Raid 1.3.4 armv7 machine code, not original source.
// Only the fields used by the three recovered functions are represented here.
// Semantic labels for graphics flags remain provisional; their bytes are exact.
static_assert(sizeof(void*) == 8, "This recovery must be built for a 64-bit target");

extern "C" std::int32_t dr_get_attack(const TileState* tile) {
    // Original Tile::GetAttack, armv7 VA 0x3d21c.
    const auto attack = tile->base_attack;
    if (attack > 1 && tile->poison.current > 0 &&
        tile->game->active_class->race_selector == 1) {
        return attack / 2;
    }
    return attack;
}

static std::int32_t add_wrapping(std::int32_t a, std::int32_t b) {
    // Original ARM addition wraps at 32 bits. Do not invoke signed-overflow UB.
    const auto bits = static_cast<std::uint32_t>(a) + static_cast<std::uint32_t>(b);
    return static_cast<std::int32_t>(bits);
}

extern "C" void dr_add_poison(TileState* tile, std::int32_t amount) {
    // Original Tile::AddPoison(int), armv7 VA 0x3d25c.
    auto& p = tile->poison;
    if (p.current == 0) {
        p.effect_clearing = 0;
        p.effect_active = 1;
        p.effect_progress_bits = 0;
    }
    p.current = add_wrapping(p.current, amount);
    p.next = add_wrapping(p.next, amount);
    p.following = add_wrapping(p.following, amount);
}

extern "C" std::int32_t dr_get_poison(TileState* tile) {
    // Original Tile::GetPoison, armv7 VA 0x3d290.
    auto& p = tile->poison;
    const auto result = p.current;
    if (result != 0) {
        p.current = p.next;
        p.next = p.following;
        p.following = 0;
        if (p.current == 0) {
            p.effect_active = 0;
            p.effect_clearing = 1;
            p.effect_progress_bits = 0;
        }
    }
    return result;
}

extern "C" std::uint32_t dr_pointer_size() {
    return sizeof(void*);
}
