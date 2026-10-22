#pragma once
#include "recovered_schedule.hpp"
#include "recovered_items.hpp"
#include "recovered_generation.hpp"
#include "recovered_stats.hpp"
namespace dungeonraid {
// The saved game (T030-N5). Game::SerialiseState writes it into the buffer Game+0x13ecf (0x800 bytes); its length
// is Game+0x146d0 and Game+0x146d4 is set when it changed (EndGameState.flag_146d0 / flag_146d4: Game::CheckEndGame
// clears the length when a game ends). The platform stores the buffer when the flag is set and puts the stored bytes
// back into it at start-up; Game::ContinueGame (InitNewGame, DeserialiseState, CalculateTilePositions) resumes the
// game. Format version 3 (header 0xff, 3); every field is the live owner of its Game field.
struct SaveSources {
    StrokeState* stroke;              // record_14aed / mode_14ae8; selection: tiles, base_damage, character (race, flaws)
    MatchState* match;                // random streams 1..5, bonus_chance, perks, spawn_count_1555c, spawn_enabled_14ae0, flag_25d
    ResourcePreviewState* preview;    // potions, armour_current, shield_value, healing_value
    ResourceState* resources;         // health, xp / up / gold and their totals, poison, skill_count, cooldowns
    PathState* path;                  // turn, total, crossing_*, battle.kill_count_165b4, combat (attack, defence, health, poison)
    GenerationState* generation;      // max_health, time_to_promotion
    ClassScrollState* scroll;         // the class records and the current class (Game+0x1648c)
    NewGameExtra* extra;              // base_bde8
    SkillSlots* skills;               // with resources->skill_max / skill_current: the Skill objects at Game+0xbf90
    ItemRecord* items;                // the five equipped items in Item** vector order (Game+0xbe9c)
    TurnFinishFlags* finish;          // help_flags_102d0 (HelpMenu+0x38)
    std::uint8_t* name;               // Game+0xbe38: the player's name, 17 bytes
    PlayerStats* player;              // DeserialiseState: the interface values it refreshes (ui_skull, ui_health_ceiling, ui_armour_max)
    struct SaveSettings* settings;    // DeserialiseState: the help setting and the difficulty-changed flag
};
// Game settings (the platform stores them when they change; DeserialiseState writes the first two).
struct SaveSettings {
    std::uint8_t help_13ec8;                 // Game::SetHelpState: help shown (the game menu's switch)
    std::uint8_t difficulty_changed_14ae4;   // Game::SetDifficulty: set when the difficulty changed
    std::uint8_t mode_changed_14aec;         // Game::SetMode: set when the mode changed
    std::uint8_t name_changed_be49;          // Game::SetName: set when the name changed
};
// Achievement: a = achievement, b = value float bits (Item::Serialise). DeserialiseState's presentation: Freeze (a = tile,
// Tile::SetFreezeVisibility), Skull / HealthCeiling / Health / ArmourMax / Armour / XP / UP / Gold (the Interface update of
// that value, a = value), Poison (Interface::SetPoison, a), PositionSkill (a = slot), UpdateSkills, HelpState
// (GameMenu::SetHelpState, a), SkillIcon / ItemIcon (a = slot: Upgrade::SetIcon and the texts). The tiles' colours, UVs,
// texts, countdowns and enemy UVs go through the generation hooks as the generation unit reports them.
enum class SaveEventKind : std::int32_t { Achievement=1, Freeze, Skull, HealthCeiling, Health, ArmourMax, Armour, XP, UP, Gold,
    Poison, PositionSkill, UpdateSkills, HelpState, SkillIcon, ItemIcon };
struct SaveHooks {
    void* context;
    void (*event)(void*,SaveEventKind,std::int32_t,std::int32_t);
    void (*update_stats)(void*);              // DeserialiseState: Game::UpdateStats (with the session's views)
    const GenerationHooks* generation;        // Tile::SetType, the Make* functions, SetSpecialType, UpdateValues
    const TurnHooks* turn;                    // Tile::SetFlameVisibility
};
constexpr std::uint32_t save_capacity=0x800;
// Game::SerialiseClasses / DeserialiseClasses: the ten class records (the progress kept between games) at Game+0x146d5:
// 0, 10, then CharacterClass::SerialiseFullState of each (47 bytes); its length Game+0x14ad8, Game+0x14adc set when it
// changed. The platform stores it like the saved game.
constexpr std::uint32_t class_save_capacity=472;
struct ClassSave { std::uint8_t bytes[class_save_capacity]; std::int32_t length_14ad8; std::uint8_t changed_14adc; };
}
extern "C" {
// Original Game::SerialiseState 0x91c4 into buffer (save_capacity bytes): header 0xff, 3; record mode (mode or
// 0xff); total, crossing samples (4 bytes each), crossing average and best (1 byte); the current class (1 byte) and
// CharacterClass::SerialiseGameState of it (race, perks / flaws 1..3, replacement skills 1..19 as the units hold
// them); spawn_count_1555c; the 36 tile types two to a byte (high nibble first); Tile::Serialise of every tile;
// turn and kill_count_165b4; bonus chances Game+0xbe18 / be20 / be28 / be30, poison and time_to_promotion bytes
// (the byte between those two is not written: it keeps what the buffer held); base_bde8[4], base_damage,
// shield_value, healing_value, health_max, health, xp + total_xp, up + total_up, gold + total_gold, armour_current;
// Item::Serialise of the five items (more than 7 stats: achievement 72); skill_count and Skill::Serialise of each
// (type, max, current, level); the name up to its terminator (at most 17 bytes); random streams 1..5; the help flags;
// spawn_enabled_14ae0. Returns the length.
std::uint32_t dr_serialise_state(const dungeonraid::SaveSources*,std::uint8_t* buffer,const dungeonraid::SaveHooks*);
// Original Game::DeserialiseState 0x15c18 / DeserialiseState2 0x15290 from buffer (after Game::InitNewGame in
// Game::ContinueGame). A buffer without the 0xff header is the format before version 1 (DeserialiseState1, not
// recovered): false, nothing read (also false, stopped there, for a class index above 9: a damaged save). Otherwise
// version = the second byte (format with a header when it is not 0):
// spawn_count_1555c = 0; version > 2: record mode (not 0xff; mode = clamp(byte, 0, 1)), total and crossing values
// (else total 0, not record mode); version > 1: the current class, CharacterClass::DeserialiseGameState of it (the
// units' race / perks / flaws follow the record) and spawn_count_1555c (else class 0); time_to_promotion = 1; every
// tile Tile::SetType(type, turn 0, difficulty) from the nibbles, then Tile::Deserialise2 (kind byte: explosive / mana /
// acid potion, magic / broken sword or arrow, a broken shield only with a header, a scroll's special type; frozen or
// burning with its flame damage; a skull's attack, defence, health, max health (Tile::UpdateValues), enemy type, state,
// flag_25d, poison values up to the first zero with the poison effect shown); turn, kill_count_165b4 (version > 1);
// chances, poison, time_to_promotion; base_bde8, base_damage, shield and healing values, health_max, health; xp / up /
// gold = sum % 100 with their totals the rest and level = total_xp / 100 + 1; armour; Item::Deserialise2 of the five
// items; with armour, armour_max and health_bonus 0 Game::UpdateStats, then health and armour back; the interface
// values; skill_count and Skill::Deserialise of each (max 255: max and current -1); the name; random streams 1..5;
// the help flags (SetHelpState(flags != 0)); Game::SetDifficulty(clamp 0..3, changed flag).
bool dr_deserialise_state(const dungeonraid::SaveSources*,const std::uint8_t* buffer,const dungeonraid::SaveHooks*);
// Original Game::SerialiseClasses 0x8ee8: the current class record takes the units' race / perks / flaws; every record
// is validated and written (dr_classes_write: CharacterClass::SerialiseFullState); the units' views follow the validated
// current record (Validate may clear perks or flaws and, below level 5, give the class its base race back); length and
// changed flag. A record without a replacement list is written as having none replaced.
void dr_serialise_classes(const dungeonraid::SaveSources*,dungeonraid::ClassSave*);
// Original Game::DeserialiseClasses 0x8ea0 (Game::Start): with the count byte 10, every record from the stored bytes
// (CharacterClass::DeserialiseFullState); the units' views follow the current record. False otherwise.
bool dr_deserialise_classes(const dungeonraid::SaveSources*,const dungeonraid::ClassSave*);
}
