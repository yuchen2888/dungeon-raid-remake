#include "recovered_attack_shield.hpp"
using namespace dungeonraid;
namespace {
void emit(const AttackShieldHooks* h,AttackShieldEventKind kind,int a=0,int b=0,int c=0,int d=0) {
    if(h && h->event) { const AttackShieldEvent e{kind,a,b,c,d};h->event(h->context,&e); }
}
}
extern "C" std::int32_t dr_process_attack_shield_wear(ResourceState* s,
    std::int32_t absorbed_damage,std::int32_t armour_loss_chance,const AttackShieldHooks* h) {
    auto& m=*s->match;
    RuleTile tiles[36];
    for(int i=0;i<36;++i)tiles[i]=m.stroke->selection.tiles[i].rule;
    const RuleGame view{0,{},tiles};
    const bool forced=dr_enemy_count(&view,29)>0;
    int lost=0;
    for(int i=0;i<absorbed_damage;++i) {
        if(forced)++lost;
        else {
            const int value=dr_random_int(&m.random,0,100,5);
            emit(h,AttackShieldEventKind::Random,0,100,5,value);
            if(value<armour_loss_chance)++lost;
        }
    }
    if(lost>0) {
        auto& armour=m.preview->armour_current;
        armour-=lost;
        if(s->ui_armour!=armour) {
            s->ui_armour=armour;emit(h,AttackShieldEventKind::ShieldValue,armour);
        }
        emit(h,AttackShieldEventKind::ShieldShatter);
    }
    emit(h,AttackShieldEventKind::Sound,lost>0?16:15);
    return lost;
}
