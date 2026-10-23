#pragma once
#include "text.hpp"
#include "texts.hpp"
#include "recovered_session.hpp"
#include <cstring>
#include <map>
#include <new>
#include <vector>
namespace drui {
// The original Interface (Game+0x4cdc): the bottom and top panels, the health jar, XP / upgrade bars, gold stack, their
// shadows, the four skill slots, the Menu and Stats buttons and the value labels. Its bytes are kept at their original
// offsets (quads at +0x0, +0x70, ...; the asm's offsets carry over unchanged); its labels, whose originals hold heap
// pointers, live beside them by offset. The game values it shows (Interface+0xcb8.. = Game+0x5994..: ui_health, the
// ceiling, ui_xp, ...) are the session's (ResourceState / PlayerStats); the Game pointer at +0x1030 is the session.
// Its menus (FoldoutMenu +0xd10, GameMenu +0xe24, StatsMenu +0xeb4) and Tooltip (+0x1038) are separate objects.
class InterfaceView {
public:
    static constexpr std::size_t size=0x1130;
    InterfaceView();                 // Interface::Interface 0x1f350 (the layout its trace shows)
    void set_fonts(const Font* font,const Font* score);
    void reset();                    // Interface::Reset 0x204a4
    // Interface::Process 0x20c64 (its drawing part), after the session's (the heartbeat as the frame found it)
    void process(const dungeonraid::SessionObjects& o,float dt,const dungeonraid::Heartbeat& heartbeat_before);
    void set_texts(const Texts& t) {texts_=&t;}
    // Interface::Render 0x1ebe0; skills: the equipped Skill objects (Game+0xbf90), their icon and level in each slot.
    void render(GL& gl,const dungeonraid::SessionObjects& o,const struct SkillView* skills);
    // Interface::PositionSkill 0x2003c: an equipped skill's icon at its slot (0.0765625 up and left of its centre).
    static Point2 skill_position(std::int32_t slot);
    void update_health_bar(const dungeonraid::SessionObjects& o,std::size_t quad,std::int32_t value);
    void update_xp_bar(std::size_t quad,std::int32_t value);
    void update_up_bar(const dungeonraid::SessionObjects& o,std::size_t quad,std::int32_t value);
    void update_gold_bar(std::size_t quads,std::int32_t value);
    void update_skull_value(const dungeonraid::SessionObjects& o);
    void update_sword_value(const dungeonraid::SessionObjects& o);
    void update_shield_value(const dungeonraid::SessionObjects& o);
    void update_shield_target(const dungeonraid::SessionObjects& o);
    void set_poison(std::int32_t poison);
    void set_health_shadow(const dungeonraid::SessionObjects& o,std::int32_t amount);
    void set_xp_shadow(const dungeonraid::SessionObjects& o,std::int32_t amount);
    void set_up_shadow(const dungeonraid::SessionObjects& o,std::int32_t amount);
    void set_gold_shadow(const dungeonraid::SessionObjects& o,std::int32_t amount);
    void update_health_colour();
    void process_heartbeat(const dungeonraid::SessionObjects& o,const dungeonraid::Heartbeat& before);
    void update_skills(const dungeonraid::SessionObjects& o);
    // Interface::SetClockState 0x1ffa8: the menu button shows the clock's picture (+0x10ac on) or "Menu".
    void set_clock_state(bool on);
    // Interface::SetClockString 0x2030c (the platform's, after Game::Process, with the clock on): the time, centred on
    // the menu button.
    void set_clock_string(const char* text);
    dungeonraid::Point target(std::int32_t type) const;   // Interface::GetTarget 0x1ff40
    dungeonraid::Point special_target(std::int32_t slot) const;   // Interface::GetSpecialTarget(int) 0x1e6ec
    dungeonraid::Point poison_position() const {return dungeonraid::Point{0.853124976f,1.38437498f};}
    // The bytes at their original offsets.
    Quad& q(std::size_t off) {return *std::launder(reinterpret_cast<Quad*>(mem_+off));}
    const Quad& q(std::size_t off) const {return *std::launder(reinterpret_cast<const Quad*>(mem_+off));}
    float f(std::size_t off) const {float v;std::memcpy(&v,mem_+off,4);return v;}
    void set_f(std::size_t off,float v) {std::memcpy(mem_+off,&v,4);}
    std::int32_t i(std::size_t off) const {std::int32_t v;std::memcpy(&v,mem_+off,4);return v;}
    void set_i(std::size_t off,std::int32_t v) {std::memcpy(mem_+off,&v,4);}
    std::uint8_t& b(std::size_t off) {return mem_[off];}
    Label& label(std::size_t off) {return labels_[off];}
private:
    void challenge_score(const dungeonraid::SessionObjects& o,float dt);   // Interface::Process 0x20db0
    const Texts* texts_=nullptr;
    std::string score_text_;   // the score line's text (kept from the last mode 0 / 1 frame)
    alignas(16) std::uint8_t mem_[size]{};
    std::map<std::size_t,Label> labels_;
};
}
