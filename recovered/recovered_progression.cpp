#include "recovered_core.hpp"
#include <algorithm>

using dungeonraid::ClassProfile;
namespace {
constexpr std::size_t game_bytes = 26, full_bytes = 47, roster_bytes = 472;
bool valid(const ClassProfile* state) {
    return state && state->replacement_skills && state->replacement_skill_count >= 20;
}
void write_u32(std::uint8_t* out, std::uint32_t value) {
    for (unsigned i = 0; i < 4; ++i) out[i] = static_cast<std::uint8_t>(value >> (i*8));
}
std::uint32_t read_u32(const std::uint8_t* in) {
    std::uint32_t result = 0;
    for (unsigned i = 0; i < 4; ++i) result |= static_cast<std::uint32_t>(in[i]) << (i*8);
    return result;
}
}

extern "C" std::uint32_t dr_progression_pointer_size() { return sizeof(void*); }

// CharacterClass::Initialise, original Thumb entry 0x111e20 (Game::Start, once per class type 0..9; other types are
// not used). The type; level 1 for class 0 and 0 (locked) for the others; the class's race, which is also its base
// race; its first perk and flaw (the class's own; 255 for class 0) and 255 in the other slots; one replacement slot
// per base skill, all 255 (none replaced; replacement_skills holds 20). The base skills (dr_class_base_skills) and the
// other 20 skills in order are constant per class. The progress counters are left as they are.
extern "C" bool dr_class_initialise(ClassProfile* state, std::int32_t type, std::int32_t* replacement_skills) {
    static constexpr std::int32_t races[10] = {0, 1, 6, 4, 5, 9, 3, 8, 2, 7};
    static constexpr std::int32_t first[10] = {255, 6, 2, 5, 4, 1, 7, 8, 9, 3};
    if (!state || !replacement_skills || type < 0 || type > 9) return false;
    state->class_type = type;
    state->level = type == 0 ? 1 : 0;
    state->race = state->base_race = races[type];
    for (int i = 0; i < 4; ++i) state->perks[i] = state->flaws[i] = i == 0 ? first[type] : 255;
    for (int i = 0; i < 20; ++i) replacement_skills[i] = 255;
    state->replacement_skills = replacement_skills;
    state->replacement_skill_count = 20;
    return true;
}

// Game::SetCurrentClass, original Thumb entry 0x1a390: the class becomes the current one when it is unlocked
// (level above 0), else class 0 (NameScreen::SelectClass shows it). Types 0..9 (the original reads past the
// records for others): else 0.
extern "C" std::int32_t dr_current_class(const ClassProfile* states, std::int32_t type) {
    return type >= 0 && type <= 9 && states[type].level ? type : 0;
}

// CharacterClass::GetReplacementSkillCount, original Thumb entry 0x111844.
extern "C" std::size_t dr_replacement_skill_count(const ClassProfile* state) {
    if (!state || !state->replacement_skills) return 0;
    std::size_t result = 0;
    for (std::size_t i = 0; i < state->replacement_skill_count; ++i)
        if (state->replacement_skills[i] != 255) ++result;
    return result;
}

// CharacterClass::Validate, 0x111870. Preserve the original loop ordering:
// later duplicates are removed, then unmatched perk/flaw pairs are cleared.
extern "C" bool dr_class_validate(ClassProfile* state) {
    if (!valid(state)) return false;
    for (int i = 0; i < 4; ++i)
        for (int j = 0; j < 4; ++j)
            if (i != j && state->perks[i] == state->perks[j]) state->perks[j] = 255;
    for (int i = 0; i < 4; ++i)
        for (int j = 0; j < 4; ++j)
            if (i != j && state->flaws[i] == state->flaws[j]) state->flaws[j] = 255;
    for (int i = 0; i < 4; ++i)
        if (state->perks[i] != 255 && state->flaws[i] == 255) state->perks[i] = 255;
    std::size_t remaining = dr_replacement_skill_count(state);
    for (int i = 0; i < 20; ++i) {
        if (state->replacement_skills[i] != 255) {
            if (remaining == 0) state->replacement_skills[i] = 255;
            else --remaining;
        }
    }
    if (state->class_type != 0 && state->level <= 4) state->race = state->base_race;
    return true;
}

// CharacterClass::SerialiseGameState, 0x11172c. The first perk/flaw and skill
// slots are class defaults, deliberately excluded by the original format.
extern "C" std::size_t dr_class_write_game(const ClassProfile* state, std::uint8_t* out, std::size_t capacity) {
    if (!valid(state) || !out || capacity < game_bytes) return 0;
    std::size_t cursor = 0;
    out[cursor++] = static_cast<std::uint8_t>(state->race);
    for (int i = 1; i < 4; ++i) {
        out[cursor++] = static_cast<std::uint8_t>(state->perks[i]);
        out[cursor++] = static_cast<std::uint8_t>(state->flaws[i]);
    }
    for (int i = 1; i < 20; ++i) out[cursor++] = static_cast<std::uint8_t>(state->replacement_skills[i]);
    return cursor;
}

// CharacterClass::DeserialiseGameState, 0x111794.
extern "C" std::size_t dr_class_read_game(ClassProfile* state, const std::uint8_t* in, std::size_t length) {
    if (!valid(state) || !in || length < game_bytes) return 0;
    std::size_t cursor = 0;
    state->race = in[cursor++];
    for (int i = 1; i < 4; ++i) {
        state->perks[i] = in[cursor++];
        state->flaws[i] = in[cursor++];
    }
    for (int i = 1; i < 20; ++i) state->replacement_skills[i] = in[cursor++];
    return cursor;
}

// CharacterClass::SerialiseFullState, 0x111934. Validate changes live state too.
extern "C" std::size_t dr_class_write_full(ClassProfile* state, std::uint8_t* out, std::size_t capacity) {
    if (!valid(state) || !out || capacity < full_bytes) return 0;
    dr_class_validate(state);
    std::size_t cursor = dr_class_write_game(state, out, capacity);
    out[cursor++] = state->level;
    const std::uint32_t values[] = {state->games_played, state->enemies_killed,
        state->normal_score, state->hard_score, state->harder_score};
    for (std::uint32_t value : values) { write_u32(out+cursor, value); cursor += 4; }
    return cursor;
}

// CharacterClass::DeserialiseFullState, 0x1119d0. Class zero always loads at
// level one; all other persisted levels are clamped to the original 0..10.
extern "C" std::size_t dr_class_read_full(ClassProfile* state, const std::uint8_t* in, std::size_t length) {
    if (!valid(state) || !in || length < full_bytes) return 0;
    std::size_t cursor = dr_class_read_game(state, in, length);
    state->level = static_cast<std::uint8_t>(std::min<unsigned>(in[cursor++], 10));
    if (state->class_type == 0) state->level = 1;
    std::uint32_t* values[] = {&state->games_played, &state->enemies_killed,
        &state->normal_score, &state->hard_score, &state->harder_score};
    for (std::uint32_t* value : values) { *value = read_u32(in+cursor); cursor += 4; }
    dr_class_validate(state);
    return cursor;
}

// Game::SerialiseClasses, 0x8ee8. The surrounding game's dirty flag and buffer
// ownership are adapter responsibilities; these functions produce the bytes.
extern "C" std::size_t dr_classes_write(ClassProfile* states, std::size_t count, std::uint8_t* out, std::size_t capacity) {
    if (!states || count != 10 || !out || capacity < roster_bytes) return 0;
    for (std::size_t i = 0; i < count; ++i) if (!valid(states+i)) return 0;
    out[0] = 0; out[1] = 10;
    for (std::size_t i = 0; i < count; ++i) dr_class_write_full(states+i, out+2+i*full_bytes, full_bytes);
    return roster_bytes;
}

// Game::DeserialiseClasses, 0x8ea0. Original code checks the count byte only.
// Native bounds checks are added before mutation for truncated/corrupt inputs.
extern "C" std::size_t dr_classes_read(ClassProfile* states, std::size_t count, const std::uint8_t* in, std::size_t length) {
    if (!states || count != 10 || !in || length < roster_bytes || in[1] != 10) return 0;
    for (std::size_t i = 0; i < count; ++i) if (!valid(states+i)) return 0;
    for (std::size_t i = 0; i < count; ++i) dr_class_read_full(states+i, in+2+i*full_bytes, full_bytes);
    return roster_bytes;
}

namespace {
void achievement(const dungeonraid::ProgressionHooks* hooks, std::int32_t difficulty, std::int32_t id) {
    // Game::QueueAchievement's original easy-difficulty gate. Queue allocation
    // and drain timing belong to the caller; preserve the ordered game events.
    if ((difficulty != 0 || id == 67) && hooks && hooks->achievement)
        hooks->achievement(hooks->context, id, 100.0f);
}
}

// Game::CheckIfAllClassesMaxed, 0xbe30: class zero is excluded.
extern "C" void dr_check_classes_maxed(const ClassProfile* states, std::size_t count,
        std::int32_t difficulty, const dungeonraid::ProgressionHooks* hooks) {
    if (!states || count != 10) return;
    for (std::size_t i = 1; i < 10; ++i) if (states[i].level <= 9) return;
    achievement(hooks, difficulty, 28);
}

// CharacterClass::UnlockAchievement, 0x111a38. Reporting achievements is an
// output of the local class state; no server result is needed to level up.
extern "C" bool dr_class_unlock_achievements(const ClassProfile* states, std::size_t count,
        std::size_t index, std::int32_t difficulty, const dungeonraid::ProgressionHooks* hooks) {
    if (!states || count != 10 || index >= count) return false;
    const ClassProfile& state = states[index];
    if (state.class_type == 0) return true;
    if (state.level != 0) {
        achievement(hooks, difficulty, state.class_type);
        if (state.level > 4) achievement(hooks, difficulty, state.base_race+9);
        if (state.level == 10) achievement(hooks, difficulty, state.class_type+18);
    }
    dr_check_classes_maxed(states, count, difficulty, hooks);
    return true;
}

// CharacterClass::LevelUp, 0x111a88.
extern "C" bool dr_class_level_up(ClassProfile* states, std::size_t count, std::size_t index,
        std::int32_t difficulty, const dungeonraid::ProgressionHooks* hooks) {
    if (!states || count != 10 || index >= count) return false;
    states[index].level = static_cast<std::uint8_t>(std::min<unsigned>(states[index].level+1u, 10));
    return dr_class_unlock_achievements(states, count, index, difficulty, hooks);
}
