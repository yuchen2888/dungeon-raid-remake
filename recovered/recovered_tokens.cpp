#include "recovered_tokens.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <vector>
using namespace dungeonraid;
namespace dungeonraid {
struct TokenQueue {MatchState* match;TokenQueueCounters counters{};std::vector<TokenRequest> requests;};
}
namespace {
int add(int a,int b) {return static_cast<int>(static_cast<std::uint32_t>(a)+static_cast<std::uint32_t>(b));}
int sub(int a,int b) {return static_cast<int>(static_cast<std::uint32_t>(a)-static_cast<std::uint32_t>(b));}
int mul(int a,int b) {return static_cast<int>(static_cast<std::uint32_t>(a)*static_cast<std::uint32_t>(b));}
int integer(double x) {
    if(std::isnan(x))return 0;
    if(x>=2147483647.0)return std::numeric_limits<int>::max();
    if(x<=-2147483648.0)return std::numeric_limits<int>::min();
    return static_cast<int>(x);
}
void emit(const TokenHooks* h,TokenEventKind kind,int index,int a=0,int b=0,int c=0,int d=0) {
    if(h && h->event) {const TokenEvent e{kind,index,a,b,c,d};h->event(h->context,&e);}
}
}
extern "C" TokenQueue* dr_token_queue_create(MatchState* match) {return new TokenQueue{match,{}, {}};}
extern "C" void dr_token_queue_destroy(TokenQueue* q) {delete q;}
extern "C" const TokenQueueCounters* dr_token_queue_counters(const TokenQueue* q) {return &q->counters;}
extern "C" void dr_token_queue_restore(TokenQueue* q,const TokenQueueCounters* c) {
    q->counters=*c;q->requests.resize(c->allocated,TokenRequest{-1,-1,-1,-1});
}
extern "C" bool dr_token_queue_request(const TokenQueue* q,std::uint32_t index,TokenRequest* out) {
    if(index>=q->counters.pending)return false;*out=q->requests[index];return true;
}
extern "C" void dr_enqueue_token(TokenQueue* q,std::uint32_t index,std::int32_t reward,
                                  bool bonus,std::int32_t position_override,const TokenHooks* h) {
    auto& c=q->counters;auto& m=*q->match;auto& s=m.stroke->selection;
    if(c.pending==c.allocated) {
        emit(h,TokenEventKind::Allocate,-1,static_cast<int>(c.allocated));
        q->requests.push_back(TokenRequest{-1,-1,-1,-1});++c.allocated;
    }
    q->requests[c.pending]={static_cast<int>(index),reward,position_override,0};
    emit(h,TokenEventKind::Initialise,static_cast<int>(c.pending),static_cast<int>(index),reward,position_override,0);
    ++c.pending;
    if(reward>=0 && reward<=3) {
        const int help[]={3,6,2,5};
        emit(h,TokenEventKind::Help,static_cast<int>(index),help[reward],0x3da9999a,0x3da9999a);
        if(reward!=0 && !(reward==3 && s.tiles[index].broken)) {
            const int bucket=reward==1?0:(reward==2?1:2);
            auto& count=bonus?c.bonus[bucket]:c.normal[bucket];count=add(count,1);
        }
    }
    if(m.stroke->record_14aed && m.stroke->mode_14ae8==0) {
        auto& p=*m.preview;
        const auto double_up=p.double_upgrade;
        const float missing=static_cast<float>(sub(p.armour_max,p.armour_current));
        const float shield=static_cast<float>(mul(add(p.shield_value,p.shield_bonus),double_up?2:1));
        const float needed=std::ceil(missing/shield);
        const int remainder=integer(static_cast<double>(c.normal[2])-static_cast<double>(needed));
        const int normal_up=std::max(remainder,0);
        const int bonus_up=remainder<0?add(remainder,c.bonus[2]):c.bonus[2];
        const float xp_multiplier=p.xp_bonus+1.0f,up_multiplier=p.upgrade_bonus+1.0f,gold_multiplier=p.gold_bonus+1.0f;
        const float gold_double=p.double_gold?2.0f:1.0f;
        const float normal_xp=static_cast<float>(c.normal[0])*xp_multiplier;
        const float normal_shield=static_cast<float>(normal_up)*up_multiplier*(double_up?2.0f:1.0f);
        const float normal_gold=static_cast<float>(c.normal[1])*gold_multiplier*gold_double;
        p.total_165d0=integer((normal_xp+normal_shield)+normal_gold);
        const float bonus_xp=static_cast<float>(c.bonus[0])*xp_multiplier;
        const float bonus_shield=static_cast<float>(std::max(bonus_up,0))*up_multiplier*(p.double_upgrade?2.0f:1.0f);
        const float bonus_gold=static_cast<float>(c.bonus[1])*gold_multiplier*gold_double;
        c.bonus_total_165d4=integer((bonus_xp+bonus_shield)+bonus_gold);
    }
}
