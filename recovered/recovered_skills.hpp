#pragma once
#include "recovered_turn.hpp"
#include "recovered_attack_shield.hpp"
#include "recovered_generation.hpp"
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
// PositionSkill: Interface::PositionSkill(a) (the skill button of slot a moves). Flare: Game::AddFlare(type a,
// tile b's resting position, colour c = RGBA bytes) -- wire to dr_add_flare (its game state). Freeze: the
// freeze overlay of tile b shown (Tile::SetFreezeVisibility(true) render part). Menu: Interface::ShowMenu(a).
// Tile appearance (Quad::SetUV / SetColour of Tile::Make*) goes to the GenerationHooks as UV / Colour events.
enum class SkillEventKind : std::int32_t { Sound=1, Achievement, ArrowColour, PositionSkill, Flare, Freeze, Menu };
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
// Board skills (H2). Each ends with the flare timers reset (MatchState shake_progress_bd90 = 0,
// shake_scale_bd94 = 1.0). Tiles are visited column-major except in ConvertTiles (row-major).
// Original Game::Upgrade 0x9694: Interface::ShowMenu(2) (the upgrade menu; FoldoutMenu).
void dr_skill_upgrade(const dungeonraid::SkillHooks*);
// Original Game::FreezeSkulls 0xa470: every skull (type 1) gets a flare (type 1, colour 100,230,255,255) and is
// frozen (Tile::SetFreezeVisibility(true): frozen, freeze overlay shown, burning cleared).
void dr_freeze_skulls(dungeonraid::SkillState*,const dungeonraid::SkillHooks*);
// Original Game::ConvertTiles 0xa7f4: every tile of type from (not a special enemy, not an arrow when from is
// 4) becomes type to (Tile::SetType with the turn and difficulty) with a white flare; gold to skulls also sets
// Game+0x165b8 (TurnFlags.b165b8[0]).
void dr_convert_tiles(dungeonraid::SkillState*,std::int32_t from,std::int32_t to,const dungeonraid::SkillHooks*,const dungeonraid::GenerationHooks*);
// Original Game::CreateManaPotions 0xa548 / CreateExplosivePotions 0xa380: every normal potion gets a flare
// (100,100,255,255 / 255,150,0,255) and becomes a mana potion (Tile::MakeManaPotion) / an explosive potion
// (Tile::MakeExplosivePotion: flag_234, UV).
void dr_create_mana_potions(dungeonraid::SkillState*,const dungeonraid::SkillHooks*,const dungeonraid::GenerationHooks*);
void dr_create_explosive_potions(dungeonraid::SkillState*,const dungeonraid::SkillHooks*,const dungeonraid::GenerationHooks*);
// Original Game::CreateArrows 0xcdac: every normal sword becomes an arrow (Tile::MakeArrow) with a white flare.
void dr_create_arrows(dungeonraid::SkillState*,const dungeonraid::SkillHooks*,const dungeonraid::GenerationHooks*);
// Original Game::CreateMagicSword 0xccc0: RandI(0, normal swords - 1, stream 5) picks one normal sword that
// becomes a magic sword (Tile::MakeMagicSword: magic_sword, colour 150,150,255,255) with a flare (100,100,255,255).
void dr_create_magic_sword(dungeonraid::SkillState*,const dungeonraid::SkillHooks*,const dungeonraid::GenerationHooks*);
// Original Game::RemoveSkill 0x9114 for the skill in slot: the later skills move up one slot (each
// PositionSkill), the removed one goes to the last slot and skill_count drops by one; an unequipped slot
// (outside 0..skill_count-1) changes nothing.
void dr_remove_skill(dungeonraid::SkillState*,std::int32_t slot,const dungeonraid::SkillHooks*);
}
