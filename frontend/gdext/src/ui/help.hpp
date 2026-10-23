#pragma once
#include "menu.hpp"
#include <vector>
namespace drui {
// The original HelpMenu (Game+0x10298), the help bubble: 13 quads (HelpMenu::HelpMenu 0x37a64: the frame, its fill and
// the pointer above or below, laid out by SetSize 0x37568) and the text's lines (InitialiseLabels 0x37d04: black, cut to
// 0.88 at scale 0.1), at a position (+0x14) snapped to the 320-point grid. Which text shows, the queue and the fade
// timer are the session's (HelpPopup); this is its picture.
class HelpView {
public:
    explicit HelpView(const Font* font);
    // HelpMenu::Show 0x37f04: the text pointing at (x, y): below it when y < 0.75 (down further), else above (up).
    void show(const std::string& text,float x,float y,float up,float down);
    // HelpMenu::Process 0x38128's fade for a frame of dt (the popup's timer and closing flag before the session's step).
    void fade(float timer,bool closing,float dt);
    // The session's menu_button: 0 inside the bubble, -1 outside (Process' test).
    std::int32_t button_at(Point2 touch) const;
    void render(GL& gl) const;   // Render 0x379dc
private:
    void set_size(float width,float height,float pointer,bool below);
    void set_alpha(std::uint8_t a);
    const Font* font_;
    MenuQuads quads_;
    std::vector<Label> labels_;   // +0x28, grown and kept; count_ (+0x34) in use
    std::int32_t count_=0;
    Point2 at_{0.0f,0.0f};        // +0x14
    float width_=0.0f, height_=0.0f;   // +0x1c / +0x20
};
}
