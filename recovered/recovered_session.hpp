#pragma once
#include "recovered_schedule.hpp"
#include "recovered_motion.hpp"
#include "recovered_encounters.hpp"
#include "recovered_refill.hpp"
#include "recovered_skills.hpp"
#include "recovered_items.hpp"
#include "recovered_menu.hpp"
#include "recovered_save.hpp"
#include "recovered_scores.hpp"
#include "recovered_labels.hpp"
namespace dungeonraid {
// One game: every recovered state object, each Game field owned once, and the recovered units wired
// to each other as Game does it (see docs/T040_SESSION_PLAN.md). No original instruction runs here.
struct Session;
// The objects of a session. Pointers stay valid for the session's lifetime; the embedding may read
// them every frame and write the renderer-owned inputs (release_inputs->health_target, current_label_active,
// screens, input_target).
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
    ReleaseInputs* release_inputs;       // the health target (renderer-owned); the label positions are the damage labels'
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
    std::uint8_t* save;                  // the saved game (save_capacity bytes, Game+0x13ecf): length end->flag_146d0 (0: none),
                                         // end->flag_146d4 set when it changed -- the platform stores it then and clears the flag
    std::uint8_t* name;                  // renderer-owned: the player's name (Game+0xbe38, 17 bytes, saved and given to the scores)
    SaveSettings* settings;              // the help switch and the difficulty-changed flag DeserialiseState writes
    ClassSave* class_save;               // the class records' save (Game::SerialiseClasses at a game's end and a class scroll's
                                         // level-up): the platform stores it when changed_14adc is set and clears the flag
    ScoreBoard* scores;                  // the high-score tables (a game's end adds its score and skills); the platform stores a
                                         // changed table (dr_session_save_changed_scores) and gives them back at start-up
    SimpleLabelState* damage_labels;     // the leech, flame and spike SimpleLabels (3; Game+0xbfc0 / 0x14afc / 0x14e70), drawn
                                         // at their position and scale; their active bytes are extra->label_active[0..2]
};
// Every presentation event of the units, unchanged, with the unit it came from. The pointer is the
// unit's own event struct (for Selection, Motion, Refill and Ability a SessionSmallEvent).
enum class SessionSource : std::int32_t { Selection=1, Match, Token, Motion, Resource, Path, Refill, Generation, Encounter,
    AttackFlare, AttackAnim, AttackAbsorb, AttackShield, AttackWeaken, AttackHealth, AttackFade, AttackAll, Vampires,
    Turn, EndGame, GameOver, Score, Release, BoardEffect, Frame, Label, GameFrame, NewGame,
    Ability, Cross, Skill, Stats, Menu, Save };   // Ability: TurnHooks.ability (kind = enemy type 28, index = tile), wired to dr_destroy_upgrade; Stats: a StatsEvent;
                        // Cross: a CrossEvent of Game::UpdateCrossVisibility; Skill: a SkillEvent; Menu: a MenuEvent;
                        // Save: Game::SerialiseState's achievement (kind 1, a = achievement, b = value bits)
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
// Game::SetCurrentClass (T040-M2): the class (0..9) becomes the current one when it is unlocked, else class 0. A new
// session already holds Game::Start's roster (CharacterClass::Initialise of the ten classes: class 0 at level 1, the
// others locked) with class 0 current; the platform then gives the stored records back (dr_session_restore_classes).
void dr_session_set_current_class(dungeonraid::Session*,std::int32_t type);
// The main menu's three new games (T040-M1): kind 0 Game::NewGame 0x16590, 1 StartTutorial 0x164c0, 2 StartChallenge
// 0x1652c. The record mode (Game+0x14aed) is set for the challenge only; InitNewGame (time seeds the random streams);
// the tutorial's difficulty is 0 (Game+0x14ae0); the main menu closes; the help switch is on for the tutorial only; the
// queued help topics (Game+0x102d0) are HelpMenu::ResetHelp's (tutorial: topics 0..22 added) or ClearHelp's (none). The
// new-game setup screen (NameScreen::Show) follows; StartCyclingGamesColour and Interface::Process(0, false) are
// presentation.
void dr_session_start_game(dungeonraid::Session*,std::int32_t kind,std::uint32_t time);
// One Game::Process frame (dr_process_frame with every step wired) for the touch (phase, position).
dungeonraid::FrameRoute dr_session_frame(dungeonraid::Session*,float dt,std::int32_t touch_phase,dungeonraid::Point touch);
// Game::SerialiseState now: the saved game into SessionObjects.save, its length and changed flag into end (the
// session runs it itself where the original does: the end of a turn, ProcessInput's tail).
void dr_session_save(dungeonraid::Session*);
// Game::DeserialiseState: the saved game in SessionObjects.save over the current state (ContinueGame runs it after a
// new game); false when the buffer has no 0xff header (the format before version 1, not recovered).
bool dr_session_deserialise(dungeonraid::Session*);
// Game::ContinueGame: with a saved game, a new game (time seeds the random streams) that the save then overwrites
// (DeserialiseState) and the tile positions; false without one (the main menu shows Continue only with one).
bool dr_session_continue_game(dungeonraid::Session*,std::uint32_t time);
// Game::SerialiseClasses now: the class records into SessionObjects.class_save (the session runs it itself at a game's
// end and a class scroll's level-up; the class screen calls it after the player changes a class).
void dr_session_save_classes(dungeonraid::Session*);
// The platform's start-up: a stored high-score table (type 0..5) back (ScoreScreen::DeserialiseState); false: no such type.
bool dr_session_restore_scores(dungeonraid::Session*,std::int32_t type,const std::uint8_t* bytes,std::uint32_t length);
// The next changed high-score table serialised into SessionObjects.scores->bytes (length scores->length): its type,
// -1 when none changed (the platform stores it under its type and calls again).
std::int32_t dr_session_save_changed_scores(dungeonraid::Session*);
// The platform's start-up: stored class records back (Game+0x146d5) and Game::Start's DeserialiseClasses (false: the
// bytes do not hold ten records, nothing read).
bool dr_session_restore_classes(dungeonraid::Session*,const std::uint8_t* bytes,std::uint32_t length);
// The platform's start-up: stored save bytes back into the session (Game+0x13ecf and its length).
void dr_session_restore_save(dungeonraid::Session*,const std::uint8_t* bytes,std::uint32_t length);
// How the last frame's input step went (InputRoute; -1 when the input step did not run).
std::int32_t dr_session_input_route(const dungeonraid::Session*);
}
