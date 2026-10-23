#pragma once
#include "quad.hpp"
#include "recovered_selection.hpp"
namespace drui {
// The original Arrow (Game+0x3658): the stroke's path drawn as up to 288 vertices (+0, 0x14 each; the count +0x1680),
// four to a triangle fan, cut from the arrow pieces of tiles.png: a start cap, a straight run, 45, 90 and 135 degree
// corners with mitred joins, and the head. Arrow::Arrow 0x1d7b8, SetColour 0x1d790, AddVertex 0x1d7d4, Render
// 0x1d808, Update 0x1d868 (run on SelectionEvent::Arrow over the session's path).
struct ArrowView {
    Vertex v[288]{};
    std::int32_t count=0;
    ArrowView() {set_colour(50,255,50);}
    void set_colour(std::uint32_t r,std::uint32_t g,std::uint32_t b);
    void add(Point2 p,std::uint8_t alpha,float u,float v);
    void update(const dungeonraid::SelectionState& s);
    void render(GL& gl) const;
};
}
