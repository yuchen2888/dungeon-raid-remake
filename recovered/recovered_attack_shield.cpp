#include "recovered_attack_shield.hpp"
#include <cmath>
#include <cstring>
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
namespace {
void flare_event(const AttackFlareHooks* h,AttackFlareEventKind kind,int tile,int a=0,int b=0,int c=0) {
    if(h && h->event) { const AttackFlareEvent e{kind,tile,a,b,c};h->event(h->context,&e); }
}
int tile_attack(const PathState* p,int i) {
    const auto& c=p->combat[i];
    const CharacterClassState character{p->match->stroke->selection.character.race};
    const GameContext game{&character};const TileState tile{c.attack,c.poison,&game};
    return dr_get_attack(&tile);
}
}
extern "C" void dr_initialise_flares(AttackDamageState* s,PathState* p,std::int32_t* flare_count,const AttackFlareHooks* h) {
    *flare_count=0;s->incoming_damage=0;s->enemy9_damage=0;
    const auto& board=p->match->stroke->selection;
    auto add=[](std::int32_t& total,int value) {
        total=static_cast<std::int32_t>(static_cast<std::uint32_t>(total)+static_cast<std::uint32_t>(value));
    };
    for(int y=0;y<6;++y)for(int x=0;x<6;++x) {
        const int i=y*6+x;const auto& rule=board.tiles[i].rule;
        if(rule.type!=1 || p->combat[i].attack_flag || rule.flag_255)continue;
        add(s->incoming_damage,tile_attack(p,i));
        if(rule.enemy_type==9)add(s->enemy9_damage,tile_attack(p,i));
        if(rule.enemy_type==32 && rule.enemy_state!=0)continue;
        flare_event(h,AttackFlareEventKind::Flare,i,0,0,-1);
        flare_event(h,AttackFlareEventKind::Flare,i,1,0,-1);
    }
}
extern "C" void dr_process_attack_fade_in(AttackDamageState* s,PathState* p,std::int32_t* flare_count,
    std::uint8_t* overlay_alpha,float dt,const AttackFlareHooks* h) {
    if(s->phase!=1)return;
    // Literal 0x44480000 (800); VMUL then VADD, each rounded to float.
    const float step=dt*800.0f;
    int alpha=static_cast<int>(static_cast<float>(*overlay_alpha)+step);
    if(alpha>200) {
        flare_event(h,AttackFlareEventKind::Sound,-1,14);
        s->phase=2;p->match->shake_progress_bd90=0;p->match->shake_scale_bd94=0x3f800000;
        dr_initialise_flares(s,p,flare_count,h);
        alpha=200;
    }
    const auto byte=static_cast<std::uint8_t>(alpha);
    *overlay_alpha=byte;
    flare_event(h,AttackFlareEventKind::SetAlpha,-1,0,byte);
    for(int i=0;i<4;++i)flare_event(h,AttackFlareEventKind::Shadow,-1,i,-1);
}
extern "C" void dr_process_attack_damage_all(PathState* p,std::int32_t amount,const AttackAllHooks* h) {
    auto emit=[h](AttackAllEventKind kind,int tile,int a=0,int b=0,int c=0,int d=0) {
        if(h && h->event) { const AttackAllEvent e{kind,tile,a,b,c,d};h->event(h->context,&e); }
    };
    if(amount<=0)return;
    auto& m=*p->match;
    for(int i=0;i<5;++i)m.matched_counts[i]=0;
    bool first=true;
    for(int x=0;x<6;++x)for(int y=0;y<6;++y) {
        const int i=y*6+x;const auto& rule=m.stroke->selection.tiles[i].rule;
        if(rule.type!=1 || p->combat[i].attack_flag)continue;
        if(first)emit(AttackAllEventKind::Sound,-1,3);
        const int enemy=rule.enemy_type;
        emit(AttackAllEventKind::Label,i,5,amount,16,0x3f800000);
        if(h->attack_skull(h->context,i,amount,false) && enemy==2)emit(AttackAllEventKind::Achievement,-1,43,0x42c80000);
        first=false;
    }
    h->move_matched_tiles(h->context);
    for(auto& c:p->combat)c.attack_flag=0;
}
extern "C" void dr_do_counterattack(PathState* p,const AttackAllHooks* h) {
    auto& m=*p->match;
    for(int i=0;i<5;++i)m.matched_counts[i]=0;
    for(int x=0;x<6;++x)for(int y=0;y<6;++y) {
        const int i=y*6+x;
        if(m.stroke->selection.tiles[i].rule.type!=1 || p->combat[i].attack_flag)continue;
        if(h->event) {
            const AttackAllEvent e{AttackAllEventKind::Label,i,2,tile_attack(p,i),11,0x3f000000};
            h->event(h->context,&e);
        }
        // The original passes the (zero) attack_flag byte as the effects flag.
        h->attack_skull(h->context,i,tile_attack(p,i),false);
    }
    h->move_matched_tiles(h->context);
    for(auto& c:p->combat)c.attack_flag=0;
}
namespace {
float as_float(std::uint32_t bits) {float f;std::memcpy(&f,&bits,4);return f;}
std::uint32_t as_bits(float f) {std::uint32_t u;std::memcpy(&u,&f,4);return u;}
// VCVT.U32.F32: round toward zero, saturating; NaN and negatives give 0.
std::uint32_t to_u32(float f) {
    if(!(f>0.0f))return 0;
    if(f>=4294967296.0f)return 0xffffffffu;
    return static_cast<std::uint32_t>(f);
}
}
extern "C" bool dr_process_attack_flares(AttackDamageState* s,AttackAnimation* a,float dt,const AttackAnimHooks* h) {
    auto emit=[h](AttackAnimEventKind kind,int x=0,int y=0,int z=0) {
        if(h && h->event) { const AttackAnimEvent e{kind,x,y,z};h->event(h->context,&e); }
    };
    if(s->phase!=2 && s->phase!=3 && s->phase!=4)return false;
    auto& m=*s->resources->match;
    m.shake_progress_bd90=as_bits(as_float(m.shake_progress_bd90)+dt);
    const float step=dt*-4.5f;
    m.shake_scale_bd94=as_bits(as_float(m.shake_scale_bd94)+step);
    bool flares_done=false;
    if(as_float(m.shake_scale_bd94)<0.5f) {
        if(s->phase==2) {
            if(a->counterattack) {
                emit(AttackAnimEventKind::Sound,27);s->phase=3;a->label_progress=0.0f;
            } else {
                s->phase=4;a->label_progress=0.0f;
                emit(AttackAnimEventKind::LabelNumber,0,s->incoming_damage);
                emit(AttackAnimEventKind::LabelPosition,0,static_cast<int>(as_bits(0.5f)),static_cast<int>(as_bits(a->label_y)));
                a->damage_label_alpha=1.0f;
                emit(AttackAnimEventKind::LabelNumber,1,s->enemy9_damage);
                // Literal 0x3d4ccccd (0.05).
                emit(AttackAnimEventKind::LabelPosition,1,static_cast<int>(as_bits(0.5f)),static_cast<int>(as_bits(a->label_y+0.05f)));
                a->poison_label_alpha=1.0f;
            }
        }
        if(as_float(m.shake_scale_bd94)<0.0f) {m.shake_scale_bd94=0;a->flare_count=0;flares_done=true;}
    }
    for(int i=0;i<a->flare_count;++i) {
        // Literal 0x437f0000 (255).
        emit(AttackAnimEventKind::FlareAlpha,i,static_cast<std::uint8_t>(to_u32(as_float(m.shake_scale_bd94)*255.0f)));
        emit(AttackAnimEventKind::FlareScale,i,static_cast<int>(m.shake_progress_bd90));
    }
    if(s->phase==3) {
        const float step3=dt*3.0f;
        a->label_progress=a->label_progress+step3;
        if(a->label_progress>1.0f) {
            a->label_progress=1.0f;
            if(flares_done) {s->phase=7;if(h && h->counterattack)h->counterattack(h->context);}
        }
        emit(AttackAnimEventKind::SetAlpha,2,static_cast<std::uint8_t>(to_u32(a->label_progress*255.0f)));
    }
    return flares_done;
}
extern "C" void dr_process_attack_phase4(AttackDamageState* s,AttackAnimation* a,bool flares_done,float dt,const AttackAnimHooks* h) {
    auto emit=[h](AttackAnimEventKind kind,int x=0,int y=0,int z=0) {
        if(h && h->event) { const AttackAnimEvent e{kind,x,y,z};h->event(h->context,&e); }
    };
    if(s->phase!=4)return;
    const float step=dt*8.0f;
    a->label_progress=a->label_progress+step;
    if(a->label_progress>1.0f) {
        a->label_progress=1.0f;
        if(flares_done) {
            auto& m=*s->resources->match;
            float low,high;
            if(m.preview->armour_current>0) {
                s->phase=5;a->bd60=as_float(0x3fa53333);low=as_float(0x3ecccccd);a->bd5c=0.5f;a->bd78=as_float(0x3f4ccccd);high=1.0f;
            } else {
                s->phase=6;a->bd60=as_float(0x3fa5999a);low=as_float(0x3ecccccd);a->bd5c=as_float(0x3f5ccccd);
                high=as_float(0x3f4ccccd);a->bd78=as_float(0x3e4ccccd);
            }
            a->bd7c=dr_random_float(&m.random,low,high,0);
            emit(AttackAnimEventKind::Random,static_cast<int>(as_bits(low)),static_cast<int>(as_bits(high)),0);
            a->bd68=a->bd34;a->bd64=a->bd30;a->bd6c=0.0f;a->bd70=1.0f;
            emit(AttackAnimEventKind::HelpMenu,static_cast<int>(as_bits(a->bd30)),static_cast<int>(as_bits(a->bd34)),16);
        }
    }
    a->bd74=a->damage_label_alpha;
    const auto alpha=static_cast<std::uint8_t>(to_u32(a->label_progress*255.0f));
    emit(AttackAnimEventKind::SetAlpha,1,alpha);
    emit(AttackAnimEventKind::LabelAlpha,0,alpha);
    emit(AttackAnimEventKind::LabelAlpha,1,alpha);
}
extern "C" bool dr_process_attack_label_motion(AttackDamageState* s,AttackAnimation* a,float dt,const AttackAnimHooks* h) {
    auto emit=[h](AttackAnimEventKind kind,int x=0,int y=0,int z=0) {
        if(h && h->event) { const AttackAnimEvent e{kind,x,y,z};h->event(h->context,&e); }
    };
    if(s->phase!=5 && s->phase!=6)return false;
    const float accel=dt*20.0f;
    a->bd70=a->bd70+accel;
    const float advance=a->bd70*dt;
    a->bd6c=a->bd6c+advance;
    bool completed=false;
    if(a->bd6c>1.0f) {a->bd6c=1.0f;completed=true;}
    // Interpolate(GLfloat2 const&, GLfloat2 const&, float): (1-t)*from + t*to, per lane.
    const float t=a->bd6c,u=1.0f-t;
    const float ay=u*a->bd68,by=t*a->bd60,ax=u*a->bd64,bx=t*a->bd5c;
    float x=ax+bx,y=ay+by;
    const float d=0.5f-a->bd6c;
    const float square=d*d;   // Sqr(float)
    const float lift=(0.25f-square)*a->bd7c;
    if(s->phase==5)x=x-lift; else y=y-lift;
    emit(AttackAnimEventKind::LabelPosition,0,static_cast<int>(as_bits(x)),static_cast<int>(as_bits(y)));
    // Literal 0x40a00000 (5); platform powf.
    const float p=::powf(a->bd6c,5.0f);
    // Interpolate(float a, float b, float t) = a*t + (1-t)*b.
    const float from=a->bd78*p,rest=1.0f-p;
    a->damage_label_alpha=from+rest*a->bd74;
    // Literal 0x3d4ccccd (0.05).
    emit(AttackAnimEventKind::LabelPosition,1,static_cast<int>(as_bits(x)),static_cast<int>(as_bits(y+0.05f)));
    a->poison_label_alpha=a->damage_label_alpha;
    return completed;
}
extern "C" void dr_process_attack_phase5_done(AttackDamageState* s,AttackAnimation* a,const AttackAnimHooks* h) {
    auto emit=[h](AttackAnimEventKind kind,int x=0,int y=0,int z=0) {
        if(h && h->event) { const AttackAnimEvent e{kind,x,y,z};h->event(h->context,&e); }
    };
    if(s->phase!=5)return;
    auto& m=*s->resources->match;
    s->phase=6;
    a->bd60=as_float(0x3fa5999a);a->bd5c=as_float(0x3f5ccccd);
    a->bd68=a->bd34;a->bd64=a->bd30;a->bd6c=0.0f;
    a->bd74=a->damage_label_alpha;a->bd70=1.0f;a->bd78=as_float(0x3e4ccccd);
    const float low=as_float(0x3ecccccd),high=as_float(0x3f4ccccd);
    a->bd7c=dr_random_float(&m.random,low,high,0);
    emit(AttackAnimEventKind::Random,static_cast<int>(as_bits(low)),static_cast<int>(as_bits(high)),0);
    const std::int32_t armour=m.preview->armour_current;
    const std::int32_t shown=armour>=s->incoming_damage?s->incoming_damage:armour;
    emit(AttackAnimEventKind::AddLabel,2,static_cast<int>(0u-static_cast<std::uint32_t>(shown)),12);
    emit(AttackAnimEventKind::HelpMenu,static_cast<int>(as_bits(a->bd30)),static_cast<int>(as_bits(a->bd34)),17);
}
extern "C" void dr_process_attack(AttackDamageState* s,PathState* p,AttackAnimation* a,std::uint8_t* overlay_alpha,
    float dt,const AttackProcessInputs* in,const AttackProcessHooks* h) {
    dr_process_attack_fade_in(s,p,&a->flare_count,overlay_alpha,dt,h->flare);       // [0x14126,0x141c6)
    const bool flares_done=dr_process_attack_flares(s,a,dt,h->anim);                 // [0x141c6,0x143ca)
    dr_process_attack_phase4(s,a,flares_done,dt,h->anim);                            // [0x143ca,0x1457c)
    if(dr_process_attack_label_motion(s,a,dt,h->anim)) {                             // [0x1457c,0x146ce)
        if(s->phase==5) {
            dr_process_attack_phase5_done(s,a,h->anim);                              // [0x146ce,0x14790)
            const std::int32_t absorbed=dr_process_attack_armour_absorb(s,h->absorb);// [0x14790,0x147e4)
            dr_process_attack_shield_wear(s->resources,absorbed,in->armour_loss_chance,h->shield); // [0x147e4,0x1487e)
            dr_process_attack_weaken(p,in->weaken,h->weaken);                        // [0x1487e,0x14938)
            dr_process_attack_damage_all(p,in->damage_all,h->all);                   // [0x14938,0x14a14)
        } else dr_process_attack_health_damage(s,h->health);                         // [0x14a14,0x14ae4)
    }
    dr_process_attack_fade(s,overlay_alpha,dt,a->counterattack!=0,h->fade);         // [0x14ae4,0x14b56)
}
