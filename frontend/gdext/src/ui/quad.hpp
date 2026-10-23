#pragma once
#include "gl.hpp"
#include "recovered_core.hpp"
namespace drui {
using Point2=dungeonraid::Point;   // the original's GLfloat2
struct Colour { std::uint8_t r, g, b, a; };
// The original Quad (0x70 bytes, vtable first): four vertices in local space (top-left, top-right, bottom-left,
// bottom-right: a triangle strip), its position (+0x54), size (+0x5c), scale (+0x64) and rotation in degrees
// (+0x6c). Original entries 0x1c508 (Quad::Quad) .. 0x1c7a0 (Render), 0x2f4b0 (SetUV(float x4)).
struct Quad {
    std::uint32_t vtable=0;   // the original's vtable word: keeps every field at its original offset
    Vertex v[4];
    Point2 position{0.5f,0.75f}, size{1.0f,1.0f}, scale{1.0f,1.0f};
    float rotation=0.0f;
    Quad();
    void set_uv(Point2 top_left,Point2 bottom_right);
    void set_uv(float x,float y,float w,float h);
    void set_size(Point2 s);
    void set_offset(Point2 o);
    void set_colour(Colour c);
    void set_alpha(std::uint8_t a);
    void copy_from(const Quad& q);
    bool contains(Point2 p) const;
    void render(GL& gl) const;
};
static_assert(sizeof(Quad)==0x70,"Quad layout");
}
