#include "recovered_resources.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
using namespace dungeonraid;
namespace {
int add(int a,int b) {return static_cast<int>(static_cast<std::uint32_t>(a)+static_cast<std::uint32_t>(b));}
int sub(int a,int b) {return static_cast<int>(static_cast<std::uint32_t>(a)-static_cast<std::uint32_t>(b));}
int mul(int a,int b) {return static_cast<int>(static_cast<std::uint32_t>(a)*static_cast<std::uint32_t>(b));}
int integer(float x) {
    if(std::isnan(x))return 0;
    if(static_cast<double>(x)>=2147483647.0)return std::numeric_limits<int>::max();
    if(x<=-2147483648.0f)return std::numeric_limits<int>::min();
    return static_cast<int>(x);
}
void emit(const ResourceHooks* h,ResourceEventKind kind,int a=0,int b=0,int c=0,int d=0) {
    if(h && h->event) {const ResourceEvent e{kind,a,b,c,d};h->event(h->context,&e);}
}
void health_bar(ResourceState* r,const ResourceHooks* h) {
    if(r->ui_health!=r->health) {r->ui_health=r->health;emit(h,ResourceEventKind::HealthBar,r->health);}
}
int enemies(const SelectionState& s,int enemy) {
    int count=0;for(const auto& t:s.tiles)if(t.rule.type==1 && t.rule.enemy_type==enemy)++count;return count;
}
void progress(int& value,float& fraction,int mode,float bonus,int doubling) {
    value=add(value,mul(mul(2,mode),doubling));
    fraction=fraction+(bonus*static_cast<float>(mode))*static_cast<float>(doubling);
    if(fraction>=1.0f) {const int whole=integer(fraction);value=add(value,whole);fraction=fraction-static_cast<float>(whole);}
}
void achievement(const ResourceHooks* h,int id) {emit(h,ResourceEventKind::Achievement,id,0x42c80000);}
}
extern "C" void dr_add_resource(ResourceState* r,int reward,int token,int amount,const ResourceHooks* h) {
    auto& m=*r->match;auto& s=m.stroke->selection;auto& p=*m.preview;
    const int mode=m.stroke->record_14aed && m.stroke->mode_14ae8==0?2:1;
    if(reward==0) {
        if(token==1 && amount>=0 && amount<r->skill_count) {
            emit(h,ResourceEventKind::Sound,4);
            r->skill_current[amount]=std::min(add(r->skill_current[amount],1),r->skill_max[amount]);
            emit(h,ResourceEventKind::Skills);return;
        }
        if(token==2) {
            emit(h,ResourceEventKind::Sound,17);
            r->health=sub(sub(r->health,p.healing_bonus),p.healing_value);
            if(r->health<0) {r->health=0;achievement(h,37);}
            health_bar(r,h);emit(h,ResourceEventKind::CheckEndGame,r->guard_164a4,r->health);return;
        }
        emit(h,ResourceEventKind::Sound,4);
        r->health=add(r->health,mul(add(p.healing_value,p.healing_bonus),p.double_healing?2:1));
        r->health=std::min(r->health,add(r->health_max,r->health_bonus));
        health_bar(r,h);
        if(dr_mortal_enemy(s.character.race)==9 && enemies(s,9)>0)return;
        r->poison=0;emit(h,ResourceEventKind::Poison,0);return;
    }
    if(reward==1 && token==3) {
        emit(h,ResourceEventKind::Sound,17);r->health=std::max(sub(r->health,amount),0);health_bar(r,h);
        emit(h,ResourceEventKind::Target,0);emit(h,ResourceEventKind::Label,2,amount,11,0x3f000000);
        if(r->guard_164a6 && !r->guard_164a4) {
            r->guard_164a4=1;emit(h,ResourceEventKind::CheckEndGame,1,r->health);r->guard_164a4=0;
        } else emit(h,ResourceEventKind::CheckEndGame,r->guard_164a4,r->health);
        return;
    }
    if(reward==1) {
        emit(h,ResourceEventKind::Sound,9);emit(h,ResourceEventKind::Help,1);
        progress(r->xp,r->xp_fraction,mode,p.xp_bonus,1);
        if(r->xp>99) {
            emit(h,ResourceEventKind::Shadow,1,-1);r->total_xp=add(r->total_xp,100);r->level=add(r->level,1);
            emit(h,ResourceEventKind::Menu,0);r->xp%=100;
            if(s.character.race==4)emit(h,ResourceEventKind::Healing);
            switch(r->level) {
            case 5:
                achievement(h,29);if(m.spawn_enabled_14ae0==3 && r->skill_count==0)achievement(h,71);break;
            case 10: {
                achievement(h,30);int perks=0,flaws=0;
                for(auto perk:m.perks)if(perk!=255)++perks;
                for(auto flaw:s.character.flaws)if(flaw!=255)++flaws;
                if(m.spawn_enabled_14ae0==3 && m.class_type!=0 && perks==1 && flaws==4)achievement(h,70);break;
            }
            case 25:achievement(h,31);break;
            case 50:achievement(h,32);break;
            case 100:achievement(h,33);break;
            default:break;
            }
        }
        if(r->ui_xp!=r->xp) {r->ui_xp=r->xp;emit(h,ResourceEventKind::XPBar,r->xp);}return;
    }
    if(reward==3) {
        if(p.armour_current!=p.armour_max && enemies(s,12)==0) {
            emit(h,ResourceEventKind::Sound,6);emit(h,ResourceEventKind::Help,3);
            p.armour_current=std::min(add(p.armour_current,mul(add(p.shield_value,p.shield_bonus),p.double_upgrade?2:1)),p.armour_max);
            if(r->ui_armour!=p.armour_current) {r->ui_armour=p.armour_current;emit(h,ResourceEventKind::Shield);}return;
        }
        emit(h,ResourceEventKind::Sound,8);emit(h,ResourceEventKind::Help,2);
        progress(r->up,r->up_fraction,mode,p.upgrade_bonus,p.double_upgrade?2:1);
        if(r->up>99) {
            emit(h,ResourceEventKind::Shadow,3,-1);r->total_up=add(r->total_up,100);
            emit(h,ResourceEventKind::Menu,2);r->up%=100;
        }
        if(r->ui_up!=r->up) {r->ui_up=r->up;emit(h,ResourceEventKind::UPBar,r->up);}return;
    }
    if(reward==2) {
        emit(h,ResourceEventKind::Sound,2);emit(h,ResourceEventKind::Help,0);
        progress(r->gold,r->gold_fraction,mode,p.gold_bonus,p.double_gold?2:1);
        if(r->gold>99) {
            emit(h,ResourceEventKind::Shadow,2,-1);r->total_gold=add(r->total_gold,100);
            emit(h,ResourceEventKind::Menu,1);r->gold%=100;
        }
        if(r->ui_gold!=r->gold) {r->ui_gold=r->gold;emit(h,ResourceEventKind::GoldBar,r->gold);}return;
    }
}
