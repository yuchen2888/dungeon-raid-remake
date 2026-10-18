#include <cmath>
#include "recovered_core.hpp"
using namespace dungeonraid;
static_assert(sizeof(void*) == 8);

extern "C" void dr_touch_start(TouchState* state, float x, float y) {
    // Game::TouchStart, original VA 0x89a4, soft-float parameter ABI.
    state->phase = 1;
    state->position = {x, y * 1.5f};
}
extern "C" void dr_touch_drag(TouchState* state, float x, float y) {
    // Original preserves the current touch phase during a drag.
    state->position = {x, y * 1.5f};
}
extern "C" void dr_touch_end(TouchState* state) { state->phase = 2; }
extern "C" void dr_touch_interrupted(TouchState* state) { state->phase = 3; }
extern "C" const TileGeometry* dr_tile_at(const BoardGeometry* board, const Point* point) {
    // Game::GetTileAtPosition, original VA 0x89e0.
    // Coordinates/pitch must be finite, pitch > 0, ratios within int32 range.
    const float top = board->vertical_offset + 0.246875f;
    if (point->y < top || point->y >= top + 1.0f) return nullptr;
    const auto x = static_cast<std::int32_t>(point->x / board->pitch);
    const auto y = static_cast<std::int32_t>((point->y - top) / board->pitch);
    // The original truncates toward zero before this bounds check.
    if (static_cast<std::uint32_t>(x) > 5 || y < 0 || y > 5) return nullptr;
    return &board->tiles[y * 6 + x];
}
extern "C" bool dr_is_selected(const TileGeometry* tile, const Point* point) {
    // Tile::IsBeingSelected, original VA 0x3d9a4. Preserve f32 operation order.
    const float dx = tile->center.x - point->x;
    const float dy = tile->center.y - point->y;
    const float squared_x = dx * dx;
    const float squared_y = dy * dy;
    const float distance = std::sqrt(squared_x + squared_y);
    return distance < tile->size * 0.8f;
}
