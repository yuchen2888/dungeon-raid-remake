#pragma once
#include "quad.hpp"
#include <cstdint>
#include <map>
#include <string>
#include <vector>
namespace drui {
// The original's bitmap fonts (Font, 0x1214 bytes: 128 characters of 0x24 bytes, then texture +0x1200, small caps
// +0x1204, spacing +0x1208, line height +0x120c, base +0x1210), read from the BMFont .fnt files as Font::LoadFont
// 0x1c930 does. Sizes are in line heights; offsets and advances are halved as the original stores them.
struct FontCharacter { float u0, v0, u1, v1, w, h, ox, oy, advance; };
// Wide characters (code points 128 and up: the Chinese texts, T050-D) come from a second BMFont file with its own
// texture (load_wide), in the same line-height units as the original's 128; a font without them draws '?'.
struct Font {
    FontCharacter chars[128]{};
    std::int32_t texture=0;
    float small_caps=-1.0f, spacing=0.0f;
    std::int32_t line_height=0, base=0;
    std::map<std::uint32_t,FontCharacter> wide;
    std::int32_t wide_texture=0;
    bool load(const std::string& path,std::int32_t texture);
    bool load_wide(const std::string& path,std::int32_t texture);
    // A wide character's glyph and texture (the '?' of the original's when missing).
    const FontCharacter& glyph(std::uint32_t code,std::int32_t& texture_out) const;
    float wide_advance(std::uint32_t code) const;   // GetAdvance for a wide character (plus the spacing)
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
    std::vector<std::int32_t> textures;   // each glyph's texture (the font's, or its wide texture)
    bool wide=false;                      // the text has wide characters (its glyphs are not one per byte)
    std::int32_t count=0;
    const Font* font=nullptr;
    Point2 position{0.5f,0.75f}, scale{1.0f,1.0f};
    float rotation=0.0f;
    Colour colour{255,255,255,255};
    float width=0.0f, space_scale=1.0f;
    explicit Label(const Font* f=nullptr):font(f) {}
    void set_text(const char* s,int length=-1);
    void set_wide_text(const char* s,int n);
    void update_colour();
    void set_sub_colour(std::uint32_t first,std::uint32_t last,Colour c);   // byte offsets into the text
    void render(GL& gl) const;
};
// UTF-8 (T050-D): the code point at s[i] (a stray byte stands for itself), i moved past it.
std::uint32_t next_code(const char* s,std::size_t& i);
// Lines may break before or after a CJK character (the Chinese texts have no spaces), except before the punctuation
// that may not start a line.
bool breaks_around(std::uint32_t code);
bool no_line_start(std::uint32_t code);   // ，。！？；：、）》」』 and their like
// A text with wide characters (T050-D) cut into lines no wider than limit, counted as the original's line cutters
// count (each character's half width plus its advance, a space's advance doubled): at a space (dropped) or around a
// CJK character. Each line: its bytes [start, end) and its width up to there.
struct TextLine { std::size_t start, end; float width; };
bool has_wide(const char* s);
std::vector<TextLine> wrap_wide(const Font& font,const char* s,float limit);
}
