#pragma once
#include "text.hpp"
#include "texts.hpp"
#include "recovered_session.hpp"
#include <vector>
namespace drui {
// The original IntroScreen (Game+0xc330), the story shown as a new game begins: a black screen (+0x8) that fades in
// with the story's lines (+0x78, the count in use +0xbc) and Begin (+0x84); Begin fades it out and the game starts.
// Open is the session's (FrameScreens.intro_c3f0, Game+0xc3f0); closing (+0xc1, Game+0xc3f1: Game::Render hides the
// main menu and the setup screen beneath), the fade (+0xc4) and the last touch phase (+0xc8) are its own.
class IntroView {
public:
    explicit IntroView(const Font* font);
    // Initialise 0x2de90, as the setup screen's Begin opens it: story is the session's RandI(0, 60, stream 0) draw.
    void initialise(const Texts& t,std::int32_t story);
    // Process 0x2dd04; true when the closing fade ended (the session's dr_session_intro_done: Game::SerialiseState).
    bool process(const dungeonraid::SessionObjects& o,float dt);
    void render(GL& gl) const;   // Render 0x2dcc8
    bool closing() const {return closing_;}
    std::vector<std::int32_t> sounds;   // this frame's Game::QueueSound calls (Begin: 18)
private:
    void set_alpha(std::uint8_t a);
    const Font* font_;
    Quad black_;
    std::vector<Label> lines_;
    std::int32_t count_=0;
    Label begin_;
    bool closing_=false;
    float fade_=0.0f;
    std::int32_t previous_=0;
};
}
