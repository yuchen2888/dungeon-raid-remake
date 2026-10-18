#pragma once
#include "recovered_match.hpp"
namespace dungeonraid {
struct TokenQueue;
struct TokenQueueCounters {
    std::uint32_t pending,allocated;
    std::int32_t normal[3],bonus[3]; // XP, gold, shield
    std::int32_t bonus_total_165d4;
};
struct TokenRequest {
    std::int32_t source_tile,reward_type,position_override,token_type;
};
enum class TokenEventKind:std::int32_t {Allocate=1,Initialise,Help};
struct TokenEvent {TokenEventKind kind;std::int32_t index,a,b,c,d;};
struct TokenHooks {void* context;void (*event)(void*,const TokenEvent*);};
}
extern "C" {
// Owns pending reward REQUEST storage. Animation, Token::Process and actual
// AddResource remain separate. Create/destroy once per game context.
dungeonraid::TokenQueue* dr_token_queue_create(dungeonraid::MatchState*);
void dr_token_queue_destroy(dungeonraid::TokenQueue*);
const dungeonraid::TokenQueueCounters* dr_token_queue_counters(const dungeonraid::TokenQueue*);
// Restore/setup counters; pending <= allocated. Allocated slots have placeholder
// requests until populated by enqueue. Useful for loading a later full save.
void dr_token_queue_restore(dungeonraid::TokenQueue*,const dungeonraid::TokenQueueCounters*);
bool dr_token_queue_request(const dungeonraid::TokenQueue*,std::uint32_t,dungeonraid::TokenRequest*);
// Game::AddToken control flow. Initialise event must eventually attach original
// token motion/target semantics. This function does not grant resources.
void dr_enqueue_token(dungeonraid::TokenQueue*,std::uint32_t tile,std::int32_t reward,
                      bool bonus,std::int32_t position_override,const dungeonraid::TokenHooks*);
}
