# Dungeon Raid Remake

**English** | [简体中文](README.zh-CN.md)

> One finger, a six-by-six board, one more run, and somehow it is morning.

<p align="center"><img src="https://github.com/yyc0409-ui/dungeon-raid-remake/releases/download/media/hero.png" alt="Dungeon Raid Remake on iPhone"></p>

## A labour of love

In 2011 Firemint, the Australian studio behind *Flight Control* and *Real Racing*, put **Dungeon Raid** on the iPhone. It looked like another match-three game. It played like a dungeon crawl that kept going deeper. Back when the iPhone 4 was new, it was the one game many people never deleted: on the train, in the queue, "just one more run" before bed, and then it was 2 a.m. It was loved by the people who played it, often called one of the most replayable games on the iPhone, and old players still talk about that one-more-run pull today.

What made it so good?

- **One stroke.** No swapping. Hold your finger down and trace through touching tiles of one kind, across, down or diagonally. The longer the chain, the better it feels.
- **Every tile matters.** Swords and skulls chain together to attack. Coins buy equipment. Shields repair armour. Potions heal. Every stroke is a choice: stay alive, or kill first?
- **The monsters hit back.** After each stroke, every skull left on the board attacks you. They pile up and get stronger, and the special ones change the game: spiky ones that hurt you when you hit them, ones that freeze tiles, turn potions into acid, steal your gold or blow up when their timer runs out, and bosses far tougher than the rest.
- **A hero that grows.** Level up from experience, spend gold on equipment, turn shields into armour upgrades and pick up skills, so no two runs build the same hero.
- **Classes to unlock.** Pick a class and a difficulty for each game. Each class has its own race, perks and flaws, and special skill. Killing special enemies on anything above Easy unlocks new classes and levels them up, with more ways to set them up.
- **No second chances.** One life per run. When you die, you keep only a score, and that is what makes every stroke tense.

Then it stopped being updated. In 2017 iOS 11 dropped support for old 32-bit apps, and Dungeon Raid vanished from everyone's phones and from the App Store. For years, old players have kept asking whether there is any way to play it again.

Lately the internet has been full of old games brought back with the help of AI, one childhood memory after another. It reminded me of the dungeon I spent hundreds of hours in, so I set out to revive it with [Claude](https://claude.com/claude-code), Anthropic's AI coding assistant. Not by running the old program in an emulator, but by recovering the original's rules one by one as readable source code and rebuilding the game on a modern engine: full screen on today's iPhones, HD pictures, and more languages.

It is an unofficial, non-commercial remake, made so that old players can have one more run, and so that people who never played it can see what a great game it was.

## What the remake offers

The original's rules are recovered as source code and checked against the original frame by frame. A new front end fills the screen on modern iPhones. It adds HD pictures and six languages, and it also runs on a Mac.

> **Bring your own game.** This repository holds **no game content**: no program, art, sound, fonts or English text from the original. You need your own copy of the original Dungeon Raid 1.3.4 to play. See [Legal](#legal).

| <img src="https://github.com/yyc0409-ui/dungeon-raid-remake/releases/download/media/menu-en.png" width="200" alt="Main menu"> | <img src="https://github.com/yyc0409-ui/dungeon-raid-remake/releases/download/media/board-en.png" width="200" alt="Chaining tiles"> | <img src="https://github.com/yyc0409-ui/dungeon-raid-remake/releases/download/media/attack-en.png" width="200" alt="Monsters attack"> |
|---|---|---|
| Main menu | Chaining tiles | Monsters attack |

| <img src="https://github.com/yyc0409-ui/dungeon-raid-remake/releases/download/media/setup-zh.png" width="200" alt="New game (Chinese)"> | <img src="https://github.com/yyc0409-ui/dungeon-raid-remake/releases/download/media/board-zh.png" width="200" alt="Board (Chinese)"> | <img src="https://github.com/yyc0409-ui/dungeon-raid-remake/releases/download/media/settings-en.png" width="200" alt="Settings"> | <img src="https://github.com/yyc0409-ui/dungeon-raid-remake/releases/download/media/languages-en.png" width="200" alt="Languages"> |
|---|---|---|---|
| New game (Chinese) | Board (Chinese) | Settings | Languages |

*Screenshots from the iPhone 18 Pro simulator, HD pictures.*

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
| A no-Mac install (an app with no game content that imports your original) | First release: tested on the simulator, not yet on real phones |
| A new screen layout for tall iPhones | Being designed |
| Android, Windows | Planned (same Godot project) |
| New content (skills, classes) | Later, after the remake is complete |

## Getting started

There are two ways: install the ready-made app on your iPhone, or build everything yourself on a Mac.

### Why you need your own copy

Copyright. Dungeon Raid's art, sound, music, fonts and text belong to their owners, and those rights did not end when the game left the store. We are just players who love the game, and it is not ours to give away.

So the work is split like this:

- **What we publish** is only what we made ourselves: the recovered rules code, the new front end, the translations, and lettering drawn with Source Han Sans. The install package holds only these. Before each release a tool checks it file by file, and it contains not a single file of the original.
- **What you bring** is your own copy of the original. When the game first opens, it reads the pictures, sounds and texts from your copy and keeps them on your phone. Nothing is uploaded anywhere.

Many remakes of old games work the same way: the engine and code are shared, and each player supplies the game content from their own copy. That way an old game can run again while the creators' rights are respected. We also won't tell anyone where to find the original's files.

### On an iPhone, no Mac needed

1. **Download** `DungeonRaid-Remake-unsigned.ipa` from [Releases](https://github.com/yyc0409-ui/dungeon-raid-remake/releases/latest). It holds none of the original's content.
2. **Install it** with a sideloading tool such as [AltStore](https://altstore.io) or [Sideloadly](https://sideloadly.io), which signs it with your own Apple ID. With a free Apple ID the app has to be refreshed every 7 days.
3. **Give it your original.** You need your own copy of Dungeon Raid 1.3.4, as an IPA with its program unencrypted. Put it in the Files app, under **On My iPhone → Dungeon Raid**. That folder appears once the app has been opened once.
4. **Open the game and tap Import.** It takes a few seconds. Any decrypted copy of 1.3.4 works, whichever tool decrypted it, including copies that keep only the armv7 code. The game checks what it reads, so another version is refused rather than misread, and a copy that is still encrypted is named as such. Afterwards you can delete the IPA from that folder.

What differs from a build on a Mac:

- The pictures are the original's pixels: making the HD ones needs a Mac.
- Spanish shows its accented letters without their accents (á as a). Its accented letters are made from the original font, so they cannot be shipped.

The import screen is in English or Chinese, following your phone's language. Everything after it is in the language you pick in Settings.

### On a Mac

For this you need an Apple silicon Mac with Xcode and Python 3.

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
