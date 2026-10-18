#!/bin/sh
set -eu
cd "$(dirname "$0")"
xcrun --sdk macosx clang++ -std=c++17 -Wall -Wextra -Werror -O2 -ffp-contract=off \
    -arch arm64 rewards_demo.cpp recovered_stroke.cpp recovered_preview.cpp recovered_rune.cpp \
    recovered_match.cpp recovered_tokens.cpp recovered_resources.cpp recovered_motion.cpp \
    recovered_battle.cpp recovered_combat.cpp recovered_random.cpp recovered_path.cpp recovered_round.cpp \
    recovered_refill.cpp recovered_generation.cpp recovered_encounters.cpp \
    recovered_selection.cpp recovered_input.cpp recovered_rules.cpp -o rewards_demo
./rewards_demo
