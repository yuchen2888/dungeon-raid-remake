#pragma once
#include "recovered_session.hpp"
#include <cstdint>
#include <string>
#include <vector>
// The front end's one link to the recovered rules (T050-A): a native session plus what the platform layer does
// around it -- the layout targets of flying tokens, the board pitch, the touch and button inputs of a frame, and
// the stored bytes (the saved game, the class records, the high-score tables, the class scroll countdown). It
// has no Godot types, so bridge_test plays whole games through it headless; the Godot class only converts.
namespace drfront {
// Layout in session units: the screen is 1 wide and 1.5 high (the original 320 x 480 points / 320), the board
// fills y 0.246875 .. 1.246875 (Game::GetTileAtPosition), the resource bars sit above it, the skill buttons below.
constexpr float screen_height=1.5f;
constexpr float board_top=0.246875f;
// Token flight targets (Interface::GetTarget, here demonstration constants that match the Godot layout).
dungeonraid::Point resource_target(std::int32_t index);
dungeonraid::Point skill_target(std::int32_t slot);
// A stored blob: key "game" (the saved game; empty bytes: delete it), "classes", "scores0".."scores5", "spawn",
// "settings" (the game menu's switches the platform keeps: sound, clock, attack dimming, high frame rate, a byte each).
struct Blob { std::string key; std::vector<std::uint8_t> bytes; };
class Bridge {
public:
    Bridge();
    ~Bridge();
    Bridge(const Bridge&)=delete;
    Bridge& operator=(const Bridge&)=delete;
    // Game::Start's seeding from the platform's time() (dr_session_seed), once after creating and before restore.
    void seed(std::uint32_t time);
    // The platform's start-up, before the first game: a stored blob back ("classes", then the scores, "game",
    // "spawn", the order of Game::Start); unknown keys are ignored.
    void restore(const Blob& blob);
    // The iPhone platform's start-up switches without stored ones (EAGLView initWithCoder: attack dimming and high
    // frame rate on, the clock off; Game::Game turned the sound on), before restore.
    void platform_defaults();
    // The main menu: a new game (0 new game, 1 tutorial, 2 challenge; the setup screen opens), Continue (false
    // without a saved game).
    void new_game(std::int32_t kind,std::uint32_t seed);
    // The new-game setup screen (T040-M3, open while screens->name_12c09 is set): its buttons pass through to the
    // session; start (false without a name) opens the story screen, intro_done closes it and the game begins.
    void setup_random_name();
    bool setup_select_class(std::int32_t type);
    bool setup_difficulty(std::int32_t difficulty);
    bool setup_mode(std::int32_t mode);
    bool setup_start(std::uint32_t seed);
    void setup_help();   // the setup screen's Help: its five texts queue (dr_session_setup_help)
    // The setup screen's Back (dr_session_setup_back: sound 0, the screen fades out, MainMenu::Show and SetActive).
    void setup_back();
    void intro_done();
    // The class screen (Edit on the setup screen, T040-M4b): its edits of the current class pass through to the session.
    void class_tab();
    bool class_select(std::int32_t type);
    bool class_race(std::int32_t race);
    void class_perk(std::int32_t slot,std::int32_t perk);
    void class_flaw(std::int32_t slot,std::int32_t flaw);
    void class_skill(std::int32_t slot,std::int32_t skill);
    void class_help(std::int32_t tab);
    void class_done();
    void class_open();   // ClassScreen::Initialise's rules (dr_session_class_open: the current record validated)
    // The sound queue (dr_session_queue_sound for the drawing's own screens; next_sound: the next queued sound and the
    // variant GetSoundMapping drew, false when none is left -- taken after each frame and its calls).
    void queue_sound(std::int32_t sound);
    bool next_sound(std::int32_t& sound,std::int32_t& variant);
    bool continue_game(std::uint32_t seed);
    bool has_save();
    // The trial prototype's leaving of the game-over screen (godot/main.gd, which draws no end screens): the screen's
    // flag and state cleared. The original-look scene runs the recovered screens instead.
    void leave_game_over();
    // One frame: touch phase 0 none, 1 down / drag, 2 up; position in session units; the skill button (0..3)
    // and the menu button (14..17 options, 7 confirm) under the touch, -1 none.
    dungeonraid::FrameRoute frame(float dt,std::int32_t phase,dungeonraid::Point touch,std::int32_t skill_button,
                                  std::int32_t menu_button);
    // The blobs that changed since the last call (the platform writes each one, an empty "game" deletes it).
    std::vector<Blob> take_changed();
    dungeonraid::SessionObjects objects();
    // The presentation events of the session, passed on as they come (the drawing layer, ui/presenter).
    using Listener=void (*)(void*,dungeonraid::SessionSource,const void*);
    void set_listener(void* context,Listener listener) {listener_context_=context;listener_=listener;}
    // Interface::GetTarget (a resource's bar, by tile type) and GetSpecialTarget (a skill slot) for flying tokens,
    // from the drawing layer; without it the demonstration constants above.
    using Target=dungeonraid::Point (*)(void*,std::int32_t);
    void set_targets(void* context,Target resource,Target slot) {target_context_=context;resource_=resource;slot_=slot;}
    dungeonraid::FrameRoute last_route() const {return route_;}
    bool started() const {return started_;}
    long events() const {return events_;}
    long frames() const {return frames_;}
private:
    static void on_event(void*,dungeonraid::SessionSource,const void*);
    static void on_target(void*,std::int32_t kind,std::int32_t index,dungeonraid::Point*);
    static void on_token_start(void*,std::int32_t kind,dungeonraid::Point*);
    dungeonraid::SessionHost host_;
    dungeonraid::Session* session_;
    dungeonraid::FrameRoute route_=dungeonraid::FrameRoute::Done;
    bool started_=false;
    long events_=0,frames_=0;
    void* listener_context_=nullptr;
    Listener listener_=nullptr;
    void* target_context_=nullptr;
    Target resource_=nullptr,slot_=nullptr;
};
// The rules' own linking test (Tile::CanMatchType through dr_can_match, as UpdateDimming): the longest of a few
// random paths from every start tile; empty when none reaches three. For tests and the "hint" key.
std::vector<int> pick_path(const dungeonraid::SelectionState&,std::uint32_t& seed);
}
