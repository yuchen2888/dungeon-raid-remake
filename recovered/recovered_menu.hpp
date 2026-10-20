#pragma once
#include "recovered_match.hpp"
#include "recovered_resources.hpp"
#include "recovered_turn.hpp"
namespace dungeonraid {
// A Skill object's game fields, for an equipped skill or a menu option: type (Skill+0x84; 40..47 are the
// level-up menu's stat options, StatType + 40), level +0x88, cooldown maximum / current +0x8c / +0x90,
// active +0x80. A stat option also has its line count +0xcc and its increments: health maximum +0x1d0,
// healing +0x1d4, shield +0x1d8, base damage +0x1dc and the bonus chances Game+0xbe18 / be20 / be28 / be30
// (+0x1e0 / e4 / e8 / ec).
struct SkillRecord {
    std::int32_t type, level, max, current;
    std::uint8_t active;
    std::int32_t lines, health, healing, shield, damage;
    std::int32_t chance[4];   // Game+0xbe18, be20, be28, be30
};
// FoldoutMenu (Interface+0xd10): the level-up (0), shop (1) and upgrade (2) menus. open is
// FrameScreens.menus[0] (FoldoutMenu+0x8); first / second are the chosen buttons 14..17 (+0x30 / +0x34, -1
// none); skill_options the level-up menu's skill option count (+0x78); options its four Skill objects
// (+0x48..), which Game::SetSkill swaps with the equipped ones.
struct MenuState {
    std::int32_t type, first, second, skill_options, previous_phase;
    float timer;
    std::uint8_t opening, confirm_ready, confirm_pressed;
    SkillRecord options[4];
};
// What the menus read and write. resources: level (Game+0xbe4c), skill_count, cooldowns; resources->match:
// random streams, bonus chances (Game+0xbe20 / 28 / 18 / 30 and the item parts +4), match->stroke:
// record_14aed / mode_14ae8; slots: the equipped skills; classes: the ten class records (Game+0x15564 +
// 388 * i), class_index Game+0x1648c; open: FrameScreens.menus[0] (FoldoutMenu+0x8).
struct MenuSources {
    ResourceState* resources;
    SkillSlots* slots;
    const ClassProfile* classes;
    std::int32_t class_index;
    std::uint8_t* open;
};
// Sound: Game::QueueSound(a).
enum class MenuEventKind : std::int32_t { Sound=1 };
struct MenuEvent { MenuEventKind kind; std::int32_t a; };
struct MenuHooks { void* context; void (*event)(void*,const MenuEvent*); };
}
extern "C" {
// The base skills of the ten classes (CharacterClass::Initialise 0x111e20, Class+0x30, 20 each in order).
extern const std::int32_t dr_class_base_skills[10][20];
// Original Skill::GetBaseCooldown 0x2ab90 (table 0x1d7e18; type 33 is -1, a one-time skill).
std::int32_t dr_skill_base_cooldown(std::int32_t type);
// Original Game::IsSkillUnlocked 0x8ddc: types up to 30 always; otherwise when the first of the classes 1..9
// whose first base skill it is has reached level 10.
bool dr_skill_unlocked(const dungeonraid::ClassProfile* classes,std::int32_t type);
// Original CharacterClass::GetSkillPool 0x111ad4: class type 0 offers every unlocked type 0..39; any other
// class its 20 skills, each the replacement skill (ClassProfile.replacement_skills, 255 none) or else the
// base skill. pool[type] is set for each type in it.
void dr_class_skill_pool(const dungeonraid::ClassProfile* classes,std::int32_t index,bool pool[40]);
// Original Skill::Initialise(SkillType, Skill*) 0x2b2a0 on option: type; cooldown maximum the base cooldown,
// or for an upgrade of the equipped skill existing its maximum - 1 (unchanged at level 10); 4 less in record
// mode 0; current the maximum, or the equipped skill's current capped by the maximum; level 1 or existing's +
// 1, at most 10, 5 in record mode 0. The active byte stays the option object's.
void dr_skill_option(dungeonraid::SkillRecord* option,std::int32_t type,const dungeonraid::SkillRecord* existing,bool record_mode0);
// Original Skill::Initialise(StatType) 0x2b434: type stat + 40, increments cleared, two lines; stat 0 base
// damage +1, 1 shield +1, 2 health +5, 3 healing +1, each with a 5 point bonus chance (Game+0xbe28 / be30 /
// be20 / be18, none when that chance is above 99, Skill::SetStatChance); 4 base damage +2, 5 shield +2, 6
// health +10 (one line); 7 the four bonus chances (four lines). Other fields stay the option object's.
void dr_stat_option(dungeonraid::SkillRecord* option,std::int32_t stat,const dungeonraid::MatchState* match);
// Original FoldoutMenu::Initialise 0x24a54, the level-up menu (type 0): opens it and draws its four options
// (two or one skills from the class pool, the rest stat options), see docs/T040_MENU.md.
void dr_menu_open_level(dungeonraid::MenuState*,const dungeonraid::MenuSources*,const dungeonraid::MenuHooks*);
}
