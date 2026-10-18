#!/bin/sh
set -eu
cd "$(dirname "$0")"
xcrun --sdk macosx clang++ -std=c++17 -Wall -Wextra -Werror -O2 -ffp-contract=off \
    -arch arm64 stroke_demo.cpp recovered_stroke.cpp recovered_preview.cpp recovered_rune.cpp \
    recovered_selection.cpp recovered_input.cpp recovered_rules.cpp -o stroke_demo
./stroke_demo
