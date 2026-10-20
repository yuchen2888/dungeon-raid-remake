#include "recovered_stats.hpp"
using namespace dungeonraid;
namespace {
std::int32_t add(std::int32_t a,std::int32_t b) {return static_cast<std::int32_t>(static_cast<std::uint32_t>(a)+static_cast<std::uint32_t>(b));}
std::int32_t sub(std::int32_t a,std::int32_t b) {return static_cast<std::int32_t>(static_cast<std::uint32_t>(a)-static_cast<std::uint32_t>(b));}
std::int32_t mul(std::int32_t a,std::int32_t b) {return static_cast<std::int32_t>(static_cast<std::uint32_t>(a)*static_cast<std::uint32_t>(b));}
void emit(const StatsHooks* h,StatsEventKind kind,std::int32_t a=0,std::int32_t tile=-1,std::int32_t b=0,std::int32_t c=0,std::int32_t d=0) {
    if(h && h->event) {const StatsEvent e{kind,tile,a,b,c,d};h->event(h->context,&e);}
}
// Skill::GetStat 0x2ab40 / Skill::GetStatChance 0x2ab5c / ItemUpgrade::GetFloatValue 0x2d090.
std::int32_t skill_stat(int type) {return type==2?5:(type>=0 && type<=3?1:0);}
constexpr std::int32_t stat_chance=5;
float float_value(std::int32_t v) {return static_cast<float>(v)*.25f;}
}
extern "C" void dr_update_stats(StatsTargets* t,const ItemStats* const* items,std::uint32_t count,const StatsHooks* h) {
    auto& r=*t->resources;auto& pv=*t->preview;auto& sel=t->stroke->selection;auto& b=*t->battle;
    auto& a=*t->attack;auto& ps=*t->player;
    const std::int32_t old_armour_max=pv.armour_max,old_armour=pv.armour_current;
    sel.weapon_damage=0;pv.armour_max=0;
    b.armour_break_chance=dr_have_flaw(&sel.character,5)?30:50;
    a.armour_loss_chance=50;
    b.poison_amount=0;sel.leech=0;a.damage_all=0;a.weaken=0;*t->regen=0;
    const bool old_cooldown=ps.skill_cooldown_be64;ps.skill_cooldown_be64=0;
    ps.base_bdec=ps.base_bdf4=ps.base_bdfc=ps.base_be04=0;
    const std::int32_t old_health_max=r.health_max,old_bonus=r.health_bonus,old_health=r.health;
    r.health_bonus=0;
    sel.bonus_base_damage=0;pv.shield_bonus=0;
    pv.xp_bonus=0;pv.gold_bonus=0;pv.upgrade_bonus=0;
    const bool skip_health_bonus=t->stroke->record_14aed && t->stroke->mode_14ae8==1;
    for(std::uint32_t i=0;i<count;++i) {
        const auto& u=items[i]->upgrade;
        sel.weapon_damage=add(u[0],sel.weapon_damage);
        pv.armour_max=add(u[11],pv.armour_max);
        b.armour_break_chance=add(u[4],b.armour_break_chance);
        a.armour_loss_chance=sub(a.armour_loss_chance,u[14]);
        b.poison_amount=add(u[3],b.poison_amount);
        sel.leech=add(u[2],sel.leech);
        a.damage_all=add(u[12],a.damage_all);
        a.weaken=add(u[15],a.weaken);
        *t->regen=add(u[17],*t->regen);
        if(u[5]>0)ps.skill_cooldown_be64=1;
        ps.base_bdec=add(u[8],ps.base_bdec);
        ps.base_bdf4=add(u[18],ps.base_bdf4);
        ps.base_bdfc=add(u[19],ps.base_bdfc);
        ps.base_be04=add(u[9],ps.base_be04);
        if(!skip_health_bonus)r.health_bonus=add(u[10],r.health_bonus);
        sel.bonus_base_damage=add(u[1],sel.bonus_base_damage);
        pv.shield_bonus=add(u[16],pv.shield_bonus);
        pv.xp_bonus=pv.xp_bonus+float_value(u[6]);
        pv.gold_bonus=pv.gold_bonus+float_value(u[7]);
        pv.upgrade_bonus=pv.upgrade_bonus+float_value(u[13]);
    }
    if(pv.xp_bonus>2.0f)pv.xp_bonus=2.0f;
    if(pv.gold_bonus>2.0f)pv.gold_bonus=2.0f;
    if(pv.upgrade_bonus>2.0f)pv.upgrade_bonus=2.0f;
    if(b.armour_break_chance>95)b.armour_break_chance=95;
    if(a.armour_loss_chance<=4)a.armour_loss_chance=5;
    if(!skip_health_bonus)r.health_bonus=add(mul(ps.base_bdfc,skill_stat(2)),r.health_bonus);
    sel.bonus_base_damage=add(mul(ps.base_bdec,skill_stat(0)),sel.bonus_base_damage);
    pv.healing_bonus=mul(ps.base_be04,skill_stat(3));
    pv.shield_bonus=add(mul(ps.base_bdf4,skill_stat(1)),pv.shield_bonus);
    ps.chance_be1c=mul(ps.base_be04,stat_chance);
    ps.chance_be24=mul(ps.base_bdfc,stat_chance);
    ps.chance_be2c=mul(ps.base_bdec,stat_chance);
    ps.chance_be34=mul(ps.base_bdf4,stat_chance);
    if(old_bonus!=r.health_bonus) {
        if(old_bonus<r.health_bonus)
            r.health=add(sub(sub(add(r.health_bonus,r.health_max),old_bonus),old_health_max),old_health);
        else {
            const std::int32_t ceiling=add(r.health_max,r.health_bonus);
            if(r.health>ceiling)r.health=ceiling;
        }
        const std::int32_t ceiling=add(r.health_bonus,r.health_max);
        if(ceiling!=ps.ui_health_ceiling_5998) {ps.ui_health_ceiling_5998=ceiling;emit(h,StatsEventKind::HealthBar,r.ui_health);}
        if(r.health!=r.ui_health) {r.ui_health=r.health;emit(h,StatsEventKind::HealthBar,r.health);}
    }
    const std::int32_t armour=sub(pv.armour_max,sub(old_armour_max,old_armour));
    pv.armour_current=armour>0?armour:0;
    if(sel.weapon_damage!=ps.ui_sword_59bc) {ps.ui_sword_59bc=sel.weapon_damage;emit(h,StatsEventKind::SwordValue);}
    const std::int32_t skull=add(sel.bonus_base_damage,sel.base_damage);
    if(skull!=ps.ui_skull_59c8) {ps.ui_skull_59c8=skull;emit(h,StatsEventKind::SkullValue);}
    if(pv.armour_current!=r.ui_armour) {r.ui_armour=pv.armour_current;emit(h,StatsEventKind::ShieldValue);}
    if(pv.armour_max!=ps.ui_armour_max_59c4) {ps.ui_armour_max_59c4=pv.armour_max;emit(h,StatsEventKind::ShieldValue);}
    std::int32_t delta=0;
    if(ps.skill_cooldown_be64 && !old_cooldown)delta=-1;
    else if(!ps.skill_cooldown_be64 && old_cooldown)delta=1;
    if(!delta)return;
    for(std::int32_t i=0;i<r.skill_count;++i) {
        r.skill_max[i]=add(r.skill_max[i],delta);
        if(r.skill_current[i]>r.skill_max[i])r.skill_current[i]=r.skill_max[i];
    }
    emit(h,StatsEventKind::UpdateSkills);
}
namespace {
bool have_perk(const MatchState& m,std::int32_t perk) {
    // CharacterClass::HavePerk 0x1115c0
    if(perk==255)return false;
    for(auto p:m.perks)if(p==perk)return true;
    return false;
}
std::int32_t graded_leech(std::int32_t v,bool upgrade) {
    if(v>22)return 2;
    if(v>20)return upgrade?2:3;
    if(v>17)return 3;
    if(upgrade && v>14)return 3;
    return 5;
}
std::int32_t graded_loss(std::int32_t chance,bool upgrade) {
    const std::int32_t d=100-(chance>100?100:chance);
    if(d>87)return 2;
    if(d>85)return upgrade?2:3;
    if(d>82)return 3;
    if(d>79)return upgrade?3:5;
    if(d>74)return 5;
    if(upgrade && d>69)return 5;
    return 10;
}
}
extern "C" std::int32_t dr_stat_upgrade(const StatsTargets* t,std::int32_t type) {
    switch(type) {
    case 2: return graded_leech(t->stroke->selection.leech,true);
    case 3: return 2;
    case 4: return 10;
    case 10: return t->stroke->record_14aed && t->stroke->mode_14ae8==1?0:10;
    case 14: return graded_loss(t->attack->armour_loss_chance,true);
    case 17: return have_perk(*t->resources->match,5)?2:1;
    default: return type>=0 && type<=19?1:0;
    }
}
extern "C" std::int32_t dr_stat_downgrade(const StatsTargets* t,std::int32_t type) {
    if(type==2)return graded_leech(t->stroke->selection.leech,false);
    if(type==14)return graded_loss(t->attack->armour_loss_chance,false);
    return dr_stat_upgrade(t,type);
}
extern "C" void dr_destroy_upgrade(StatsTargets* t,ItemStats* const* items,std::uint32_t count,std::uint32_t tile,const StatsHooks* h) {
    auto& m=*t->resources->match;
    const std::int32_t index=dr_random_int(&m.random,0,static_cast<std::int32_t>(count)-1,5);
    ItemStats& item=*items[index];
    std::int32_t positive[20];int n=0;
    for(int k=0;k<20;++k)if(item.upgrade[k]>0)positive[n++]=k;
    if(n) {
        const std::int32_t type=positive[dr_random_int(&m.random,0,n-1,5)];
        // Item::ReduceStat 0x29d9c
        const std::int32_t reduced=sub(item.upgrade[type],dr_stat_downgrade(t,type));
        item.upgrade[type]=reduced>0?reduced:0;
        emit(h,StatsEventKind::ItemText,index);   // Item::MakeStats
        emit(h,StatsEventKind::Achievement,39,-1,0x42c80000);
    }
    emit(h,StatsEventKind::Label,32,static_cast<std::int32_t>(tile),0,40,0x3f800000);
    emit(h,StatsEventKind::Sound,22);
    dr_update_stats(t,items,count,h);
}
extern "C" void dr_item_increase_stat(const StatsTargets* t,ItemStats* item,std::int32_t index,std::int32_t type,const StatsHooks* h) {
    const std::int32_t increased=add(dr_stat_upgrade(t,type),item->upgrade[type]);
    item->upgrade[type]=increased>0?increased:0;
    emit(h,StatsEventKind::ItemText,index);   // Item::MakeStats
}
