#pragma once
#include "menu.hpp"
#include "text.hpp"
#include "texts.hpp"
#include "recovered_session.hpp"
#include <vector>
namespace drui {
// The original UnlockMenu (Game+0x164d8, a Menu of 9 quads), the popup a class scroll brings: the unlock line with
// the class's unlock description, or the level-up line with its new level (texts.txt), in a box (a nine-piece frame sized to the text,
// centred, kept on screen and on the 320-point grid) with the class's picture between title and text. While it is
// open the game pauses; a touch once it is fully shown closes it. Its alpha (all of it at once) and its open / closing
// state are the session's (UnlockPopup); this is its picture. Not yet: the bonus prompt (ShowPromo).
class UnlockView {
public:
    explicit UnlockView(const Font* font);                       // UnlockMenu::UnlockMenu 0x108d88
    // Show(ClassType, level) 0x1096fc, as the session shows it (ReleaseEventKind::UnlockMenu: a = class, b = level).
    void show(const Texts& t,std::int32_t type,std::int32_t level);
    void set_alpha(std::uint8_t a);                              // Process 0x1090e8's alpha, after the session's step
    void render(GL& gl) const;                                   // Render 0x109040
private:
    void show(const char* title,const char* text);               // Show(const char*, const char*) 0x1094b8
    void initialise_labels(const char* text);                    // InitialiseLabels 0x1092f0
    void set_size(float w,float h);                              // SetSize 0x108b50
    const Font* font_;
    MenuQuads quads_{9};                 // +0x4
    Label title_;                        // +0x10
    std::vector<Label> lines_;           // +0x48
    std::int32_t count_=0;               // +0x54
    Quad icon_;                          // +0x58
    Point2 at_{0.0f,0.0f};               // +0xcc
    std::int32_t texture_=Menus;         // +0xd8
};
}
