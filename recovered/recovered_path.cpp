#include "recovered_path.hpp"
using namespace dungeonraid;
namespace {
struct Adapter {
    PathState* p;RoundState view{};const PathHooks* h;
    void import_state() {
        auto& m=*p->match;auto& s=m.stroke->selection;
        view.battle.kill_count_165b4=p->battle.kill_count_165b4;
        view.battle.kill_count_15548=p->battle.kill_count_15548;
        view.battle.killed_attack_164ac=p->battle.killed_attack_164ac;
        view.battle.armour_break_chance=p->battle.armour_break_chance;
        view.battle.poison_amount=p->battle.poison_amount;
        view.battle.grant_coin_on_attack=p->battle.grant_coin_on_attack;
        view.battle.poison_sound_queued=p->battle.poison_sound_queued;view.battle.lich_progress_bits=static_cast<int>(m.shake_progress_bd90);
        view.battle.lich_transition_bits=static_cast<int>(m.shake_scale_bd94);
        view.character=s.character;view.turn=p->turn;view.base_attack=s.current_damage;view.direction_bonus=s.weapon_damage;
        view.flag_5e14=p->input_ready;view.sound_13ec4=m.sound_13ec4;
        view.record_14aed=m.stroke->record_14aed;view.mode_14ae8=m.stroke->mode_14ae8;
        view.round_kills_165d0=m.preview->total_165d0;
        view.pending_165d4=dr_token_queue_counters(p->queue)->bonus_total_165d4;
        view.crossing_best=p->crossing_best;view.crossing_average=p->crossing_average;view.crossing_samples=p->crossing_samples;view.total_165cc=p->total;
        for(int i=0;i<5;++i)view.matched_counts[i]=m.matched_counts[i];
        for(int i=0;i<36;++i) {
            const auto& t=s.tiles[i];const auto& c=p->combat[i];auto& v=view.tiles[i];
            v.rule=t.rule;v.attack_flag_86=c.attack_flag;
            v.battle.combat={c.attack,c.poison,&view.battle.context};
            v.battle.type=t.rule.type;v.battle.enemy_type=t.rule.enemy_type;v.battle.enemy_state=t.rule.enemy_state;
            v.battle.defence=c.defence;v.battle.health=c.health;v.battle.center=t.geometry.center;
            v.battle.frozen=t.rule.flag_255;v.battle.freeze_overlay_visible=c.overlay;v.battle.flag_256=t.flaming;v.battle.flag_25e=c.flag_25e;
        }
    }
    void export_state() {
        auto& m=*p->match;auto& s=m.stroke->selection;
        p->battle.kill_count_165b4=view.battle.kill_count_165b4;
        p->battle.kill_count_15548=view.battle.kill_count_15548;
        p->battle.killed_attack_164ac=view.battle.killed_attack_164ac;
        p->battle.armour_break_chance=view.battle.armour_break_chance;
        p->battle.poison_amount=view.battle.poison_amount;
        p->battle.grant_coin_on_attack=view.battle.grant_coin_on_attack;
        p->battle.poison_sound_queued=view.battle.poison_sound_queued;m.shake_progress_bd90=static_cast<unsigned>(view.battle.lich_progress_bits);
        m.shake_scale_bd94=static_cast<unsigned>(view.battle.lich_transition_bits);
        s.character=view.character;p->turn=view.turn;s.current_damage=view.base_attack;s.weapon_damage=view.direction_bonus;
        p->input_ready=view.flag_5e14;m.sound_13ec4=view.sound_13ec4;
        m.stroke->record_14aed=view.record_14aed;m.stroke->mode_14ae8=view.mode_14ae8;
        m.preview->total_165d0=view.round_kills_165d0;
        auto counters=*dr_token_queue_counters(p->queue);counters.bonus_total_165d4=view.pending_165d4;
        dr_token_queue_restore(p->queue,&counters);
        p->crossing_best=view.crossing_best;p->crossing_average=view.crossing_average;p->crossing_samples=view.crossing_samples;p->total=view.total_165cc;
        for(int i=0;i<5;++i)m.matched_counts[i]=view.matched_counts[i];
        for(int i=0;i<36;++i) {
            auto& t=s.tiles[i];auto& c=p->combat[i];const auto& v=view.tiles[i];
            t.rule=v.rule;t.rule.type=v.battle.type;t.rule.enemy_type=v.battle.enemy_type;t.rule.enemy_state=v.battle.enemy_state;
            t.rule.flag_255=v.battle.frozen;c.attack_flag=v.attack_flag_86;
            c.attack=v.battle.combat.base_attack;c.poison=v.battle.combat.poison;c.defence=v.battle.defence;c.health=v.battle.health;
            c.overlay=v.battle.freeze_overlay_visible;t.flaming=v.battle.flag_256;c.flag_25e=v.battle.flag_25e;
        }
    }
    static int random(void* context,int tile,int lo,int hi,int stream) {
        auto& a=*static_cast<Adapter*>(context);a.export_state();
        const int result=dr_random_int(&a.p->match->random,lo,hi,stream);
        const RoundEvent e{tile,static_cast<BattleEvent>(0),lo,hi,stream,result};
        if(a.h->event)a.h->event(a.h->context,&e);
        a.import_state();return result;
    }
    static void event(void* context,const RoundEvent* e) {
        auto& a=*static_cast<Adapter*>(context);a.export_state();
        if(a.h->event)a.h->event(a.h->context,e);
        if(e->kind==BattleEvent::MatchTile)dr_match_tile(a.p->match,e->tile_index,e->a,a.h->match);
        if(e->kind==BattleEvent::Token)dr_enqueue_token(a.p->queue,e->tile_index,e->a,e->b!=0,-1,a.h->tokens);
        a.import_state();
    }
};
}
extern "C" void dr_commit_path(PathState* p,const std::uint8_t* path,std::size_t length,
    const std::uint8_t* excluded,std::size_t excluded_length,const PathHooks* h) {
    Adapter adapter{p,{},h};adapter.import_state();
    const RoundHooks hooks{&adapter,Adapter::random,Adapter::event};
    dr_match_path(&adapter.view,path,length,excluded,excluded_length,&hooks);adapter.export_state();
}
namespace {
struct SingleAttack {
    Adapter* adapter;std::int32_t tile;
    static std::int32_t random(void* context,std::int32_t low,std::int32_t high,std::int32_t stream) {
        auto* s=static_cast<SingleAttack*>(context);return Adapter::random(s->adapter,s->tile,low,high,stream);
    }
    static void forward(void* context,BattleEvent kind,std::int32_t a,std::int32_t b,std::int32_t c,std::int32_t d) {
        auto* s=static_cast<SingleAttack*>(context);
        const RoundEvent e{kind==BattleEvent::Achievement?-1:s->tile,kind,a,b,c,d};
        Adapter::event(s->adapter,&e);
    }
};
}
extern "C" bool dr_path_attack_skull(PathState* p,std::uint32_t index,std::int32_t amount,
    bool effects,const PathHooks* h) {
    Adapter adapter{p,{},h};adapter.import_state();
    CharacterClassState active_class{adapter.view.character.race};
    adapter.view.battle.context.active_class=&active_class;
    auto& tile=adapter.view.tiles[index].battle;tile.combat.game=&adapter.view.battle.context;
    SingleAttack single{&adapter,static_cast<std::int32_t>(index)};
    const BattleHooks hooks{&single,SingleAttack::random,SingleAttack::forward};
    const bool result=dr_attack_skull(&adapter.view.battle,&tile,amount,effects,&hooks);
    adapter.export_state();return result;
}
