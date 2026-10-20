#include "recovered_items.hpp"
#include <iterator>
#include <set>
using namespace dungeonraid;
namespace {
std::int32_t add(std::int32_t a,std::int32_t b) {return static_cast<std::int32_t>(static_cast<std::uint32_t>(a)+static_cast<std::uint32_t>(b));}
std::int32_t sub(std::int32_t a,std::int32_t b) {return static_cast<std::int32_t>(static_cast<std::uint32_t>(a)-static_cast<std::uint32_t>(b));}
bool record_mode(const StatsTargets* t,std::int32_t mode) {return t->stroke->record_14aed && t->stroke->mode_14ae8==mode;}
RandomState& random(const StatsTargets* t) {return t->resources->match->random;}
float chance(const StatsTargets* t) {return dr_random_float(&random(t),0.0f,1.0f,2);}
// v - downgrade, floor 0
std::int32_t lowered(const StatsTargets* t,std::int32_t v,std::int32_t u) {const std::int32_t d=sub(v,dr_stat_downgrade(t,u));return d>0?d:0;}
constexpr std::int32_t kIconRange[5][2]={{0,79},{80,159},{240,319},{160,239},{320,399}};
constexpr std::int32_t kPrefixes=148;
// Item::InitialiseNames: the name groups by icon range [lo, hi) and their sizes
constexpr std::int32_t kNameGroups[13][3]={{0,20,15},{20,40,12},{40,50,13},{50,60,12},{60,80,15},{80,160,17},{160,240,16},
                                           {240,320,17},{320,340,14},{340,360,11},{360,370,14},{370,380,16},{380,400,16}};
constexpr std::int32_t kStatPool[5][8]={{0,1,2,3,4,6,8,9},{6,7,10,11,12,13,17,-1},{10,11,12,14,15,17,18,19},{0,1,11,12,13,15,16,-1},
                                         {5,8,9,10,17,18,19,-1}};
}
extern "C" bool dr_upgrade_allowed(const StatsTargets* t,std::int32_t type) {
    switch(type) {
    case 2:return t->stroke->selection.leech<=24;
    case 4:return t->battle->armour_break_chance<=94;
    case 6:return t->preview->xp_bonus<2.0f;
    case 7:return t->preview->gold_bonus<2.0f;
    case 10:return !record_mode(t,1);
    case 13:return t->preview->upgrade_bonus<2.0f;
    case 14: {const std::int32_t v=t->attack->armour_loss_chance;return 100-(v>100?100:v)<=89;}
    default:return true;
    }
}
extern "C" std::int32_t dr_random_item_stat(const StatsTargets* t,std::int32_t item_type,bool allow5) {
    std::set<std::int32_t> pool;
    if(item_type>=0 && item_type<=4)for(auto u:kStatPool[item_type])if(u>=0)pool.insert(u);
    if(!allow5)pool.erase(5);
    if(record_mode(t,0))pool.erase(15);
    else if(dr_random_int(&random(t),0,t->attack->weaken,4)!=0)pool.erase(15);
    for(auto u:{10,2,6,13,7,14,4})if(!dr_upgrade_allowed(t,u))pool.erase(u);
    auto it=pool.begin();std::advance(it,dr_random_int(&random(t),0,static_cast<std::int32_t>(pool.size())-1,4));
    return *it;
}
extern "C" void dr_item_initialise(RandomState* r,ItemRecord* item,std::int32_t type) {
    const auto& range=kIconRange[type>=0 && type<=3?type:4];
    item->icon=dr_random_int(r,range[0],range[1],2);item->type=type;
}
extern "C" void dr_item_generate_name(RandomState* r,ItemRecord* item,const ItemRecord* existing) {
    if(!existing) {item->prefix_level=item->prefix=-1;}
    else {
        const std::int32_t e=existing->prefix_level;
        if(kPrefixes-12>e) {const std::int32_t v=dr_random_int(r,e+1,e+10,2);item->prefix_level=item->prefix=v;}
        else {item->prefix_level=e;item->prefix=dr_random_int(r,e,kPrefixes-1,2);}
    }
    for(const auto& g:kNameGroups)if(item->icon>=g[0] && item->icon<g[1]) {item->name=dr_random_int(r,0,g[2]-1,2);break;}
}
extern "C" void dr_item_generate_stats(const StatsTargets* t,ItemRecord* item,const ItemRecord* existing) {
    auto& s=item->stats.upgrade;for(auto& v:s)v=0;
    if(!existing) {
        switch(item->type) {
        case 0:s[0]=2;break;
        case 1:case 3:s[11]=1;break;
        case 2:s[11]=dr_have_flaw(&t->stroke->selection.character,6)?1:2;break;
        case 4:if(!record_mode(t,1))s[10]=10;break;
        default:break;
        }
        return;
    }
    const auto& e=existing->stats.upgrade;
    std::set<std::int32_t> positive;for(int u=0;u<20;++u)if(e[u]>0)positive.insert(u);
    switch(item->type) {
    case 0:
        s[0]=add(e[0],1);positive.erase(0);
        for(auto u:positive) {
            if(chance(t)<0.15f) {s[u]=lowered(t,e[u],u);s[0]=add(s[0],1);}
            else s[u]=e[u];
        }
        break;
    case 1: {
        s[11]=add(e[11],1);positive.erase(11);int raised=0;
        for(auto u:positive) {
            if(chance(t)<0.2f) {
                if(dr_upgrade_allowed(t,u) && raised<=0 && chance(t)<0.5f) {s[u]=add(dr_stat_upgrade(t,u),e[u]);++raised;}
                else {s[u]=lowered(t,e[u],u);s[11]=add(s[11],1);}
            } else s[u]=e[u];
        }
        break;
    }
    case 2: {
        const bool kept=chance(t)<0.2f;
        s[11]=add(e[11],kept?2:1);positive.erase(11);
        for(auto u:positive) {
            if(!kept && chance(t)<0.1f) {s[u]=lowered(t,e[u],u);s[11]=add(s[11],1);}
            else s[u]=e[u];
        }
        break;
    }
    case 3:
        s[11]=add(e[11],1);positive.erase(11);
        for(auto u:positive) {
            if(u==0) {
                if(chance(t)<0.7f) {s[0]=lowered(t,e[0],0);s[11]=add(s[11],1);}
                else s[0]=e[0];
            } else if(chance(t)<0.2f) {
                s[u]=lowered(t,e[u],u);
                if(chance(t)<0.2f)s[0]=add(s[0],1);else s[11]=add(s[11],1);
            } else s[u]=e[u];
        }
        break;
    case 4: {
        const std::int32_t up=dr_stat_upgrade(t,10);
        s[10]=add(e[10],up/2);positive.erase(10);
        for(auto u:positive) {
            if(chance(t)<0.1f) {
                s[u]=lowered(t,e[u],u);
                const std::int32_t r=dr_random_item_stat(t,4,false);s[r]=add(dr_stat_upgrade(t,r),s[r]);
            } else s[u]=e[u];
        }
        if(record_mode(t,1) || chance(t)<0.5f) {
            const std::int32_t r=dr_random_item_stat(t,4,s[5]==0);s[r]=add(dr_stat_upgrade(t,r),s[r]);
        }
        break;
    }
    default:break;
    }
}
extern "C" void dr_item_make(const StatsTargets* t,ItemRecord* item,std::int32_t type,const ItemRecord* existing) {
    dr_item_initialise(&random(t),item,type);dr_item_generate_name(&random(t),item,existing);dr_item_generate_stats(t,item,existing);
}
