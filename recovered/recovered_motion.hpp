#pragma once
#include "recovered_match.hpp"
#include "recovered_resources.hpp"
namespace dungeonraid {
struct TokenMotion {
    Point position,scale;
    std::uint8_t active;
    std::int32_t reward_type,token_type;
    Point direction;
    float speed,progress,acceleration,initial_distance;
    std::int32_t target_or_amount,linked_tile; // -1 = no tile target
};
enum class MotionEventKind:std::int32_t {CopyTile=1,WhiteColour,XPVisual,TileVisual};
struct MotionHooks {
    void* context;
    void (*event)(void*,MotionEventKind,std::int32_t);
    // Interface target selection is an explicit boundary. kind=0 ordinary
    // resource target; kind=1 skill-slot target. All callbacks required.
    void (*target)(void*,std::int32_t kind,std::int32_t index,Point*);
    std::int32_t (*choose_special)(void*,TokenMotion*);
};
}
extern "C" {
// CopyTile models graphical copy separately; caller provides current scale as
// copied by Quad::CopyFrom. This module owns position/type/motion state.
void dr_initialise_token(dungeonraid::TokenMotion*,dungeonraid::MatchState*,
    std::uint32_t tile,std::int32_t reward,const dungeonraid::Point* position,
    std::int32_t incoming_type,const dungeonraid::MotionHooks*);
// Original Token::SetTargetTile 0x1b4d4: linked tile; with a tile, the initial distance becomes
// the distance from the token to that tile's centre.
void dr_token_set_target_tile(dungeonraid::TokenMotion*,const dungeonraid::StrokeState*,std::int32_t tile);
// Exact Token::Process math. Caller checks active before invoking, as original
// Game::Process does. Position/delta-time must be finite ordinary game values.
void dr_process_token(dungeonraid::TokenMotion*,const dungeonraid::StrokeState*,
    float delta_time,const dungeonraid::MotionHooks*);
// Game::Process token subsection only (0x1744c..0x174da, 0x17d56..62).
// pending <= supplied storage. Returns false on menu/death early exit; true
// when the subsection reaches the next subsystem. No other frame work runs.
bool dr_process_reward_tokens(dungeonraid::TokenMotion*,std::uint32_t* pending,
    dungeonraid::ResourceState*,float,const dungeonraid::MotionHooks*,
    const dungeonraid::ResourceHooks*,const std::uint8_t blocking_menus[3]);
}
