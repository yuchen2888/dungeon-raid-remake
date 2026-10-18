#pragma once
#include "recovered_stroke.hpp"
namespace dungeonraid {
struct RuneState {
    std::uint8_t enabled_16491;
    std::uint32_t highlight_count_164a0, allocated_highlights;
};
}
extern "C" {
// ProcessInput 0x16748..0x1674c: called AFTER input gates, BEFORE processing
// an accepted nonzero touch phase. ProcessRune itself does not reset long paths.
void dr_reset_rune_preview(dungeonraid::RuneState*);
// Original ProcessRune's board scan and dispatch. MatchTile and rendering are
// explicit callbacks, not silently implemented. The caller owns frame resets.
// Board coordinates are 0..5; tile types are 0..6; path is valid and nonempty
// whenever length > 3. Selected flags normally correspond to that path.
void dr_process_rune(dungeonraid::StrokeState*, dungeonraid::RuneState*, bool commit,
                     const dungeonraid::SelectionHooks*);
}
