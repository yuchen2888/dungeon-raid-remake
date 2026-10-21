#pragma once
#include "recovered_turn.hpp"
#include "recovered_attack_shield.hpp"
#include "recovered_generation.hpp"
#include "recovered_match.hpp"
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
// Particles: Game::AddParticles(tile b, type a). Text: Tile::UpdateText(a, c, d) on tile b. Label:
// Game::AddSimpleLabel(type a, tile b's resting position, number c, colour d, scale 0.5). EnemyUV:
// Tile::UpdateEnemyUV on tile b. MoveMatchedTiles: Game::MoveMatchedTiles (wire to dr_move_matched_tiles).
// JumpDown: Game::JumpDown(tile b) (wire to dr_jump_down). SwapTiles: Game::SwapTiles(a, b, c, d) (wire to
// dr_swap_tiles). SetSpecialType: Tile::SetSpecialType(tile b, a) (wire to dr_set_special_type). FlameVisibility:
// Tile::SetFlameVisibility(true, damage a, self flame true) on tile b (wire to dr_set_flame_visibility).
// UpdateSkills: Interface::UpdateSkills. ButtonColour: the skill button a's colour (RGBA b). Tooltip: Tooltip::Show
// (skill type a, cooldown max b, current c) at the button of slot d (on every press of an equipped button). TooltipHide: Tooltip::Hide. Tile appearance (Quad::SetUV / SetColour of
// Tile::Make*) and RandI go to the GenerationHooks as UV / Colour / Random events.
enum class SkillEventKind : std::int32_t { Sound=1, Achievement, ArrowColour, PositionSkill, Flare, Freeze, Menu,
    Particles, Text, Label, EnemyUV, MoveMatchedTiles, JumpDown, SwapTiles, SetSpecialType, FlameVisibility, UpdateSkills,
    ButtonColour, Tooltip, TooltipHide };
// The skill buttons of Interface::ProcessInput 0x209e4 (Interface+0xbd0: the pressed slot, -1 none;
// Interface+0x1034: the touch phase of the previous call).
struct SkillInput { std::int32_t pressed, previous_phase; };
struct SkillEvent { SkillEventKind kind; std::int32_t a,b,c,d; };
struct SkillHooks {
    void* context;
    void (*event)(void*,const SkillEvent*);
    void (*action)(void*,SkillAction,std::int32_t a,std::int32_t b);
    const MatchHooks* match;   // Game::MatchTile (dr_match_tile) in GrabTiles / KillSpecialEnemy
    const PathHooks* path;     // Game::AttackSkull (dr_path_attack_skull) in ExplodeArmour
};
}
extern "C" {
// Original Skill::CanActivate(int) 0x2ac74 for a skill type: whether the board has what the skill acts on
// (skulls, skulls that are not special enemies, special enemies, shields, swords, normal potions or swords,
// armour with skulls); types without a condition and types above 36 are always true.
bool dr_skill_can_activate(const dungeonraid::SkillState*,std::int32_t type);
// Original Interface::GetSpecialTarget(Token*) 0x20358: the skill slot a special reward token (kind 1, a mana potion
// tile) recharges. The slots 0..skill_count-1 whose skill is not type 29 and whose cooldown is not full (current !=
// max) are collected in order (a std::set<int>); none: -1; else the RandI(0, n-1, stream 5)-th of them. Other token
// kinds: 0. (skill_count above 4 does not occur; the native loop stops at the four slots.)
std::int32_t dr_special_target(const dungeonraid::SkillState*,std::int32_t token_kind);
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
// Original Game::DemoteSpecialEnemy 0xa6f4: RandI(0, special enemies - 1, stream 5) picks one: enemy type 0
// (UpdateEnemyUV), enemy state 0, flare (0,255,0,255).
void dr_demote_special_enemy(dungeonraid::SkillState*,const dungeonraid::SkillHooks*,const dungeonraid::GenerationHooks*);
// Original Game::PromoteNormalEnemy 0xb648: RandI(0, plain skulls - 1, stream 5) picks one, promoted with
// Tile::Promote(turn, difficulty, true) while promotion_enabled (+0x14af4) is 0 (then 1); flare
// (240,150,10,255); a promoted enemy 31 jumps down (Game::JumpDown).
void dr_promote_normal_enemy(dungeonraid::SkillState*,const dungeonraid::SkillHooks*,const dungeonraid::GenerationHooks*);
// Original Game::KillSpecialEnemy 0x11498: RandI(0, special enemies - 1, stream 5) picks one; the five
// matched counters are cleared; MatchTile(pick, 7) and a white flare; MoveMatchedTiles; without Game+0x1554c
// every tile's attack flag is cleared.
void dr_kill_special_enemy(dungeonraid::SkillState*,const dungeonraid::SkillHooks*,const dungeonraid::GenerationHooks*);
// Original Game::GrabTiles 0x12060: the five matched counters and Game+0x13ec4 cleared; every tile of the type
// (a normal potion for type 0) is MatchTile'd with the reward; MoveMatchedTiles; without Game+0x1554c every
// tile's attack flag is cleared (no flare timer reset).
void dr_grab_tiles(dungeonraid::SkillState*,std::int32_t type,std::int32_t reward,const dungeonraid::SkillHooks*);
// Original Game::ShatterDefence 0xcf4c: every plain skull with defence loses it (particles 1, UpdateText(0,1,0))
// and with attack above 1 drops to attack 1 (particles 3, UpdateText(1,0,0)). No flare timer reset.
void dr_shatter_defence(dungeonraid::SkillState*,const dungeonraid::SkillHooks*);
// Original Game::ExplodeArmour 0x115dc: the five matched counters cleared; every skull gets a flare
// (240,150,10,255), a label 2 with twice the armour (colour 11) and AttackSkull(tile, twice the armour, no effects);
// MoveMatchedTiles; without Game+0x1554c every tile's attack flag is cleared.
void dr_explode_armour(dungeonraid::SkillState*,const dungeonraid::SkillHooks*);
// H4. Original Game::CheckShockAwe 0xbdf4: Game+0x165b9..0x165bc (TurnFlags.b165b8[1..4], set by the four
// collect skills) all set: achievement 63 (100.0).
void dr_check_shock_awe(const dungeonraid::SkillState*,const dungeonraid::SkillHooks*);
// Original Game::CollectBoard 0x11c3c: b165b8[4] set, CheckShockAwe, inhibit_force_coins (+0x15563) set; the five
// matched counters and Game+0x13ec4 cleared; every tile but special enemies MatchTile(5) with a flare
// (240,150,10,255); MoveMatchedTiles; attack flags without Game+0x1554c; flare timers; inhibit_force_coins cleared.
void dr_collect_board(dungeonraid::SkillState*,const dungeonraid::SkillHooks*);
// Original Game::CollectRandomRow 0x11ea8: b165b8[1] set, CheckShockAwe; after ConvertColumnToSwords
// (b15561) both b15561 and b15562 are cleared and CollectBoard runs instead. Otherwise b15562 set, a row
// RandI(0,5,5), counters cleared; along the row every tile but special enemies is MatchTile'd (5; 7 for a potion
// with flag_233) with a yellow flare (255,255,0,255); MoveMatchedTiles, attack flags, flare timers; six skulls
// in the row: achievement 60.
void dr_collect_random_row(dungeonraid::SkillState*,const dungeonraid::SkillHooks*,const dungeonraid::GenerationHooks*);
// Original Game::CollectRandomBlock 0x11748: b165b8[2] set, CheckShockAwe; centre y = RandI(1,4,5), x =
// RandI(1,4,5); counters cleared; the 3x3 block (column-major) as in CollectRandomRow with flares (240,150,10,255);
// MoveMatchedTiles, attack flags, flare timers.
void dr_collect_random_block(dungeonraid::SkillState*,const dungeonraid::SkillHooks*,const dungeonraid::GenerationHooks*);
// Original Game::CollectEdgeTiles 0x11ac4: b165b8[3] set, CheckShockAwe; counters cleared; every edge tile but
// special enemies MatchTile(5) with a yellow flare; MoveMatchedTiles, attack flags, flare timers.
void dr_collect_edge_tiles(dungeonraid::SkillState*,const dungeonraid::SkillHooks*);
// Original Game::ConvertColumnToSwords 0x11da0: after CollectRandomRow (b15562) both flags are cleared and
// CollectBoard runs instead. Otherwise b15561 set, a column RandI(0,5,5): every tile but special enemies becomes
// a sword (SetType 4) with a flare (240,150,10,255); flare timers.
void dr_convert_column_to_swords(dungeonraid::SkillState*,const dungeonraid::SkillHooks*,const dungeonraid::GenerationHooks*);
// Original Game::Teleport 0x1133c: counters cleared; every tile (column-major) matched with a flare
// (0,100,255,255); special enemies on the board: achievement 65 (1.0); MoveMatchedTiles with filter_enabled set
// around it; every tile's attack flag cleared; flare timers.
void dr_teleport(dungeonraid::SkillState*,const dungeonraid::SkillHooks*);
// Original Game::Earthquake 0xb780: column-major, every tile SwapTiles(x, y, RandI(0,5,5), RandI(0,5,5)) and a
// flare (115,60,20,255) at (x, y); flare timers.
void dr_earthquake(dungeonraid::SkillState*,const dungeonraid::SkillHooks*,const dungeonraid::GenerationHooks*);
// Original Game::KillSkullsNextToCoins 0x11908: counters and Game+0x13ec4 cleared; column-major, every plain skull
// with gold among its eight neighbours is MatchTile'd (5) with a flare (240,150,10,255); MoveMatchedTiles, attack
// flags, flare timers.
void dr_kill_skulls_next_to_coins(dungeonraid::SkillState*,const dungeonraid::SkillHooks*);
// Original Game::CreateChain 0xa618: up to ten tries of (x, y) = (RandI(0,5,5), RandI(0,5,5)) until the tile is
// not a special enemy; it becomes special 0 (Tile::SetSpecialType) with a flare (100,100,255,255); flare timers.
void dr_create_chain(dungeonraid::SkillState*,const dungeonraid::SkillHooks*,const dungeonraid::GenerationHooks*);
// H5. Original Game::FireBreath 0xa274 (after any skill, for race 8): RandI(0, plain skulls - 1, 5) picks one plain
// skull (column-major): flare (240,150,10,255) and Tile::SetFlameVisibility(true, base damage, self flame); flare timers.
void dr_fire_breath(dungeonraid::SkillState*,const dungeonraid::SkillHooks*,const dungeonraid::GenerationHooks*);
// A SkillHooks action run by its recovered function (the dispatch of Skill::Activate's board calls).
void dr_skill_action(dungeonraid::SkillState*,dungeonraid::SkillAction,std::int32_t a,std::int32_t b,const dungeonraid::SkillHooks*,
    const dungeonraid::GenerationHooks*);
// Original Interface::ProcessInput 0x209e4, the skill buttons (run by Interface::Process when input is ready and
// no in-game menu is open). button: the equipped slot whose button is under the touch (-1 none; the layout is
// the renderer's). A new touch (phase 1 after phase 0) on an equipped button shows its tooltip and, when its
// cooldown is full (current == max), sound 0 and the button is pressed. A release or cancel (phase 2 / 3) of a
// pressed button: still on it and Skill::CanActivate, then Skill::Activate, the cooldown restarts (0, or max when
// max < 0), FireBreath for race 8 and UpdateSkills; the press ends and the tooltip hides. The game / stats menu
// buttons are the renderer's.
void dr_skill_input(dungeonraid::SkillState*,dungeonraid::SkillInput*,std::int32_t phase,std::int32_t button,
    const dungeonraid::SkillHooks*,const dungeonraid::GenerationHooks*);
// Original Game::RemoveSkill 0x9114 for the skill in slot: the later skills move up one slot (each
// PositionSkill), the removed one goes to the last slot and skill_count drops by one; an unequipped slot
// (outside 0..skill_count-1) changes nothing.
void dr_remove_skill(dungeonraid::SkillState*,std::int32_t slot,const dungeonraid::SkillHooks*);
}
