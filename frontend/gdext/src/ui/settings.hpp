#pragma once
#include "menu.hpp"
#include <vector>
namespace drui {
// The settings page (T050-D, redone in T050-J; the remake's own: the main menu's OpenFeint button, whose service is
// gone, opens it). Drawn as the original draws the game menu: the darkened screen, the game menu's panel pieces and
// purple buttons (tiles.png), the menu font. Three pages:
// - the settings: the language (a row that opens the language page), the sound volume, vibration, the pictures (HD
//   or the original's), the original's smooth / attack dimming / clock switches (the game menu's, the session's
//   SaveSettings), the animation speed, and About;
// - the languages: one a row, each its name in its own words (the LangNames picture, a row each), the chosen one lit
//   and ticked; more than fit scroll;
// - About: the texts about.1.. .
// Its words are the texts settings.* (English when the texts have none). The frontend's own values (language,
// volume, vibration, pictures, speed) are the platform's to keep: configure() gives them, values() reads them back.
struct SettingsValues {
    std::int32_t language=0;   // index into the configured languages
    float volume=1.0f;
    bool vibration=true, hd=true, fast=false;
};
class SettingsView {
public:
    SettingsView(const Font* font,const Font* menu_font);
    // The languages offered (each its row in the names picture) and the frontend's values.
    void configure(const std::vector<std::int32_t>& name_rows,const SettingsValues& v);
    const SettingsValues& values() const {return values_;}
    void open(const Texts& t);
    void close() {open_=false;}
    bool is_open() const {return open_;}
    // A touch (phase 1 held, 2 ended, 0 none): -1 nothing; Changed a frontend value changed (Language: the language);
    // Volume the volume slides (no sound, not yet to keep); Switch one of the original's switches flipped in s; Page
    // another page shown; Closed the page closed. Buttons act when a touch begins on them; a language when a touch
    // ends on it without having scrolled.
    enum Result : std::int32_t { Nothing=-1, Changed=1, Language=2, Volume=3, Switch=4, Page=5, Closed=100 };
    std::int32_t touch(std::int32_t phase,Point2 p,dungeonraid::SaveSettings& s);
    void render(GL& gl,const dungeonraid::SaveSettings& s);
private:
    enum Shown { Main, Languages, About };
    struct Piece { std::int32_t texture; Vertex v[4]; };
    void layout(const dungeonraid::SaveSettings& s);
    void add(std::int32_t texture,float x,float y,float w,float h,Point2 uv,Point2 uv_size,Colour c);
    void panel();
    void button(float x,float y,float w,float h,bool lit);
    void label(const Font* f,const std::string& text,float x,float y,float scale,Colour c,int align,float room=0.0f);
    const std::string& word(const char* key,const char* english) const;
    float row_y(std::int32_t i) const;
    const Font* font_;
    const Font* menu_font_;
    const Texts* texts_=nullptr;
    std::vector<Piece> pieces_;
    std::vector<Label> labels_;
    std::size_t label_count_=0;
    Quad background_;
    std::vector<std::int32_t> name_rows_;
    SettingsValues values_;
    Shown shown_=Main;
    float scroll_=0.0f, scroll_from_=0.0f, touch_from_=0.0f;
    bool scrolled_=false, sliding_=false;
    std::int32_t previous_=1;
    bool open_=false;
};
}
