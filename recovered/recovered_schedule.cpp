#include "recovered_schedule.hpp"
#include <algorithm>
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
