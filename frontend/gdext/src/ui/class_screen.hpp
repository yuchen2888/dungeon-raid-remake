#pragma once
#include "strip.hpp"
#include "text.hpp"
#include "texts.hpp"
#include "recovered_session.hpp"
#include <string>
#include <vector>
namespace drui {
// The class screen's calls on the session (ClassScreen::Process's Game:: and CharacterClass:: calls), done by the
// embedding after the frame, each followed by what the rest of that Process shows of it (ClassView::after_request).
enum class ClassAction : std::int32_t {
    Tab=1,        // a tab chosen: Game::SerialiseClasses (dr_session_class_tab)
    Select,       // a class released on: Game::SetCurrentClass (dr_session_class_select; value: the class)
    Race,         // a race released on: the record's race (dr_session_class_set_race; value: the race)
    Perk,         // CharacterClass::SetPerk (dr_session_class_set_perk; value: slot, value2: perk or 255)
    Flaw,         // CharacterClass::SetFlaw (dr_session_class_set_flaw; value: slot, value2: flaw or 255)
    Skill,        // CharacterClass::SetReplacementSkill (dr_session_class_set_skill; value: slot, value2: skill or 255)
    Help,         // the Help button released on: HelpMenu::QueueHelp of the tab's texts (dr_session_class_help)
    Done,         // Return released on: Validate, SetCurrentClass, SerialiseClasses (dr_session_class_done)
};
struct ClassRequest { ClassAction action; std::int32_t value, value2; bool grabbed; };
// Where a class screen Help text (105..122) points: HelpMenu::QueueHelp's x, y and size (Show's last two).
struct HelpPlace { Point2 at; float size; };
// The original ClassScreen (NameScreen+0x299c), the class editor the setup screen's Edit opens: four tabs (class, race,
// perks & flaws, skills) over a backing, each tab's pictures in its own list of strips (+0xa10 + 12 x tab: buttons,
// their icons, panels, slots), the tab's texts (labels +0x9d4, +0x9f4, +0xa00, the level labels +0x9e8), Help and Return,
// and the icon being dragged (A +0xac0, B +0xb0c). The records it shows and edits are the session's (the class records,
// the current class); its touches call the session through requests and queue the click (sound 0).
class ClassView {
public:
    ClassView(const Font* font);
    void initialise(const Texts& t,const dungeonraid::SessionObjects& o);   // Initialise 0x10c784 (Edit pressed)
    void process(const dungeonraid::SessionObjects& o,float dt);            // Process 0x10ca70
    std::vector<ClassRequest> requests;                                     // this frame's session calls
    std::vector<std::int32_t>* sounds=nullptr;                              // where its Game::QueueSound calls go
    void after_request(const dungeonraid::SessionObjects& o,const ClassRequest& r);
    void render(GL& gl) const;                                              // Render 0x109ff4
    HelpPlace help_place(std::int32_t text) const;                          // Process's QueueHelp places, 105..122
    bool open() const {return open_;}
    float fade() const {return fade_;}
private:
    using Strips=std::vector<QuadStrip>;
    const dungeonraid::ClassProfile& record(const dungeonraid::SessionObjects& o) const {return o.classes[o.scroll->current];}
    void add_panel(std::int32_t tab,float w,float h,float x,float y);       // AddPanel 0x10c22c
    void select_tab(const dungeonraid::SessionObjects& o,std::int32_t tab); // SelectTab 0x10c4ac
    void set_alpha(std::uint32_t a);                                        // SetAlpha 0x1097e4
    void render_tab(GL& gl,std::int32_t tab) const;                         // RenderTab 0x109ef8
    void set_text(std::int32_t i,const std::string& text,std::vector<Label>& lines,std::int32_t& count);   // 0x10a24c
    void set_text(const std::string& text,float x,float y,float width,float scale,std::vector<Label>& lines,
                  std::int32_t& count,Colour colour);                                                    // 0x10a34c
    void set_class_level(std::int32_t level,std::int32_t i,const QuadStrip& strip);   // SetClassLevel 0x10a4f8
    void grab_icon(const dungeonraid::SessionObjects& o,std::int32_t tab,std::int32_t from,std::int32_t to,std::int32_t type);   // 0x10a684
    void update_perks(const dungeonraid::SessionObjects& o);                // UpdatePerks 0x10a974
    void show_race(std::int32_t race);                                      // ShowRace 0x10b1b8
    void update_race(const dungeonraid::SessionObjects& o);                 // UpdateRace 0x10b524
    void show_text(const char* title,const std::string& text,bool icon);    // ShowText 0x10b624
    void show_skill_text(std::int32_t skill);                               // ShowSkillText 0x10bc9c
    void show_flaw_text(std::int32_t flaw);                                 // ShowFlawText 0x10bd60
    void show_perk_text(std::int32_t perk);                                 // ShowPerkText 0x10bda8
    void update_class(const dungeonraid::SessionObjects& o);                // UpdateClass 0x10bdf0
    void update_abilities(const dungeonraid::SessionObjects& o);            // UpdateAbilities 0x109b90
    void release(const dungeonraid::SessionObjects& o);                     // Process: the touch ended
    void drag(const dungeonraid::SessionObjects& o);                        // Process: the touch held
    const Font* font_;
    const Texts* texts_=nullptr;
    QuadStrip s_[33];             // +0x4: the tabs 0..3, the tab line 4, the line under the tabs 5, the dimming 6, the
                                  // black 7, the backing 8, Help 9, Return 10, the tabs' slots 11..21 and icons 22..32
    std::int32_t tab_=0;          // +0x9d0
    std::vector<Label> text_;     // +0x9d4: the tab's text box (and tab 2's eight perk / flaw descriptions first)
    std::int32_t text_count_=0;   // +0x9e0
    bool perk_icon_=false;        // +0x9e4: tab 2's text box shows its icon
    bool skill_icon_=false;       // +0x9e5: tab 3's
    std::vector<Label> levels_;   // +0x9e8: the class levels on the class icons
    std::size_t level_first_=1;   // Render's first level label: 1 for class 0, else 0
    std::vector<Label> info_;     // +0x9f4: the class panel's lines
    std::vector<Label> race_;     // +0xa00: the race panel's lines
    std::int32_t race_count_=0;   // +0xa0c
    Strips tabs_[4];              // +0xa10
    std::vector<Label> tab_labels_;   // +0xa40
    std::int32_t skill_panel_=0, perk_slots_=0, perk_panels_=0, perk_text_=0;   // +0xa4c, +0xa50, +0xa54, +0xa58
    std::int32_t race_panels_=0, race_icons_=0, class_panels_=0, class_slots_=0;  // +0xa5c, +0xa60, +0xa64, +0xa68
    bool open_=false, closing_=false;   // +0xa6c, +0xa6d
    float fade_=0.0f;             // +0xa70
    std::int32_t touch_=0;        // +0xa74: a touch is down
    std::int32_t pressed_=-1;     // +0xa78: the class or race button pressed
    bool back_=false, help_=false;   // +0xa7c, +0xa7d: Return, Help pressed
    std::int32_t dragged_perk_=-1;   // +0xa80: the perk (0..9) or flaw (10..19) dragged
    bool draggable_[20]{};        // +0xa84: perks 0..9, flaws 10..19 that can be dragged
    Point2 grab_{0.0f,0.0f}, grab_icon_{0.0f,0.0f};   // +0xa98, +0xaa0: the dragged pictures' offsets from the touch
    std::int32_t dragged_skill_=-1;  // +0xaa8: the other skill (0..19) dragged
    bool skill_draggable_[20]{};  // +0xaac
    QuadStrip a_, b_;             // +0xac0, +0xb0c: the dragged frame and icon
};
}
