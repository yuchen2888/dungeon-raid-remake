#!/bin/sh
set -eu
cd "$(dirname "$0")"
xcrun --sdk macosx clang++ -std=c++17 -Wall -Wextra -Werror -O2 -ffp-contract=off \
    -arch arm64 session_demo.cpp recovered_session.cpp recovered_labels.cpp recovered_save.cpp recovered_scores.cpp recovered_menu.cpp recovered_items.cpp recovered_skills.cpp \
    recovered_schedule.cpp recovered_stats.cpp recovered_turn.cpp recovered_attack_shield.cpp recovered_encounters.cpp \
    recovered_generation.cpp recovered_refill.cpp recovered_path.cpp recovered_motion.cpp recovered_resources.cpp \
    recovered_tokens.cpp recovered_match.cpp recovered_rune.cpp recovered_preview.cpp recovered_stroke.cpp \
    recovered_random.cpp recovered_selection.cpp recovered_progression.cpp recovered_round.cpp recovered_battle.cpp \
    recovered_input.cpp recovered_rules.cpp recovered_combat.cpp -o session_demo
./session_demo
