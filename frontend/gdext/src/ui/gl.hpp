#pragma once
#include <cstdint>
#include <vector>
// The front end's presentation (T050-A): the original game's drawing code recovered, independent of any engine. It
// draws through this small OpenGL ES 1.1 stand-in (the calls the original makes: bound texture, model-view stack,
// vertex arrays, glDrawArrays), which records each draw with its vertices transformed to screen units (the screen is
// 1 wide, 1.5 high: glOrthof(0, 1, 1.5, 0)). The Godot layer only paints the recorded draws; the reference checks
// (frontend/tools/lockstep.py) compare them with what the original draws in the emulator (original_frame.py, whose
// recorder does the same transform in double precision).
namespace drui {
// The original's vertex (Quad+0x4 etc.: 0x14 bytes): position, RGBA, texture coordinates.
struct Vertex { float x, y; std::uint8_t colour[4]; float u, v; };
static_assert(sizeof(Vertex)==0x14,"vertex layout");
// Texture names of the original (GetTextureName): 1 tiles, 2 font, 3 icons, 4 menus, 5 fontMenu, 6 fontScore.
enum Texture : std::int32_t { NoTexture=0, Tiles=1, FontTexture, Icons, Menus, FontMenu, FontScore };
struct DrawVertex { double x, y; float u, v; std::uint8_t colour[4]; };
// tag: which screen drew it (GL::set_tag; the checks compare one screen's draws on their own).
struct Draw { std::int32_t texture, mode; std::uint8_t blend; std::uint32_t first, count; std::int32_t tag; };
enum DrawTag : std::int32_t { GameTag=0, MainMenuTag, NameTag, IntroTag, HelpTag, ScoreTag, GameOverTag, UnlockTag };
class GL {
public:
    GL();
    void clear();                 // a new frame: the recorded draws go, the state stays (as GL's)
    void bind_texture(std::int32_t name) {texture_=name;}
    void enable_texture(bool on) {textured_=on;}
    void enable_blend(bool on) {blend_=on;}
    void set_tag(std::int32_t tag) {tag_=tag;}
    void load_identity();
    void push();
    void pop();
    void translate(float x,float y);
    void scale(float x,float y);
    void rotate(float degrees,float z);
    // glDrawArrays(mode, 0, count) on interleaved original vertices (5 triangle strip, 4 triangles, 6 fan).
    void draw(std::int32_t mode,const Vertex* v,std::uint32_t count);
    const std::vector<Draw>& draws() const {return draws_;}
    const std::vector<DrawVertex>& vertices() const {return vertices_;}
private:
    struct Matrix { double a,b,c,d,e,f; };   // x' = a x + c y + e, y' = b x + d y + f
    void multiply(const Matrix& n);
    std::vector<Matrix> stack_;
    std::int32_t texture_=0;
    bool textured_=true,blend_=true;
    std::int32_t tag_=GameTag;
    std::vector<Draw> draws_;
    std::vector<DrawVertex> vertices_;
};
}
