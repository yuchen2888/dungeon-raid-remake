#pragma once
#include "recovered_path.hpp"
namespace dungeonraid {
struct FallingTile {
    Point target;
    std::uint8_t moving;
    float speed, acceleration;
};
struct RefillState {
    PathState* path;
    FallingTile falling[36];
};
enum class RefillEventKind : std::int32_t { Swap=1, AppendMoving, Randomise, Stab };
struct RefillHooks {
    void* context;
    // Randomise and Stab are synchronous gameplay dependencies. Swap lets a
    // renderer (or additional tile subsystem) swap its own per-tile state too.
    void (*event)(void*,RefillEventKind,std::int32_t,std::int32_t);
};
}
extern "C" {
// Original PositionTile. x must be 0..5. A target row must be 0..5;
// a current-position row may be negative (off-board spawning).
void dr_position_tile(dungeonraid::RefillState*,std::uint32_t,int x,int y,bool target);
// Original MoveMatchedTiles, including stable per-column order and deferred
// pointer-ordered Stab calls. The original moving-list append is a callback.
void dr_move_matched_tiles(dungeonraid::RefillState*,const dungeonraid::RefillHooks*);
// Original SwapTiles. The shared storage swap emits Swap for additional state.
void dr_swap_tiles(dungeonraid::RefillState*,int x1,int y1,int x2,int y2,const dungeonraid::RefillHooks*);
// Original Tile::Process; caller chooses which moving tiles to process.
void dr_process_falling_tile(dungeonraid::RefillState*,std::uint32_t,float dt);
// Game::Process moving-list subsection (0x173c8..0x173ff), not the full loop.
// Caller supplies writable storage of at least *count entries; order retained.
void dr_process_falling_list(dungeonraid::RefillState*,std::int32_t* indices,std::uint32_t* count,float dt);
}
