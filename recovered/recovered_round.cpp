#include "recovered_core.hpp"
#include <algorithm>
#include <set>
using namespace dungeonraid;

namespace {
std::int32_t add32(std::int32_t a, std::int32_t b) {
    return static_cast<std::int32_t>(static_cast<std::uint32_t>(a) + static_cast<std::uint32_t>(b));
}
std::int32_t mul32(std::int32_t a, std::int32_t b) {
    return static_cast<std::int32_t>(static_cast<std::uint32_t>(a) * static_cast<std::uint32_t>(b));
}
struct Bridge {
    const RoundHooks* hooks;
    std::int32_t tile;
    void event(BattleEvent kind, std::int32_t a=0, std::int32_t b=0,
               std::int32_t c=0, std::int32_t d=0) const {
        const RoundEvent event{kind == BattleEvent::Achievement ? -1 : tile, kind, a,b,c,d};
        hooks->event(hooks->context, &event);
    }
    void achievement(std::int32_t code, std::int32_t value=0x42c80000) const {
        event(BattleEvent::Achievement,code,value);
    }
    static std::int32_t random(void* context, std::int32_t low, std::int32_t high, std::int32_t stream) {
        const auto* bridge=static_cast<Bridge*>(context);
        return bridge->hooks->random(bridge->hooks->context,bridge->tile,low,high,stream);
    }
    static void forward(void* context, BattleEvent kind, std::int32_t a,
                        std::int32_t b, std::int32_t c, std::int32_t d) {
        static_cast<Bridge*>(context)->event(kind,a,b,c,d);
    }
};
}

extern "C" void dr_match_path(RoundState* state, const std::uint8_t* path,
                               std::size_t length, const std::uint8_t* excluded,
                               std::size_t excluded_length, const RoundHooks* hooks) {
    // Game::MatchTiles, VA 0x12188. Callers provide valid board indices/path.
    // The event boundary keeps MatchTile/MoveMatchedTiles as explicit unfinished
    // subsystems instead of substituting new gameplay for the original.
    state->flag_5e14=0;
    for(auto& count:state->matched_counts) count=0;
    state->sound_13ec4=state->battle.poison_sound_queued=0;
    const bool no_reward=length<=3 && dr_have_flaw(&state->character,2);
    bool all_border=true, all_coins=true, previous_excluded=false;
    std::set<std::int32_t> crossed_cells;
    std::int32_t crossings=0, previous_x=0, previous_y=0;
    RuleTile rule_board[36];
    const RuleTile* rule_path[36];
    for(std::size_t i=0;i<36;++i) {
        rule_board[i]=state->tiles[i].rule;
        rule_board[i].type=state->tiles[i].battle.type;
        rule_board[i].enemy_type=state->tiles[i].battle.enemy_type;
        rule_board[i].enemy_state=state->tiles[i].battle.enemy_state;
    }
    for(std::size_t i=0;i<length;++i) rule_path[i]=&rule_board[path[i]];
    RuleGame rules{state->turn,state->character,rule_board};
    CharacterClassState active_class{state->character.race};
    const auto* saved_class=state->battle.context.active_class;
    state->battle.context.active_class=&active_class;
    Bridge bridge{hooks,-1};
    BattleHooks battle_hooks{&bridge,Bridge::random,Bridge::forward};
    auto attack=[&](std::int32_t index,std::int32_t amount,bool effects) {
        bridge.tile=index;
        active_class.race_selector=state->character.race;
        auto& tile=state->tiles[index].battle;
        tile.combat.game=&state->battle.context;
        return dr_attack_skull(&state->battle,&tile,amount,effects,&battle_hooks);
    };
    auto damage_type=[&](std::size_t path_index) {
        // MatchTile callbacks may alter other tiles or the active character.
        for(std::size_t j=0;j<36;++j) {
            rule_board[j]=state->tiles[j].rule;
            rule_board[j].type=state->tiles[j].battle.type;
            rule_board[j].enemy_type=state->tiles[j].battle.enemy_type;
            rule_board[j].enemy_state=state->tiles[j].battle.enemy_state;
        }
        rules.turn=state->turn;rules.character=state->character;
        return dr_damage_type(&rules,rule_path,length,path_index);
    };
    auto member=[&](const std::uint8_t* values,std::size_t count,std::uint8_t value) {
        for(std::size_t i=0;i<count;++i) if(values[i]==value) return true;
        return false;
    };
    std::size_t tail=length?length-1:0;
    for(std::size_t i=0;i<length;++i) {
        const auto index=path[i];
        auto& tile=state->tiles[index];
        const auto x=tile.rule.x,y=tile.rule.y;
        if(i && x!=previous_x && y!=previous_y) {
            const auto cell=std::min(x,previous_x)+6*std::min(y,previous_y);
            if(!crossed_cells.insert(cell).second) ++crossings;
        }
        previous_x=x;previous_y=y;
        all_border=all_border && (x==0 || x==5 || y==0 || y==5);
        if(member(excluded,excluded_length,index)) {
            all_coins=false;previous_excluded=true;continue;
        }
        const bool coin=tile.battle.type==2;
        const bool enemy=tile.battle.type==1 && !(tile.battle.enemy_type==32 && tile.battle.enemy_state!=0);
        if(!(all_coins && coin) && enemy) {
            const auto category=damage_type(i);
            auto amount=state->base_attack;
            const bool bonus=category==3;
            if(category==0 || category==1) amount=0;
            else if(bonus) amount=add32(amount,state->direction_bonus);
            const bool killed=attack(index,amount,true);
            if(killed && bonus) bridge.achievement(48,0x40000000);
            if(killed && previous_excluded && tile.battle.enemy_type!=0 && i==tail && tail>=2) {
                tail-=2;
                const auto& before=state->tiles[path[tail]];
                if(before.battle.type==4 && before.rule.flag_231 &&
                   (std::abs(before.rule.x-x)>1 || std::abs(before.rule.y-y)>1))
                    bridge.achievement(56);
            }
            all_coins=false;
        } else {
            if(!(all_coins && coin)) all_coins=false;
            bridge.tile=index;
            if(tile.rule.special_type==0 && length==36) bridge.achievement(59);
            bridge.event(BattleEvent::MatchTile,no_reward?7:5);
        }
        previous_excluded=false;
    }
    // Original visits columns first, then rows. Preserve effect/random order.
    for(std::uint8_t x=0;x<6;++x) for(std::uint8_t y=0;y<6;++y) {
        const auto index=static_cast<std::uint8_t>(y*6+x);
        const auto& tile=state->tiles[index].battle;
        if(tile.type==1 && tile.enemy_type==30 && !member(path,length,index))
            attack(index,state->base_attack,false);
    }
    bridge.tile=-1;
    if(crossings>5) bridge.achievement(75);
    if(state->record_14aed && state->mode_14ae8==1) {
        if(state->round_kills_165d0>0) {
            state->crossing_best=std::max(state->crossing_best,crossings);
            if(state->crossing_average==0) state->crossing_average=mul32(crossings,10);
            else state->crossing_average=add32(mul32(state->crossing_average,state->crossing_samples),
                mul32(crossings,10))/add32(state->crossing_samples,1);
            state->crossing_samples=add32(state->crossing_samples,1);
            if(crossings>14) {
                bridge.achievement(77);
                bridge.event(BattleEvent::Label,41,0,49,0x3f800000);
            } else if(crossings>9) bridge.event(BattleEvent::Label,40,0,48,0x3f800000);
            else if(crossings>4) bridge.event(BattleEvent::Label,39,0,47,0x3f800000);
        }
        state->total_165cc=add32(state->total_165cc,state->round_kills_165d0);
        state->round_kills_165d0=state->pending_165d4=0;
    }
    if(all_border && length==20) bridge.achievement(68);
    if(all_coins && length==36) bridge.achievement(69);
    for(auto& tile:state->tiles) tile.attack_flag_86=0;
    bridge.event(BattleEvent::MoveMatchedTiles);
    state->battle.context.active_class=saved_class;
}
