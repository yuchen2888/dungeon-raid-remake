#pragma once
#include "arrow.hpp"
#include "effects.hpp"
#include "help.hpp"
#include "screens.hpp"
#include "setup.hpp"
#include "intro.hpp"
#include "gameover.hpp"
#include "scores.hpp"
#include "unlock.hpp"
#include "tooltip.hpp"
#include "menu.hpp"
#include "interface.hpp"
#include "text.hpp"
#include "recovered_session.hpp"
#include <string>
#include <vector>
namespace drui {
// The presentation half of an original Tile (Tile is-a Quad; offsets of the 608-byte original): the tile's own quad
// (texture coordinates, colour, size; its position is the session's geometry.center), the cross +0xcc, the
// freeze / flame overlay +0x140 and the mortal-enemy glow +0x1b4 (its spin speed +0x228), and the four labels
// (attack +0xbc, defence +0xc0, health +0xc4, countdown +0xc8; Tile::InitialiseLabels). Game::SwapTiles swaps whole
// tiles, so a RefillEventKind::Swap swaps these too. The tile's game state stays in the session.
struct TileView {
    Quad quad, cross, overlay, glow;
    bool labels=false;
    Label attack, defence, health, countdown;
    float glow_speed=0.0f;
    TileView();
};
// The original game's drawing, recovered (T050-A): fed by the session's presentation events (as the original's
// presentation objects are by the game code) and drawn by render() as Game::Render 0xd1cc does, into gl. Built step
// by step against the original (frontend/tools/lockstep.py); what is not recovered yet is listed in
// docs/T050_GODOT_PLAN.md.
class Presenter {
public:
    Presenter();
    // Game::CreateFont 0x9e34 with the original's .fnt files from the local asset folder.
    bool load(const std::string& assets);
    void event(const dungeonraid::SessionObjects& o,dungeonraid::SessionSource source,const void* e);
    void render(const dungeonraid::SessionObjects& o);
    // What the frame's processing left for after the session's step (Interface::Process's own part, the game-over,
    // high-score and unlock pictures), done once the frame is over: before its sounds play and before it is drawn.
    void finish_frame(const dungeonraid::SessionObjects& o);
    GL gl;
    Font font, menu_font, score_font;
    TileView tiles[36];
    InterfaceView iface;
    ArrowView arrow;
    // The reward tokens (Game+0xb520, a vector of Token, each a Quad with its flight +0x70..): their pictures here,
    // their flight (position, scale, active) in the session's TokenMotion slots. token_slot: the slot the last
    // TokenEventKind::Initialise named, which the Motion events that follow dress.
    std::vector<Quad> tokens;
    std::int32_t token_slot=-1;
    // The SimpleLabels: Game::AddSimpleLabel's pool (Game+0xb540, in use Game+0xb54c), the cross labels of
    // Game::UpdateCrossVisibility (Game+0x164c8 / 0x164d4) and the current-damage label (Game+0xb550, colour 10 and
    // duration 0.2 from Game::Start). The leech, flame and spike labels are the session's (damage_labels).
    LabelPool labels, cross_labels;
    ParticlePool particles;    // Game::AddParticles's pool (Game+0xb530, in use Game+0xb53c)
    std::vector<Quad> flares;  // Game::AddFlare's quads (Game+0xbd80); the number shown is the session's flare_count
    // The enemy attack's dimming of the screen (Game+0xb91c: size 2 x 2 at (0.5, 0.5), black, Game::Start 0xbb1a), its
    // alpha the session's (Game+0xb92b), shown with the game menu's attack dimming switch on
    // (SaveSettings.dimming_13eca).
    Quad overlay;
    // The original's English texts (texts.txt beside the fonts), the level-up / shop / upgrade menu (Interface+0xd10)
    // and the five equipped items' pictures and texts it shows (Game+0xbe88..), built when the menu opens.
    Texts texts;
    FoldoutView foldout{&font};
    std::vector<ItemView> equipped;
    SkillView skills[4]{SkillView{&font},SkillView{&font},SkillView{&font},SkillView{&font}};   // Game+0xbf90
    bool menu_pending=false;
    bool interface_due=false;   // this frame's Interface::Process (heartbeat, highlights) still to run, with its dt
    float interface_dt=0.0f;
    // The in-game menu (Interface+0xe24, opened by Interface's menu button) and what its frame's processing found
    // before the session ran it (the menus open, the game menu's and Interface's buttons' state), to see what changed.
    GameMenuView game_menu;
    StatsMenuView stats_menu{&font};   // the character sheet (Interface+0xeb4, opened by Interface's stats button)
    HelpView help{&font};              // the help bubble (Game+0x10298)
    MainMenuView main_menu;            // the main menu (Game+0xc3fc)
    SetupView setup{&font,&menu_font}; // the new-game setup screen (Game+0x102dc)
    IntroView intro{&font};            // the story screen (Game+0xc330)
    bool intro_ended=false;            // its closing fade ended this frame (the embedding closes it in the session)
    GameOverView game_over{&font};     // the game-over tally (Game+0xcac0)
    struct GameOverBefore {            // the tally as its frame's step found it (process after the step)
        bool due=false;
        dungeonraid::GameOverTally tally{};
        std::int32_t state=0, phase=0;
        std::int32_t ended_line=-1, ended_value=0;   // the step's GameOverLine (a line ended at this value)
    } game_over_before;
    ScoreView scores{&font,&menu_font,&score_font};   // the high scores (Game+0xef68)
    struct ScoresBefore {              // the frame's start: was it open, the pages' state; did it run or show
        bool due=false, open=false, routed=false, shown=false;
        dungeonraid::ScorePages pages{};
    } scores_before;
    UnlockView unlock{&font};          // the unlock popup (Game+0x164d8)
    TooltipView tooltip{&font};        // Interface's tooltip (Interface+0x1038)
    // Game::QueueSound 0x903c for the drawing's own screens (the class, mode and story screens, the setup screen's
    // keyboard, Edit and mode help): into the session's queue (the embedding's sink, dr_session_queue_sound), which
    // holds every other sound and drops them while the sound is off.
    using SoundSink=void (*)(void*,std::int32_t);
    void set_sound_sink(void* context,SoundSink sink) {sound_context_=context;sound_sink_=sink;}
    void queue_sound(std::int32_t sound) {if(sound_sink_)sound_sink_(sound_context_,sound);}
    bool unlock_due=false;             // its frame's UnlockMenu::Process still to be shown (after the session's)
    bool setup_was_open=false;         // the setup screen was open last frame
    struct MenusBefore {
        std::uint8_t open[3]{};
        dungeonraid::OverlayMenu game{}, stats{};
        dungeonraid::InterfaceButtons buttons{};
        dungeonraid::Heartbeat heartbeat{};
    } menus_before;
    // The menu button under a touch while a menu is open: FoldoutMenu's (14..17 the options, 7 confirm), the game
    // menu's (9..15), the stats menu's (its tabs 10..15, 0 elsewhere inside); -1 none (outside the stats menu).
    std::int32_t menu_button_at(const dungeonraid::SessionObjects& o,Point2 touch) const;
    // The skill button under a touch (Interface::ProcessInput: the slots 0..3 (CursorInButton), the menu button 4 and
    // the stats button 5 (Quad::ContainsPoint); -1 none.
    std::int32_t skill_button_at(const dungeonraid::SessionObjects& o,Point2 touch) const;
    // The platform's clock (EAGLView drawView: Interface::SetClockString after Game::Process while the clock is on).
    void set_clock(const dungeonraid::SessionObjects& o,const char* text);
    dungeonraid::SimpleLabelState current{};
    Point2 label_target{};     // Interface::GetTarget(a) of a ResourceEvent Target, for the Label that follows it
    // The enemy attack's damage display (Game::Start 0xb98c..0xbb0a): the damage bar Game+0xb8ac (red) and the shield
    // bar Game+0xb98c (yellow) behind the damage label Game+0xb9fc (type 2, colour 11) and enemy 9's poison label
    // Game+0x151e4 (type 7, colour 15); the session sets their numbers, positions and alphas by event.
    Quad attack_bar[2];
    dungeonraid::SimpleLabelState attack_labels[2]{};
    Quad shield_chunk[2];      // the shield shatter's two halves (Game+0xbea8 / 0xbf18)
    float dt=0.0f;   // the frame's dt (Interface::Process gets it; the session's frame events do not carry it)
private:
    void* sound_context_=nullptr;
    SoundSink sound_sink_=nullptr;
    void initialise_labels(int i);
    void update_text(const dungeonraid::SessionObjects& o,int i,bool attack,bool defence,bool health);
    void update_countdown(const dungeonraid::SessionObjects& o,int i);
    void update_enemy_uv(const dungeonraid::SessionObjects& o,int i);
    void dim(const dungeonraid::SessionObjects& o,int i);
    void undim(const dungeonraid::SessionObjects& o,int i);
    void freeze(int i,bool on);
    void flame(int i,bool on);
    void token_picture(const dungeonraid::SessionObjects& o,const dungeonraid::SessionSmallEvent& e);
    void effect_event(const dungeonraid::SessionObjects& o,dungeonraid::SessionSource source,const void* e);
    void add_label(const dungeonraid::SessionObjects& o,std::int32_t type,Point2 at,std::int32_t number,std::int32_t colour,
                   float scale);
    void add_flare(const dungeonraid::SessionObjects& o,std::int32_t type,Point2 at,std::int32_t colour);
    void add_particles(const dungeonraid::SessionObjects& o,std::int32_t tile,std::int32_t type);
    Point2 label_position(const dungeonraid::SessionObjects& o,std::int32_t tile,const Label& l) const;
    void add_cross_label(const dungeonraid::SessionObjects& o,std::int32_t type,std::int32_t tile,std::int32_t colour);
    void current_label(const dungeonraid::SessionObjects& o,const dungeonraid::FrameEvent& e);
    void process_pools();
    void game_start(const dungeonraid::SessionObjects* o);
    void open_menu(const dungeonraid::SessionObjects& o);
    void show_help(const dungeonraid::SessionObjects& o,std::int32_t text);
    void render_main_menu(const dungeonraid::SessionObjects& o);
    void finish_interface(const dungeonraid::SessionObjects& o);
    void finish_game_over(const dungeonraid::SessionObjects& o);
    void finish_scores(const dungeonraid::SessionObjects& o);
    void finish_unlock(const dungeonraid::SessionObjects& o);
    void render_tile(const dungeonraid::SessionObjects& o,int i);
    void render_text(const dungeonraid::SessionObjects& o,int i);
    void render_overlays(const dungeonraid::SessionObjects& o,int i);
};
}
