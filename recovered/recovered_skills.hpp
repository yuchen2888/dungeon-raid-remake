#pragma once
#include "recovered_turn.hpp"
#include "recovered_attack_shield.hpp"
namespace dungeonraid {
// The state player skills read and write. The equipped skills are the Skill objects of Game+0xbf90
// (resources->skill_count of them, Game+0xbfa0); per slot their type (Skill+0x84), level (+0x88) and active
// byte (+0x80) are SkillSlots, their cooldown maximum / current (+0x8c / +0x90) ResourceState.skill_max /
// skill_current.
struct SkillState {
    SkillSlots* slots;
    ResourceState* resources;      // skill_count, cooldowns, guard_164a4
    PathState* path;               // battle.grant_coin_on_attack (Game+0xbfbb); ->match: selection, preview
    GenerationState* generation;   // one_health (+0x14af5), force_coins (+0x14af6)
    TurnFlags* flags;              // next_coin_bfbc, next_be78[], prev_164a7 / next_164a8, arrow_hold_16492
    TurnFinishFlags* finish;       // flag_1554c (copied into the next-turn flags), next_one_health / next_force_coins
    RuneState* rune;               // enabled_16491
    AttackAnimation* animation;    // counterattack (Game+0xbfba)
    EndGameState* end;             // revive_second (Game+0x164a5)
};
// The Game functions a skill runs on the board (Skill::Activate calls them; wire each to its recovered
// function; a, b are the TileType arguments of GrabTiles / ConvertTiles).
enum class SkillAction : std::int32_t { FreezeSkulls=1, GrabTiles, ShatterDefence, ConvertTiles, Teleport, CreateExplosivePotions,
    Upgrade, CollectRandomRow, DemoteSpecialEnemy, KillSpecialEnemy, PromoteNormalEnemy, CreateMagicSword, Earthquake,
    ExplodeArmour, CollectRandomBlock, CreateManaPotions, ConvertColumnToSwords, CreateArrows, KillSkullsNextToCoins,
    CollectEdgeTiles, CreateChain, CollectBoard };
// Sound: a=sound. Achievement: a=id, b=float bits. ArrowColour: Arrow::SetColour(a, b, c) on Game+0x3658.
// PositionSkill: Interface::PositionSkill(a) (the skill button of slot a moves).
enum class SkillEventKind : std::int32_t { Sound=1, Achievement, ArrowColour, PositionSkill };
struct SkillEvent { SkillEventKind kind; std::int32_t a,b,c; };
struct SkillHooks {
    void* context;
    void (*event)(void*,const SkillEvent*);
    void (*action)(void*,SkillAction,std::int32_t a,std::int32_t b);
};
}
extern "C" {
// Original Skill::CanActivate(int) 0x2ac74 for a skill type: whether the board has what the skill acts on
// (skulls, skulls that are not special enemies, special enemies, shields, swords, normal potions or swords,
// armour with skulls); types without a condition and types above 36 are always true.
bool dr_skill_can_activate(const dungeonraid::SkillState*,std::int32_t type);
// Original Skill::Activate 0x2ad40 for a skill of the given type: its sound and board action, or a
// this-turn flag set to 1 with its next-turn flag copied from Game+0x1554c (and the skill's active byte set
// where the original sets it); skill 33 (CollectBoard) gives achievement 64 with more than 19 plain skulls
// and removes itself (dr_remove_skill on slot, -1 when it is not equipped). active: the skill's active byte.
void dr_skill_activate(dungeonraid::SkillState*,std::int32_t type,std::int32_t slot,std::uint8_t* active,const dungeonraid::SkillHooks*);
// Original Game::RemoveSkill 0x9114 for the skill in slot: the later skills move up one slot (each
// PositionSkill), the removed one goes to the last slot and skill_count drops by one; an unequipped slot
// (outside 0..skill_count-1) changes nothing.
void dr_remove_skill(dungeonraid::SkillState*,std::int32_t slot,const dungeonraid::SkillHooks*);
}
