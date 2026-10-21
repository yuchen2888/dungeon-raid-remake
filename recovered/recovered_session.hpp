#pragma once
#include "recovered_schedule.hpp"
#include "recovered_motion.hpp"
#include "recovered_encounters.hpp"
#include "recovered_refill.hpp"
#include "recovered_skills.hpp"
#include "recovered_items.hpp"
#include "recovered_menu.hpp"
namespace dungeonraid {
// One game: every recovered state object, each Game field owned once, and the recovered units wired
// to each other as Game does it (see docs/T040_SESSION_PLAN.md). No original instruction runs here.
struct Session;
// The objects of a session. Pointers stay valid for the session's lifetime; the embedding may read
// them every frame and write the renderer-owned inputs (release_inputs, current_label_active,
// extra->label_active, screens, input_target).
struct SessionObjects {
    StrokeState* stroke;                 // selection (board, path), resource counts, record / mode
    ResourcePreviewState* preview;
    MatchState* match;
    RuneState* rune;
    TokenQueue* tokens;
    ResourceState* resources;
    PathState* path;
    RefillState* refill;
    GenerationState* generation;
    AttackDamageState* damage;
    AttackAnimation* animation;          // counterattack is Game+0xbfba for EndOfTurn and ProcessAttack
    std::uint8_t* overlay_alpha;         // Game+0xb92b
    AttackProcessInputs* attack_inputs;
    SkillSlots* skills;
    TurnFlags* turn_flags;
    TurnFinishFlags* finish;
    EndGameState* end;
    std::uint8_t* activated;             // Tile+0x254 of the 36 tiles
    EndOfTurnState* end_of_turn;         // regen
    ReleaseFlights* flights;
    ReleaseInputs* release_inputs;       // renderer-owned label positions and the health target
    ClassProfile* classes;               // the 10 class records; the active one is classes[scroll->current]
    ClassScrollState* scroll;
    PlayerStats* player;
    NewGameExtra* extra;
    ShieldShatterState* shatter;
    TouchState* touch;
    FrameScreens* screens;
    std::int32_t* input_target;          // Game+0x58ac, -1 = none: the pressed skill button (skill_input->pressed)
    std::uint8_t* current_label_active;  // SimpleLabel active byte of the current-damage label (Game+0xb550)
    TokenMotion* motions;                // token slots (count: motion_count)
    std::uint32_t motion_count;
    std::int32_t* falling;               // the moving-tile list Game+0xb3f8 in order (count: falling_count)
    std::uint32_t falling_count;
    std::int32_t* skill_button;          // renderer-owned: the equipped skill button under the touch (-1 none)
    SkillInput* skill_input;             // the pressed skill button and the previous touch phase (Interface)
    ItemRecord* items;                   // the five equipped items (Game+0xbe88..0xbe98, the Item** vector Game+0xbe9c in order)
    MenuState* menu;                     // FoldoutMenu (Interface+0xd10): the level-up, shop and upgrade menus
    std::int32_t* menu_button;           // renderer-owned: the menu button under the touch (14..17 options, 7 confirm, -1 none)
    std::uint8_t* dimmed;                // 36 tiles: dimmed by Game::UpdateDimming (cannot continue the path)
};
// Every presentation event of the units, unchanged, with the unit it came from. The pointer is the
// unit's own event struct (for Selection, Motion, Refill and Ability a SessionSmallEvent).
enum class SessionSource : std::int32_t { Selection=1, Match, Token, Motion, Resource, Path, Refill, Generation, Encounter,
    AttackFlare, AttackAnim, AttackAbsorb, AttackShield, AttackWeaken, AttackHealth, AttackFade, AttackAll, Vampires,
    Turn, EndGame, GameOver, Score, Release, BoardEffect, Frame, Label, GameFrame, NewGame,
    Ability, Cross, Skill, Stats, Menu };   // Ability: TurnHooks.ability (kind = enemy type 28, index = tile), wired to dr_destroy_upgrade; Stats: a StatsEvent;
                        // Cross: a CrossEvent of Game::UpdateCrossVisibility; Skill: a SkillEvent; Menu: a MenuEvent
struct SessionSmallEvent { std::int32_t kind,index,a,b; };
struct SessionHost {
    void* context;
    void (*event)(void*,SessionSource,const void*);
    // Interface::GetTarget for a flying reward token (MotionHooks.target: kind 0 resource, 1 skill slot).
    void (*target)(void*,std::int32_t kind,std::int32_t index,Point*);
    // Interface::GetTarget(kind) as the start of a token thrown by an enemy ability (TurnHooks.token_start).
    void (*token_start)(void*,std::int32_t kind,Point*);
};
}
extern "C" {
// A session with zeroed state, wired; difficulty is the Game::QueueAchievement gate (1 in the tests).
dungeonraid::Session* dr_session_create(const dungeonraid::SessionHost*,std::int32_t difficulty);
void dr_session_destroy(dungeonraid::Session*);
// Pointers to every object (the token queue's request storage is reached through recovered_tokens).
dungeonraid::SessionObjects dr_session_objects(dungeonraid::Session*);
// Re-establishes the pointers between the objects after they were written as a whole (a loaded state).
void dr_session_link(dungeonraid::Session*);
// Sets the moving-tile list and the token slots (a loaded state; normally they come from play).
void dr_session_set_falling(dungeonraid::Session*,const std::int32_t* tiles,std::uint32_t count);
void dr_session_set_motions(dungeonraid::Session*,const dungeonraid::TokenMotion*,std::uint32_t count);
// Game::InitNewGame (dr_init_new_game) on the session's objects; time seeds the random streams.
void dr_session_new_game(dungeonraid::Session*,std::uint32_t time);
// One Game::Process frame (dr_process_frame with every step wired) for the touch (phase, position).
dungeonraid::FrameRoute dr_session_frame(dungeonraid::Session*,float dt,std::int32_t touch_phase,dungeonraid::Point touch);
// How the last frame's input step went (InputRoute; -1 when the input step did not run).
std::int32_t dr_session_input_route(const dungeonraid::Session*);
}
