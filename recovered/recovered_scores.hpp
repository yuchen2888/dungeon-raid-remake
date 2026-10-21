#pragma once
#include <cstdint>
namespace dungeonraid {
// ScoreScreen's high-score tables (T030-N5d; ScoreScreen at Game+0xef68): ten scores for each of six score types
// (ScoreType: the difficulties 0..3, then the game modes 0..1 as 4 and 5). A score (56 bytes at ScoreScreen+0x1e0 +
// 560 * type + 56 * i) holds the player's name, the game's turn and three values (variant 0: xp, gold, up; variant 1:
// the mode's three), the score and four skills (ScoreScreen::SetSkills; -1 none). The platform stores each type's
// serialised table when its changed flag is set and gives the stored tables back at start-up.
struct ScoreRecord {
    char name[20];
    std::int32_t turn, a, b, c, score;
    std::int32_t skills[4];
};
struct ScoreBoard {
    ScoreRecord scores[6][10];        // +0x1e0
    std::int32_t count[6];            // +0xf00
    std::int32_t last_type, last_pos; // +0xf18 / +0xf1c: the latest score (-1 none)
    std::uint8_t bytes[0x400];        // +0xf20: a serialised table
    std::int32_t length;              // +0x1320
    std::int32_t serialised_type;     // +0x1324
    std::uint8_t changed[6];          // +0x1328
};
}
extern "C" {
// ScoreScreen's constructor: no scores, no latest score, nothing changed.
void dr_scores_init(dungeonraid::ScoreBoard*);
// Original ScoreScreen::AddScore(name, turn, a, b, c, score, ScoreType) 0x347c0 (AddScore(GameMode) uses type mode + 4,
// AddScore(Difficulty) type difficulty): the previous latest type and this one are changed; the place is after every
// score not below it (the tenth place when there are ten higher or equal ones: the new score replaces the tenth); the
// lower ones move down (at most ten kept); name copied, values written, skills -1; the count grows to at most 10.
void dr_score_add(dungeonraid::ScoreBoard*,const char* name,std::int32_t turn,std::int32_t a,std::int32_t b,std::int32_t c,
                  std::int32_t score,std::int32_t type);
// Original ScoreScreen::SetSkills 0x34418: the latest score's four skills.
void dr_score_set_skills(dungeonraid::ScoreBoard*,std::int32_t,std::int32_t,std::int32_t,std::int32_t);
// Original ScoreScreen::GetScoreCount 0x344c8 / HaveScoresChanged 0x344f0.
std::int32_t dr_score_count(const dungeonraid::ScoreBoard*);
bool dr_scores_changed(const dungeonraid::ScoreBoard*);
// Original ScoreScreen::SerialiseState(ScoreType) 0x34524 into bytes: the count, the latest score's place when it is
// in this type (else 0xff), then each score's turn, a, b, c, score (4 bytes each), skills (1 byte each) and name (to its
// terminator, at most 17 bytes); length, the type, its changed flag cleared.
void dr_score_serialise(dungeonraid::ScoreBoard*,std::int32_t type);
// Original ScoreScreen::SerialiseChangedState 0x34630: the first changed type serialised; returns it (-1: none).
std::int32_t dr_score_serialise_changed(dungeonraid::ScoreBoard*);
// Original ScoreScreen::DeserialiseState(int, ScoreType) 0x34680 from bytes: count clamp(0..10); a latest place other
// than 0xff makes this type's place the latest; scores back (skills 0xff: -1, else clamp(0..39)); changed flag cleared.
void dr_score_deserialise(dungeonraid::ScoreBoard*,std::int32_t type);
}
