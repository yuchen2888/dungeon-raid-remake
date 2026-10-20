#include "recovered_skills.hpp"
#include "recovered_path.hpp"
#include <cstring>
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
void emit(const SkillHooks* h,SkillEventKind kind,std::int32_t a=0,std::int32_t b=0,std::int32_t c=0,std::int32_t d=0) {
    const SkillEvent e{kind,a,b,c,d};h->event(h->context,&e);
}
void act(const SkillHooks* h,SkillAction action,std::int32_t a=0,std::int32_t b=0) {h->action(h->context,action,a,b);}
constexpr std::int32_t rgba(std::uint32_t r,std::uint32_t g,std::uint32_t b,std::uint32_t a) {
    return static_cast<std::int32_t>(r|g<<8|b<<16|a<<24);
}
void flare(const SkillHooks* h,std::int32_t tile,std::int32_t type,std::int32_t colour) {emit(h,SkillEventKind::Flare,type,tile,colour);}
void reset_flare_timers(SkillState* s) {auto& m=*s->path->match;m.shake_progress_bd90=0;m.shake_scale_bd94=0x3f800000;}
SelectionState& board(SkillState* s) {return s->path->match->stroke->selection;}
bool normal_potion(const SkillState* s,int i) {
    const auto& f=s->path->match->preview->potions[i];
    return board(s).tiles[i].rule.type==0 && !f.flag_234 && !f.flag_232 && !f.flag_233;
}
bool normal_sword(const SelectionTile& t) {return t.rule.type==4 && !t.magic_sword && !t.rule.flag_231;}
void tile_event(const GenerationHooks* h,GenerationEventKind kind,int tile,std::int32_t a,std::int32_t b=0,std::int32_t c=0,std::int32_t d=0) {
    if(h && h->event) {const GenerationEvent e{kind,tile,a,b,c,d};h->event(h->context,&e);}
}
std::int32_t float_bits(float f) {std::int32_t b;std::memcpy(&b,&f,4);return b;}
constexpr int column_major(int k) {return (k%6)*6+k/6;}   // k-th tile visited: x = k / 6, y = k % 6
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
extern "C" void dr_skill_upgrade(const SkillHooks* h) {emit(h,SkillEventKind::Menu,2);}
extern "C" void dr_freeze_skulls(SkillState* s,const SkillHooks* h) {
    for(int k=0;k<36;++k) {
        const int i=column_major(k);auto& t=board(s).tiles[i];
        if(t.rule.type!=1)continue;
        flare(h,i,1,rgba(100,230,255,255));
        emit(h,SkillEventKind::Freeze,0,i);   // Tile::SetFreezeVisibility(true)
        t.rule.flag_255=1;s->path->combat[i].overlay=1;t.flaming=0;
    }
    reset_flare_timers(s);
}
extern "C" void dr_convert_tiles(SkillState* s,std::int32_t from,std::int32_t to,const SkillHooks* h,const GenerationHooks* gh) {
    for(int i=0;i<36;++i) {   // row-major
        const auto& rule=board(s).tiles[i].rule;
        if(from==1 && rule.enemy_type)continue;
        if(rule.type!=from)continue;
        if(from==4 && rule.flag_231)continue;
        dr_set_tile_type(s->generation,static_cast<std::uint32_t>(i),to,s->path->turn,s->path->match->spawn_enabled_14ae0,gh);
        flare(h,i,1,rgba(255,255,255,255));
    }
    reset_flare_timers(s);
    if(to==1 && from==2)s->flags->b165b8[0]=1;
}
extern "C" void dr_create_mana_potions(SkillState* s,const SkillHooks* h,const GenerationHooks* gh) {
    for(int k=0;k<36;++k) {
        const int i=column_major(k);if(!normal_potion(s,i))continue;
        flare(h,i,1,rgba(100,100,255,255));dr_make_mana_potion(s->generation,static_cast<std::uint32_t>(i),gh);
    }
    reset_flare_timers(s);
}
extern "C" void dr_create_explosive_potions(SkillState* s,const SkillHooks* h,const GenerationHooks* gh) {
    for(int k=0;k<36;++k) {
        const int i=column_major(k);if(!normal_potion(s,i))continue;
        flare(h,i,1,rgba(255,150,0,255));
        // Tile::MakeExplosivePotion: UV (variant * 0.0517578125, type * 0.0517578125 + 0.6044921875), flag_234
        const float u=static_cast<float>(s->generation->tiles[i].variant)*.0517578125f;
        const float v=static_cast<float>(board(s).tiles[i].rule.type)*.0517578125f+.6044921875f;
        tile_event(gh,GenerationEventKind::UV,i,float_bits(u),float_bits(v),float_bits(.0517578125f),float_bits(.0517578125f));
        s->path->match->preview->potions[i].flag_234=1;
    }
    reset_flare_timers(s);
}
extern "C" void dr_create_arrows(SkillState* s,const SkillHooks* h,const GenerationHooks* gh) {
    for(int k=0;k<36;++k) {
        const int i=column_major(k);if(!normal_sword(board(s).tiles[i]))continue;
        dr_make_arrow(s->generation,static_cast<std::uint32_t>(i),gh);flare(h,i,1,rgba(255,255,255,255));
    }
    reset_flare_timers(s);
}
extern "C" void dr_create_magic_sword(SkillState* s,const SkillHooks* h,const GenerationHooks* gh) {
    std::int32_t n=0;for(const auto& t:board(s).tiles)n+=normal_sword(t);
    std::int32_t pick=dr_random_int(&s->path->match->random,0,n-1,5);
    tile_event(gh,GenerationEventKind::Random,-1,0,n-1,5,pick);   // RandI as the generation unit reports it
    for(int k=0;k<36 && pick>=0;++k) {
        const int i=column_major(k);auto& t=board(s).tiles[i];
        if(!normal_sword(t))continue;
        if(pick) {--pick;continue;}
        tile_event(gh,GenerationEventKind::Colour,i,rgba(150,150,255,255));t.magic_sword=1;   // Tile::MakeMagicSword
        flare(h,i,1,rgba(100,100,255,255));pick=-1;
    }
    reset_flare_timers(s);
}
namespace {
std::int32_t pick_random(SkillState* s,std::int32_t n,const GenerationHooks* gh) {   // RandI(0, n - 1, stream 5)
    const std::int32_t v=dr_random_int(&s->path->match->random,0,n-1,5);tile_event(gh,GenerationEventKind::Random,-1,0,n-1,5,v);return v;
}
bool special(const RuleTile& r) {return r.type==1 && r.enemy_type;}
bool plain_skull(const RuleTile& r) {return r.type==1 && !r.enemy_type;}
void clear_matched_counts(SkillState* s) {for(int i=0;i<5;++i)s->path->match->matched_counts[i]=0;}
void after_matches(SkillState* s,const SkillHooks* h) {   // MoveMatchedTiles, then attack flags unless Game+0x1554c
    emit(h,SkillEventKind::MoveMatchedTiles);
    if(!s->finish->flag_1554c)for(auto& c:s->path->combat)c.attack_flag=0;
}
}
extern "C" void dr_demote_special_enemy(SkillState* s,const SkillHooks* h,const GenerationHooks* gh) {
    std::int32_t n=0;for(const auto& t:board(s).tiles)n+=special(t.rule);
    std::int32_t pick=pick_random(s,n,gh);
    for(int k=0;k<36 && pick>=0;++k) {
        const int i=column_major(k);auto& rule=board(s).tiles[i].rule;
        if(!special(rule))continue;
        if(pick) {--pick;continue;}
        rule.enemy_type=0;emit(h,SkillEventKind::EnemyUV,0,i);rule.enemy_state=0;
        flare(h,i,1,rgba(0,255,0,255));pick=-1;
    }
    reset_flare_timers(s);
}
extern "C" void dr_promote_normal_enemy(SkillState* s,const SkillHooks* h,const GenerationHooks* gh) {
    std::int32_t n=0;for(const auto& t:board(s).tiles)n+=plain_skull(t.rule);
    std::int32_t pick=pick_random(s,n,gh);
    for(int k=0;k<36 && pick>=0;++k) {
        const int i=column_major(k);const auto& rule=board(s).tiles[i].rule;
        if(!plain_skull(rule))continue;
        if(pick) {--pick;continue;}
        auto& g=*s->generation;g.promotion_enabled=0;
        dr_promote_tile(&g,static_cast<std::uint32_t>(i),s->path->turn,s->path->match->spawn_enabled_14ae0,true,gh);
        g.promotion_enabled=1;flare(h,i,1,rgba(240,150,10,255));
        if(board(s).tiles[i].rule.enemy_type==31)emit(h,SkillEventKind::JumpDown,0,i);
        pick=-1;
    }
    reset_flare_timers(s);
}
extern "C" void dr_kill_special_enemy(SkillState* s,const SkillHooks* h,const GenerationHooks* gh) {
    std::int32_t n=0;for(const auto& t:board(s).tiles)n+=special(t.rule);
    std::int32_t pick=pick_random(s,n,gh);clear_matched_counts(s);
    for(int k=0;k<36 && pick>=0;++k) {
        const int i=column_major(k);
        if(!special(board(s).tiles[i].rule))continue;
        if(pick) {--pick;continue;}
        dr_match_tile(s->path->match,static_cast<std::uint32_t>(i),7,h->match);flare(h,i,1,rgba(255,255,255,255));pick=-1;
    }
    after_matches(s,h);reset_flare_timers(s);
}
extern "C" void dr_grab_tiles(SkillState* s,std::int32_t type,std::int32_t reward,const SkillHooks* h) {
    clear_matched_counts(s);s->path->match->sound_13ec4=0;
    for(int k=0;k<36;++k) {
        const int i=column_major(k);
        if(board(s).tiles[i].rule.type!=type || (type==0 && !normal_potion(s,i)))continue;
        dr_match_tile(s->path->match,static_cast<std::uint32_t>(i),reward,h->match);
    }
    after_matches(s,h);
}
extern "C" void dr_shatter_defence(SkillState* s,const SkillHooks* h) {
    for(int k=0;k<36;++k) {
        const int i=column_major(k);if(!plain_skull(board(s).tiles[i].rule))continue;
        auto& c=s->path->combat[i];
        if(c.defence>0) {emit(h,SkillEventKind::Particles,1,i);c.defence=0;emit(h,SkillEventKind::Text,0,i,1,0);}
        if(c.attack>1) {emit(h,SkillEventKind::Particles,3,i);c.attack=1;emit(h,SkillEventKind::Text,1,i,0,0);}
    }
}
extern "C" void dr_explode_armour(SkillState* s,const SkillHooks* h) {
    clear_matched_counts(s);
    for(int k=0;k<36;++k) {
        const int i=column_major(k);if(board(s).tiles[i].rule.type!=1)continue;
        flare(h,i,1,rgba(240,150,10,255));
        auto twice=[s] {return static_cast<std::int32_t>(static_cast<std::uint32_t>(s->path->match->preview->armour_current)<<1);};
        emit(h,SkillEventKind::Label,2,i,twice(),11);   // twice the armour, read again for the attack
        dr_path_attack_skull(s->path,static_cast<std::uint32_t>(i),twice(),false,h->path);
    }
    after_matches(s,h);reset_flare_timers(s);
}
namespace {
int at(int x,int y) {return y*6+x;}
void match(SkillState* s,int i,std::int32_t reward,const SkillHooks* h) {dr_match_tile(s->path->match,static_cast<std::uint32_t>(i),reward,h->match);}
// The collect skills' reward: 5, but 7 for a potion with flag_233.
std::int32_t collect_reward(const SkillState* s,int i) {
    return board(s).tiles[i].rule.type==0 && s->path->match->preview->potions[i].flag_233 ? 7:5;
}
}
extern "C" void dr_check_shock_awe(const SkillState* s,const SkillHooks* h) {
    const auto& b=s->flags->b165b8;
    if(b[1] && b[2] && b[3] && b[4])emit(h,SkillEventKind::Achievement,63,0x42c80000);
}
extern "C" void dr_collect_board(SkillState* s,const SkillHooks* h) {
    s->flags->b165b8[4]=1;dr_check_shock_awe(s,h);s->generation->inhibit_force_coins=1;
    clear_matched_counts(s);s->path->match->sound_13ec4=0;
    for(int k=0;k<36;++k) {
        const int i=column_major(k);if(special(board(s).tiles[i].rule))continue;
        match(s,i,5,h);flare(h,i,1,rgba(240,150,10,255));
    }
    after_matches(s,h);reset_flare_timers(s);s->generation->inhibit_force_coins=0;
}
extern "C" void dr_collect_random_row(SkillState* s,const SkillHooks* h,const GenerationHooks* gh) {
    auto& f=*s->flags;f.b165b8[1]=1;dr_check_shock_awe(s,h);
    if(f.b15561) {f.b15561=0;f.b15562=0;dr_collect_board(s,h);return;}
    f.b15562=1;
    const std::int32_t row=pick_random(s,6,gh);
    clear_matched_counts(s);s->path->match->sound_13ec4=0;
    std::int32_t skulls=0;
    for(int x=0;x<6;++x) {
        const int i=at(x,row);if(special(board(s).tiles[i].rule))continue;
        match(s,i,collect_reward(s,i),h);
        if(board(s).tiles[i].rule.type==1)++skulls;
        flare(h,i,1,rgba(255,255,0,255));
    }
    after_matches(s,h);reset_flare_timers(s);
    if(skulls==6)emit(h,SkillEventKind::Achievement,60,0x42c80000);
}
extern "C" void dr_collect_random_block(SkillState* s,const SkillHooks* h,const GenerationHooks* gh) {
    s->flags->b165b8[2]=1;dr_check_shock_awe(s,h);
    auto between=[&] {   // RandI(1, 4, stream 5)
        const std::int32_t v=dr_random_int(&s->path->match->random,1,4,5);tile_event(gh,GenerationEventKind::Random,-1,1,4,5,v);return v;
    };
    const std::int32_t cy=between(),cx=between();
    clear_matched_counts(s);s->path->match->sound_13ec4=0;
    for(int x=cx-1;x<=cx+1;++x)for(int y=cy-1;y<=cy+1;++y) {
        const int i=at(x,y);if(special(board(s).tiles[i].rule))continue;
        match(s,i,collect_reward(s,i),h);flare(h,i,1,rgba(240,150,10,255));
    }
    after_matches(s,h);reset_flare_timers(s);
}
extern "C" void dr_collect_edge_tiles(SkillState* s,const SkillHooks* h) {
    s->flags->b165b8[3]=1;dr_check_shock_awe(s,h);
    clear_matched_counts(s);s->path->match->sound_13ec4=0;
    for(int x=0;x<6;++x)for(int y=0;y<6;++y) {
        if(x!=0 && x!=5 && y!=0 && y!=5)continue;
        const int i=at(x,y);if(special(board(s).tiles[i].rule))continue;
        match(s,i,5,h);flare(h,i,1,rgba(255,255,0,255));
    }
    after_matches(s,h);reset_flare_timers(s);
}
extern "C" void dr_convert_column_to_swords(SkillState* s,const SkillHooks* h,const GenerationHooks* gh) {
    auto& f=*s->flags;
    if(f.b15562) {f.b15562=0;f.b15561=0;dr_collect_board(s,h);return;}
    f.b15561=1;
    const std::int32_t x=pick_random(s,6,gh);
    for(int y=0;y<6;++y) {
        const int i=at(x,y);if(special(board(s).tiles[i].rule))continue;
        dr_set_tile_type(s->generation,static_cast<std::uint32_t>(i),4,s->path->turn,s->path->match->spawn_enabled_14ae0,gh);
        flare(h,i,1,rgba(240,150,10,255));
    }
    reset_flare_timers(s);
}
extern "C" void dr_teleport(SkillState* s,const SkillHooks* h) {
    clear_matched_counts(s);
    for(int k=0;k<36;++k) {const int i=column_major(k);board(s).tiles[i].rule.matched=1;flare(h,i,1,rgba(0,100,255,255));}
    std::int32_t specials=0;for(const auto& t:board(s).tiles)specials+=special(t.rule);
    if(specials>0)emit(h,SkillEventKind::Achievement,65,0x3f800000);
    s->generation->filter_enabled=1;emit(h,SkillEventKind::MoveMatchedTiles);s->generation->filter_enabled=0;
    for(auto& c:s->path->combat)c.attack_flag=0;
    reset_flare_timers(s);
}
extern "C" void dr_earthquake(SkillState* s,const SkillHooks* h,const GenerationHooks* gh) {
    for(int x=0;x<6;++x)for(int y=0;y<6;++y) {
        const std::int32_t x2=pick_random(s,6,gh),y2=pick_random(s,6,gh);
        emit(h,SkillEventKind::SwapTiles,x,y,x2,y2);flare(h,at(x,y),1,rgba(115,60,20,255));
    }
    reset_flare_timers(s);
}
extern "C" void dr_kill_skulls_next_to_coins(SkillState* s,const SkillHooks* h) {
    clear_matched_counts(s);s->path->match->sound_13ec4=0;
    for(int x=0;x<6;++x)for(int y=0;y<6;++y) {
        const int i=at(x,y);if(!plain_skull(board(s).tiles[i].rule))continue;
        bool gold=false;
        for(int nx=x-1;nx<=x+1 && !gold;++nx)for(int ny=y-1;ny<=y+1;++ny) {
            if(nx==x && ny==y)continue;
            if(nx<0 || nx>5 || ny<0 || ny>5)continue;
            if(board(s).tiles[at(nx,ny)].rule.type==2) {gold=true;break;}
        }
        if(!gold)continue;
        match(s,i,5,h);flare(h,i,1,rgba(240,150,10,255));
    }
    after_matches(s,h);reset_flare_timers(s);
}
extern "C" void dr_create_chain(SkillState* s,const SkillHooks* h,const GenerationHooks* gh) {
    for(int attempt=0;attempt<10;++attempt) {
        const std::int32_t x=pick_random(s,6,gh),y=pick_random(s,6,gh);
        const int i=at(x,y);if(special(board(s).tiles[i].rule))continue;
        emit(h,SkillEventKind::SetSpecialType,0,i);flare(h,i,1,rgba(100,100,255,255));break;
    }
    reset_flare_timers(s);
}
