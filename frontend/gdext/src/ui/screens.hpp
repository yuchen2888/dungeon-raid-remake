#pragma once
#include "quad.hpp"
#include "recovered_session.hpp"
namespace drui {
// The original MainMenu (Game+0xc3fc): the background and title (+0x10, +0x80), "more games" (+0xf0, its colour cycling
// through the hues while the cycle runs), the eight buttons (+0x160 + 0x70 k: 0 Continue, 1 New game, 2 Challenge,
// 3 Tutorial, 4 High scores, 5 the sound switch (turned on its side), 6 the dashboard, 7 the bonus, shown only when
// offered) and the "overwrite the saved game?" box (+0x4e8 darkening, +0x558 the box, +0x5c8 / +0x638 the chosen
// answer). The menu's game part (fades, the splash, the pressed button, the box) is the session's (MainMenuScreen,
// T040-M7); this is its picture, set as MainMenu::Process 0x2e668 sets it, by mirroring each frame's step before the
// session takes it (process()).
class MainMenuView {
public:
    MainMenuView();
    void set_sound_state(bool on);   // MainMenu::SetSoundState 0x2e4e8 (the sound button's picture and place)
    void show(const dungeonraid::SessionObjects& o);   // MainMenu::Show 0x2f60c (back from the scores or the setup screen)
    void fade_in();                  // MainMenu::FadeIn 0x2e214's picture (everything transparent)
    void start_cycling();            // StartCyclingGamesColour 0x2e628 (a game starts; the platform's start-up)
    void stop_cycling();             // StopCyclingGamesColour 0x2e648 (Game::ShowMoreGames)
    // A main-menu button acted (the session's MainMenuButton event, before the action): Continue, and New game /
    // Challenge / Tutorial without a saved game, start a game (StartCyclingGamesColour), and the frame's colour step
    // follows in MainMenu::Process.
    void button_acted(const dungeonraid::SessionObjects& o,std::int32_t button,float dt);
    // MainMenu::Process's picture for this frame's step (dt), from the session's state before it.
    void process(const dungeonraid::SessionObjects& o,float dt);
    // The session's menu_button for the main menu (Quad::ContainsPoint): the box's answers 10 / 11 while it is open, else
    // "more games" 8, the bonus 9 (when shown), the buttons 0..7; -1 none.
    std::int32_t button_at(const dungeonraid::SessionObjects& o,Point2 touch) const;
    void render(GL& gl,const dungeonraid::SessionObjects& o) const;   // MainMenu::Render 0x2e260
private:
    void update_more_games_colour();   // UpdateMoreGamesColour 0x2e5d4: HSVtoRGB(hue, 0.9, 0.6)
    void set_buttons(std::uint8_t a,std::uint8_t dim,bool has_save,bool has_scores);
    Quad background_, title_, more_games_, buttons_[8], darken_, box_, yes_, no_;
    float hue_=0.0f;          // +0x6bc
    bool cycling_=true;       // +0x6c0
};
}
