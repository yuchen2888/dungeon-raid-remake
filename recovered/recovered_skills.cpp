#include "recovered_skills.hpp"
#include <utility>
using namespace dungeonraid;
namespace {
const SelectionState& board(const SkillState* s) {return s->path->match->stroke->selection;}
std::int32_t tile_count(const SkillState* s,std::int32_t type) {   // Game::GetTileCount
    std::int32_t n=0;for(const auto& t:board(s).tiles)if(t.rule.type==type)++n;return n;
}
std::int32_t special_enemies(const SkillState* s) {               // Game::GetSpecialEnemyCount
    std::int32_t n=0;for(const auto& t:board(s).tiles)if(t.rule.type==1 && t.rule.enemy_type)++n;return n;
}
std::int32_t normal_potions(const SkillState* s) {                // Game::GetNormalPotionCount (Tile::IsNormalPotion)
    std::int32_t n=0;const auto& potions=s->path->match->preview->potions;
    for(std::size_t i=0;i<36;++i) {
        const auto& f=potions[i];
        if(board(s).tiles[i].rule.type==0 && !f.flag_234 && !f.flag_232 && !f.flag_233)++n;
    }
    return n;
}
std::int32_t normal_swords(const SkillState* s) {                 // Game::GetNormalSwordCount
    std::int32_t n=0;for(const auto& t:board(s).tiles)if(t.rule.type==4 && !t.magic_sword && !t.rule.flag_231)++n;return n;
}
void emit(const SkillHooks* h,SkillEventKind kind,std::int32_t a=0,std::int32_t b=0,std::int32_t c=0) {
    const SkillEvent e{kind,a,b,c};h->event(h->context,&e);
}
void act(const SkillHooks* h,SkillAction action,std::int32_t a=0,std::int32_t b=0) {h->action(h->context,action,a,b);}
// The flag skills: the flag for this turn is set, its next-turn flag is copied from Game+0x1554c.
void flag(SkillState* s,std::uint8_t& now,std::uint8_t& next,std::uint8_t* active) {
    now=1;next=s->finish->flag_1554c;*active=1;
}
}
extern "C" bool dr_skill_can_activate(const SkillState* s,std::int32_t type) {
    switch(type) {
    case 3:return tile_count(s,3)>0;
    case 6:case 13:return tile_count(s,4)>0;
    case 20:case 21:return special_enemies(s)>0;
    case 5:case 14:case 23:return tile_count(s,1)-special_enemies(s)>0;
    case 27:return tile_count(s,1)!=0 && s->path->match->preview->armour_current>0;
    case 2:case 8:case 9:case 29:return normal_potions(s)>0;
    case 25:case 31:return normal_swords(s)>0;
    case 0:case 1:case 4:case 34:return tile_count(s,1)>0;
    case 36:return tile_count(s,1)-special_enemies(s)>0 && tile_count(s,2)>0;
    case 12:case 15:case 32:return tile_count(s,2)>0;
    default:return true;
    }
}
extern "C" void dr_skill_activate(SkillState* s,std::int32_t type,std::int32_t slot,std::uint8_t* active,const SkillHooks* h) {
    auto& sel=s->path->match->stroke->selection;auto& p=*s->path->match->preview;auto& f=*s->flags;auto& fin=*s->finish;
    auto sound=[h](std::int32_t v) {emit(h,SkillEventKind::Sound,v);};
    switch(type) {
    case 0:sound(0x13);flag(s,s->path->battle.grant_coin_on_attack,f.next_coin_bfbc,active);break;
    case 1:sound(0x14);act(h,SkillAction::FreezeSkulls);break;
    case 2:sound(0x13);act(h,SkillAction::GrabTiles,0,0);break;
    case 3:sound(0x13);act(h,SkillAction::GrabTiles,3,3);break;
    case 4:sound(0x13);s->animation->counterattack=1;*active=1;break;
    case 5:sound(0x16);act(h,SkillAction::ShatterDefence);break;
    case 6:sound(0x13);act(h,SkillAction::ConvertTiles,4,2);break;
    case 7:sound(0x15);act(h,SkillAction::Teleport);break;
    case 8:sound(0x18);act(h,SkillAction::CreateExplosivePotions);break;
    case 9:sound(0x13);act(h,SkillAction::GrabTiles,0,1);break;
    case 10:sound(0x13);act(h,SkillAction::Upgrade);break;
    case 11:sound(0x19);act(h,SkillAction::CollectRandomRow);break;
    case 12:sound(0x13);act(h,SkillAction::GrabTiles,2,2);break;
    case 13:sound(0x13);act(h,SkillAction::ConvertTiles,4,3);break;
    case 14:sound(0x13);act(h,SkillAction::ConvertTiles,1,4);break;
    case 15:sound(0x13);act(h,SkillAction::ConvertTiles,2,4);break;
    case 16:sound(0x17);flag(s,sel.double_damage,f.next_be78[0],active);break;   // Game+0xbe74 / 0xbe78
    case 17:sound(0x17);flag(s,p.double_gold,f.next_be78[3],active);break;       // Game+0xbe77 / 0xbe7b
    case 18:sound(0x17);flag(s,p.double_healing,f.next_be78[2],active);break;    // Game+0xbe76 / 0xbe7a
    case 19:sound(0x17);flag(s,p.double_upgrade,f.next_be78[1],active);break;    // Game+0xbe75 / 0xbe79
    case 20:sound(0x13);act(h,SkillAction::DemoteSpecialEnemy);break;
    case 21:sound(0x1a);act(h,SkillAction::KillSpecialEnemy);break;
    case 22:sound(0x1b);flag(s,s->generation->one_health,fin.next_one_health_14af7,active);break;      // +0x14af5 / 0x14af7
    case 23:sound(0xe);act(h,SkillAction::PromoteNormalEnemy);break;
    case 24:sound(0x22);flag(s,s->generation->force_coins,fin.next_force_coins_14af8,active);break;    // +0x14af6 / 0x14af8
    case 25:sound(0x13);act(h,SkillAction::CreateMagicSword);break;
    case 26:sound(0x25);act(h,SkillAction::Earthquake);break;
    case 27:sound(0x1c);act(h,SkillAction::ExplodeArmour);break;
    case 28:sound(0x1c);act(h,SkillAction::CollectRandomBlock);break;
    case 29:sound(0x18);act(h,SkillAction::CreateManaPotions);break;
    case 30:sound(0x1b);act(h,SkillAction::ConvertColumnToSwords);break;
    case 31:sound(0x1a);act(h,SkillAction::CreateArrows);break;
    case 32:sound(0xe);act(h,SkillAction::ConvertTiles,2,1);break;
    case 33:
        if(tile_count(s,1)-special_enemies(s)>19)emit(h,SkillEventKind::Achievement,0x40,0x42c80000);
        sound(0x13);act(h,SkillAction::CollectBoard);dr_remove_skill(s,slot,h);break;
    case 34:sound(0xe);flag(s,f.prev_164a7,f.next_164a8,active);break;
    case 35:   // the rune: enabled, arrow colour (0x50, 0x82, 0xff), arrow hold from Game+0x1554c
        sound(0x13);s->rune->enabled_16491=1;emit(h,SkillEventKind::ArrowColour,0x50,0x82,0xff);
        f.arrow_hold_16492=fin.flag_1554c;*active=1;break;
    case 36:sound(2);sound(2);sound(2);act(h,SkillAction::KillSkullsNextToCoins);break;
    case 37:sound(0x13);flag(s,s->resources->guard_164a4,s->end->revive_second,active);break;       // +0x164a4 / 0x164a5
    case 38:sound(0x1b);act(h,SkillAction::CollectEdgeTiles);break;
    case 39:sound(0x17);act(h,SkillAction::CreateChain);break;
    default:break;
    }
}
extern "C" void dr_remove_skill(SkillState* s,std::int32_t slot,const SkillHooks* h) {
    auto& r=*s->resources;auto& k=*s->slots;
    if(slot<0 || slot>=r.skill_count)return;
    for(std::int32_t i=slot;i<r.skill_count-1;++i) {   // the skill objects move up; the removed one goes last
        std::swap(k.id[i],k.id[i+1]);std::swap(k.level[i],k.level[i+1]);std::swap(k.active[i],k.active[i+1]);
        std::swap(r.skill_max[i],r.skill_max[i+1]);std::swap(r.skill_current[i],r.skill_current[i+1]);
        emit(h,SkillEventKind::PositionSkill,i);
    }
    --r.skill_count;
}
