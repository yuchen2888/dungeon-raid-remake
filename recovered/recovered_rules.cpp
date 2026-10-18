#include "recovered_core.hpp"
using namespace dungeonraid;

// Reconstructed from Dungeon Raid 1.3.4 ARMv7 instructions.
// Enum values and flag offsets are kept explicit where names are unconfirmed.
static_assert(sizeof(void*) == 8);

extern "C" bool dr_have_flaw(const RuleClass* character, std::int32_t flaw) {
    if (flaw == 255) return false;
    for (auto value : character->flaws) if (value == flaw) return true;
    return false;
}
extern "C" std::int32_t dr_mortal_enemy(std::int32_t race) {
    // TBB table at original VA 0x1116fa; races 1 through 9.
    constexpr std::int32_t table[] = {9, 14, 13, 16, 12, 5, 20, 8, 19};
    return race >= 1 && race <= 9 ? table[race - 1] : 0;
}
extern "C" std::int32_t dr_enemy_count(const RuleGame* game, std::int32_t enemy) {
    std::int32_t count = 0;
    for (std::size_t i = 0; i < 36; ++i)
        if (game->board[i].type == 1 && game->board[i].enemy_type == enemy) ++count;
    return count;
}
extern "C" std::int32_t dr_nearest_unmatched(
    const RuleGame* game, std::int32_t x, std::int32_t y) {
    // Original GetNearestUnmatchedTile; called with x=0..5, y=0..6.
    for (auto row = y - 1; row >= 0; --row)
        if (!game->board[row * 6 + x].matched) return row;
    return -1;
}
static bool phylactery(const RuleTile* tile) {
    return tile->type == 1 && tile->enemy_type == 32 && tile->enemy_state != 0;
}
extern "C" bool dr_can_match(const RuleTile* tile, const RuleTile* const* path,
                              std::size_t count, bool flag) {
    // Original Tile::CanMatchType, VA 0x3f644. This tests type eligibility;
    // adjacency, path backtracking and minimum length are handled elsewhere.
    if (tile->flag_255 && tile->type != 1) return false;
    if (!count || tile->special_type == 0) return true;
    if (tile->special_type == 1) return false;
    const auto* last = path[count - 1];
    if (!flag && last->type == 4 && last->flag_231) return true;
    if (last->special_type == 0) return true;
    if (last->special_type == 1) return false;
    if (count > 1) {
        const auto* before_last = path[count - 2];
        if (before_last && before_last->type == 4 && before_last->flag_231)
            return !phylactery(tile) && (tile->type == 1 || tile->type == 4);
    }
    if (phylactery(tile)) return last->type == 2 || phylactery(last);
    if (phylactery(last)) return tile->type == 2 || phylactery(tile);
    return tile->type == last->type ||
           (tile->type == 1 && last->type == 4) ||
           (tile->type == 4 && last->type == 1);
}
extern "C" std::int32_t dr_damage_type(
    const RuleGame* game, const RuleTile* const* path, std::size_t count,
    std::size_t index) {
    // Original Tile::GetDamageType, VA 0x3f790. Returns original enum 0..3.
    const auto* tile = path[index];
    if (tile->type != 1 || phylactery(tile)) return 0;
    if (game->turn <= 4 && dr_have_flaw(&game->character, 0)) return 1;
    const auto* next = index + 1 < count ? path[index + 1] : nullptr;
    if (tile->enemy_type == 27)
        return !next || next->y >= tile->y ? 1 : 2;
    const auto race = game->character.race;
    if (race == 2 && next && next->x == tile->x && next->y < tile->y && index > 0) {
        const auto* previous = path[index - 1];
        if (previous->x == next->x && previous->y > tile->y) return 3;
    }
    if (tile->enemy_type == 14 && dr_mortal_enemy(race) == 14) return 1;
    if (tile->enemy_type != 30 && dr_enemy_count(game, 30) > 0) return 1;
    return 2;
}
