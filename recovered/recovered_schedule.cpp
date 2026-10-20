#include "recovered_schedule.hpp"
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
