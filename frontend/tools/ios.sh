#!/bin/sh
# The iPhone version (T050-B): builds the game library for iOS, exports the Godot project as an Xcode project into
# frontend/dist/ios/ and builds, installs and starts it.
#
#   frontend/tools/ios.sh simulator [device name]   the iOS simulator (default "iPhone 18 Pro"), no signing needed
#   frontend/tools/ios.sh device                    a connected iPhone, signed with your Apple developer team
#
# The team (the 10 letters and digits Xcode shows under Signing & Capabilities) is DR_TEAM_ID or the one line of
# frontend/godot/team_id.local (not in Git); export_presets.cfg keeps it empty and gets it only while Godot exports.
#
# Needs: Xcode, Godot 4.7.2 in /Applications with its export templates (godotengine.org, installed with the owner's
# consent on 2026-10-23), godot-cpp (see frontend/README.md) and the local original files
# (frontend/tools/import_original_assets.py). Nothing is uploaded; the build stays in frontend/dist/ (ignored by Git).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
FRONTEND="$(dirname "$HERE")"
GODOT=/Applications/Godot.app/Contents/MacOS/Godot
OUT="$FRONTEND/dist/ios"
BUNDLE=com.yuchen.dungeonraid.remake
WHERE="${1:-simulator}"

python3 "$FRONTEND/gdext/build.py" ios
# Godot's import cache first (the extension list, the sounds), then the Xcode project.
"$GODOT" --headless --path "$FRONTEND/godot" --import >/dev/null 2>&1 || true
rm -rf "$OUT"
mkdir -p "$OUT"
TEAM="${DR_TEAM_ID:-$(head -1 "$FRONTEND/godot/team_id.local" 2>/dev/null | tr -d ' \r')}"
if [ -z "$TEAM" ]; then
    [ "$WHERE" = simulator ] || { echo "no Apple developer team: put it in frontend/godot/team_id.local (or DR_TEAM_ID)"; exit 1; }
    TEAM=0000000000   # (the simulator signs nothing)
fi
PRESETS="$FRONTEND/godot/export_presets.cfg"
cp "$PRESETS" "$OUT/export_presets.cfg.orig"
trap 'cp "$OUT/export_presets.cfg.orig" "$PRESETS"' EXIT
sed -i '' "s/^application\/app_store_team_id=\"\"/application\/app_store_team_id=\"$TEAM\"/" "$PRESETS"
"$GODOT" --headless --path "$FRONTEND/godot" --export-debug iOS "$OUT/DungeonRaid.ipa" >"$OUT/export.log" 2>&1 || true
cp "$OUT/export_presets.cfg.orig" "$PRESETS"
[ -d "$OUT/DungeonRaid.xcodeproj" ] || { tail -20 "$OUT/export.log"; echo "Godot's iOS export failed ($OUT/export.log)"; exit 1; }

if [ "$WHERE" = simulator ]; then
    NAME="${2:-iPhone 18 Pro}"
    ID="$(xcrun simctl list devices available | grep -F "$NAME (" | head -1 | sed -E 's/.*\(([0-9A-F-]{36})\).*/\1/')"
    [ -n "$ID" ] || { echo "no simulator named $NAME"; exit 1; }
    xcrun simctl boot "$ID" 2>/dev/null || true
    # (no Simulator window is opened: screenshots come through simctl, and the owner keeps the screen)
    # Godot's simulator engine is x86_64 only; the arm64 simulator gets a copy of the device engine (sim_retarget.py).
    LIB="$OUT/DungeonRaid.xcframework"
    python3 "$HERE/sim_retarget.py" "$LIB/ios-arm64/libgodot.a" "$LIB/ios-arm64_x86_64-simulator/libgodot.a"
    xcodebuild -project "$OUT/DungeonRaid.xcodeproj" -scheme DungeonRaid -configuration Debug -sdk iphonesimulator \
        -destination "platform=iOS Simulator,id=$ID" -derivedDataPath "$OUT/build" ARCHS=arm64 CODE_SIGNING_ALLOWED=NO build >"$OUT/build.log" 2>&1 \
        || { grep -E "error:" "$OUT/build.log" | head; echo "Xcode build failed ($OUT/build.log)"; exit 1; }
    APP="$OUT/build/Build/Products/Debug-iphonesimulator/DungeonRaid.app"
    xcrun simctl install "$ID" "$APP"
    xcrun simctl launch "$ID" "$BUNDLE"
    echo "running on the simulator $NAME"
elif [ "$WHERE" = device ]; then
    # Xcode signs with the team and fetches a development profile for the connected iPhone
    # (the Apple account has to be signed in to Xcode; a free account's profile lasts 7 days).
    xcodebuild -project "$OUT/DungeonRaid.xcodeproj" -scheme DungeonRaid -configuration Debug -sdk iphoneos \
        -destination "generic/platform=iOS" -derivedDataPath "$OUT/build" -allowProvisioningUpdates build >"$OUT/build.log" 2>&1 \
        || { grep -E "error:" "$OUT/build.log" | head; echo "Xcode build failed ($OUT/build.log)"; exit 1; }
    APP="$OUT/build/Build/Products/Debug-iphoneos/DungeonRaid.app"
    # The first paired iPhone (by cable, or on the same Wi-Fi once paired).
    LIST="$OUT/devices.json"
    xcrun devicectl list devices --json-output "$LIST" >/dev/null 2>&1 || true
    DEVICE="$(python3 -c 'import json,sys
for d in json.load(open(sys.argv[1]))["result"]["devices"]:
    h=d["hardwareProperties"]
    if h.get("reality")=="physical" and h.get("platform")=="iOS" and d["connectionProperties"].get("pairingState")=="paired":
        print(h["udid"]); break' "$LIST" 2>/dev/null)"
    [ -n "$DEVICE" ] || { echo "built $APP; no paired iPhone found (connect it with a cable and trust this Mac)"; exit 1; }
    xcrun devicectl device install app --device "$DEVICE" "$APP"
    xcrun devicectl device process launch --device "$DEVICE" "$BUNDLE"
    echo "running on the iPhone"
else
    echo "usage: frontend/tools/ios.sh simulator [device name] | device"
    exit 1
fi
