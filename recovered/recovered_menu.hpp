#pragma once
#include "recovered_match.hpp"
#include "recovered_resources.hpp"
#include "recovered_turn.hpp"
#include "recovered_stats.hpp"
#include "recovered_items.hpp"
#include "recovered_skills.hpp"
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
// (+0x48..), which Game::SetSkill swaps with the equipped ones; items the shop's three Item objects (+0x38..),
// which Game::SetItem swaps with the equipped one; scroll_slot the shop option that comes with a scroll (+0x10c,
// -1 none) and scroll its Skill object (+0x110).
struct MenuState {
    std::int32_t type, first, second, skill_options, previous_phase;
    float timer;
    std::uint8_t opening, confirm_ready, confirm_pressed;
    SkillRecord options[4];
    ItemRecord items[3];
    std::int32_t scroll_slot;
    SkillRecord scroll;
    // The upgrade menu: four equipped items (FoldoutMenu+0x58.., here their slot in MenuSources.equipped) and the
    // ItemUpgrade proposed for each (+0x68..: stat type +0x80, amount +0x84).
    std::int32_t upgrade_items[4], upgrade_type[4], upgrade_amount[4];
};
// What the menus read and write. resources: level (Game+0xbe4c), skill_count, cooldowns; resources->match:
// random streams, bonus chances (Game+0xbe20 / 28 / 18 / 30 and the item parts +4), match->stroke:
// record_14aed / mode_14ae8; slots: the equipped skills; classes: the ten class records (Game+0x15564 +
// 388 * i), class_index Game+0x1648c; open: FrameScreens.menus[0] (FoldoutMenu+0x8). Game::SetSkill also
// writes preview (healing_value Game+0xbe08, shield_value 0xbe10), selection (base_damage 0xbdc0, read
// bonus_base_damage 0xbdc4), player (ui_health_ceiling_5998, ui_skull_59c8, read skill_cooldown_be64) and
// stat_counts (Game+0xbde8 / bdf0 / bdf8 / be00, NewGameExtra.base_bde8); perk 3 is read from match->perks.
// The current class's race (the shop's scroll chance) is read from selection->character, the view every unit
// reads (Shapeshift changes it there), not from classes[class_index].
struct MenuSources {
    ResourceState* resources;
    SkillSlots* slots;
    const ClassProfile* classes;
    std::int32_t class_index;
    std::uint8_t* open;
    ResourcePreviewState* preview;
    SelectionState* selection;
    PlayerStats* player;
    std::int32_t* stat_counts;
    // The shop: equipped the five equipped items (Game+0xbe88..0xbe98: types 0..3, then the rest), stats what
    // the item functions and Game::UpdateStats read and write (with stats_hooks), skills for Skill::CanActivate,
    // and probe the 40 words at Game+0xbf90 that the scroll draw reads (see FoldoutMenu::Initialise(1)).
    ItemRecord* equipped;
    StatsTargets* stats;
    const StatsHooks* stats_hooks;
    const SkillState* skills;
    const std::uint32_t* probe;
};
// Sound: Game::QueueSound(a). PositionSkill: Interface::PositionSkill(a). UpdateSkills: Interface::UpdateSkills.
// HealthBar: Interface::UpdateHealthBar(value a). SkullValue: Interface::UpdateSkullValue. Highlight:
// FoldoutMenu::HighlightButton(button a, selection b, on c). Confirm: the confirm button's colour (a = 1 pressed,
// 0 normal). TooltipHide: Tooltip::Hide. ScrollTooltip: Tooltip::ShowScroll(type a). ActivateScroll: Skill::Activate of
// the scroll's Skill object (type a, not equipped: wire to dr_skill_activate with slot -1). Achievement: a, b float bits.
enum class MenuEventKind : std::int32_t { Sound=1, PositionSkill, UpdateSkills, HealthBar, SkullValue, Highlight, Confirm, TooltipHide,
    ScrollTooltip, ActivateScroll, Achievement };
struct MenuEvent { MenuEventKind kind; std::int32_t a,b,c; };
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
// The other 20 skills of a class type 0..9 (CharacterClass::Initialise's list at Class+0x3c): the types 0..39 that are
// not its base skills, in order.
void dr_class_other_skills(std::int32_t type,std::int32_t out[20]);
// What the class screen lets the current class take (ClassScreen::UpdatePerks 0x10a974 / UpdateAbilities 0x109b90,
// T040-M4), nothing being dragged: perk / flaw i (0..9) when the perk is unlocked in the game (dr_perk_unlocked), the
// class is not class 0, its slot 1 is open (level 3 or more) and it does not hold that perk (flaw) yet; its other skill
// i (dr_class_other_skills) when the skill is unlocked (dr_skill_unlocked), the class is not class 0, may replace
// skills at its level and does not use that skill yet.
void dr_class_choices(const dungeonraid::ClassProfile* classes,std::size_t current,std::uint8_t perks[10],std::uint8_t flaws[10],
                      std::uint8_t skills[20]);
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
// Original Game::SetSkill 0x13e68 with option (a Skill object of the menu). A skill (type < 40): an equipped skill
// of that type is exchanged with option (Interface::PositionSkill); otherwise, with fewer than 4 equipped, the
// object of the next slot is exchanged with option and skill_count grows (PositionSkill), its cooldown maximum
// one less with the cooldown item (Game+0xbe64) and one less again as the fourth skill with perk 3, current
// capped; then UpdateSkills. With 4 equipped and no match, UpdateSkills only. A stat option (40..47): healing and
// shield grow, the four bonus chances grow up to 100, health maximum and health grow (not in record mode 1;
// health bar refreshed when the ceiling or health changed), base damage grows (skull value refreshed), and stat
// 0..3 counts one more at Game+0xbde8 / bdf0 / bdf8 / be00. The returned object (stored back in the menu) is
// what option now holds.
void dr_set_skill(const dungeonraid::MenuSources*,dungeonraid::SkillRecord* option,const dungeonraid::MenuHooks*);
// Original FoldoutMenu::ProcessInput 0x239c8 at touch phase (Game+0x10) with button the menu button under the
// touch (14..17 the options, 7 the confirm button, -1 none; the layout is the renderer's). A new touch (phase 1
// after phase 0): on the enabled confirm button presses it (sound 0); else on an option (17 not in the shop) it
// deselects a chosen one, chooses it first, or -- level-up menu -- second while there is none (shop / upgrade:
// replaces the first); sounds 1 shop, 9 level-up (not when both are chosen and another is touched), 8 upgrade.
// The confirm button is enabled with both choices (level-up) or the first. A release (phase 2) of a pressed
// confirm button still on it starts the closing animation (sound 11 / 12 / 13 by type), elsewhere un-presses
// it. Tooltip::Hide unless phase 1; the phase is kept.
void dr_menu_input(dungeonraid::MenuState*,std::int32_t phase,std::int32_t button,const dungeonraid::MenuHooks*);
// Original FoldoutMenu::Initialise 0x24a54, the shop (type 1): three items, each Item::Initialise(Item*) from the
// equipped item of a type RandI(stream 2) draws among those left; with chance 0.25 (0.5 for race 3) against
// Rand(stream 2) a scroll in option RandI(0, 2, stream 2): Rand(stream 2) = r, candidates every type but 33 (and 24
// in record mode 1) that is unlocked, can activate and -- when r >= 0.1 -- whose probe word is 0; RandI(stream 2)
// picks one, Skill::Initialise(type, none).
void dr_menu_open_shop(dungeonraid::MenuState*,const dungeonraid::MenuSources*,const dungeonraid::MenuHooks*);
// Original FoldoutMenu::Initialise 0x24a54, the upgrade menu (type 2): four of the five equipped items, each the
// item of a type RandI(stream 4) draws among those left, with ItemUpgrade::Initialise 0x2da74: the stat
// GetRandomStat(item type, allow 5 when its stat 5 is 0) and the amount GetStatUpgrade(stat).
void dr_menu_open_upgrade(dungeonraid::MenuState*,const dungeonraid::MenuSources*,const dungeonraid::MenuHooks*);
// Original FoldoutMenu::Process 0x23c44 (Interface::Process while the menu is open): a negative timer
// (open) takes input; otherwise the animation timer grows by dt and at 0.3 s the opening ends (timer -1) or the
// closing ends: the menu closes (timer -1) and the choice applies -- level-up: Game::SetSkill on the first and
// then the second chosen option; shop: Game::SetItem 0x8b08 exchanges the chosen item with the equipped one of
// its type, Game::UpdateStats, and the scroll of that option is activated (achievement 49 for race 3); upgrade:
// Item::AddUpgrade 0x29de0 adds the amount to the item's stat, Game::UpdateStats.
void dr_menu_process(dungeonraid::MenuState*,const dungeonraid::MenuSources*,float dt,std::int32_t phase,std::int32_t button,
    const dungeonraid::MenuHooks*);
}
