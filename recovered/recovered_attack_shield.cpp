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
extern "C" std::int32_t dr_process_attack_armour_absorb(AttackDamageState* s,const AttackAbsorbHooks* h) {
    auto emit=[h](AttackAbsorbEventKind kind,int a,int b=0,int c=0,int d=0) {
        if(h && h->event) { const AttackAbsorbEvent e{kind,a,b,c,d};h->event(h->context,&e); }
    };
    const std::int32_t damage=s->incoming_damage,armour=s->resources->match->preview->armour_current;
    const std::int32_t absorbed=armour>=damage?damage:armour;
    // Original SUBS wraps; keep that in the unsigned domain.
    s->incoming_damage=static_cast<std::int32_t>(static_cast<std::uint32_t>(damage)-static_cast<std::uint32_t>(armour));
    if(s->incoming_damage>0)emit(AttackAbsorbEventKind::DamageNumber,s->incoming_damage);
    else {
        s->phase=7;
        if(s->enemy9_damage>0) {
            emit(AttackAbsorbEventKind::Label,7,s->enemy9_damage,15,0x3f000000);
            s->enemy9_damage=0;
        }
    }
    return absorbed;
}
extern "C" void dr_process_attack_health_damage(AttackDamageState* s,const AttackHealthHooks* h) {
    auto emit=[h](AttackHealthEventKind kind,int a=0,int b=0,int c=0,int d=0) {
        if(h && h->event) { const AttackHealthEvent e{kind,a,b,c,d};h->event(h->context,&e); }
    };
    auto& r=*s->resources;
    emit(AttackHealthEventKind::Sound,17);
    emit(AttackHealthEventKind::Label,2,s->incoming_damage,11,0x3f000000);
    if(s->enemy9_damage>=r.poison)r.poison=s->enemy9_damage;
    emit(AttackHealthEventKind::Poison,r.poison);
    if(s->enemy9_damage>0) {
        emit(AttackHealthEventKind::Label,7,s->enemy9_damage,15,0x3f000000);
        s->enemy9_damage=0;
    }
    emit(AttackHealthEventKind::Vampires);
    emit(AttackHealthEventKind::HelpHealth);
    s->phase=7;
    // Original RSB wraps; only a signed negative result is floored.
    const auto health=static_cast<std::int32_t>(static_cast<std::uint32_t>(r.health)-static_cast<std::uint32_t>(s->incoming_damage));
    r.health=health<0?0:health;
    if(r.health!=r.ui_health) {
        r.ui_health=r.health;emit(AttackHealthEventKind::HealthBar,r.health);
    }
}
extern "C" void dr_process_attack_weaken(PathState* p,std::int32_t weaken,const AttackWeakenHooks* h) {
    auto emit=[h](AttackWeakenEventKind kind,int tile,int a=0,int b=0,int c=0,int d=0) {
        if(h && h->event) { const AttackWeakenEvent e{kind,tile,a,b,c,d};h->event(h->context,&e); }
    };
    if(weaken<=0)return;
    const auto& board=p->match->stroke->selection;
    bool first=true;
    for(int x=0;x<6;++x)for(int y=0;y<6;++y) {
        const int i=y*6+x;auto& c=p->combat[i];
        if(board.tiles[i].rule.type!=1 || c.attack_flag || c.attack<=1)continue;
        if(first)emit(AttackWeakenEventKind::Sound,-1,30);
        // Original RSB wraps; only a signed result below 1 is raised to 1.
        const auto reduced=static_cast<std::int32_t>(static_cast<std::uint32_t>(c.attack)-static_cast<std::uint32_t>(weaken));
        c.attack=reduced<1?1:reduced;
        emit(AttackWeakenEventKind::Text,i,1,0,0);
        emit(AttackWeakenEventKind::Label,i,4,weaken,14,0x3f800000);
        emit(AttackWeakenEventKind::Particles,i,3);
        first=false;
    }
}
extern "C" void dr_process_attack_fade(AttackDamageState* s,std::uint8_t* overlay_alpha,
    float dt,bool alternate_quad,const AttackFadeHooks* h) {
    if(s->phase!=7)return;
    // Literal 0xc4610000 (-900); VMUL then VADD, each rounded to float (no fusion).
    const float step=dt*-900.0f;
    const float value=static_cast<float>(*overlay_alpha)+step;
    int alpha=static_cast<int>(value);
    if(alpha<0) {alpha=0;s->phase=8;}
    const auto byte=static_cast<std::uint8_t>(alpha);
    *overlay_alpha=byte;
    auto emit=[h](int quad,int value) {
        if(h && h->event) { const AttackFadeEvent e{AttackFadeEventKind::SetAlpha,quad,value};h->event(h->context,&e); }
    };
    emit(0,byte);emit(alternate_quad?2:1,byte);
}
