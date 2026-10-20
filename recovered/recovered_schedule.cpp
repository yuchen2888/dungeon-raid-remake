#include "recovered_schedule.hpp"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <vector>
using namespace dungeonraid;
extern "C" std::int32_t dr_count_attackers(const PathState* p) {
    const auto& board=p->match->stroke->selection;
    std::int32_t n=0;
    for(int i=0;i<36;++i) {
        const auto& t=board.tiles[i];const auto& c=p->combat[i];
        if(t.rule.type!=1 || c.attack_flag || t.rule.flag_255)continue;
        const CharacterClassState character{board.character.race};
        const GameContext game{&character};const TileState view{c.attack,c.poison,&game};
        if(dr_get_attack(&view)>0)++n;
    }
    return n;
}
namespace {
bool have_perk(const MatchState& m,std::int32_t perk) {
    if(perk==255)return false;
    for(auto p:m.perks)if(p==perk)return true;
    return false;
}
}
extern "C" InputGate dr_input_gate(PathState* p,AttackDamageState* d,RuneState* rune,const InputGateInputs* in,const ScheduleHooks* h) {
    if(in->falling_count)return InputGate::Blocked;
    if(in->tokens_pending>0 || in->flare_count>0)return InputGate::Blocked;
    bool end_turn=false;
    if(!p->input_ready && d->phase==0) {
        const bool skip=p->turn<=4 && have_perk(*p->match,0);
        if(!skip && dr_count_attackers(p)>0) {d->phase=1;return InputGate::AttackStarted;}
        d->phase=8;end_turn=true;
    } else {
        if(static_cast<std::uint32_t>(d->phase-1)<=6u)return InputGate::Blocked;
        end_turn=d->phase==8;
    }
    if(end_turn)h->end_of_turn(h->context);
    d->phase=0;p->input_ready=1;
    if(!in->touch_phase || in->input_target>=0)return InputGate::Idle;
    rune->highlight_count_164a0=0;
    return InputGate::Dispatch;
}
namespace {
std::int32_t bits(float value) {std::int32_t out;std::memcpy(&out,&value,sizeof out);return out;}
void emit(const ReleaseHooks* h,ReleaseEventKind kind,std::int32_t tile,std::int32_t a=0,std::int32_t b=0,
          std::int32_t c=0,std::int32_t d=0,Point at={0,0}) {
    const ReleaseEvent e{kind,tile,a,b,c,d,at.x,at.y};h->event(h->context,&e);
}
void fly(LabelFlight& flight,RandomState& random,Point label) {
    flight.arc=dr_random_float(&random,0.4f,0.8f,0);
    flight.start=label;flight.progress=0;flight.speed=1.0f;
}
}
extern "C" void dr_add_revenge_health(PathState* p,const ReleaseHooks* h) {
    auto& board=p->match->stroke->selection;
    for(int x=0;x<6;++x)for(int y=0;y<6;++y) {
        const int i=y*6+x;const auto& t=board.tiles[i];
        if(t.rule.matched || t.rule.type!=1 || t.rule.enemy_type!=21)continue;
        const auto kills=p->battle.kill_count_15548;
        p->combat[i].attack+=kills;
        emit(h,ReleaseEventKind::Text,i,1,0,0);
        emit(h,ReleaseEventKind::Label,i,27,kills,35,bits(1.0f),t.geometry.center);
        emit(h,ReleaseEventKind::Sound,-1,14);
    }
}
extern "C" void dr_release_clear(SelectionState* s,const ReleaseHooks* h) {
    s->path_length=0;
    for(auto& value:s->fake)value=0;
    s->current_damage=0;
    if(!s->flame_label_moving)s->current_flame_damage=0;
    if(!s->spike_label_moving)s->current_spike_damage=0;
    emit(h,ReleaseEventKind::CrossVisibility,-1);
}
extern "C" ReleaseRoute dr_release_path(ReleaseState* r,const ReleaseInputs* in,const ReleaseHooks* h) {
    PathState& p=*r->path;MatchState& m=*p.match;SelectionState& s=m.stroke->selection;
    const ReleaseRoute route=dr_release_route(&s);
    if(route!=ReleaseRoute::MatchPath) {
        s.current_leech=0;
        if(route==ReleaseRoute::ClassScroll)return route;
        dr_release_clear(&s,h);return route;
    }
    r->finish->flag_1554c=1;
    bool enemy=false,sword=false;
    for(std::size_t i=0;i<s.path_length;++i) {
        const auto type=s.tiles[s.path[i]].rule.type;
        if(type==1)enemy=true;else if(type==4)sword=true;
    }
    if(enemy)emit(h,ReleaseEventKind::Sound,-1,27);
    else if(sword) {
        emit(h,ReleaseEventKind::Sound,-1,26);
        if(r->finish->help_flags_102d0&0x10)
            emit(h,ReleaseEventKind::Help,s.path[0],4,0,0,bits(0.0828125f),s.tiles[s.path[0]].geometry.center);
    }
    auto& battle=p.battle;auto& g=*r->generation;
    battle.kill_count_15548=0;g.generated_enemies=0;battle.killed_attack_164ac=0;g.generated_count=0;
    emit(h,ReleaseEventKind::MatchTiles,-1);
    if(g.generated_count>9 && g.generated_count==g.generated_enemies)
        emit(h,ReleaseEventKind::Achievement,-1,74,bits(100.0f));
    if(s.current_flame_damage>0) {fly(r->flights->flame,m.random,in->flame_label);s.flame_label_moving=1;}
    if(s.current_spike_damage>0) {fly(r->flights->spike,m.random,in->spike_label);s.spike_label_moving=1;}
    if(battle.kill_count_15548>0) {
        dr_add_revenge_health(&p,h);
        if(battle.kill_count_15548>14 && s.character.race==6) {
            emit(h,ReleaseEventKind::IncreaseStat,-1,11);
            emit(h,ReleaseEventKind::UpdateStats,-1);
            emit(h,ReleaseEventKind::Label,-1,34,0,42,bits(1.0f),Point{0.5f,1.290625f});
            emit(h,ReleaseEventKind::Achievement,-1,52,bits(10.0f));
            if(r->flags->b165b8[0])emit(h,ReleaseEventKind::Achievement,-1,57,bits(100.0f));
        }
    }
    if(r->flags->prev_164a7 && battle.killed_attack_164ac>0) {
        auto& res=*r->resources;
        res.health=std::min(res.health+battle.killed_attack_164ac,res.health_max+res.health_bonus);
        emit(h,ReleaseEventKind::Sound,-1,4);
        if(res.health!=res.ui_health) {res.ui_health=res.health;emit(h,ReleaseEventKind::HealthBar,-1,res.health);}
        emit(h,ReleaseEventKind::Label,-1,29,battle.killed_attack_164ac,37,bits(1.0f),in->health_target);
    }
    if(!s.skull_counted)s.current_leech=0;
    else fly(r->flights->leech,m.random,in->leech_label);
    dr_release_clear(&s,h);
    return route;
}
namespace {
void level_achievement(void* context,std::int32_t id,float value) {
    emit(static_cast<const ReleaseHooks*>(context),ReleaseEventKind::Achievement,-1,id,bits(value));
}
void level_up(ClassScrollState* sc,std::size_t index,const ReleaseHooks* h) {
    const ProgressionHooks ph{const_cast<ReleaseHooks*>(h),level_achievement};
    dr_class_level_up(sc->classes,10,index,sc->difficulty,&ph);
}
}
extern "C" bool dr_release_class_scroll(PathState* p,ClassScrollState* sc,const ReleaseHooks* h) {
    MatchState& m=*p->match;SelectionState& s=m.stroke->selection;
    ClassProfile& active=sc->classes[sc->current];
    bool unlock=true;
    if(active.level<=9 && active.class_type!=0)unlock=dr_random_int(&m.random,0,1,5)==0;
    bool done=false;
    if(unlock) {
        std::vector<std::int32_t> locked;
        for(std::int32_t i=0;i<=9;++i)if(!sc->classes[i].level)locked.push_back(i);
        if(!locked.empty()) {
            const std::int32_t chosen=locked[dr_random_int(&m.random,0,static_cast<std::int32_t>(locked.size())-1,5)];
            level_up(sc,chosen,h);
            emit(h,ReleaseEventKind::UnlockMenu,-1,chosen,1);
            done=true;
        }
    }
    if(!done && active.level<=9) {
        level_up(sc,sc->current,h);
        emit(h,ReleaseEventKind::UnlockMenu,-1,active.class_type,active.level);
    }
    m.class_level=active.level;
    for(int i=1;i<=9;++i)m.unlocked[i-1]=sc->classes[i].level;
    emit(h,ReleaseEventKind::MatchTile,s.path[0],7);
    emit(h,ReleaseEventKind::MoveMatchedTiles,-1);
    if(h->check_end_game(h->context))return true;
    emit(h,ReleaseEventKind::SerialiseState,-1);
    emit(h,ReleaseEventKind::SerialiseClasses,-1);
    dr_release_clear(&s,h);
    return false;
}
namespace {
void emit(const NewGameHooks* h,NewGameEventKind kind,std::int32_t tile,std::int32_t a=0,std::int32_t b=0) {
    const NewGameEvent e{kind,tile,a,b};h->event(h->context,&e);
}
void new_game_achievement(void* context,std::int32_t id,float value) {
    emit(static_cast<const NewGameHooks*>(context),NewGameEventKind::Achievement,-1,id,bits(value));
}
}
extern "C" void dr_calculate_tile_positions(StrokeState* stroke,const NewGameHooks* h) {
    SelectionState& s=stroke->selection;
    s.geometry.vertical_offset=stroke->record_14aed?0.015625f:0.0f;
    const float pitch=s.geometry.pitch,half=pitch*0.5f;
    for(int y=0;y<6;++y)for(int x=0;x<6;++x) {
        const int i=y*6+x;auto& t=s.tiles[i];
        const float rx=(static_cast<float>(x)+0.5f)*pitch+0.003125f;
        const float ry=(static_cast<float>(y)+0.5f)*pitch+0.246875f+s.geometry.vertical_offset;
        t.resting_position=Point{rx,ry};
        t.size=pitch;t.geometry.size=half;
        emit(h,NewGameEventKind::SetSize,i,bits(pitch),bits(pitch));
        t.rule.x=x;t.rule.y=y;t.geometry.center=t.resting_position;
        s.geometry.tiles[i]=t.geometry;
        emit(h,NewGameEventKind::Labels,i);
    }
}
extern "C" void dr_init_new_game(NewGameState* n,std::uint32_t time,const NewGameHooks* h) {
    MatchState& m=*n->match;StrokeState& stroke=*m.stroke;SelectionState& s=stroke.selection;
    ResourceState& r=*n->resources;ResourcePreviewState& pv=*n->preview;PathState& p=*n->path;
    GenerationState& g=*n->generation;TurnFlags& f=*n->flags;NewGameExtra& x=*n->extra;
    dr_random_set_seed(&m.random,time,6);dr_random_flush(&m.random);
    dr_calculate_tile_positions(&stroke,h);
    const ProgressionHooks ph{const_cast<NewGameHooks*>(h),new_game_achievement};
    for(std::size_t i=0;i<10;++i)dr_class_unlock_achievements(n->classes,10,i,n->difficulty,&ph);
    n->end->victory=0;
    x.tokens_type0_165d8=0;p.total=0;pv.total_165d0=0;
    TokenQueueCounters counters=*dr_token_queue_counters(n->tokens);
    counters.bonus_total_165d4=0;
    p.crossing_samples=p.crossing_average=p.crossing_best=0;
    x.bonus_type0_165ec=0;
    for(auto& v:counters.normal)v=0;
    for(auto& v:counters.bonus)v=0;
    x.tokens_type4_165e8=x.bonus_type4_165fc=0;
    s.current_damage=0;s.current_leech=0;p.turn=0;s.current_flame_damage=0;s.current_spike_damage=0;
    m.spawn_count_1555c=0;p.battle.kill_count_165b4=0;r.poison=0;x.value_164d4=0;
    g.promotion_enabled=1;
    if(stroke.record_14aed && stroke.mode_14ae8==0)g.time_to_promotion=200;
    else g.time_to_promotion=dr_have_flaw(&s.character,8)?49:50;
    f.b15561=f.b15562=0;g.inhibit_force_coins=0;
    n->rune->enabled_16491=0;f.arrow_hold_16492=0;
    r.guard_164a4=0;n->end->revive_second=0;r.guard_164a6=0;f.prev_164a7=0;f.next_164a8=0;
    s.spiky_enemy_attacked=0;s.flame_label_moving=0;s.spike_label_moving=0;
    g.filter_enabled=1;
    *n->counterattack=0;p.battle.grant_coin_on_attack=0;f.next_coin_bfbc=0;
    g.one_health=0;g.force_coins=0;n->finish->next_one_health_14af7=0;n->finish->next_force_coins_14af8=0;
    s.double_damage=0;pv.double_upgrade=pv.double_healing=pv.double_gold=0;
    for(auto& v:f.next_be78)v=0;
    emit(h,NewGameEventKind::TurnLabel,-1);
    for(int y=0;y<6;++y)for(int col=0;col<6;++col) {
        const std::uint32_t i=static_cast<std::uint32_t>(y*6+col);
        dr_position_tile(g.refill,i,col,y,false);
        dr_randomise_tile(&g,i,h->generation);
    }
    g.filter_enabled=0;g.filter_swords=0;
    for(auto& v:x.base_bde8)v=1;
    s.base_damage=3;
    if(have_perk(m,4))++s.base_damage;
    r.health_max=40;
    if(stroke.record_14aed && stroke.mode_14ae8==1)r.health_max=100;
    if(have_perk(m,9))r.health_max+=10;
    if(dr_have_flaw(&s.character,1))r.health_max-=10;
    PlayerStats& pl=*n->player;
    if(s.base_damage!=pl.ui_skull_59c8) {pl.ui_skull_59c8=s.base_damage;emit(h,NewGameEventKind::SkullValue,-1);}
    if(r.health_max!=pl.ui_health_ceiling_5998) {pl.ui_health_ceiling_5998=r.health_max;emit(h,NewGameEventKind::HealthBar,-1,r.ui_health);}
    r.health=r.health_max;
    if(r.health!=r.ui_health) {r.ui_health=r.health;emit(h,NewGameEventKind::HealthBar,-1,r.health);}
    r.xp=0;if(r.ui_xp) {r.ui_xp=0;emit(h,NewGameEventKind::XPBar,-1,0);}
    r.up=0;if(r.ui_up) {r.ui_up=0;emit(h,NewGameEventKind::UPBar,-1,0);}
    r.gold=0;if(r.ui_gold) {r.ui_gold=0;emit(h,NewGameEventKind::GoldBar,-1,0);}
    pv.shield_value=1;pv.healing_value=1;
    for(auto& v:m.bonus_chance)v=20;   // Game+0xbe20/0xbe28/0xbe18/0xbe30
    if(have_perk(m,7))m.bonus_chance[2]+=10;
    if(dr_have_flaw(&s.character,4))m.bonus_chance[3]-=10;
    pv.armour_current=0;pv.armour_max=0;
    for(int i=0;i<5;++i)emit(h,NewGameEventKind::Item,-1,i,i);
    for(auto& skill:x.skill_ff)for(auto& v:skill)v=0xff;
    r.health_bonus=0;pl.skill_cooldown_be64=0;
    emit(h,NewGameEventKind::UpdateStats,-1);
    r.xp_fraction=r.gold_fraction=r.up_fraction=0;
    n->attack->phase=0;p.input_ready=1;n->shatter->active=0;r.skill_count=0;
    counters.pending=0;dr_token_queue_restore(n->tokens,&counters);
    x.particles_b53c=x.labels_b54c=0;
    r.level=1;r.total_xp=r.total_gold=r.total_up=0;
    n->finish->flag_1554c=0;
    for(auto& v:x.label_active)v=0;
    emit(h,NewGameEventKind::InterfaceReset,-1);
}
namespace {
void emit(const LabelHooks* h,LabelEventKind kind,std::int32_t label,std::int32_t a=0,std::int32_t b=0,Point at={0,0}) {
    const LabelEvent e{kind,label,a,b,at.x,at.y};h->event(h->context,&e);
}
// Interpolate(GLfloat2, GLfloat2, t) 0x1be38 and Interpolate(float, float, t) 0x1b800 (note the
// opposite weighting of the float overload).
// The original's "0.06" label offset literal is 0x3d75c290, one ulp above 0.06f.
float label_gap() {const std::uint32_t raw=0x3d75c290u;float out;std::memcpy(&out,&raw,sizeof out);return out;}
Point interpolate(Point a,Point b,float t) {const float u=1.0f-t;return Point{u*a.x+t*b.x,u*a.y+t*b.y};}
float interpolate(float a,float b,float t) {return a*t+(1.0f-t)*b;}
// One frame of a released label's flight; true on arrival.
bool fly(LabelFlight& f,int label,float dt,const LabelHooks* h) {
    f.speed=f.speed+dt*10.0f;
    f.progress=f.progress+f.speed*dt;
    if(f.progress>1.0f)f.progress=1.0f;
    const Point at=interpolate(f.start,Point{0.8625f,1.29375f},f.progress);
    const float d=f.progress-0.5f;
    emit(h,LabelEventKind::Position,label,0,0,Point{at.x,at.y-(0.25f-d*d)*f.arc});
    emit(h,LabelEventKind::Scale,label,bits(interpolate(0.1f,1.0f,std::pow(f.progress,5.0f))));
    return !(f.progress<1.0f);
}
void show(std::uint8_t active,int label,std::int32_t type,std::int32_t value,Point at,const LabelHooks* h) {
    if(!active)emit(h,LabelEventKind::Initialise,label,type,value,at);
    else {emit(h,LabelEventKind::Position,label,0,0,at);emit(h,LabelEventKind::Number,label,value);}
}
void health_bar(ResourceState& r,const LabelHooks* h) {
    if(r.health!=r.ui_health) {r.ui_health=r.health;emit(h,LabelEventKind::HealthBar,-1,r.health);}
}
// Flame / spike arrival: the label's damage hits the player.
bool hurt(ResourceState& r,std::int32_t& value,std::uint8_t& moving,std::int32_t achievement,std::int32_t sound,const LabelHooks* h) {
    r.health=r.health-value;
    if(r.health<0) {r.health=0;emit(h,LabelEventKind::Achievement,-1,achievement,bits(100.0f));}
    health_bar(r,h);
    value=0;moving=0;
    emit(h,LabelEventKind::Sound,-1,sound);
    return h->check_end_game(h->context);
}
}
extern "C" bool dr_process_damage_labels(DamageLabelState* d,float dt,Point touch,const LabelHooks* h) {
    SelectionState& s=*d->selection;ResourceState& r=*d->resources;ReleaseFlights& f=*d->flights;
    const std::uint8_t* active=d->active;
    // leech
    if(active[0] && s.current_leech==0)emit(h,LabelEventKind::Process,0,bits(dt));
    else if(s.current_leech>0) {
        if(s.current_damage>0) {
            show(active[0],0,8,s.current_leech,Point{touch.x,touch.y-0.1f},h);
            emit(h,LabelEventKind::Alpha,0,s.skull_counted?0xff:0x80);
        } else if(fly(f.leech,0,dt,h)) {
            r.health=r.health+s.current_leech;
            const std::int32_t ceiling=r.health_max+r.health_bonus;
            if(r.health>ceiling)r.health=ceiling;
            health_bar(r,h);
            s.current_leech=0;
            emit(h,LabelEventKind::Sound,-1,4);
        }
    }
    // flame
    if(active[1] && s.current_flame_damage==0)emit(h,LabelEventKind::Process,1,bits(dt));
    else if(s.current_flame_damage>0) {
        if(!s.flame_label_moving) {
            const float offset=s.current_leech>0?label_gap():0.1f;
            show(active[1],1,9,s.current_flame_damage,Point{touch.x,touch.y-offset},h);
        } else if(fly(f.flame,1,dt,h) && hurt(r,s.current_flame_damage,s.flame_label_moving,35,17,h))return true;
    }
    // spike
    if(active[2] && s.current_spike_damage==0)emit(h,LabelEventKind::Process,2,bits(dt));
    else if(s.current_spike_damage>0) {
        if(!s.spike_label_moving) {
            float offset=s.current_leech>0?label_gap():0.1f;
            if(s.current_flame_damage>0)offset=offset-0.04f;
            show(active[2],2,10,s.current_spike_damage,Point{touch.x,touch.y-offset},h);
        } else if(fly(f.spike,2,dt,h) && hurt(r,s.current_spike_damage,s.spike_label_moving,34,25,h))return true;
    }
    return false;
}
namespace {
void emit(const BoardEffectHooks* h,BoardEffectEventKind kind,std::int32_t tile,std::int32_t a=0,std::int32_t b=0,std::int32_t c=0,Point at={0,0}) {
    const BoardEffectEvent e{kind,tile,a,b,c,at.x,at.y};h->event(h->context,&e);
}
float from_bits(std::uint32_t raw) {float out;std::memcpy(&out,&raw,sizeof out);return out;}
std::uint32_t to_bits(float value) {std::uint32_t out;std::memcpy(&out,&value,sizeof out);return out;}
// Tile::ProcessEffects 0x3dcfc
void tile_effects(PathState& p,GenerationState& g,int i,float dt,const BoardEffectHooks* h) {
    if(g.tiles[i].flag_224)emit(h,BoardEffectEventKind::Spin,i,bits(dt));
    PoisonState& poison=p.combat[i].poison;
    if(!poison.effect_active && !poison.effect_clearing)return;
    float progress=from_bits(poison.effect_progress_bits)+dt*3.0f;
    if(progress>=1.0f)progress=1.0f;
    poison.effect_progress_bits=to_bits(progress);
    const bool clearing=poison.effect_clearing;
    const auto channel=[&](float tinted) {
        return static_cast<std::int32_t>(clearing?interpolate(255.0f,tinted,progress):interpolate(tinted,255.0f,progress));
    };
    emit(h,BoardEffectEventKind::Colour,i,channel(169.0f),channel(76.0f),channel(202.0f));
    if(progress>=1.0f) {
        poison.effect_active=0;poison.effect_clearing=0;
        emit(h,BoardEffectEventKind::Text,i,1,0,0);
    }
}
}
extern "C" void dr_initialise_shield_shatter(ShieldShatterState* s,const BoardEffectHooks* h) {
    emit(h,BoardEffectEventKind::ShatterInitialise,-1);
    s->progress=0;s->active=1;
}
extern "C" void dr_process_board_effects(BoardEffectsState* b,float dt,const BoardEffectHooks* h) {
    PathState& p=*b->path;MatchState& m=*p.match;const SelectionState& s=m.stroke->selection;
    if(b->finish->help_flags_102d0&1) {
        const std::int32_t a=dr_random_int(&m.random,0,5,0);
        const std::int32_t c=dr_random_int(&m.random,0,5,0);
        emit(h,BoardEffectEventKind::Help,a*6+c,0,0,0,s.tiles[a*6+c].resting_position);
    }
    ShieldShatterState& shatter=*b->shatter;
    if(shatter.active) {
        shatter.progress=shatter.progress+dt*2.0f;
        if(shatter.progress>1.0f)shatter.active=0;
        else {emit(h,BoardEffectEventKind::ShieldChunk,-1,0);emit(h,BoardEffectEventKind::ShieldChunk,-1,1);}
    }
    for(int x=0;x<6;++x)for(int y=0;y<6;++y)tile_effects(p,*b->generation,y*6+x,dt,h);
}
namespace {
void emit(const FrameHooks* h,FrameEventKind kind,std::int32_t a=0,std::int32_t b=0,std::int32_t c=0,Point at={0,0}) {
    const FrameEvent e{kind,a,b,c,at.x,at.y};h->event(h->context,&e);
}
}
extern "C" void dr_reset_round_counters(FrameState* f,std::uint32_t falling_count) {
    if(falling_count || f->path->match->stroke->selection.path_length)return;
    TokenQueueCounters counters=*dr_token_queue_counters(f->tokens);
    if(f->preview->total_165d0<=0 && counters.bonus_total_165d4<=0)return;
    f->preview->total_165d0=0;counters.bonus_total_165d4=0;
    f->extra->tokens_type0_165d8=f->extra->tokens_type4_165e8=0;
    f->extra->bonus_type0_165ec=f->extra->bonus_type4_165fc=0;
    for(auto& v:counters.normal)v=0;
    for(auto& v:counters.bonus)v=0;
    dr_token_queue_restore(f->tokens,&counters);
}
extern "C" void dr_process_flare_fade(FrameState* f,float dt,const FrameHooks* h) {
    AttackAnimation& a=*f->animation;MatchState& m=*f->path->match;
    if(a.flare_count<=0)return;
    const std::int32_t phase=f->attack->phase;
    if(phase==2 || phase==4 || phase==3)return;
    m.shake_progress_bd90=to_bits(from_bits(m.shake_progress_bd90)+(dt+dt));
    const float alpha=from_bits(m.shake_scale_bd94)+dt*-3.5f;
    m.shake_scale_bd94=to_bits(alpha);
    if(alpha<0.0f) {m.shake_scale_bd94=0;a.flare_count=0;}   // bpl: NaN keeps the flares
    for(std::int32_t i=0;i<a.flare_count;++i) {
        const auto value=static_cast<std::uint32_t>(from_bits(m.shake_scale_bd94)*255.0f);
        emit(h,FrameEventKind::FlareAlpha,i,static_cast<std::int32_t>(value&0xff),static_cast<std::int32_t>(m.shake_progress_bd90));
    }
}
extern "C" void dr_process_damage_label(FrameState* f,std::uint8_t label_active,float dt,const FrameHooks* h) {
    SelectionState& s=f->path->match->stroke->selection;
    if(label_active && s.current_damage==0) {emit(h,FrameEventKind::Process,bits(dt));return;}
    if(s.current_damage<=0)return;
    const Point at{f->touch->position.x,f->touch->position.y-0.14f};
    if(!label_active) {emit(h,FrameEventKind::Initialise,1,s.current_damage,0,at);return;}
    emit(h,FrameEventKind::Position,0,0,0,at);
    emit(h,FrameEventKind::Number,s.current_damage);
    if(!s.skull_counted)return;
    emit(h,FrameEventKind::Help,8,0,0,at);
    emit(h,FrameEventKind::BaseDamageHelp);
    const bool pending=(f->finish->help_flags_102d0>>10)&1;
    emit(h,FrameEventKind::WeaponDamageHelp);
    if(!pending || (f->finish->help_flags_102d0&0x400))return;
    s.current_damage=0;
    f->touch->phase=3;
    emit(h,FrameEventKind::ProcessInput);
}
namespace {
void emit(const GameFrameHooks* h,GameFrameEventKind kind,std::int32_t a=0,std::int32_t b=0) {
    const GameFrameEvent e{kind,a,b};h->event(h->context,&e);
}
void consume(TouchState& t) {if(static_cast<std::uint32_t>(t.phase-2)<=1u)t.phase=0;}
FrameRoute screen(const GameFrameHooks* h,TouchState& t,FrameRoute route) {
    consume(t);emit(h,GameFrameEventKind::Screen,static_cast<std::int32_t>(route));return route;
}
}
extern "C" FrameRoute dr_process_frame(GameFrame* f,float dt,const GameFrameHooks* h) {
    (void)dt;
    TouchState& t=*f->touch;const FrameScreens& s=*f->screens;
    emit(h,GameFrameEventKind::UpdateTime);emit(h,GameFrameEventKind::CalculateFPS);
    emit(h,GameFrameEventKind::QueuesReset);
    if(f->end->game_over_screen) {
        screen(h,t,FrameRoute::GameOver);
        if(s.game_over_state_cc1c==3) {
            const bool record=f->stroke->record_14aed;
            emit(h,GameFrameEventKind::ScoreShow,record?f->stroke->mode_14ae8:f->match->spawn_enabled_14ae0,record);
        }
        return FrameRoute::GameOver;
    }
    if(s.help_102a4)return screen(h,t,FrameRoute::Help);
    if(s.unlock_165a0)return screen(h,t,FrameRoute::Unlock);
    if(s.main_menu_c400 && !s.score_ef6c)return screen(h,t,s.name_12c09?FrameRoute::Name:FrameRoute::MainMenu);
    if(s.name_12c09)return screen(h,t,FrameRoute::Name);
    if(s.intro_c3f0)return screen(h,t,FrameRoute::Intro);
    if(s.score_ef6c)return screen(h,t,FrameRoute::Score);
    FrameRoute route=FrameRoute::Done;
    if(s.menus[0] || s.menus[1] || s.menus[2])route=FrameRoute::Menu;
    else {
        h->input(h->context);
        if(s.menus[0] || s.menus[1] || s.menus[2])return FrameRoute::MenuAfterInput;
        h->effects(h->context);
        h->falling(h->context);
        if(!h->tokens(h->context))return FrameRoute::TokensExit;
        h->pools(h->context);
        h->flare_fade(h->context);
        h->damage_label(h->context);
        if(h->damage_labels(h->context))return FrameRoute::Ended;
        h->attack(h->context);
    }
    emit(h,GameFrameEventKind::InterfaceProcess,f->path->input_ready);
    consume(t);
    return route;
}
extern "C" InputRoute dr_process_input(InputState* in,const InputHooks* h) {
    PathState& p=*in->path;StrokeState& stroke=*p.match->stroke;
    switch(dr_input_gate(&p,in->damage,in->rune,in->gate_inputs,h->schedule)) {
    case InputGate::Blocked: return InputRoute::Blocked;
    case InputGate::AttackStarted: return InputRoute::AttackStarted;
    case InputGate::Idle: return InputRoute::Idle;
    case InputGate::Dispatch: break;
    }
    const std::int32_t phase=in->gate_inputs->touch_phase;
    if(phase==3) {dr_cancel_stroke(&stroke,h->selection);return InputRoute::Cancel;}
    if(phase==2) {
        dr_prepare_release(&stroke,h->selection);
        if(dr_release_path(in->release,in->release_inputs,h->release)!=ReleaseRoute::ClassScroll)return InputRoute::Release;
        return dr_release_class_scroll(&p,in->scroll,h->release)?InputRoute::ScrollEnded:InputRoute::Scroll;
    }
    if(!stroke.selection.path_length) {dr_begin_stroke(&stroke,h->selection);return InputRoute::Begin;}
    dr_update_stroke(&stroke,h->selection);
    return InputRoute::Update;
}
