#pragma once
#include "menu.hpp"
namespace drui {
// The settings page (T050-D, the remake's own: the main menu's OpenFeint button, whose service is gone, opens it). It
// offers the language. Drawn as the original draws the game menu: the darkened screen, the game menu's panel pieces and
// purple buttons (tiles.png), the menu font; the languages' names are a picture of their own (LangNames: each written
// in its own language, so they show whatever language the game is in). Its words are the texts settings.title,
// settings.language and settings.back (English when the texts have none).
class SettingsView {
public:
    explicit SettingsView(const Font* menu_font);
    void open(const Texts& t,std::int32_t language);   // language: the shown one (its index in the names picture)
    void close() {open_=false;}
    bool is_open() const {return open_;}
    // A touch (phase 1 held, 2 ended, 0 none): a button acts when a touch begins on it. -1 nothing, 0.. a language
    // chosen (its index), Back for the back button.
    static constexpr std::int32_t Back=100;
    std::int32_t touch(std::int32_t phase,Point2 p);
    void render(GL& gl) const;
private:
    MenuQuads quads_;            // the panel (9), the buttons (3), the language names (2), the marks (2)
    Quad background_;
    Label title_, language_, back_;
    std::int32_t language_index_=0;
    std::int32_t previous_=1;
    bool open_=false;
};
}
