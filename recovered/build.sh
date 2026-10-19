#!/bin/sh
set -eu
cd "$(dirname "$0")"
for module in combat rules input battle round progression selection random stroke preview rune match tokens resources motion path refill generation encounters attack_shield turn; do
    set -- "recovered_${module}.cpp"
    case "$module" in
        battle) set -- "$@" recovered_combat.cpp ;;
        round) set -- "$@" recovered_combat.cpp recovered_rules.cpp recovered_battle.cpp ;;
        selection) set -- "$@" recovered_input.cpp recovered_rules.cpp ;;
        stroke) set -- "$@" recovered_selection.cpp recovered_input.cpp recovered_rules.cpp ;;
        preview) set -- "$@" recovered_rules.cpp ;;
        match) set -- "$@" recovered_battle.cpp recovered_combat.cpp recovered_random.cpp recovered_rules.cpp ;;
        resources) set -- "$@" recovered_rules.cpp ;;
        motion) set -- "$@" recovered_random.cpp recovered_resources.cpp recovered_rules.cpp ;;
        path) set -- "$@" recovered_round.cpp recovered_match.cpp recovered_tokens.cpp recovered_battle.cpp recovered_combat.cpp recovered_rules.cpp recovered_random.cpp ;;
        generation) set -- "$@" recovered_rules.cpp recovered_random.cpp ;;
        encounters) set -- "$@" recovered_refill.cpp recovered_combat.cpp recovered_rules.cpp ;;
        attack_shield) set -- "$@" recovered_rules.cpp recovered_random.cpp recovered_combat.cpp ;;
        turn) set -- "$@" recovered_battle.cpp recovered_combat.cpp recovered_rules.cpp recovered_generation.cpp recovered_random.cpp ;;
    esac
    xcrun --sdk macosx clang++ -std=c++17 -Wall -Wextra -Werror -O2 \
        -ffp-contract=off -arch arm64 -arch x86_64 -dynamiclib \
        "$@" -o "recovered_${module}_native.dylib"
    xcrun --sdk iphoneos clang++ -std=c++17 -Wall -Wextra -Werror -O2 \
        -ffp-contract=off -arch arm64 -miphoneos-version-min=18.0 -c \
        "recovered_${module}.cpp" -o "recovered_${module}_ios_arm64.o"
done
xcrun --sdk iphoneos libtool -static -o libDungeonRaidRecovered-ios-arm64.a \
    recovered_combat_ios_arm64.o recovered_rules_ios_arm64.o recovered_input_ios_arm64.o \
    recovered_battle_ios_arm64.o recovered_round_ios_arm64.o recovered_progression_ios_arm64.o \
    recovered_selection_ios_arm64.o recovered_random_ios_arm64.o \
    recovered_stroke_ios_arm64.o recovered_preview_ios_arm64.o recovered_rune_ios_arm64.o \
    recovered_match_ios_arm64.o recovered_tokens_ios_arm64.o recovered_resources_ios_arm64.o \
    recovered_motion_ios_arm64.o recovered_path_ios_arm64.o recovered_refill_ios_arm64.o recovered_generation_ios_arm64.o recovered_encounters_ios_arm64.o recovered_attack_shield_ios_arm64.o recovered_turn_ios_arm64.o
printf '%s\n' 'Built native macOS libraries and iPhone ARM64 static library.'
