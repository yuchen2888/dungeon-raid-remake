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
void emit(const MenuHooks* h,MenuEventKind kind,std::int32_t a) {
    if(h && h->event) {const MenuEvent e{kind,a};h->event(h->context,&e);}
}
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
    *s->open=1;menu->type=0;menu->timer=0.0f;menu->opening=1;menu->confirm_ready=menu->confirm_pressed=0;menu->first=menu->second=-1;
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
