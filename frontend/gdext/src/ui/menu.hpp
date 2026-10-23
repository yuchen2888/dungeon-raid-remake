#pragma once
#include "text.hpp"
#include "texts.hpp"
#include "recovered_session.hpp"
#include <vector>
namespace drui {
// The original Menu (Menu::Menu(int) 0x2d014): n quads of four vertices (+0x4, a heap array) laid out in points of a
// 320-point-wide screen and texture pixels of a 1024-pixel texture, drawn as fans.
struct MenuQuads {
    std::vector<Vertex> v;
    explicit MenuQuads(int quads):v(static_cast<std::size_t>(4*quads)) {}
    void set_vertex(int i,float x,float y,float u,float w);                   // SetVertex 0x2cb14
    void set_quad(int q,Point2 at,Point2 uv,Point2 size,float sx,float sy);  // SetQuad 0x2cb70: the picture size x scale
    void set_quad_colour(int q,std::uint8_t r,std::uint8_t g,std::uint8_t b,std::uint8_t a);   // 0x2cc5c
    void set_vertex_uv(int i,float u,float w);                                // 0x2ccac
    void set_quad_uv(int q,Point2 uv,Point2 size);                            // 0x2cce0
    void set_vertex_pos(int i,float x,float y);                               // 0x2cd5c
    void set_quad_pos(int q,float x,float y);                                 // 0x2cd90: moved, same size
    void set_quad(int q,Point2 uv,Point2 size);                               // 0x2ce38: at (0, 0)
    void set_quad_size(int q,float w,float h);                                // 0x2cedc
    void set_quad(int q,float x,float y,float w,float h);                     // 0x2cf68
    const Vertex* quad(int q) const {return v.data()+4*q;}
};
// The original Upgrade (Upgrade::Upgrade 0x260cc), the picture of a skill, an item or an item upgrade: a strip of four
// vertices 0.153125 square (+0x4) at a position (+0x54), cut from a grid of 50.03-pixel cells (SetIcon 0x26130).
struct Icon {
    Vertex v[4]{};
    Point2 position{0.28125f,0.0f};
    Icon();
    void set_icon(int column,int row,int texture_size,int x_offset);
    // Upgrade::RenderIcon 0x26230; extras: Skill::RenderExtras 0x2b120 draws the level label (skills only).
    void render(GL& gl,const Label* extras) const;
};
// A Skill object's picture and texts (Skill::Skill 0x2b1e0, Initialise 0x2b2a0 / 0x2b434): the icon, the level label
// (+0x94, shown on the icon for a skill), the name (+0x5c) and up to four stat lines (+0xd0, 64 bytes each).
struct SkillView {
    Icon icon;
    Label level;
    std::string name;
    std::string stats[4];
    std::int32_t type=-1, lines=0;
    explicit SkillView(const Font* font=nullptr):level(font) {}
    void skill(const Texts& t,std::int32_t type,std::int32_t level,std::int32_t max,const dungeonraid::SkillRecord* existing);
    void stat(const Texts& t,std::int32_t stat,const dungeonraid::SessionObjects& o);
    void render(GL& gl,bool extras) const {icon.render(gl,extras && type<=39?&level:nullptr);}
};
// An Item object's picture and texts: the icon (Item::Initialise(ItemType) 0x264a8: icons.png), the name (+0x5c,
// Item::GenerateName 0x263a0) and the two stat lines of Item::MakeStats 0x28e30 (+0xe4 / +0xe8), with each stat's
// line (+0x18c) and place in it (+0xec / +0xf0), and the stats themselves (+0x94).
struct ItemView {
    Icon icon;
    std::string name, line[2];
    std::int32_t type=0;
    std::int32_t line_of[20]{}, from[20]{}, to[20]{}, stats[20]{};
    void item(const Texts& t,const dungeonraid::ItemRecord& r);
};
// An ItemUpgrade's picture and texts (ItemUpgrade::Initialise 0x2da74): icon, name (+0x5c), stat line (+0x88).
struct UpgradeView {
    Icon icon;
    std::string name, stats;
    std::int32_t type=0;
    void upgrade(const Texts& t,std::int32_t type,std::int32_t amount,const ItemView& item);
    const std::string& description(const Texts& t,const dungeonraid::SessionObjects& o) const;   // GetDescription 0x2d034
};
// Font::SplitLines 0x1cc5c: the text cut at spaces into lines no wider than width at that scale.
std::vector<std::string> split_lines(const Font& font,const std::string& text,float scale,float width);
// The original FoldoutMenu (Interface+0xd10): the level-up (0), shop (1) and upgrade (2) menus that slide in over
// the board. The game part (choices, timers) is the session's (MenuState, dr_menu_*); this is its picture: 31 quads
// (FoldoutMenu::FoldoutMenu 0x23f50: the panel's frame and fill, the confirm button, two selection bars, option frames
// and the menu's title), the darkened screen behind (+0x9c), the options' icons and the labels.
class FoldoutView {
public:
    explicit FoldoutView(const Font* font);
    // FoldoutMenu::Initialise 0x24a54, its picture, on the options the session chose (menu open).
    void open(const Texts& t,const dungeonraid::SessionObjects& o,std::vector<ItemView>& equipped);
    // FoldoutMenu::Process 0x23c44 before the session's (timer < 0: taking input, nothing to show).
    void process(const dungeonraid::SessionObjects& o,float dt);
    void highlight(const Texts& t,const dungeonraid::SessionObjects& o,std::vector<ItemView>& equipped,std::int32_t button,
                   std::int32_t selection,bool on);                     // HighlightButton 0x237dc
    void confirm(bool pressed);                                         // the confirm button's colour
    // The button under the touch (FoldoutMenu::CursorInQuad 0x23160 for the confirm button 7, CursorInButton 0x231d8 for
    // the options 14..17; 17 not in the shop), -1 none.
    std::int32_t button_at(const dungeonraid::SessionObjects& o,Point2 touch) const;
    void render(GL& gl,const dungeonraid::SessionObjects& o,std::vector<ItemView>& equipped) const;   // Render 0x246a8
    std::int32_t type=0;
    SkillView& option(std::int32_t k) {return options_[k];}
    Point2 at() const {return at_;}   // the menu's place (+0x18), as it slides
    // The options Game::SetSkill exchanges with equipped skills as the level-up menu closes (first, then second; the
    // stat options are not exchanged), in the order of the session's PositionSkill events.
    std::vector<std::int32_t> exchanges;
private:
    void add_label(std::int32_t option,const std::string& text);        // AddLabel 0x2369c
    void update_labels(const dungeonraid::SessionObjects& o,const std::vector<ItemView>& equipped);   // 0x23234
    const ItemView* equipped_of(const std::vector<ItemView>& equipped,std::int32_t type) const;   // Game::GetItem
    const Font* font_;
    MenuQuads quads_;
    Quad background_;
    Point2 at_{1.0f,0.28125f};
    std::vector<Label> labels_;
    std::int32_t count_=0, lines_[4]{}, skill_options_=0, scroll_slot_=-1;
    SkillView options_[4], scroll_;
    ItemView items_[3];
    Point2 slot_{0.0f,0.0f};       // the fourth item slot's position (+0x44): the equipped item the chosen one replaces
    std::int32_t upgrade_items_[4]{};
    UpgradeView upgrades_[4];
};
// The original GameMenu (Interface+0xe24), the in-game menu Interface's menu button opens: 21 quads (GameMenu::GameMenu
// 0x31dac: the panel's frame and fill, the seven buttons 9..15 and the five switches' marks 16..20) over the darkened
// screen (+0x20). Its game part (fade timer, pressed button, the switches) is the session's (OverlayMenu, SaveSettings).
class GameMenuView {
public:
    GameMenuView();
    void show();                                              // GameMenu::Show 0x31b88: all transparent
    void fade(const dungeonraid::OverlayMenu& m);             // GameMenu::Process 0x32580's fade, after its timer step
    void press(std::int32_t button,bool on);                  // a button pressed (alpha 150) or let go (255)
    std::int32_t button_at(Point2 touch) const;               // CursorInQuad 0x31b28 for the buttons 9..15; -1 none
    // Render 0x31be4, with the switches' marks as Set{Sound,Help,Clock,Dimming,Smooth}State 0x3252c.. leave them.
    void render(GL& gl,const dungeonraid::SaveSettings& s);
private:
    MenuQuads quads_;
    Quad background_;
};
// The original StatsMenu (Interface+0xeb4), the character sheet Interface's stats button opens: 16 quads (the panel,
// whose height follows the shown page (SetMenuHeight 0x328d8), the page's backing 9 and the six tabs 10..15: the five
// equipped items and the class), the class's picture (a QuadStrip of one quad, +0x90), the 17 rows of names and values
// (CreateLabels 0x32bd4, SetLabelValue 0x32b00), the difficulty and score lines (+0x100 / +0x138) and the page's lines
// (+0xf4: an item's stats, or the race, its bonus, the perks and flaws). Its game part (the fade, the shown tab) is
// the session's (OverlayMenu).
class StatsMenuView {
public:
    explicit StatsMenuView(const Font* font);
    // StatsMenu::Show 0x3381c (equipped: the five equipped items' pictures, by item type; their icons move to the tabs).
    void show(const Texts& t,const dungeonraid::SessionObjects& o,std::vector<ItemView>& equipped);
    // StatsMenu::Process 0x33c0c's fade, after its timer step (closed: the items' icons opaque again).
    void fade(const dungeonraid::OverlayMenu& m,std::vector<ItemView>& equipped);
    // StatsMenu::Process: tab 10..15 shown in place of previous (-1 none).
    void tab(const Texts& t,const dungeonraid::SessionObjects& o,const std::vector<ItemView>& equipped,std::int32_t tab,
             std::int32_t previous);
    // The session's menu_button: -1 outside the panel (CursorOutsideMenu 0x327a0), the tab under the touch
    // (CursorInQuad 0x32878), else 0.
    std::int32_t button_at(Point2 touch) const;
    void render(GL& gl,const std::vector<ItemView>& equipped) const;   // Render 0x336ec
private:
    void set_menu_height(std::int32_t height);
    void set_label_value(std::int32_t row,std::int32_t base,std::int32_t bonus,bool percent,const Texts& t);
    void set_alpha(std::uint8_t a,std::vector<ItemView>& equipped);
    const Font* font_;
    MenuQuads quads_;
    Quad background_, strip_;      // strip_: the QuadStrip's one quad (texture size 512, at (80, 177) / 320)
    Point2 strip_at_{0.0f,0.0f};
    float height_=203.0f;          // +0x178
    float right_=0.928125024f;     // +0x174: the values' right edge
    Label names_[17], values_[17], difficulty_, score_;
    std::vector<Label> lines_;
    std::int32_t count_=0;         // +0x170: the page's lines shown
};
}
