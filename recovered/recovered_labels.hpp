#pragma once
#include "recovered_core.hpp"
#include "recovered_random.hpp"
#include <cstdint>
namespace dungeonraid {
// A SimpleLabel object (0x358 bytes, the same layout): a type's glyph and a number drawn as up to eight glyphs from
// the label atlas, four vertices each, in label space (the position is applied when drawn). The game reads some of
// it: its active byte, and the shop's scroll draw reads the leech label's type and first vertices as words
// (FoldoutMenu::Initialise(1), T040-K6).
struct LabelVertex { float x, y; std::uint8_t colour[4]; float u, v; };   // x, y / 320; u, v / 1024; RGBA
struct LabelGlyph { float u0, v0, u1, v1; };                              // atlas pixels
struct SimpleLabelState {
    std::uint8_t active;              // +0x0
    std::int32_t type;                // +0x4 (SimpleLabelType)
    LabelVertex vertices[32];         // +0x8
    LabelGlyph glyphs[8];             // +0x288
    float glyph_scale[8];             // +0x308
    std::int32_t count;               // +0x328: glyphs
    float offset_x, offset_y;         // +0x32c / +0x330: the glyph being laid out
    float x, y;                       // +0x334: position
    float scale;                      // +0x33c
    float size;                       // +0x340: the digits' scale (0.5 or 1)
    float speed;                      // +0x344: rise per second
    float timer, duration;            // +0x348 / +0x34c
    std::int32_t number;              // +0x350
    std::uint8_t alpha;               // +0x354: the alpha the fade starts from
};
static_assert(sizeof(SimpleLabelState)==0x358,"SimpleLabel layout");
}
extern "C" {
// Original SimpleLabel::SimpleLabel 0x22194: inactive, no glyphs, number 0, scale 1, duration 1, alpha 255 (the rest is
// whatever the memory held).
void dr_label_construct(dungeonraid::SimpleLabelState*);
// Original SimpleLabel::SetColour 0x221c4: the colour (table of 50; others white) with alpha 255 on all 32 vertices.
void dr_label_set_colour(dungeonraid::SimpleLabelState*,std::int32_t colour);
// Original SimpleLabel::Initialise 0x23078: active, type, position, timer 0; speed 0.1 for types 1, 8, 9, 10, 0.08 for
// type 3, else Rand(0.1, 0.2) on stream 0; number; scale; digit size 0.5 for types 3, 4, 5, 7, 8, 9, 10, 26, 27, 29
// (else 1); RegenerateLabel.
void dr_label_initialise(dungeonraid::SimpleLabelState*,std::int32_t type,dungeonraid::Point position,std::int32_t number,float scale,
                         dungeonraid::RandomState*);
// Original SimpleLabel::SetNumber 0x2311c: for the types showing a number, a different number is set and the label rebuilt.
void dr_label_set_number(dungeonraid::SimpleLabelState*,std::int32_t number);
// Original SimpleLabel::SetPosition 0x22d6c / SetAlpha 0x22f64 (all 32 vertices).
void dr_label_set_position(dungeonraid::SimpleLabelState*,dungeonraid::Point);
void dr_label_set_alpha(dungeonraid::SimpleLabelState*,std::uint8_t alpha);
// Original SimpleLabel::Process 0x22f80: the timer advances; at its duration the label goes inactive; else it rises by
// dt * speed and its glyphs' alpha is (1 - (timer / duration)^2) * alpha.
void dr_label_process(dungeonraid::SimpleLabelState*,float dt);
// Original SimpleLabel::RegenerateLabel 0x22d7c: the glyphs (CreateNumberDefinition before the type's glyph for types 1,
// 2, 5, 7, 9, 10, 26, 27, after it for 3, 4, 8, 29; CreateTypeDefinition; CreateTypeDefinitionLast: type 8's last
// glyph), centred, four vertices each (SetVertex) with alpha 255.
void dr_label_regenerate(dungeonraid::SimpleLabelState*);
}
