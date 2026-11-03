#!/bin/sh
# The shell app (T081): the iPhone version with none of the original's content, for anyone to download. The player
# puts their own original IPA in the app's folder (Files app) and the game imports it (frontend/godot/importer.gd).
#
#   frontend/tools/shell_ipa.sh                     frontend/dist/shell/DungeonRaid-Remake-unsigned.ipa: unsigned, for
#                                                   sideloading tools (AltStore, Sideloadly ...), which sign it with
#                                                   the player's own Apple ID
#   frontend/tools/shell_ipa.sh simulator [name]    builds it for the iOS simulator and installs it there instead
#
# Needs what ios.sh needs, and the local import data (make_shell_data.py, run here) and the language folders. After
# building, frontend/tools/shell_audit.py checks the package holds none of the original's content.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
FRONTEND="$(dirname "$HERE")"
GODOT=/Applications/Godot.app/Contents/MacOS/Godot
OUT="$FRONTEND/dist/shell"
BUNDLE=io.github.yyc0409-ui.dungeonraid
WHERE="${1:-device}"

python3 "$FRONTEND/gdext/build.py" ios
python3 "$HERE/make_shell_data.py"
python3 "$HERE/make_shell_art.py"
"$GODOT" --headless --path "$FRONTEND/godot" --import >/dev/null 2>&1 || true
rm -rf "$OUT"
mkdir -p "$OUT"
# The export reads the launch picture from project.godot: the shell's own, only while it exports. Its signing team is
# a placeholder: the package is left unsigned.
PROJECT="$FRONTEND/godot/project.godot"
PRESETS="$FRONTEND/godot/export_presets.cfg"
cp "$PROJECT" "$OUT/project.godot.orig"
cp "$PRESETS" "$OUT/export_presets.cfg.orig"
trap 'cp "$OUT/project.godot.orig" "$PROJECT"; cp "$OUT/export_presets.cfg.orig" "$PRESETS"' EXIT
sed -i '' 's#^boot_splash/image=.*#boot_splash/image="res://shell/splash.png"#' "$PROJECT"
sed -i '' 's/^application\/app_store_team_id=""/application\/app_store_team_id="0000000000"/' "$PRESETS"
"$GODOT" --headless --path "$FRONTEND/godot" --export-debug "iOS shell" "$OUT/DungeonRaid.ipa" >"$OUT/export.log" 2>&1 || true
cp "$OUT/project.godot.orig" "$PROJECT"
cp "$OUT/export_presets.cfg.orig" "$PRESETS"
[ -d "$OUT/DungeonRaid.xcodeproj" ] || { tail -20 "$OUT/export.log"; echo "Godot's iOS export failed ($OUT/export.log)"; exit 1; }

if [ "$WHERE" = simulator ]; then
    NAME="${2:-iPhone 18 Pro}"
    ID="$(xcrun simctl list devices available | grep -F "$NAME (" | head -1 | sed -E 's/.*\(([0-9A-F-]{36})\).*/\1/')"
    [ -n "$ID" ] || { echo "no simulator named $NAME"; exit 1; }
    xcrun simctl boot "$ID" 2>/dev/null || true
    LIB="$OUT/DungeonRaid.xcframework"
    python3 "$HERE/sim_retarget.py" "$LIB/ios-arm64/libgodot.a" "$LIB/ios-arm64_x86_64-simulator/libgodot.a"
    xcodebuild -project "$OUT/DungeonRaid.xcodeproj" -scheme DungeonRaid -configuration Debug -sdk iphonesimulator \
        -destination "platform=iOS Simulator,id=$ID" -derivedDataPath "$OUT/build" ARCHS=arm64 CODE_SIGNING_ALLOWED=NO build >"$OUT/build.log" 2>&1 \
        || { grep -E "error:" "$OUT/build.log" | head; echo "Xcode build failed ($OUT/build.log)"; exit 1; }
    xcrun simctl install "$ID" "$OUT/build/Build/Products/Debug-iphonesimulator/DungeonRaid.app"
    xcrun simctl launch "$ID" "$BUNDLE"
    echo "running on the simulator $NAME"
    exit 0
fi
xcodebuild -project "$OUT/DungeonRaid.xcodeproj" -scheme DungeonRaid -configuration Debug -sdk iphoneos \
    -destination "generic/platform=iOS" -derivedDataPath "$OUT/build" CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO build >"$OUT/build.log" 2>&1 \
    || { grep -E "error:" "$OUT/build.log" | head; echo "Xcode build failed ($OUT/build.log)"; exit 1; }
rm -rf "$OUT/package"
mkdir -p "$OUT/package/Payload"
cp -R "$OUT/build/Build/Products/Debug-iphoneos/DungeonRaid.app" "$OUT/package/Payload/"
(cd "$OUT/package" && zip -qry ../DungeonRaid-Remake-unsigned.ipa Payload)
echo "built $OUT/DungeonRaid-Remake-unsigned.ipa"
