#include "recovered_match.hpp"
#include <vector>
using namespace dungeonraid;
namespace {
std::int32_t add(std::int32_t a,std::int32_t b) {
    return static_cast<std::int32_t>(static_cast<std::uint32_t>(a)+static_cast<std::uint32_t>(b));
}
void emit(const MatchHooks* h,MatchEventKind kind,int index=-1,int a=0,int b=0,int c=0,int d=0) {
    if(h && h->event) {const MatchEvent e{kind,index,a,b,c,d};h->event(h->context,&e);}
}
int random(MatchState* s,const MatchHooks* h,int lo,int hi,int stream) {
    const auto result=dr_random_int(&s->random,lo,hi,stream);
    emit(h,MatchEventKind::Random,stream,lo,hi,result);return result;
}
void explosion_sound(MatchState* s,const MatchHooks* h) {
    if(!s->sound_13ec4) {emit(h,MatchEventKind::Sound,-1,28);s->sound_13ec4=1;}
}
void flare(const MatchHooks* h,int index) {emit(h,MatchEventKind::Flare,index,1,static_cast<int>(0xff0000ffU));}
struct Rewards {
    MatchState* state;const MatchHooks* hooks;std::vector<int> values;
};
int reward_random(void* context,int lo,int hi,int stream) {
    auto& r=*static_cast<Rewards*>(context);return random(r.state,r.hooks,lo,hi,stream);
}
void reward_event(void* context,BattleEvent event,int a,int,int,int) {
    if(event==BattleEvent::Reward)static_cast<Rewards*>(context)->values.push_back(a);
}
void explode(MatchState* m,int index,bool include_center,const MatchHooks* h) {
    auto& board=m->stroke->selection.tiles;
    const int x=board[index].rule.x,y=board[index].rule.y;
    explosion_sound(m,h);
    for(int dx=-1;dx<=1;++dx)for(int dy=-1;dy<=1;++dy) {
        if(!include_center && dx==0 && dy==0)continue;
        const int nx=x+dx,ny=y+dy;if(nx<0 || nx>5 || ny<0 || ny>5)continue;
        const int target=ny*6+nx;const auto& t=board[target];
        if(t.rule.type==1 && t.rule.enemy_type!=0)continue;
        if(t.rule.type!=0 || !m->preview->potions[target].flag_234)flare(h,target);
        dr_match_tile(m,target,5,h);
    }
    flare(h,index);m->shake_progress_bd90=0;m->shake_scale_bd94=0x3f800000;
}
}
extern "C" void dr_match_tile(MatchState* m,std::uint32_t index,std::int32_t reward_type,
                               const MatchHooks* h) {
    auto& s=m->stroke->selection;auto& t=s.tiles[index];
    if(t.rule.matched)return;
    if(reward_type==5)reward_type=t.rule.type;
    t.rule.matched=1;
    if(reward_type<=4)m->matched_counts[reward_type]=add(m->matched_counts[reward_type],1);
    if(!(t.rule.type==1 && t.rule.enemy_type==10)) {
        if(t.broken) {emit(h,MatchEventKind::Achievement,-1,73,0x3f800000);return;}
        if(reward_type==7 || reward_type==4 || t.rule.special_type!=3)return;
    }
    if(t.rule.type==1) {
        emit(h,MatchEventKind::Particles,index,0);
        if(t.rule.enemy_type==10)explode(m,index,false,h);
    }
    if(reward_type==7)return;
    if(t.rule.type==0 && m->preview->potions[index].flag_234) {explode(m,index,true,h);return;}
    if(t.rule.type==1 && t.rule.enemy_type!=0) {
        Rewards rewards{m,h,{}};BattleHooks hooks{&rewards,reward_random,reward_event};
        dr_get_rewards(t.rule.enemy_type,&hooks);
        for(auto type:rewards.values)emit(h,MatchEventKind::Token,0,type,0,index);
        if(m->spawn_enabled_14ae0>0) {
            if(!(m->stroke->record_14aed && m->stroke->mode_14ae8==0 && random(m,h,0,100,0)>49))
                m->spawn_remaining_15558=add(m->spawn_remaining_15558,-1);
            m->spawn_dirty_15555=1;
            if(m->spawn_remaining_15558<=0) {
                bool all_unlocked=true;for(auto unlocked:m->unlocked)if(!unlocked)all_unlocked=false;
                if(m->spawn_count_1555c>2 ||
                   ((m->class_type==0 || m->class_level>9) && all_unlocked))m->spawn_remaining_15558=0;
                else {
                    if(m->flag_25d[index])emit(h,MatchEventKind::Achievement,-1,66,0x42c80000);
                    m->spawn_remaining_15558=random(m,h,20,30,0);
                    m->spawn_count_1555c=add(m->spawn_count_1555c,1);
                    emit(h,MatchEventKind::SetSpecialType,index,1);
                    t.rule.matched=0;
                }
            }
        }
        emit(h,MatchEventKind::Achievement,-1,46,0x3f800000);
        if(t.rule.enemy_type==14 && dr_mortal_enemy(s.character.race)==14)
            emit(h,MatchEventKind::Achievement,-1,42,0x42c80000);
        else if(t.rule.enemy_type==3)emit(h,MatchEventKind::Achievement,-1,44,0x42c80000);
        if(s.character.race==9) {
            emit(h,MatchEventKind::Achievement,-1,55,0x40000000);
            emit(h,MatchEventKind::Shapeshift);
        }
        emit(h,MatchEventKind::Help,index,22,0x3da9999a,0x3da9999a);
        return;
    }
    emit(h,MatchEventKind::Token,index,reward_type,0,-1);
    const auto& flags=m->preview->potions[index];
    if(t.rule.type==0 && (flags.flag_234 || flags.flag_232 || flags.flag_233))return;
    const int count=m->matched_counts[reward_type];
    if(count<=3)return;
    int chance=reward_type<=3?add(m->bonus_chance[reward_type],m->bonus_chance_extra[reward_type]):0;
    if(count>9)for(auto perk:m->perks)if(perk==2)chance=100;
    if(chance<random(m,h,1,100,5))return;
    emit(h,MatchEventKind::Help,index,1,0x3d23d70a,0);
    emit(h,MatchEventKind::Token,index,reward_type,1,-1);
    emit(h,MatchEventKind::Label,index,reward_type);
}
