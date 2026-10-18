#pragma once
#include "recovered_selection.hpp"

namespace dungeonraid {
struct StrokeState {
    SelectionState selection;
    std::int32_t resource_counts_164b0[6];
    std::uint8_t record_14aed;
    std::int32_t mode_14ae8;
};
enum class ReleaseRoute : std::int32_t { ClearOnly=0, MatchPath=1, ClassScroll=2 };
}
extern "C" {
// Extracted branches of Game::ProcessInput, NOT a complete implementation.
// Caller must already pass its movement/token/menu/attack-stage gates.
// begin requires an empty path. update handles both empty and existing paths.
// Input geometry is in original board coordinates, not UIKit screen points.
void dr_begin_stroke(dungeonraid::StrokeState*, const dungeonraid::SelectionHooks*);
void dr_update_stroke(dungeonraid::StrokeState*, const dungeonraid::SelectionHooks*);
void dr_cancel_stroke(dungeonraid::StrokeState*, const dungeonraid::SelectionHooks*);
// Side-effect-free decision at the post-ProcessRune release boundary. Does not
// clear the path, match tiles, grant rewards or apply the scroll effect.
// fake[] must describe the valid subset of the current non-repeating path.
dungeonraid::ReleaseRoute dr_release_route(const dungeonraid::SelectionState*);
// Release prefix after input gates and rune-preview reset: undim the board,
// invoke ProcessRune(true), restore selected sizes/flags, then classify route.
// Still stops before path MatchTiles, scroll effects, cleanup and turn scheduling.
dungeonraid::ReleaseRoute dr_prepare_release(dungeonraid::StrokeState*,
                                           const dungeonraid::SelectionHooks*);
}
