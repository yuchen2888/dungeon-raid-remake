#include "recovered_stats.hpp"
using namespace dungeonraid;
namespace {
std::int32_t add(std::int32_t a,std::int32_t b) {return static_cast<std::int32_t>(static_cast<std::uint32_t>(a)+static_cast<std::uint32_t>(b));}
std::int32_t sub(std::int32_t a,std::int32_t b) {return static_cast<std::int32_t>(static_cast<std::uint32_t>(a)-static_cast<std::uint32_t>(b));}
std::int32_t mul(std::int32_t a,std::int32_t b) {return static_cast<std::int32_t>(static_cast<std::uint32_t>(a)*static_cast<std::uint32_t>(b));}
void emit(const StatsHooks* h,StatsEventKind kind,std::int32_t value=0) {if(h && h->event)h->event(h->context,kind,value);}
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
