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
// The new-game setup screen (NameScreen, Game+0x102dc; T040-M3): what its rules use. Its on-screen keyboard, layout and
// alpha are the renderer's (the original also shortens a name that is wider than its box, by the font's widths).
struct SetupScreen {
    std::uint8_t challenge;   // NameScreen+0x3bbc: a challenge game (mode buttons instead of difficulty buttons)
    char name[19];            // +0x2935: the name being entered (a random name can be 17 characters)
    std::int32_t length;      // +0x2948
    std::uint8_t named;       // +0x294c: a name was entered (else the box shows "Enter name" and Start stays hidden)
    float timer;              // +0x2930 (T040-M7d): NameScreen::Show's 0.3 s fade-in, Back's 0.3 s fade-out
    std::uint8_t closing;     // +0x2934: fading out after Back (the screen closes when the timer runs out)
    std::int32_t previous_phase;   // +0x2960: the touch phase of its last input frame (1 after Show and the class screen)
};
// The setup calls below stand for a press in the last frame (call them after dr_session_frame): one is taken only when
// that frame ran the screen's input (the Name route with no fade running) and began a touch there (phase 1 after an input
// frame with phase 0); else it does nothing / returns false (T040-M7d). One press a frame. The class screen's own fades
// are the renderer's (T040-M4b): the original keeps the setup screen's previous phase at 1 until it has closed.
// The in-game menu (GameMenu, Interface+0xe24) and the statistics menu (StatsMenu, Interface+0xeb4) (T040-M5): open while
// screens->menus[1] / menus[2] (their +0xc). Their quads, labels, texts and fades are the renderer's.
struct OverlayMenu {
    std::int32_t previous_phase;   // +0x10: the touch phase of the last frame that took input
    std::int32_t pressed;          // +0x14: GameMenu: the pressed button 9..15 (-1 none); StatsMenu: the page's tab 10..15
                                   // (-1: the first page)
    std::uint8_t closing;          // +0x18: fading out (the menu closes when the timer runs out)
    float timer;                   // +0x1c: the 0.2 s fade (no input until it runs out)
};
// Interface's menu and stats buttons (Interface+0xcb4 / +0xcb5): touched; their menu opens when the touch ends.
struct InterfaceButtons { std::uint8_t menu_pressed, stats_pressed; };
// The main menu (MainMenu, Game+0xc3fc; open while screens->main_menu_c400; T040-M5, M7). Its quads, button colours and the
// "more games" colour cycle are the renderer's.
struct MainMenuScreen {
    float timer;                  // +0x8: MainMenu::FadeIn's 0.5 s / FadeOut's 0.3 s
    std::uint8_t fading;          // +0xc: fading in (else out: the menu closes when the fade-out ends)
    std::uint8_t splash;          // +0x8f: the title's alpha (255 at start-up, 500 less per second; no input until 0)
    std::uint8_t has_save;        // +0x4e4: a saved game exists (Continue shown, a new game asks first)
    std::uint8_t has_scores;      // +0x4e5: high scores exist (High scores shown)
    std::uint8_t bonus;           // +0x4e6: the bonus button is shown (the platform's)
    std::int32_t pressed;         // +0x4e0: the touched button 0..7 (-1 none)
    std::uint8_t confirm;         // +0x6a8: "overwrite the saved game?" open
    std::uint8_t chosen;          // +0x6b0: its answer (yes)
    std::uint8_t closing;         // +0x6b1: it is fading out
    std::int32_t confirm_kind;    // +0x6ac: the game a yes starts (0 new game, 1 challenge, 2 tutorial)
    float confirm_timer;          // +0x6b4: its 0.3 s fades
    std::int32_t previous_phase;  // +0x6b8
};
// The game-over screen (GameOverScreen, Game+0xcac0; open while end->game_over_screen, +0x4; its state is
// screens->game_over_state_cc1c, +0x15c: 0 fade-in, 1 a pause and the panel, 2 the tally, 3 the last 10 s and the
// fade-out to the high scores; T040-M7). Its texts, icons, panels and fades are the renderer's.
struct GameOverTally {
    std::uint8_t win;             // +0x158: GameOverScreen::Initialise(win)
    std::int32_t line;            // +0x160: the tally's line: 0..2 headings, 3 turns, 4 level, 5 XP, 6 gold, 7 upgrade points (a
                                  // challenge game's mode 1: its crossing average / best / samples), 8 the class's 5 icons,
                                  // 9 skills, 10 perks, 11 flaws, 12 score, 21 the enemies left on the board (-1 before 0)
    float progress;               // +0x164: the state's fade; in a line: 1 = shown whole (a tap)
    float wait;                   // +0x168: the pause before the next line (0.5 s; 10 s at the end; a tap ends it)
    float value;                  // +0x16c: a number line's counting value (times the rate each frame)
    float rate;                   // +0x170: its growth (+0.1 a second)
    std::int32_t shown[5];        // +0x174..+0x184: icons shown: the class's (line 8), skills (9), perks (10), flaws (11), enemies (21)
    float tick;                   // +0x188: 0.2 s between icons
    std::int32_t perks,flaws,enemies;   // +0x18c / +0x190 / +0x194: their counts (GameOverScreen::InitIcons)
    std::int32_t previous_phase;  // +0x24a4
};
// The high-score screen (ScoreScreen, Game+0xef68; open while screens->score_ef6c, +0x4; T040-M7): six pages (0..3 the
// difficulties, 4..5 the challenge modes) that a drag or the arrow buttons slide; its panels, texts and fades are the
// renderer's.
struct ScorePages {
    std::uint8_t closing;         // +0x5: fading out (Back): the screen closes when the timer runs out
    float timer;                  // +0x8: 0.3 s fades
    std::int32_t previous_phase;  // +0x15c
    std::uint8_t dragging;        // +0x160: a drag across the pages
    float last_x,start_x;         // +0x164 / +0x168: the touch's x last frame / where the drag began
    float velocity;               // +0x16c: the drag's speed (x per second, smoothed: 0.4 new)
    float drag;                   // +0x170: the pages' shift (the drag's x; while sliding, toward the direction: 0.3 a frame)
    float unused_174;             // +0x174
    std::uint8_t sliding;         // +0x178: sliding after a drag or an arrow; when it is in place the page changes
    std::int32_t direction;       // +0x17c: 1 the page before, -1 the page after, 0 back where it was
    std::uint8_t back,left,right; // +0x1cc / +0x1cd / +0x1ce: buttons touched
    std::int32_t page;            // +0x1d0
};
// The unlock popup (UnlockMenu, Game+0x164d8; T040-M8): a class levelled up or unlocked by a class scroll
// (UnlockMenu::Show(ClassType, level): sound 12). Open while screens->unlock_165a0 (+0xc8), and then Game::Process runs only
// UnlockMenu::Process (the game pauses). Its texts, icon and layout are the renderer's; its alpha is state: the fade-in
// starts from what the last fade-out left (0 at start-up).
struct UnlockPopup {
    std::uint8_t closing;         // +0xc9: fading out
    std::uint8_t alpha;           // the panel's alpha (its first vertex's, +4 -> +0xb): 255 a second x 8 in / out
    std::int32_t previous_phase;  // +0xd4: the touch phase when fully shown (1 after Show)
};
// The help popup (HelpMenu, Game+0x10298; T040-M6): open while screens->help_102a4 (+0xc), and then Game::Process runs only
// HelpMenu::Process (the game pauses). The topics still to come are finish->help_flags_102d0 (+0x38): each shows once. Its
// texts, box layout and fades are the renderer's.
struct HelpPopup {
    std::uint8_t closing;          // +0xd: fading out
    float timer;                   // +0x10: the 0.2 s fade (no input until it runs out)
    std::int32_t previous_phase;   // +0x24 (HelpMenu::Show sets 1: a touch must end before a new one counts)
    std::int32_t text;             // the shown text: a topic 0..22 (HelpMenu::Initialise) or a screen text (HelpMenu::QueueHelp):
                                   // 100..104 the setup screen's, 105..109 / 110..113 / 114..117 / 118..122 the class screen's
                                   // tabs 0..3
    Point at;                      // HelpMenu::Show's position and size: a topic's as the game gives them (a screen text's and
    float width,height;            // topics 19 / 20's position are the renderer's: 0)
    std::int32_t skill_slot;       // topics 19 / 20: the skill button it points at, else -1
    std::uint32_t queued;          // the screen texts waiting behind it (std::list<HelpItem> +0x3c), oldest first (at most 64; more cannot
                                   // occur: the screens that queue them take no input while the popup is open)
    std::int32_t queue[64];
};
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
    std::int32_t* skill_button;          // renderer-owned: the equipped skill button under the touch (0..3), Interface's
                                         // menu button (4) or stats button (5), -1 none
    SkillInput* skill_input;             // the pressed skill button and the previous touch phase (Interface)
    ItemRecord* items;                   // the five equipped items (Game+0xbe88..0xbe98, the Item** vector Game+0xbe9c in order)
    MenuState* menu;                     // FoldoutMenu (Interface+0xd10): the level-up, shop and upgrade menus
    std::int32_t* menu_button;           // renderer-owned: the menu button under the touch. FoldoutMenu: 14..17 options, 7
                                         // confirm, -1 none; game menu: 9..15, -1 none; stats menu: tabs 10..15, -1 outside
                                         // the menu, any other value inside it; help popup: 0 inside the box, -1 outside;
                                         // main menu (T040-M7): buttons 0..7 (7: the bonus button), 8 more games, 10 yes / 11 no of the
                                         // confirmation, -1 none (under the last touch also when it has ended); high scores:
                                         // 1 Back, 2 the left arrow, 3 the right arrow, plus 16 when the touch is on the pages'
                                         // rows (a drag starts there), -1 none
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
    SetupScreen* setup;                  // the new-game setup screen (open while screens->name_12c09 is set)
    OverlayMenu* game_menu;              // GameMenu (open while screens->menus[1])
    OverlayMenu* stats_menu;             // StatsMenu (open while screens->menus[2])
    InterfaceButtons* interface_buttons;
    MainMenuScreen* main_menu;
    HelpPopup* help;                     // the help popup (open while screens->help_102a4)
    ScorePages* scores_screen;           // the high-score screen (open while screens->score_ef6c)
    GameOverTally* game_over;            // the game-over screen (open while end->game_over_screen)
    std::uint32_t* time;                 // platform-owned (T040-M7): its time() -- the games the main menu starts seed their
                                         // random streams with it (as dr_session_start_game's time)
    UnlockPopup* unlock;                 // the unlock popup (open while screens->unlock_165a0; T040-M8)
};
// Every presentation event of the units, unchanged, with the unit it came from. The pointer is the
// unit's own event struct (for Selection, Motion, Refill and Ability a SessionSmallEvent).
enum class SessionSource : std::int32_t { Selection=1, Match, Token, Motion, Resource, Path, Refill, Generation, Encounter,
    AttackFlare, AttackAnim, AttackAbsorb, AttackShield, AttackWeaken, AttackHealth, AttackFade, AttackAll, Vampires,
    Turn, EndGame, GameOver, Score, Release, BoardEffect, Frame, Label, GameFrame, NewGame,
    Ability, Cross, Skill, Stats, Menu, Save, Interface };   // Ability: TurnHooks.ability (kind = enemy type 28, index = tile), wired to dr_destroy_upgrade; Stats: a StatsEvent;
                        // Cross: a CrossEvent of Game::UpdateCrossVisibility; Skill: a SkillEvent; Menu: a MenuEvent;
                        // Save: Game::SerialiseState's achievement (kind 1, a = achievement, b = value bits);
                        // Interface: an InterfaceEventKind (a SessionSmallEvent)
struct SessionSmallEvent { std::int32_t kind,index,a,b; };
// The game menu, the stats menu and Interface's two buttons (T040-M5). Sound: Game::QueueSound(a). Setting: a game menu
// switch changed (index = its button: 10 sound, 11 help, 12 clock, 13 attack dimming, 14 high frame rate; a = the new
// state): GameMenu::Set*State, Interface::SetClockState (12) and MainMenu::SetSoundState (10) are presentation.
// MainMenu: the game menu's quit button (15) ran MainMenu::FadeIn. Help: the help popup shows a text (HelpMenu::Show,
// index = SessionObjects.help->text; T040-M6); when the last queued topic shows, the help switch goes off first (Setting 11, 0).
// MoreGames / BonusRequest / Dashboard: the main menu's "more games" and bonus buttons (Game::ShowMoreGames /
// ShowBonusRequest) and button 6 (Game+0x15545: the original launches OpenFeint's dashboard) -- the platform's.
// MainMenuButton: a main-menu button 0..6 acted (index; 0 Continue, 1 New game, 2 Challenge, 3 Tutorial, 4 High scores,
// 5 sound, 6 Dashboard), before its action -- for 1..3 over a saved game when the confirmation's yes starts it.
// NagScreen: the game-over tally ended (Game::ShowNagScreen: the platform's, the original's promotion).
enum class InterfaceEventKind : std::int32_t { Sound=1, Setting, MainMenu, Help, MoreGames, BonusRequest, Dashboard, MainMenuButton,
    NagScreen };
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
// Game::SetCurrentClass (T040-M2): the class (0..9) becomes the current one when it is unlocked, else class 0; the
// units' views of the current record (race, perks, flaws, type, level) follow it (T040-M3). A new
// session already holds Game::Start's roster (CharacterClass::Initialise of the ten classes: class 0 at level 1, the
// others locked) with class 0 current; the platform then gives the stored records back (dr_session_restore_classes).
void dr_session_set_current_class(dungeonraid::Session*,std::int32_t type);
// Game::SetMode 0x83e8 / SetDifficulty 0x842c / SetName 0x8470 (T040-M3): the mode (0..1, StrokeState.mode_14ae8), the
// difficulty (0..3, MatchState.spawn_enabled_14ae0) or the name (16 characters at most) and its changed flag
// (SaveSettings) when it differs.
void dr_session_set_mode(dungeonraid::Session*,std::int32_t mode);
void dr_session_set_difficulty(dungeonraid::Session*,std::int32_t difficulty);
void dr_session_set_name(dungeonraid::Session*,const char* name);
// The setup screen's buttons (NameScreen::ProcessInput 0x3bff8, T040-M3). The name the renderer's keyboard edits is
// SessionObjects.setup (name, length, named). Random name: NameScreen::GenerateRandomName 0x3882c (stream 0: "%s%s" of
// a start and an end part, or "%s%s %s%s" of two pairs) and the name counts as entered. A class button selects an
// unlocked class only (Game::SetCurrentClass); a challenge game's two mode buttons Game::SetMode, the other games' four
// difficulty buttons Game::SetDifficulty (false when the screen has no such button). Start (shown only with an entered
// name): Game::SetName(the name), the story screen opens (IntroScreen::Initialise; its random draws come before the
// new game re-seeds), Game::InitNewGame (time seeds the random streams), the setup screen closes; false without a name.
void dr_session_setup_random_name(dungeonraid::Session*);
bool dr_session_setup_select_class(dungeonraid::Session*,std::int32_t type);
bool dr_session_setup_mode(dungeonraid::Session*,std::int32_t mode);
bool dr_session_setup_difficulty(dungeonraid::Session*,std::int32_t difficulty);
bool dr_session_setup_start(dungeonraid::Session*,std::uint32_t time);
// Back (T040-M7d; NameScreen::ProcessInput, its button at +0x154, acting only while the renderer's keyboard is hidden):
// sound 0, the setup screen fades out (0.3 s; the frame's Name route counts it down and then closes the screen), the main
// menu shows again (MainMenu::Show, MainMenu::SetActive(true) with the pressing touch down). False while a fade runs.
bool dr_session_setup_back(dungeonraid::Session*);
// The story screen's end (IntroScreen::Process 0x2dd04: Continue pressed and the fade done): it closes and
// Game::SerialiseState saves the new game.
void dr_session_intro_done(dungeonraid::Session*);
// The class screen (ClassScreen, T040-M4b; opened from the setup screen): its dragging, tabs and texts are the
// renderer's. Edits act on the current class record (SessionObjects.classes[scroll->current]) and the units' views
// follow it. Choices: what may be dragged now (dr_class_choices: perks / flaws 0..9, the class's other skills 0..19,
// dr_class_other_skills). A class icon selects an unlocked class (Game::SetCurrentClass); a race icon can be dropped on
// the class when the race is unlocked and the class can choose (dr_race_unlocked / dr_class_can_choose_race: the
// record's race is set); perk, flaw and skill slots take CharacterClass::SetPerk / SetFlaw / SetReplacementSkill (255
// takes one off). A tab change saves the records (Game::SerialiseClasses); Done validates the current record
// (CharacterClass::Validate), makes its type the current class (Game::SetCurrentClass) and saves the records.
void dr_session_class_choices(dungeonraid::Session*,std::uint8_t perks[10],std::uint8_t flaws[10],std::uint8_t skills[20]);
bool dr_session_class_select(dungeonraid::Session*,std::int32_t type);
bool dr_session_class_set_race(dungeonraid::Session*,std::int32_t race);
void dr_session_class_set_perk(dungeonraid::Session*,std::int32_t slot,std::int32_t perk);
void dr_session_class_set_flaw(dungeonraid::Session*,std::int32_t slot,std::int32_t flaw);
void dr_session_class_set_skill(dungeonraid::Session*,std::int32_t slot,std::int32_t skill);
void dr_session_class_tab(dungeonraid::Session*);
void dr_session_class_done(dungeonraid::Session*);
// The main menu's three new games (T040-M1): kind 0 Game::NewGame 0x16590, 1 StartTutorial 0x164c0, 2 StartChallenge
// 0x1652c. The record mode (Game+0x14aed) is set for the challenge only; InitNewGame (time seeds the random streams);
// the tutorial's difficulty is 0 (Game+0x14ae0); the main menu closes; the help switch is on for the tutorial only; the
// queued help topics (Game+0x102d0) are HelpMenu::ResetHelp's (tutorial: topics 0..22 added) or ClearHelp's (none). The
// new-game setup screen (NameScreen::Show) follows; StartCyclingGamesColour and Interface::Process(0, false) are
// presentation. The new-game setup screen opens (NameScreen::Show(the name, challenge), T040-M3): the name (16
// characters at most, counted as entered) or, without one, the placeholder "Enter name". Last, Interface::Process(0, false)
// (dr_session_interface_process with dt 0, input not ready; T040-M6).
void dr_session_start_game(dungeonraid::Session*,std::int32_t kind,std::uint32_t time);
// Interface::Process 0x20c64 for one frame's input (T040-M5; dr_session_frame runs it as Game::Process does, with the
// frame's dt and touch). An open FoldoutMenu runs (dr_menu_process), else an open game menu (GameMenu::Process 0x32580),
// else an open stats menu (StatsMenu::Process 0x33c0c), else, with input ready, Interface::ProcessInput 0x209e4.
// The menus first let their 0.2 s fade run out (a closing menu then closes). The game menu: a touch's start (phase 1
// after phase 0) on a button (menu_button 9..15) presses it (sound 0); the touch's end (phase 2 or 3) still on the
// pressed button acts: 9 closes it (fade-out, Game::UpdateHelpState: queued help topics dropped when help is off, all
// 23 queued again when none are and help is on), 10..14 switch sound / help / clock / attack dimming / high frame rate
// (sound 0 when the sound comes on), 15 MainMenu::FadeIn (the main menu opens, 0.5 s fade; the game menu stays open
// beneath it until Interface::Reset). The stats menu: a touch's start outside the menu (menu_button -1) closes it
// (sound 0, fade-out); on a tab other than the shown one (10..15) shows that tab (sound 0); other values: inside, on no
// tab. Interface::ProcessInput: besides the skill buttons (dr_skill_input), a touch's start on the menu button
// (skill_button 4) or the stats button (5) touches it (sound 0); the touch's end opens its menu (GameMenu::Show /
// StatsMenu::Show: fade-in, nothing pressed, the first page). Interface::Reset (a new game) closes both menus and
// clears the touched buttons and the pressed skill button. Then, with no FoldoutMenu open, Interface::ProcessHeartbeat:
// help 14 when the shown health is at most 0.35 of the shown ceiling (ResourceState.ui_health / PlayerStats
// .ui_health_ceiling_5998; the heartbeat's beat and sound are presentation).
void dr_session_interface_process(dungeonraid::Session*,float dt,bool input_ready);
// The help popup (T040-M6). Topics: HelpMenu::Initialise 0x380b8, wherever the game shows one (dr_session_frame and the
// other calls run them): nothing while the popup is open or when the topic is not queued (help_flags_102d0 bit); else its
// bit clears (none left: the help switch goes off) and the popup shows it (fade-in 0.2 s, previous phase 1). Screen texts:
// HelpMenu::QueueHelp 0x38268, shown at once when the popup is closed, else queued. HelpMenu::Process 0x38128 (route Help):
// after the fade, a touch's start (phase 1 after phase 0) inside the box (menu_button >= 0; -1 outside) fades it out; when
// that ends it closes and the oldest queued text shows. The setup screen's help button (NameScreen::ProcessInput: sound 0,
// texts 100..104) and the class screen's (ClassScreen::Process, released on it: the shown tab's texts; false for another
// tab) queue the screen texts; while the popup is open Game::Process runs neither screen.
void dr_session_setup_help(dungeonraid::Session*);
bool dr_session_class_help(dungeonraid::Session*,std::int32_t tab);
// One Game::Process frame (dr_process_frame with every step wired) for the touch (phase, position). The screens' routes
// run natively (T040-M6, M7): Help (HelpMenu::Process), GameOver (GameOverScreen::Process 0x30c28: 2 s fade-in; 1 s pause
// and 1 s panel; the tally -- a 0.5 s pause before each line (sound 27), numbers counting up (times a rate growing 0.1 a
// second; sound 2 as the whole part changes, 10 when shown whole), icons one each 0.2 s (sound 2, the enemies 14), a tap
// showing the line whole and ending a pause; then Game::ShowNagScreen, 10 s (a tap ends them) and a 2 s fade-out; from
// its state 3 Game::Process shows the high scores: the challenge mode's page, else the difficulty's, without a fade-in),
// Score (ScoreScreen::Process 0x367f8: 0.3 s fades; a drag on the rows or an arrow slides to the page before / after
// (0.3 of the way a frame, in place within 0.00625; a drag counts past 0.1 of speed or half a page), the page saved with
// Game::SetScorePage; Back: the main menu shows (MainMenu::Show, SetActive) as the scores fade out) and MainMenu
// (MainMenu::Process 0x2e668: the fades, the title, then the buttons acting when the touch ends on them -- Continue
// (Game::ContinueGame: dr_session_continue_game, the menu fading out), New game / Challenge / Tutorial (dr_session_start_game
// with SessionObjects.time; over a saved game "overwrite?" asks first, its yes or no answering after its 0.3 s fade-in), High
// scores (the saved page, a fade-in), the sound switch, Dashboard; "more games" and the bonus button), Name (T040-M7d:
// the setup screen's 0.3 s fades; its buttons are the dr_session_setup_* calls) and Unlock (T040-M8: UnlockMenu::Process,
// the unlock popup a class scroll shows; the game waits). The story and class screens are the API calls above and the
// renderer's.
dungeonraid::FrameRoute dr_session_frame(dungeonraid::Session*,float dt,std::int32_t touch_phase,dungeonraid::Point touch);
// Game::SerialiseState now: the saved game into SessionObjects.save, its length and changed flag into end (the
// session runs it itself where the original does: the end of a turn, ProcessInput's tail).
void dr_session_save(dungeonraid::Session*);
// Game::DeserialiseState: the saved game in SessionObjects.save over the current state (ContinueGame runs it after a
// new game); false when the buffer has no 0xff header (the format before version 1, not recovered).
bool dr_session_deserialise(dungeonraid::Session*);
// Game::ContinueGame: with a saved game, a new game (time seeds the random streams) that the save then overwrites
// (DeserialiseState) and the tile positions, then Interface::Process(0, false) (dr_session_interface_process: the
// heartbeat's help 14 may show); false without one (the main menu shows Continue only with one).
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
