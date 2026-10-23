#pragma once
#include "strip.hpp"
#include "class_screen.hpp"
#include "text.hpp"
#include "texts.hpp"
#include "recovered_session.hpp"
#include <map>
#include <vector>
namespace drui {
// The original NameScreen (Game+0x102dc), the new-game setup screen: the name panel (its box, Random, the on-screen
// keyboard that slides up from the bottom), the difficulty panel (four buttons; a challenge game's two mode buttons and
// Help instead), the class panel (ten classes with their levels, Help), the class's properties (class, race and skill
// pictures, four perks over four flaws, Edit), Back and Begin. Its pieces live at their original offsets (strip(),
// quad(), label()), its own state (fade, keyboard, pressed key) too; the name being entered and the rules' choices are
// the session's (SetupScreen, the class records, difficulty and mode): the touches call it through requests; the
// keyboard's, the name box's, Edit's and the mode help's clicks (sound 0) are its own, the others the session's.
// The setup and class screens' picture coordinates: GLfloat2 / 512 (texels), CharacterClass::GetIconCoords 0x1113e4
// (icon_coords: row a, column b, a 24-pixel picture in row small >= 0), Skill::GetIconUVs 0x2ac38 (skill_uvs: 0..1 of
// the 1024-pixel tiles texture), CharacterClass::IsPerkUnlocked 0x111548 and the enemies' pictures.
Point2 texels(Point2 p);
void icon_coords(std::int32_t a,std::int32_t b,std::int32_t small,Point2& p0,Point2& p1);
void skill_uvs(std::int32_t t,Point2& p0,Point2& p1);
bool perk_unlocked(const dungeonraid::ClassProfile& c,int k);
void enemy_uv(std::int32_t e,Point2& a,Point2& b);   // Tile::GetEnemyUV 0x3d2c4 (0..1 of tiles.png)
// NameScreen's panel (MakePanel 0x39a64: a frame with or without a heading band), button (MakeButton 0x398d8) and
// heading label (MakeHeadingLabel 0x387b4, in the menu font); ModeScreen's are the same code, ScoreScreen's too (its
// MakePanel 0x355e0 with a narrower band: 0.0375).
void make_panel(QuadStrip& s,bool heading,float w,float h,float x,float y,float band=0.0562499985f);
void make_button(QuadStrip& s,float w,float h,float x,float y);
void make_heading_label(const QuadStrip& s,Label& b,const Font* font,const std::string& text);
// The original ModeScreen (NameScreen+0x36f4), the challenge modes' explanation the setup screen's challenge Help
// opens: the two modes' buttons (choosing one is Game::SetMode, the session's), the chosen mode's picture, its four
// lines, scoring and special rules (ShowMode, again whenever the session's mode differs from the shown one, +0x2f4),
// and Back (+0xf0). While it is open NameScreen::Process runs only NameScreen::UpdateMode and this. Its touches click
// (sound 0).
class ModeView {
public:
    ModeView(const Font* font,const Font* menu_font);
    void initialise(const Texts& t);                         // Initialise 0x112a8c (the headings, once the fonts are made)
    void show();                                             // Show 0x112bec: a 0.3 s fade in
    void update_mode(const dungeonraid::SessionObjects& o);  // UpdateMode 0x113730 (NameScreen::UpdateMode calls it)
    std::int32_t process(const dungeonraid::SessionObjects& o,float dt);   // Process 0x112c0c: the mode chosen, or -1
    void render(GL& gl) const;                               // Render 0x112d3c
    bool open() const {return open_;}
    std::vector<std::int32_t>* sounds=nullptr;               // where its Game::QueueSound calls go (the setup screen's)
private:
    void set_alpha(std::uint8_t a);                          // SetAlpha 0x112ad8
    void show_mode(std::int32_t mode);                       // ShowMode 0x112f84
    void add_label(const std::string& text,const QuadStrip& panel,std::vector<Label>& lines,std::int32_t& count,float indent);
    const Font* font_;
    const Font* menu_font_;
    const Texts* texts_=nullptr;
    Quad black_, back_;                              // +0x10, +0x80
    QuadStrip done_, heading_;                       // +0xf0 (Back), +0x140
    Label heading_label_;                            // +0x18c
    QuadStrip buttons_[2], icons_[2];                // +0x1c4, +0x25c
    std::int32_t shown_=2;                           // +0x2f4
    QuadStrip intro_panel_, picture_;                // +0x2f8, +0x344
    std::vector<Label> intro_;                       // +0x390 (count +0x39c)
    std::int32_t intro_count_=0;
    QuadStrip scoring_;                              // +0x3a0
    Label scoring_label_;                            // +0x3ec
    std::vector<Label> scoring_lines_;               // +0x424 (count +0x430)
    std::int32_t scoring_count_=0;
    QuadStrip rules_;                                // +0x434
    Label rules_label_;                              // +0x480
    std::vector<Label> rules_lines_;                 // +0x4b8 (count +0x4c4)
    std::int32_t rules_count_=0;
    bool open_=false, closing_=false;                // +0x4, +0x5
    float timer_=0.0f;                               // +0x8
    std::int32_t previous_=0;                        // +0xc: the touch phase it last acted on
    bool pressed_=false;                             // +0x13c: Back held
};
// The session calls a setup screen touch makes (NameScreen::ProcessInput's Game:: calls), done by the embedding after the
// frame in this order: Random (dr_session_setup_random_name), Difficulty / Mode / Class (value: which), Begin
// (dr_session_setup_start), Help (dr_session_setup_help), Back (dr_session_setup_back), Edit (dr_session_class_open,
// then the class screen opens; its own calls are ClassView's requests) and ScreenMode (a mode chosen on the mode screen: dr_session_setup_mode, shown by the
// next frame's UpdateMode).
enum class SetupAction : std::int32_t { RandomName=1, Difficulty, Mode, Class, Start, Help, Back, Edit, ScreenMode };
struct SetupRequest { SetupAction action; std::int32_t value; };
class SetupView {
public:
    SetupView(const Font* font,const Font* menu_font);
    void initialise(const Texts& t);                                   // Initialise 0x395f0 (the fonts' texts)
    void show(const Texts& t,const dungeonraid::SessionObjects& o);    // Show 0x3bd60 (the session's NameScreen::Show)
    void select_class(const dungeonraid::SessionObjects& o);           // SelectClass 0x3b974 (the current class)
    void process(const dungeonraid::SessionObjects& o,float dt);       // Process 0x3cac0 with ProcessInput 0x3bff8
    std::vector<SetupRequest> requests;                                // this frame's session calls (see SetupAction)
    std::vector<std::int32_t> sounds;                                  // this frame's Game::QueueSound calls (and its screens')
    // What the rest of this frame's Process shows of a request once the session made it (the name, the chosen
    // difficulty, mode or class).
    void after_request(const dungeonraid::SessionObjects& o,const SetupRequest& r);
    // HelpMenu::QueueHelp's place for the class panel's Help texts 100..104 (and the class screen's 105..122).
    Point2 help_place(std::int32_t text) const;
    HelpPlace class_help_place(std::int32_t text) const {return class_.help_place(text);}
    // The class screen's session calls this frame, and what its Process shows of each once made (with the setup
    // screen's NameScreen::SelectClass after Game::SetCurrentClass).
    std::vector<ClassRequest>& class_requests() {return class_.requests;}
    void class_after(const dungeonraid::SessionObjects& o,const ClassRequest& r);
    void render(GL& gl,const dungeonraid::SessionObjects& o) const;    // Render 0x39dfc
    bool open() const {return open_;}
private:
    void update_name(const dungeonraid::SessionObjects& o);            // UpdateName 0x3981c
    void update_difficulty(const dungeonraid::SessionObjects& o);      // UpdateDifficulty 0x3bcd8
    void update_mode(const dungeonraid::SessionObjects& o);            // UpdateMode 0x3bc40
    void set_alpha(std::int32_t a);                                    // SetAlpha 0x38950
    void fade_begin(const dungeonraid::SetupScreen& n,float dt);       // Process: Begin's fade
    void process_input(const dungeonraid::SessionObjects& o,float dt); // ProcessInput 0x3bff8
    void press(std::size_t strip,std::size_t label);                   // a button pressed: both darker (/ 1.2)
    void release(std::size_t strip,std::size_t label);
    void make_panel(std::size_t strip,bool heading,float w,float h,float x,float y);   // MakePanel 0x39a64
    void make_button(std::size_t strip,float w,float h,float x,float y);              // MakeButton 0x398d8
    void make_button_label(std::size_t strip,std::size_t label,const std::string& text);   // MakeButtonLabel 0x39518
    void make_heading_label(std::size_t strip,std::size_t label,const std::string& text);  // MakeHeadingLabel 0x387b4
    QuadStrip& strip(std::size_t off) {return strips_[off];}
    const QuadStrip& strip(std::size_t off) const {return strips_.at(off);}
    Quad& quad(std::size_t off) {return quads_[off];}
    const Quad& quad(std::size_t off) const {return quads_.at(off);}
    Label& label(std::size_t off) {return labels_[off];}
    const Label& label(std::size_t off) const {return labels_.at(off);}
    Label& key_label(int k) {return labels_[0x10000+static_cast<std::size_t>(k)];}   // the 30 keys' labels (+0x28b0, on the heap)
    const Label& key_label(int k) const {return labels_.at(0x10000+static_cast<std::size_t>(k));}
    const Font* menu_font_;
    std::map<std::size_t,QuadStrip> strips_;
    std::map<std::size_t,Quad> quads_;
    std::map<std::size_t,Label> labels_;
    bool open_=false;            // +0x292d
    bool keyboard_=false;        // +0x292c: the keyboard is up
    bool closing_=false;         // +0x2934
    float timer_=0.0f;           // +0x2930: the 0.3 s fades
    float slide_=0.0f;           // +0x2928: the keyboard's slide, 0..1
    float blink_=0.0f;           // +0x2950: the cursor's blink
    bool shift_=true;            // +0x2958
    float repeat_=0.0f;          // +0x2954: the delete key's repeat
    std::int32_t pressed_=-1;    // +0x295c: the pressed key (0..29) or button (30 Random, 31 Edit, 32 Help, 33 Back, 34 Help)
    std::int32_t previous_=1;    // +0x2960: the touch phase of the last frame
    std::uint8_t begin_before_=0;   // Begin's alpha before this frame's fade, and the frame's dt (for after_request)
    float dt_=0.0f;
    ModeView mode_;              // +0x36f4
    ClassView class_;            // +0x299c
    const Texts* texts_=nullptr;
};
}
