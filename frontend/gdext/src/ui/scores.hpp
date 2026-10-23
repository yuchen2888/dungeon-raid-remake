#pragma once
#include "strip.hpp"
#include "text.hpp"
#include "texts.hpp"
#include "recovered_session.hpp"
namespace drui {
// The original ScoreScreen (Game+0xef68), the high scores: a backing (+0x7c) under the title banner (+0xec) and Back
// (+0x180), and the six tables (0..3 the difficulties, 4..5 the challenge modes) shown one a page. Three page objects
// (+0x1d4: the page before, the page shown, the page after) slide with a drag or the arrows; once one has slid in the
// three rotate and the new neighbour is filled (InitialisePage). A page: ten ranks and rows (each with the name, the
// turns, three values, the score and four skill icons; the latest score in yellow, the empty rows dimmed), the value
// headings, the arrows and the table's name. The scores, the page shown, the fades, the drag and the buttons touched
// are the session's (ScoreBoard, ScorePages); this is its picture.
class ScoreView {
public:
    ScoreView(const Font* font,const Font* menu_font,const Font* score_font);   // ScoreScreen::ScoreScreen 0x35f60
    void initialise(const Texts& t);                                  // Initialise 0x352a4 (once the fonts are made)
    void show(const dungeonraid::SessionObjects& o,bool from_game);   // Show(bool) 0x36720, as the session opened it
    // Process 0x367f8's picture after the session's step (before: the pages' state as the step found it).
    void process(const dungeonraid::SessionObjects& o,const dungeonraid::ScorePages& before);
    // Process at Game::SetScorePage (the session's ScorePageTurn): slid into place, the three pages rotate and the new
    // neighbour is filled (direction 1 the page before, -1 the one after, 0 back in place).
    void turn_page(const dungeonraid::SessionObjects& o,std::int32_t direction);
    // The session's menu_button: 1 Back, 2 the left arrow, 3 the right arrow (QuadStrip::ContainsPoint), plus 16 on the
    // rows (where a drag starts), else 0.
    std::int32_t button_at(Point2 touch) const;
    void render(GL& gl,const dungeonraid::SessionObjects& o) const;   // Render 0x3509c
private:
    struct Page {                        // ScorePage (0x298c bytes)
        QuadStrip ranks[10], rows[10];   // +0x0, +0x2f8
        Label lines[10][7];              // +0x5f0: the rank, name, turns, three values and score of each row
        Quad skills[10][4];              // +0x1540
        Label headings[5];               // +0x26c0: Turns, the three values', Score
        QuadStrip left, left_arrow, right, right_arrow, title;   // +0x27d8, +0x2824, +0x2870, +0x28bc, +0x2908
        Label title_label;               // +0x2954
    };
    void create_page(Page& p);           // CreatePage 0x35b04
    void initialise_page(const dungeonraid::SessionObjects& o,std::int32_t k);   // InitialisePage 0x36284
    void set_alpha(const dungeonraid::SessionObjects& o,std::uint8_t a);       // SetAlpha 0x34ca4
    void render_page(GL& gl,const dungeonraid::SessionObjects& o,std::int32_t k) const;   // RenderPage 0x34ea8
    Page& page(std::int32_t k) {return pages_[slot_[k]];}
    const Page& page(std::int32_t k) const {return pages_[slot_[k]];}
    const Font* font_;
    const Font* menu_font_;
    const Font* score_font_;
    const Texts* texts_=nullptr;
    Quad black_, backing_, banner_;      // +0xc, +0x7c, +0xec
    QuadStrip back_;                     // +0x180
    Page pages_[3];
    std::int32_t slot_[3]{0,1,2};        // +0x1d4..: the page objects before, at and after the page shown
};
}
