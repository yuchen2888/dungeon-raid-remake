#include "recovered_menu.hpp"
#include <algorithm>
#include <iterator>
#include <set>
using namespace dungeonraid;

extern "C" const std::int32_t dr_class_base_skills[10][20]={
    {0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19},
    {31,2,3,4,5,7,8,9,10,12,13,14,16,18,21,22,23,24,25,29},
    {32,2,3,4,6,8,9,11,12,15,16,17,18,19,20,22,23,24,25,27},
    {33,1,2,5,6,7,8,9,10,12,13,15,18,19,21,20,25,26,28,29},
    {34,3,4,5,7,9,10,11,12,13,14,16,18,19,21,20,22,23,25,27},
    {35,1,2,3,6,7,8,9,10,12,15,17,18,21,20,24,25,26,28,29},
    {36,0,2,3,4,6,8,9,10,11,12,13,14,15,17,18,22,23,24,25},
    {37,2,3,4,5,8,9,11,12,13,14,16,18,19,21,20,23,24,25,27},
    {38,2,3,4,5,6,7,10,11,12,13,14,15,16,19,21,22,23,25,27},
    {39,0,1,4,5,7,8,9,12,14,15,16,18,21,22,23,24,25,27,28}};
namespace {
constexpr std::int32_t kBaseCooldown[40]={13,16,15,16,18,18,15,20,18,18,35,12,18,15,25,15,14,15,15,15,
                                          18,20,18,15,25,14,12,16,14,20,24,15,15,-1,14,12,25,35,18,16};
void emit(const MenuHooks* h,MenuEventKind kind,std::int32_t a=0,std::int32_t b=0,std::int32_t c=0) {
    if(h && h->event) {const MenuEvent e{kind,a,b,c};h->event(h->context,&e);}
}
std::int32_t add(std::int32_t a,std::int32_t b) {return static_cast<std::int32_t>(static_cast<std::uint32_t>(a)+static_cast<std::uint32_t>(b));}
bool record_mode(const MenuSources* s,std::int32_t mode) {
    const StrokeState& st=*s->resources->match->stroke;return st.record_14aed && st.mode_14ae8==mode;
}
// The equipped skill of slot i as a Skill object.
SkillRecord equipped(const MenuSources* s,std::int32_t i) {
    SkillRecord k{};const auto& r=*s->resources;
    k.type=s->slots->id[i];k.level=s->slots->level[i];k.max=r.skill_max[i];k.current=r.skill_current[i];k.active=s->slots->active[i];
    return k;
}
// The n-th value of a std::set<int> in ascending order.
std::int32_t nth(const std::set<std::int32_t>& set,std::int32_t n) {auto it=set.begin();std::advance(it,n);return *it;}
}
extern "C" std::int32_t dr_skill_base_cooldown(std::int32_t type) {return kBaseCooldown[type];}
extern "C" bool dr_skill_unlocked(const ClassProfile* classes,std::int32_t type) {
    if(type<=30)return true;
    for(int i=1;i<=9;++i)if(dr_class_base_skills[classes[i].class_type][0]==type)return classes[i].level==10;   // class i's first base skill
    return false;
}
extern "C" void dr_class_skill_pool(const ClassProfile* classes,std::int32_t index,bool pool[40]) {
    std::fill(pool,pool+40,false);const ClassProfile& c=classes[index];
    if(c.class_type==0) {for(int t=0;t<40;++t)pool[t]=dr_skill_unlocked(classes,t);return;}
    for(int i=0;i<20;++i) {
        const std::int32_t r=c.replacement_skills?c.replacement_skills[i]:255;
        pool[r!=255?r:dr_class_base_skills[c.class_type][i]]=true;
    }
}
extern "C" void dr_skill_option(SkillRecord* o,std::int32_t type,const SkillRecord* existing,bool record_mode0) {
    o->type=type;
    std::int32_t max=existing?(existing->level!=10?existing->max-1:existing->max):kBaseCooldown[type];
    if(record_mode0)max-=4;
    o->max=max;
    o->current=existing?std::min(existing->current,max):max;
    const std::int32_t level=existing?existing->level+1:1;
    o->level=record_mode0?5:std::min(level,10);
}
extern "C" void dr_stat_option(SkillRecord* o,std::int32_t stat,const MatchState* m) {
    o->type=stat+40;o->health=o->healing=o->shield=o->damage=0;std::fill(o->chance,o->chance+4,0);o->lines=2;
    // Skill::SetStatChance: 5 unless the chance is already above 99
    auto chance=[&](int k,std::int32_t value) {o->chance[k]=value>99?0:5;};
    // Game+0xbe18 / be20 / be28 / be30 are MatchState.bonus_chance[2] / [0] / [1] / [3]
    switch(stat) {
    case 0:o->damage=1;chance(2,m->bonus_chance[1]);break;
    case 1:o->shield=1;chance(3,m->bonus_chance[3]);break;
    case 2:o->health=5;chance(1,m->bonus_chance[0]);break;
    case 3:o->healing=1;chance(0,m->bonus_chance[2]);break;
    case 4:o->lines=1;o->damage=2;break;
    case 5:o->lines=1;o->shield=2;break;
    case 6:o->lines=1;o->health=10;break;
    case 7:o->lines=4;chance(0,m->bonus_chance[2]);chance(2,m->bonus_chance[1]);chance(3,m->bonus_chance[3]);chance(1,m->bonus_chance[0]);break;
    default:break;
    }
}
extern "C" void dr_menu_open_level(MenuState* menu,const MenuSources* s,const MenuHooks* h) {
    auto& r=*s->resources;auto& m=*r.match;
    *s->open=1;menu->type=0;menu->timer=0.0f;menu->opening=1;menu->confirm_ready=menu->confirm_pressed=0;menu->first=menu->second=-1;menu->previous_phase=0;
    emit(h,MenuEventKind::Sound,12);
    const bool f=record_mode(s,0);
    std::set<std::int32_t> pool;
    if(r.skill_count==4)for(int i=0;i<4;++i)pool.insert(s->slots->id[i]);
    else {bool p[40];dr_class_skill_pool(s->classes,s->class_index,p);for(int t=0;t<40;++t)if(p[t])pool.insert(t);}
    bool all_capped=true;
    for(int i=0;i<r.skill_count;++i) {
        const std::int32_t type=s->slots->id[i];
        if(!f && s->slots->level[i]<=9 && type!=33)all_capped=false;
        else pool.erase(type);
    }
    if(f)pool.erase(22);
    std::set<std::int32_t> stats{0,1,2,3,4,5,6};
    bool chances_full=true;
    for(int k=0;k<4;++k)if(!(m.bonus_chance[k]+m.bonus_chance_extra[k]>99))chances_full=false;
    if(!chances_full)stats.insert(7);
    if(record_mode(s,1)) {pool.erase(24);pool.erase(7);stats.erase(6);}
    const std::int32_t cap=r.skill_count==3 && all_capped?1:2;
    const std::int32_t n=std::min<std::int32_t>(cap,static_cast<std::int32_t>(pool.size()));
    menu->skill_options=n;
    const ClassProfile& cls=s->classes[s->class_index];
    for(int i=0;i<n;++i) {
        std::int32_t chosen=nth(pool,dr_random_int(&m.random,0,static_cast<std::int32_t>(pool.size())-1,3));
        const std::int32_t first=dr_class_base_skills[cls.class_type][0];
        if(i==0 && r.level==2 && cls.class_type!=0 && (!f || first!=33))chosen=first;
        int found=-1;for(int j=0;j<r.skill_count;++j)if(s->slots->id[j]==chosen)found=j;
        if(i==0 && r.skill_count==3 && found<0) {
            pool.clear();
            if(!f)for(int j=0;j<r.skill_count;++j)if(s->slots->level[j]<=9 && s->slots->id[j]!=33)pool.insert(s->slots->id[j]);
        } else pool.erase(chosen);
        if(found>=0) {const SkillRecord e=equipped(s,found);dr_skill_option(&menu->options[i],chosen,&e,f);}
        else dr_skill_option(&menu->options[i],chosen,nullptr,f);
    }
    for(int i=n;i<4;++i) {
        const std::int32_t stat=nth(stats,dr_random_int(&m.random,0,static_cast<std::int32_t>(stats.size())-1,3));
        stats.erase(stat);dr_stat_option(&menu->options[i],stat,&m);
    }
}
namespace {
// Exchange option's skill fields with the object of slot i (Game+0xbf90 pointers: the objects move).
void exchange(const MenuSources* s,SkillRecord* o,std::int32_t i) {
    auto& k=*s->slots;auto& r=*s->resources;
    std::swap(o->type,k.id[i]);std::swap(o->level,k.level[i]);std::swap(o->active,k.active[i]);
    std::swap(o->max,r.skill_max[i]);std::swap(o->current,r.skill_current[i]);
}
void shorten(std::int32_t& max,std::int32_t& current) {max-=1;current=std::min(current,max);}
bool have_perk(const MatchState& m,std::int32_t perk) {
    if(perk==255)return false;
    for(auto p:m.perks)if(p==perk)return true;
    return false;
}
}
extern "C" void dr_set_skill(const MenuSources* s,SkillRecord* o,const MenuHooks* h) {
    auto& r=*s->resources;auto& m=*r.match;
    if(o->type<=39) {
        for(int i=0;i<r.skill_count;++i)if(s->slots->id[i]==o->type) {
            exchange(s,o,i);emit(h,MenuEventKind::PositionSkill,i);emit(h,MenuEventKind::UpdateSkills);return;
        }
        if(r.skill_count>3) {emit(h,MenuEventKind::UpdateSkills);return;}
        const std::int32_t i=r.skill_count;
        exchange(s,o,i);emit(h,MenuEventKind::PositionSkill,i);r.skill_count=i+1;
        if(s->player->skill_cooldown_be64)shorten(r.skill_max[i],r.skill_current[i]);
        if(r.skill_count==4 && have_perk(m,3))shorten(r.skill_max[i],r.skill_current[i]);
        emit(h,MenuEventKind::UpdateSkills);return;
    }
    auto& pv=*s->preview;
    pv.healing_value=add(pv.healing_value,o->healing);pv.shield_value=add(pv.shield_value,o->shield);
    // Game+0xbe18 / be20 / be28 / be30 = MatchState.bonus_chance[2] / [0] / [1] / [3]
    const int chance_index[4]={2,0,1,3};
    for(int k=0;k<4;++k) {auto& c=m.bonus_chance[chance_index[k]];c=std::min(add(c,o->chance[k]),100);}
    if(!record_mode(s,1) && o->health>0) {
        r.health_max=add(r.health_max,o->health);r.health=add(r.health,o->health);
        const std::int32_t ceiling=add(r.health_bonus,r.health_max);
        if(ceiling!=s->player->ui_health_ceiling_5998) {s->player->ui_health_ceiling_5998=ceiling;emit(h,MenuEventKind::HealthBar,r.ui_health);}
        if(r.health!=r.ui_health) {r.ui_health=r.health;emit(h,MenuEventKind::HealthBar,r.health);}
    }
    if(o->damage>0) {
        auto& sel=*s->selection;sel.base_damage=add(sel.base_damage,o->damage);
        const std::int32_t skull=add(sel.base_damage,sel.bonus_base_damage);
        if(skull!=s->player->ui_skull_59c8) {s->player->ui_skull_59c8=skull;emit(h,MenuEventKind::SkullValue);}
    }
    if(o->type>=40 && o->type<=43)s->stat_counts[o->type-40]=add(s->stat_counts[o->type-40],1);
}
namespace {
std::int32_t item_slot(std::int32_t type) {return type>=0 && type<=3?type:4;}   // Game::GetItem / SetItem
void update_stats(const MenuSources* s) {
    const ItemStats* items[5];for(int i=0;i<5;++i)items[i]=&s->equipped[i].stats;
    dr_update_stats(s->stats,items,5,s->stats_hooks);
}
}
extern "C" void dr_menu_open_shop(MenuState* menu,const MenuSources* s,const MenuHooks* h) {
    auto& m=*s->resources->match;
    *s->open=1;menu->type=1;menu->timer=0.0f;menu->opening=1;menu->confirm_ready=menu->confirm_pressed=0;menu->first=menu->second=-1;menu->previous_phase=0;
    emit(h,MenuEventKind::Sound,11);
    std::set<std::int32_t> types{0,1,2,3,4};
    for(int i=0;i<3;++i) {
        const std::int32_t t=nth(types,dr_random_int(&m.random,0,static_cast<std::int32_t>(types.size())-1,2));
        const ItemRecord& existing=s->equipped[item_slot(t)];
        dr_item_make(s->stats,&menu->items[i],existing.type,&existing);types.erase(t);
    }
    const float chance=s->selection->character.race==3?0.5f:0.25f;   // the current class's race (Game+0x15564+388*index+8)
    if(!(chance<=dr_random_float(&m.random,0.0f,1.0f,2))) {
        menu->scroll_slot=dr_random_int(&m.random,0,2,2);
        const float r=dr_random_float(&m.random,0.0f,1.0f,2);
        std::int32_t candidates[40];std::int32_t n=0;
        for(std::int32_t t=0;t<40;++t) {
            if(t==33 || (t==24 && record_mode(s,1)))continue;
            if(!(r<0.1f) && s->probe[t]!=0)continue;
            if(!dr_skill_unlocked(s->classes,t) || !dr_skill_can_activate(s->skills,t))continue;
            candidates[n++]=t;
        }
        const std::int32_t pick=dr_random_int(&m.random,0,n-1,2);
        dr_skill_option(&menu->scroll,candidates[pick],nullptr,record_mode(s,0));
    } else menu->scroll_slot=-1;
}
extern "C" void dr_menu_open_upgrade(MenuState* menu,const MenuSources* s,const MenuHooks* h) {
    auto& m=*s->resources->match;
    *s->open=1;menu->type=2;menu->timer=0.0f;menu->opening=1;menu->confirm_ready=menu->confirm_pressed=0;menu->first=menu->second=-1;menu->previous_phase=0;
    emit(h,MenuEventKind::Sound,13);
    std::set<std::int32_t> types{0,1,2,3,4};
    for(int i=0;i<4;++i) {
        const std::int32_t t=nth(types,dr_random_int(&m.random,0,static_cast<std::int32_t>(types.size())-1,4));types.erase(t);
        const std::int32_t slot=item_slot(t);const ItemRecord& item=s->equipped[slot];
        menu->upgrade_items[i]=slot;
        menu->upgrade_type[i]=dr_random_item_stat(s->stats,item.type,item.stats.upgrade[5]==0);
        menu->upgrade_amount[i]=dr_stat_upgrade(s->stats,menu->upgrade_type[i]);
    }
}
extern "C" void dr_menu_input(MenuState* menu,std::int32_t phase,std::int32_t button,const MenuHooks* h) {
    if(phase==1) {
        if(menu->previous_phase==0) {
            if(menu->confirm_ready && button==7) {emit(h,MenuEventKind::Sound,0);menu->confirm_pressed=1;emit(h,MenuEventKind::Confirm,1);}
            else for(std::int32_t b=14;b<=17;++b) {
                if(b==17 && menu->type==1)continue;
                if(button!=b)continue;
                const bool both_other=menu->type==0 && menu->first!=-1 && menu->second!=-1 && b!=menu->first && b!=menu->second;
                if(!both_other)emit(h,MenuEventKind::Sound,menu->type==1?1:menu->type==0?9:menu->type==2?8:-1);
                if(menu->type==1 && menu->scroll_slot==b-14)emit(h,MenuEventKind::ScrollTooltip,menu->scroll.type);
                if(both_other) {}
                else if(menu->first==b) {emit(h,MenuEventKind::Highlight,b,0,0);menu->first=-1;}
                else if(menu->second==b) {emit(h,MenuEventKind::Highlight,b,1,0);menu->second=-1;}
                else if(menu->first==-1) {menu->first=b;emit(h,MenuEventKind::Highlight,b,0,1);}
                else if(menu->type!=0) {emit(h,MenuEventKind::Highlight,menu->first,0,0);menu->first=b;emit(h,MenuEventKind::Highlight,b,0,1);}
                else if(menu->second==-1) {emit(h,MenuEventKind::Highlight,b,1,1);menu->second=b;}
                break;
            }
            menu->confirm_ready=menu->type==0?(menu->first!=-1 && menu->second!=-1):(menu->first!=-1);
        }
    } else if(phase==2 && menu->confirm_pressed) {
        if(button==7) {
            menu->timer=0.0f;menu->opening=0;
            if(menu->type>=0 && menu->type<=2)emit(h,MenuEventKind::Sound,menu->type==1?11:menu->type==0?12:13);
        } else menu->confirm_pressed=0;
        emit(h,MenuEventKind::Confirm,0);
    }
    if(phase!=1)emit(h,MenuEventKind::TooltipHide);
    menu->previous_phase=phase;
}
extern "C" void dr_menu_process(MenuState* menu,const MenuSources* s,float dt,std::int32_t phase,std::int32_t button,const MenuHooks* h) {
    if(menu->timer<0.0f) {dr_menu_input(menu,phase,button,h);return;}
    menu->timer=menu->timer+dt;
    if(menu->timer<0.3f)return;
    menu->timer=-1.0f;
    if(menu->opening)return;
    *s->open=0;
    if(menu->type==0) {dr_set_skill(s,&menu->options[menu->first-14],h);dr_set_skill(s,&menu->options[menu->second-14],h);}
    else if(menu->type==1) {
        ItemRecord& chosen=menu->items[menu->first-14];std::swap(chosen,s->equipped[item_slot(chosen.type)]);
        update_stats(s);
        if(menu->scroll_slot>=0 && menu->scroll_slot==menu->first-14) {
            emit(h,MenuEventKind::ActivateScroll,menu->scroll.type);
            if(s->selection->character.race==3)emit(h,MenuEventKind::Achievement,49,0x40000000);
        }
    } else if(menu->type==2) {
        const int k=menu->first-14;auto& v=s->equipped[menu->upgrade_items[k]].stats.upgrade[menu->upgrade_type[k]];
        v=add(v,menu->upgrade_amount[k]);update_stats(s);
    }
}
