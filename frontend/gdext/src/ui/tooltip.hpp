#pragma once
#include "menu.hpp"
#include "text.hpp"
#include "texts.hpp"
#include <vector>
namespace drui {
// The original Tooltip (Interface+0x1038, a Menu of 9 quads), the box that explains what is under the finger: an enemy
// a stroke starts on (its name and description; the class's mortal enemy in red with the race's weakness), an equipped
// skill being pressed (name, description, cooldown) or a scroll in the shop. A nine-piece frame sized to the text, kept
// on screen and on the 320-point grid, above or below the point. It fades in to 240 and out at 255 x 8 a second
// (Process, the end of Interface::Process); all of it is presentation: the session only says when to show or hide it.
class TooltipView {
public:
    explicit TooltipView(const Font* font);                                       // Tooltip::Tooltip 0x2bc54
    void show_enemy(const Texts& t,std::int32_t enemy,std::int32_t mortal,std::int32_t race,Point2 at);   // 0x2c384
    void show_skill(const Texts& t,std::int32_t skill,std::int32_t max,std::int32_t current,Point2 at);   // 0x2c4a4
    void show_scroll(const Texts& t,std::int32_t skill,Point2 at);                                        // 0x2c2f8
    void hide() {if(visible_)hiding_=true;}                                       // Hide 0x2b7b8
    void hide_instantly();                                                        // HideInstantly 0x2bf64
    void process(float dt);                                                       // Process 0x2bfcc
    bool visible() const {return visible_;}
    void render(GL& gl) const;                                                    // Render 0x2bed4
private:
    void show(Point2 at,std::int32_t offset);                                     // Show(GLfloat2, int) 0x2b90c
    void initialise_labels(const Texts& t,const char* title,const std::string& text,Colour colour);   // 0x2c1d8
    void add_label(const std::string& text,Colour colour);                        // AddLabel 0x2c0a4
    void set_size(float w,float h);                                               // SetSize 0x2b7c8
    void set_alpha(std::uint8_t a);
    const Font* font_;
    MenuQuads quads_{9};                 // +0x4
    Label title_;                        // +0x10
    std::vector<Label> lines_;           // +0x48
    std::int32_t count_=0;               // +0x54
    bool visible_=false, hiding_=false;  // +0x58, +0x59
    Point2 at_{0.0f,0.0f};               // +0x5c
};
}
