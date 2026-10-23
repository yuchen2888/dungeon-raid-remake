#pragma once
#include "quad.hpp"
#include <vector>
namespace drui {
// The original QuadStrip (0x4c bytes): quads laid out in rows (+0x24, each added in the current row +0x30), each with a
// size policy (+0xc: 0 its picture's width and the rest of the height, 1 the rest of the width and its extent's height,
// 2 its picture's width and its extent's height, 3 the rest of both; the rest is what the fixed size +0x38 / +0x3c leaves
// once the row's and the column's other quads are taken) and an extent (+0x18, -1: the picture's height); texture
// coordinates in pixels of a texture of +0x34 (512) pixels; the top-left corner +0x44. 0x110a80 ..
class QuadStrip {
public:
    std::vector<Quad> quads;
    std::vector<std::int32_t> policies;
    std::vector<float> extents;
    std::vector<std::int32_t> rows;
    std::int32_t row=0;            // +0x30: the row quads are added to
    std::int32_t texture_size=512; // +0x34
    Point2 fixed{0.0f,0.0f};       // +0x38
    bool has_fixed=false;          // +0x40
    Point2 position{0.0f,0.0f};    // +0x44
    void add_quad(Point2 uv0,Point2 uv1,std::int32_t policy,float extent);   // AddQuad 0x1110f8
    void add_quad();                                                          // AddQuad() 0x11120c: blank, policy 3
    void update_size();                                                       // UpdateSize 0x110fa4
    Point2 fixed_size(std::int32_t row,std::int32_t column) const;            // GetFixedSize 0x110d3c
    Point2 size() const;                                                      // GetSize 0x110e94
    Point2 middle() const;                                                    // GetMiddle 0x3cd58
    void set_position(Point2 p);                                              // SetPosition 0x110ac0
    void set_position_centre(Point2 p);                                       // SetPositionCentre 0x110f44
    void align_with(const QuadStrip& other);                                  // AlignWith 0x110eb8
    void set_uv(Point2 uv0,Point2 uv1);                                       // SetUV 0x110b74 (the last quad)
    void set_colour(Colour c);                                                // SetColour 0x110c94
    void set_alpha(std::uint8_t a);                                           // SetAlpha 0x110c60
    void mirror();                                                            // Mirror 0x110cec
    bool contains(Point2 p) const;                                            // ContainsPoint 0x110c28
    void render(GL& gl) const;                                                // Render 0x110c00
private:
    Point2 picture(const Quad& q) const;   // the quad's picture size in screen units (its texture span x size / 320)
};
}
