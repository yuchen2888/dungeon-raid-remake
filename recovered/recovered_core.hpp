#pragma once
#include <cstddef>
#include <cstdint>

// Reconstructed native data structures; these are NOT the old 32-bit layouts.
namespace dungeonraid {
struct PoisonState {
    std::int32_t current, next, following;
    std::uint8_t effect_active, effect_clearing;
    std::uint32_t effect_progress_bits;
};
struct CharacterClassState { std::int32_t race_selector; };
struct GameContext { const CharacterClassState* active_class; };
struct TileState {
    std::int32_t base_attack;
    PoisonState poison;
    const GameContext* game;
};
struct RuleTile {
    std::int32_t type, special_type, enemy_type, enemy_state, x, y;
    std::uint8_t flag_231, flag_255, matched;
};
struct RuleClass { std::int32_t race, flaws[4]; };
struct RuleGame {
    std::int32_t turn;
    RuleClass character;
    const RuleTile* board;
};
struct Point { float x, y; };
struct TouchState { std::int32_t phase; Point position; };
struct TileGeometry { Point center; float size; };
struct BoardGeometry { float vertical_offset, pitch; TileGeometry tiles[36]; };

// Persistent class state. Pointers and sizes use the native ABI; encoded bytes
// retain the original ARM32 game's 26/47-byte class and 472-byte roster format.
struct ClassProfile {
    std::int32_t class_type, race, base_race;
    std::int32_t perks[4], flaws[4];
    std::int32_t* replacement_skills;
    std::size_t replacement_skill_count;
    std::uint8_t level;
    std::uint32_t games_played, enemies_killed, normal_score, hard_score, harder_score;
};
struct ProgressionHooks {
    void* context;
    void (*achievement)(void*, std::int32_t, float);
};

// Single-target combat. Event hooks connect to rendering/reward subsystems.
struct BattleTile {
    TileState combat;
    std::int32_t type, enemy_type, enemy_state, defence, health;
    Point center;
    std::uint8_t frozen, freeze_overlay_visible, flag_256, flag_25e;
};
struct BattleGame {
    GameContext context;
    std::int32_t kill_count_165b4, kill_count_15548, killed_attack_164ac;
    std::int32_t armour_break_chance, poison_amount;
    std::uint8_t grant_coin_on_attack, poison_sound_queued;
    std::int32_t lich_progress_bits, lich_transition_bits;
};
enum class BattleEvent : std::int32_t {
    Token = 1, Particles, UpdateText, MatchTile, UpdateEnemyUV,
    Flare, Sound, Label, Freeze, Achievement, Reward, MoveMatchedTiles
};
struct BattleHooks {
    void* context;
    std::int32_t (*random)(void*, std::int32_t, std::int32_t, std::int32_t);
    void (*event)(void*, BattleEvent, std::int32_t, std::int32_t, std::int32_t, std::int32_t);
};
struct RoundTile {
    BattleTile battle;
    RuleTile rule;
    std::uint8_t attack_flag_86;
};
struct RoundState {
    BattleGame battle;
    RuleClass character;
    std::int32_t turn, base_attack, direction_bonus;
    RoundTile tiles[36];
    std::int32_t matched_counts[5];
    std::uint8_t flag_5e14, sound_13ec4, record_14aed;
    std::int32_t mode_14ae8, round_kills_165d0;
    std::int32_t crossing_best, crossing_average, crossing_samples;
    std::int32_t total_165cc, pending_165d4;
};
struct RoundEvent {
    std::int32_t tile_index; // -1 for game-wide events.
    BattleEvent kind;
    std::int32_t a, b, c, d;
};
struct RoundHooks {
    void* context;
    std::int32_t (*random)(void*, std::int32_t, std::int32_t, std::int32_t, std::int32_t);
    void (*event)(void*, const RoundEvent*);
};
}

extern "C" {
std::int32_t dr_get_attack(const dungeonraid::TileState*);
void dr_add_poison(dungeonraid::TileState*, std::int32_t);
std::int32_t dr_get_poison(dungeonraid::TileState*);
std::uint32_t dr_pointer_size();
bool dr_have_flaw(const dungeonraid::RuleClass*, std::int32_t);
std::int32_t dr_mortal_enemy(std::int32_t);
std::int32_t dr_enemy_count(const dungeonraid::RuleGame*, std::int32_t);
std::int32_t dr_nearest_unmatched(const dungeonraid::RuleGame*, std::int32_t, std::int32_t);
bool dr_can_match(const dungeonraid::RuleTile*, const dungeonraid::RuleTile* const*, std::size_t, bool);
std::int32_t dr_damage_type(const dungeonraid::RuleGame*, const dungeonraid::RuleTile* const*, std::size_t, std::size_t);
void dr_touch_start(dungeonraid::TouchState*, float, float);
void dr_touch_drag(dungeonraid::TouchState*, float, float);
void dr_touch_end(dungeonraid::TouchState*);
void dr_touch_interrupted(dungeonraid::TouchState*);
const dungeonraid::TileGeometry* dr_tile_at(const dungeonraid::BoardGeometry*, const dungeonraid::Point*);
bool dr_is_selected(const dungeonraid::TileGeometry*, const dungeonraid::Point*);
std::size_t dr_replacement_skill_count(const dungeonraid::ClassProfile*);
bool dr_class_validate(dungeonraid::ClassProfile*);
std::size_t dr_class_write_game(const dungeonraid::ClassProfile*, std::uint8_t*, std::size_t);
std::size_t dr_class_read_game(dungeonraid::ClassProfile*, const std::uint8_t*, std::size_t);
std::size_t dr_class_write_full(dungeonraid::ClassProfile*, std::uint8_t*, std::size_t);
std::size_t dr_class_read_full(dungeonraid::ClassProfile*, const std::uint8_t*, std::size_t);
std::size_t dr_classes_write(dungeonraid::ClassProfile*, std::size_t, std::uint8_t*, std::size_t);
std::size_t dr_classes_read(dungeonraid::ClassProfile*, std::size_t, const std::uint8_t*, std::size_t);
std::uint32_t dr_progression_pointer_size();
void dr_check_classes_maxed(const dungeonraid::ClassProfile*, std::size_t,
    std::int32_t, const dungeonraid::ProgressionHooks*);
bool dr_class_unlock_achievements(const dungeonraid::ClassProfile*, std::size_t,
    std::size_t, std::int32_t, const dungeonraid::ProgressionHooks*);
bool dr_class_level_up(dungeonraid::ClassProfile*, std::size_t,
    std::size_t, std::int32_t, const dungeonraid::ProgressionHooks*);
bool dr_attack_skull(dungeonraid::BattleGame*, dungeonraid::BattleTile*, std::int32_t, bool,
                     const dungeonraid::BattleHooks*);
void dr_make_phylactery(dungeonraid::BattleTile*, const dungeonraid::BattleHooks*);
void dr_set_freeze(dungeonraid::BattleTile*, bool, const dungeonraid::BattleHooks*);
void dr_get_rewards(std::int32_t, const dungeonraid::BattleHooks*);
void dr_match_path(dungeonraid::RoundState*, const std::uint8_t*, std::size_t,
                   const std::uint8_t*, std::size_t, const dungeonraid::RoundHooks*);
}
