#pragma once
#include "recovered_stats.hpp"
namespace dungeonraid {
// An Item object's game fields: type (Item+0x80: 0..4), icon (+0x84), name prefix level and index (+0x88 /
// +0x8c, -1 none), name index (+0x90) and its stats (+0x94, UpgradeType 0..19). The icon and the name indices
// choose the item's picture and name (the renderer's tables); they come from random stream 2.
struct ItemRecord {
    std::int32_t type, icon, prefix_level, prefix, name;
    ItemStats stats;
};
}
extern "C" {
// Original ItemUpgrade::IsUpgradeAllowed 0x2d25c: leech (2) while Game+0xbe60 <= 24; armour break chance (4)
// while Game+0xbdcc <= 94; the XP / gold / upgrade bonuses (6 / 7 / 13) below 2.0; health bonus (10) unless record
// mode 1; armour loss chance (14) while Game+0xbdc8 >= 11; any other type.
bool dr_upgrade_allowed(const dungeonraid::StatsTargets*,std::int32_t type);
// Original ItemUpgrade::GetRandomStat 0x2d314: a random stat of an item type -- 0: 0 1 2 3 4 6 8 9; 1: 6 7 10 11 12
// 13 17; 2: 10 11 12 14 15 17 18 19; 3: 0 1 11 12 13 15 16; 4: 5 8 9 10 17 18 19 -- without 5 unless allow5,
// without 15 in record mode 0 or when RandI(0, Game+0xbe6c, stream 4) is not 0, without the types IsUpgradeAllowed
// refuses; RandI(0, n - 1, stream 4) picks one in ascending order.
std::int32_t dr_random_item_stat(const dungeonraid::StatsTargets*,std::int32_t item_type,bool allow5);
// Original Item::Initialise(ItemType) 0x264a8: type and icon RandI(range, stream 2): 0: 0..79, 1: 80..159, 2:
// 240..319, 3: 160..239, 4: 320..399.
void dr_item_initialise(dungeonraid::RandomState*,dungeonraid::ItemRecord*,std::int32_t type);
// Original Item::GenerateName 0x263a0: without an existing item no prefix (-1); else a prefix level and index from
// RandI(stream 2) above the existing one (148 prefixes), then the name index RandI(0, n - 1, stream 2) of the
// icon's name group (13 groups by icon range).
void dr_item_generate_name(dungeonraid::RandomState*,dungeonraid::ItemRecord*,const dungeonraid::ItemRecord* existing);
// Original Item::GenerateStats 0x29e04: stats cleared; a new item (no existing) gets its type's base stat (0:
// stat 0 = 2; 1 and 3: stat 11 = 1; 2: stat 11 = 1 with flaw 6, else 2; 4: stat 10 = 10 unless record mode 1).
// From an existing item of the same type, the main stat grows by one (type 4: health bonus by half an upgrade)
// and each other positive stat may drop (or for type 1 rise once) by Rand(stream 2) chances, see
// docs/T040_MENU.md.
void dr_item_generate_stats(const dungeonraid::StatsTargets*,dungeonraid::ItemRecord*,const dungeonraid::ItemRecord* existing);
// Item(Game*, ItemType) 0x2a5ac / Item::Initialise(Item*) 0x2a584: Initialise(type), GenerateName, GenerateStats
// (MakeStats, the item's text, is the renderer's).
void dr_item_make(const dungeonraid::StatsTargets*,dungeonraid::ItemRecord*,std::int32_t type,const dungeonraid::ItemRecord* existing);
}
