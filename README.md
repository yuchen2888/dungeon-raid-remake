# Dungeon Raid Remake

**English** | [简体中文](README.zh-CN.md)

An unofficial, non-commercial remake of **Dungeon Raid** (Firemint, 2011), the match-three dungeon crawler, for today's iPhone and Mac.

The original left the App Store long ago and no longer runs on current iOS. This project brings it back with the original's rules recovered as source code, a new front end, full-screen support for modern iPhones, HD pictures and six languages.

> **Bring your own game.** This repository holds **no game content**: no program, art, sound, fonts or English text from the original. You need your own copy of the original Dungeon Raid 1.3.4 to play. See [Legal](#legal).

<!-- screenshots -->

## What it is, and what it is not

**It is:**

- **The original's rules, as source code.** Every rule that decides a game was recovered from the original program into readable C++ (`recovered/`): matching, attacks, armour, enemies and their abilities, the end of each turn, levels, the shop, upgrades, skills, classes, scores and saved games. It does not emulate the old program.
- **Checked frame by frame.** A test bench (`frontend/tools/lockstep.py`) plays the same games in the original program and in the remake, comparing them frame by frame. The latest run covered 25,925 frames with no difference. That includes every sound the original queues.
- **A new front end.** It is built with [Godot 4.7](https://godotengine.org) and draws what the original drew, where it drew it. The screen is filled on modern iPhones and the launch screen is redone.
- **HD pictures.** The original's pictures are enlarged 4x with Real-ESRGAN and touched up. You can switch back to the original pixels at any time.
- **Six languages.** English, Simplified Chinese, Traditional Chinese, Japanese, Korean and Spanish. Every text is translated, including the 61-part story and the words drawn inside pictures. Chinese, Japanese and Korean use Source Han Sans for their letters. Korean breaks lines at spaces, and Japanese keeps small kana off the start of a line.
- **A new settings page.** It has a language page, sound volume, vibration, HD or original pictures, the original's switches (smooth motion, attack dimming, clock) and animation speed.
- **Plays on silent.** The sound follows the media volume, like other games, not the ringer switch.

**It is not:**

- An official product. Firemint and EA have nothing to do with it.
- A source of game content. You supply the original's files yourself.
- Finished. See [Status](#status).

## Status

| Part | State |
|---|---|
| Rules (one game and everything around it) | Recovered, checked against the original |
| Mac app | Playable |
| iPhone (iOS 16+) | Playable; built and installed from a Mac |
| Languages | 6, all texts and pictures |
| HD pictures | Done (4x) |
| A no-Mac install (an app with no game content that imports your original) | In progress |
| A new screen layout for tall iPhones | Being designed |
| Android, Windows | Planned (same Godot project) |
| New content (skills, classes) | Later, after the remake is complete |

## Getting started

For now the game is built on a Mac: Apple silicon, with Xcode and Python 3.

1. **Get the original.** You need your own copy of Dungeon Raid 1.3.4 (the IPA), with its program unencrypted.
2. **Get the tools.**
   - [Godot 4.7.2](https://godotengine.org/download/archive/4.7.2-stable/) in `/Applications`, with its export templates.
   - [godot-cpp](https://github.com/godotengine/godot-cpp) 10.0.0-stable in `frontend/gdext/godot-cpp/`.
   - Python 3 with Pillow and NumPy.
   - The four weights of [Source Han Sans](https://github.com/adobe-fonts/source-han-sans) (CN, TW, JP, KR) in `frontend/tools/fonts/`, for the languages.
   - Optional: [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) (ncnn-vulkan, macOS), for the HD pictures.
3. **Make the game files from your copy.** `frontend/tools/import_original_assets.py` copies the original's pictures, fonts, sounds and texts into `frontend/godot/assets/original/`, which Git ignores. Then:
   - `localise_atlas.py <language>` and `make_cjk_font.py <language>` make each language's pictures and letters;
   - `make_hd.py` makes the HD pictures.

   A single step that does all of this from your IPA is being written. Until then, the scripts expect the decoded files laid out as described in `frontend/README.md`.
4. **Play.**
   - Mac: `python3 frontend/gdext/build.py app`, then open `frontend/dist/Dungeon Raid.app`.
   - iPhone simulator: `frontend/tools/ios.sh simulator`.
   - Your iPhone: put your Apple developer team ID (10 characters, shown in Xcode under Signing & Capabilities) in `frontend/godot/team_id.local`, connect the phone, then run `frontend/tools/ios.sh device`. A free Apple ID works, but the app must be reinstalled every 7 days.

To play, drag through three or more touching tiles of one kind, then let go. Swords and skulls chain together.

## How it works

```
 original program ──(reverse engineering)──▶ recovered/   C++ rules core, no platform code
                                                │
                                                ▼
                    frontend/gdext/   Godot extension: a session that runs the core and says what to draw
                                                │
                                                ▼
                    frontend/godot/   Godot project: drawing, touch, sound, saves (Mac, iPhone)
```

- `recovered/`: the rules, one module per area, each with its own checks (`verify_*.py`). A check runs the original function and the recovered one from the same state and compares them.
- `frontend/gdext/src/ui/`: the screens (board, menus, shop, class screen, settings, story), drawn as the original drew them.
- `frontend/tools/`: the frame-by-frame bench (`lockstep.py`), the iPhone build (`ios.sh`), and the tools that make pictures, letters and HD versions.
- `docs/`: progress, decisions and the evidence for each recovered function, mostly in Chinese. `docs/REVERSE_ENGINEERING.md` lists what is known about the original.

## Checks

```bash
python3 frontend/tools/lockstep.py 80
```

```bash
/Applications/Godot.app/Contents/MacOS/Godot --headless --path frontend/godot -s res://tests/smoke.gd
```

The first plays 80 games' worth of input in the original and the remake and reports frames that differ. It needs the original program and its local test runner. The second plays 20 turns in the remake alone.

## Contributing

Translations, bug reports and screenshots from real devices are very welcome; please open an issue. If you spot a rule that plays differently from the original, say what happened and, if you can, attach the save (`Documents/` in the app's folder).

The project's working rules (for people and for AI coding tools) are in [AGENTS.md](AGENTS.md).

## Legal

- Dungeon Raid is a game by Firemint Pty Ltd (2011), later part of Electronic Arts. Its name, art, sound, music, fonts and text belong to their owners. This project is not affiliated with or endorsed by Firemint or EA.
- This repository contains none of the original's content, and no install package made from this project may contain it. Use only files from a copy you legally own. The authors are not responsible for anyone who distributes game content or install packages that contain it.
- The code here is offered for study, preservation and personal play, non-commercially.
- If you are a rights holder and have a concern, please open an issue and it will be dealt with promptly.

## Acknowledgements

- Firemint, for the original game.
- [Godot Engine](https://godotengine.org) (MIT) and [godot-cpp](https://github.com/godotengine/godot-cpp) (MIT).
- [Source Han Sans](https://github.com/adobe-fonts/source-han-sans) by Adobe (SIL Open Font License 1.1).
- [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) (BSD 3-Clause), for enlarging the pictures.

## License

The code in this repository is under the [MIT License](LICENSE). It covers only this project's own code and documents, never the original game's content. Third-party code keeps its own licence.
