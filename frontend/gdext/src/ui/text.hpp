#pragma once
#include "quad.hpp"
#include <string>
#include <vector>
namespace drui {
// The original's bitmap fonts (Font, 0x1214 bytes: 128 characters of 0x24 bytes, then texture +0x1200, small caps
// +0x1204, spacing +0x1208, line height +0x120c, base +0x1210), read from the BMFont .fnt files as Font::LoadFont
// 0x1c930 does. Sizes are in line heights; offsets and advances are halved as the original stores them.
struct FontCharacter { float u0, v0, u1, v1, w, h, ox, oy, advance; };
struct Font {
    FontCharacter chars[128]{};
    std::int32_t texture=0;
    float small_caps=-1.0f, spacing=0.0f;
    std::int32_t line_height=0, base=0;
    bool load(const std::string& path,std::int32_t texture);
    void use_small_caps(float s);
    float advance(char c,float space_scale) const;
    Point2 offset(char c) const;
    Point2 size(char c) const;
    Point2 top_left(char c) const;
    Point2 bottom_right(char c) const;
};
// The original Label (0x38 bytes): its text, one Quad per character (+0x4, grown, never shrunk), the characters in
// use (+0x10), font (+0x14), position (+0x18), scale (+0x20), rotation (+0x28), colour (+0x2c), the laid-out width
// (+0x30) and the space advance's scale (+0x34). Label::Label 0x1d204, SetText 0x1d528, UpdateColour 0x1d490,
// Render 0x1d4c4.
struct Label {
    std::string text;
    std::vector<Quad> glyphs;
    std::int32_t count=0;
    const Font* font=nullptr;
    Point2 position{0.5f,0.75f}, scale{1.0f,1.0f};
    float rotation=0.0f;
    Colour colour{255,255,255,255};
    float width=0.0f, space_scale=1.0f;
    explicit Label(const Font* f=nullptr):font(f) {}
    void set_text(const char* s,int length=-1);
    void update_colour();
    void set_sub_colour(std::uint32_t first,std::uint32_t last,Colour c);
    void render(GL& gl) const;
};
}
