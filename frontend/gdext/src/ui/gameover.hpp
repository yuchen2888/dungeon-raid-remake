#pragma once
#include "menu.hpp"
#include "text.hpp"
#include "texts.hpp"
#include "recovered_session.hpp"
#include <vector>
namespace drui {
// The original GameOverScreen (Game+0xcac0), the tally a game's end shows: a coloured screen (+0x8: green for a win,
// red for a loss) that fades in over the board with the win's title (+0xe8) or the loss's tombstone (+0x78), turns
// black, and then counts the game up line by line (22 labels, +0x198: 0 the name, 1 the class, 2 the difficulty or
// mode, 3..7 and 12 the headings of the counted numbers, 8..11 those of the icons, 13..17 and 20 the numbers), with
// the five equipped items' and the skills' icons (the game's own, Game::GetItem / Game+0xbf90, moved here by InitIcons:
// the skills' stay moved, also on the board's interface beneath),
// the class's perks (+0x1a4) and flaws (+0x364), and the enemies left on the board (+0x524, under their mortal glow
// +0x14e4) under the score; after 10 seconds it all fades out over the high-score screen. Its rules (the state +0x15c,
// the line +0x160, the fades, the counting and the icons shown) are the session's (GameOverTally); this is its picture.
// (Initialise's last call, QueueSound 12 / 33, the presenter queues.)
class GameOverView {
public:
    explicit GameOverView(const Font* font);
    // Initialise 0x307f8, as the session opens the screen (TurnEvent EndGameEventKind::GameOverScreen, a = win).
    void initialise(const Texts& t,const dungeonraid::SessionObjects& o,bool win);
    // Process 0x30c28's picture after the session's step: before is the tally, its state and the touch phase as the
    // step found them; ended_line / ended_value the line the step ended and its final value (the session's GameOverLine,
    // else -1); skills are the game's equipped skills (Game+0xbf90) InitIcons moves.
    void process(const dungeonraid::SessionObjects& o,const dungeonraid::GameOverTally& before,std::int32_t state,
                 std::int32_t phase,std::int32_t ended_line,std::int32_t ended_value,float dt,SkillView* skills);
    void render(GL& gl,const dungeonraid::SessionObjects& o) const;   // Render 0x2fe7c
private:
    void init_icons(const dungeonraid::SessionObjects& o,SkillView* skills);   // InitIcons 0x3013c
    void show_value(const dungeonraid::SessionObjects& o,std::int32_t line,float value);
    const Font* font_;
    const Texts* texts_=nullptr;
    Quad black_, tombstone_, title_;    // +0x8, +0x78, +0xe8
    bool win_=false;                    // +0x158
    std::vector<Label> labels_;         // +0x198
    Quad perks_[4], flaws_[4];          // +0x1a4, +0x364
    Quad enemies_[36], glows_[36];      // +0x524, +0x14e4
    Icon items_[5];                     // Game::GetItem(0..4)'s icons as InitIcons placed them
    SkillView* skills_=nullptr;         // Game+0xbf90's (the presenter's)
};
}
