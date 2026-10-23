#!/usr/bin/env python3
"""Copies the original game's art, fonts and sounds into frontend/godot/assets/original/ for local play (T050-A).

  python3 frontend/tools/import_original_assets.py

The original assets stay on this machine: the target folder is ignored by Git (frontend/.gitignore) and nothing is
uploaded. Sources, all local: reference/decoded-assets/ (the textures, already decoded from the iOS PNG format),
reference/original-assets/ (the bitmap fonts' .fnt files), the local IPA (the .caf sounds and the icon), and the
original program DungeonRaid-original (the sound table: GetSoundName 0x1b838, GetSoundVariations 0x1b9f0 and
GetSoundVolume 0x1ba34, read from their jump tables; the game's English texts, see texts()). Sounds are converted to
WAV with macOS's afconvert.

  python3 frontend/tools/import_original_assets.py --texts    # only the texts (texts.txt)
  python3 frontend/tools/import_original_assets.py --raw      # only the "keep" import settings (see keep_raw()) and the icons
"""
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "frontend", "godot", "assets", "original")
DECODED = os.path.join(ROOT, "reference", "decoded-assets")
ORIGINAL = os.path.join(ROOT, "reference", "original-assets")
IPA = os.path.join(ROOT, "DungeonRaid-independent-experimental-unsigned.ipa")
PROGRAM = os.path.join(ROOT, "DungeonRaid-original")
TEXTURES = ["tiles.png", "icons.png", "menus.png", "font.png", "fontMenu.png", "fontScore.png", "Default.png"]
FONTS = ["font.fnt", "fontMenu.fnt", "fontScore.fnt"]

sys.path.insert(0, HERE)
from macho import ARMv7  # noqa: E402


def sound_table():
    """The original's 38 sounds: name, variations (files name1..nameN), volume."""
    m = ARMv7(PROGRAM)
    names = [m.cstr(m.ldr_add_pc(a)) for a in m.tbb(0x1b83c, 0x26)]
    variations = []
    for a in m.tbb(0x1b9f4, 0x26):
        ins = m.u16(a)
        assert ins & 0xff00 == 0x2000, hex(ins)   # movs r0, #n
        variations.append(ins & 0xff)
    volumes = []
    for a in m.tbb(0x1ba38, 0x26):
        ins = m.u16(a)
        if ins & 0xf800 == 0x4800:                # ldr r0, [pc, #i]: a float literal
            bits = m.u32(((a + 4) & ~3) + (ins & 0xff) * 4)
        else:                                     # mov.w r0, #1.0 / #0.5
            bits = {0xf04f507e: 0x3f800000, 0xf04f507c: 0x3f000000}[(m.u16(a) << 16) | m.u16(a + 2)]
        volumes.append(round(struct.unpack("<f", struct.pack("<I", bits))[0], 4))
    return [{"id": i, "name": n, "variations": v, "volume": w} for i, (n, v, w) in enumerate(zip(names, variations, volumes))]


def pcrel(m, ldr, add):
    """The address an 'ldr rX, [pc, #i]' (16 or 32 bit) at ldr and the 'add rX, pc' at add compute."""
    h = m.u16(ldr)
    if h & 0xf800 == 0x4800:
        lit = ((ldr + 4) & ~3) + (h & 0xff) * 4
    else:
        assert h in (0xf8df, 0xf85f), hex(h)
        imm = m.u16(ldr + 2) & 0xfff
        lit = ((ldr + 4) & ~3) + (imm if h == 0xf8df else -imm)
    return (m.u32(lit) + add + 4) & 0xffffffff


# Texts the drawing uses, by key: the (ldr, add) pair of the instruction that loads each in the original program.
NAMED = {
    "empty": (0x2981a, 0x29820),
    # Skill::Initialise 0x2b2a0: the level on the icon, the cooldown line (upgrade, new)
    "skill.level": (0x2b386, 0x2b38c), "skill.cooldown_up": (0x2b3da, 0x2b3e6), "skill.cooldown": (0x2b3ee, 0x2b3f8),
    # Skill::Initialise(StatType) 0x2b434 and Skill::SetStatChance 0x2abc8
    "stat.base_dmg": (0x2b4c8, 0x2b4d2), "stat.armour": (0x2b4f8, 0x2b502), "stat.max_health": (0x2b548, 0x2b550),
    "stat.healing": (0x2b578, 0x2b580), "stat.chance_xp": (0x2b4e0, 0x2b4e8), "stat.chance_shield": (0x2b510, 0x2b518),
    "stat.chance_potion": (0x2b55e, 0x2b56a), "stat.chance_coin": (0x2b58e, 0x2b596), "stat.coin": (0x2b61a, 0x2b622),
    "stat.xp": (0x2b632, 0x2b63c), "stat.shield": (0x2b64e, 0x2b656), "stat.potion": (0x2b668, 0x2b670),
    "stat.chance": (0x2abfa, 0x2ac04), "stat.chance_max": (0x2ac14, 0x2ac1a),
    # FoldoutMenu::HighlightButton 0x237dc
    "menu.replaces": (0x238cc, 0x238d0),
    # ItemUpgrade::GetDescription 0x2d034 (record mode 1, its first upgrade) and WriteStatPercent / Float / Int
    "upgrade.potion_desc": (0x2d04c, 0x2d04e),
    "upgrade.percent_up": (0x2d0c6, 0x2d0ce), "upgrade.percent": (0x2d0da, 0x2d0e4),
    "upgrade.float_up": (0x2d13a, 0x2d142), "upgrade.float": (0x2d186, 0x2d18c),
    "upgrade.int_up": (0x2d1da, 0x2d1e2), "upgrade.int": (0x2d1ee, 0x2d1f8),
    # Item::GenerateName 0x263a0
    "item.novice": (0x263ae, 0x263b8), "item.name": (0x2646c, 0x26476),
    # Item::MakeStats 0x28e30
    "item.separator": (0x29868, 0x29870), "item.quick": (0x292ea, 0x292f2),
    # StatsMenu::CreateLabels 0x32bd4 (the rows' names), SetLabelValue 0x32b00, Show 0x3381c, Process 0x33c0c
    "stats.row.0": (0x32dc6, 0x32dcc), "stats.row.1": (0x32dda, 0x32de0), "stats.row.2": (0x32dee, 0x32df6),
    "stats.row.3": (0x32e04, 0x32e0c), "stats.row.4": (0x32e1a, 0x32e22), "stats.row.5": (0x32e30, 0x32e38),
    "stats.row.6": (0x32e46, 0x32e4e), "stats.row.7": (0x32e5c, 0x32e64), "stats.row.8": (0x32e72, 0x32e7a),
    "stats.row.9": (0x32e88, 0x32e90), "stats.row.10": (0x32e9e, 0x32ea6), "stats.row.11": (0x32eb4, 0x32ebc),
    "stats.row.12": (0x32eca, 0x32ed2), "stats.row.13": (0x32ee0, 0x32ee8), "stats.row.14": (0x32ef6, 0x32efe),
    "stats.row.15": (0x32f0c, 0x32f14), "stats.row.16": (0x32f22, 0x32f2a),
    "stats.percent": (0x32b28, 0x32b30), "stats.int": (0x32b36, 0x32b3c), "stats.difficulty": (0x33a7a, 0x33a7c),
    "stats.score": (0x33ab0, 0x33ab2), "stats.race_class": (0x33f62, 0x33f64),
    # NameScreen::Initialise 0x395f0 and Show 0x3bd60 (the new-game setup screen)
    "setup.begin": (0x39602, 0x39618), "intro.begin": (0x2df12, 0x2df20),
    "mode.heading": (0x112a90, 0x112a9a), "mode.scoring": (0x112aa2, 0x112aae), "mode.rules": (0x112ab4, 0x112ac0), "setup.name": (0x396ce, 0x396d4), "setup.difficulty": (0x396da, 0x396e2),
    "setup.challenge": (0x396ea, 0x396f2), "setup.class": (0x396fa, 0x39706), "setup.properties": (0x3970e, 0x3971a),
    "setup.help": (0x39722, 0x3972a), "setup.random": (0x39724, 0x39730), "setup.edit": (0x3975e, 0x3976c),
    "setup.back": (0x39774, 0x3977e), "setup.enter_name": (0x3bddc, 0x3bde4), "setup.level": (0x3bfa8, 0x3bfac),
    # NameScreen::ProcessInput 0x3bff8: the class panel's Help texts (the help popup's texts 100..104)
    "help.screen.100": (0x3c4e2, 0x3c4f0), "help.screen.101": (0x3c50a, 0x3c514), "help.screen.102": (0x3c526, 0x3c534),
    "help.screen.103": (0x3c552, 0x3c55c), "help.screen.104": (0x3c57c, 0x3c58e),
    # GameOverScreen::Initialise 0x307f8 (the tally's headings, the class line, the values' first text) and Process
    # 0x30c28 (the values)
    "over.turn": (0x30888, 0x30896), "over.level": (0x308a6, 0x308ae), "over.average": (0x308ca, 0x308d2),
    "over.max": (0x308dc, 0x308e6), "over.pretzels": (0x308f0, 0x308f6), "over.xp": (0x308fe, 0x30908),
    "over.gold": (0x30912, 0x3091c), "over.upgrades": (0x30926, 0x3092c), "over.items": (0x3093a, 0x30948),
    "over.skills": (0x30952, 0x30960), "over.perks": (0x3096a, 0x30976), "over.flaws": (0x30980, 0x3098a),
    "over.score": (0x30994, 0x3099e), "over.class": (0x30a12, 0x30a18), "over.zero": (0x30ad8, 0x30afa),
    "over.tenths": (0x311d8, 0x311de), "over.int": (0x31200, 0x31204),
    # ScoreScreen::Initialise 0x352a4 (the headings, the ranks), InitialisePage 0x36284 (the value headings: a
    # challenge's mode 1 page, the others) and SetLabelNumber 0x34c04
    "scores.turns": (0x35330, 0x35336), "scores.score": (0x3534a, 0x35352), "scores.rank": (0x353ea, 0x353fe),
    "scores.avg": (0x3647e, 0x36486), "scores.max": (0x3648e, 0x36496), "scores.total": (0x3649e, 0x364a6),
    "scores.xp": (0x364aa, 0x364b2), "scores.gp": (0x364ba, 0x364c2), "scores.up": (0x364ca, 0x364d2),
    "scores.int": (0x34c1c, 0x34c22), "scores.tenths": (0x34c38, 0x34c3c),
    # UnlockMenu::Show(ClassType, int) 0x1096fc: a class levelled up, a class unlocked (its description: class.unlock)
    "unlock.level_title": (0x10971e, 0x109726), "unlock.level_text": (0x109738, 0x10973c),
    "unlock.class_title": (0x109756, 0x10975a),
    # Tooltip::ShowScroll 0x2c2f8, Show(EnemyType) 0x2c384, Show(SkillType, int, int) 0x2c4a4
    "tooltip.scroll": (0x2c310, 0x2c314), "tooltip.scroll_text": (0x2c32e, 0x2c334), "tooltip.mortal": (0x2c3c6, 0x2c3ca),
    "tooltip.cooldown": (0x2c4ec, 0x2c4f2),
    # Interface::Process 0x20c64: a challenge game's score line and turn
    "challenge.score_both": (0x20f96, 0x20fa0), "challenge.score_bonus": (0x20fbc, 0x20fc0), "challenge.score": (0x20fc6, 0x20fca),
    "challenge.score_plus": (0x21032, 0x21036), "challenge.score_plus1": (0x21040, 0x21044),
    "challenge.score_plus2": (0x2104e, 0x21052), "challenge.score_plus3": (0x21058, 0x2105c), "challenge.turn": (0x21092, 0x21094),
}
# Item::MakeStatLabels 0x26600 (the stats menu's item page): each stat above 0 on a line of its own, in this order,
# with the (ldr, add) of its format; 5 (a skill) is a fixed text.
ITEM_LINES = [(11, 0x2662e, 0x26636), (0, 0x26658, 0x2665e), (1, 0x26688, 0x2668c), (10, 0x266b6, 0x266ba),
              (8, 0x266e4, 0x266e8), (18, 0x26712, 0x26716), (19, 0x26740, 0x26744), (9, 0x2676e, 0x26772),
              (2, 0x2679c, 0x267a0), (3, 0x267ca, 0x267ce), (4, 0x267f8, 0x267fc), (5, 0x26826, 0x2682c),
              (6, 0x26866, 0x26868), (7, 0x268b4, 0x268b8), (13, 0x26904, 0x26908), (12, 0x26944, 0x2694a),
              (14, 0x26974, 0x26978), (15, 0x269a2, 0x269a6), (16, 0x269d0, 0x269d4), (17, 0x269fe, 0x26a02)]
# ClassScreen's texts (key: (ldr, add) of the string): its labels, tab texts, the messages of Process and the Help
# button's texts 105..122 (HelpMenu::QueueHelp in ClassScreen::Process).
CLASS_TEXTS = {
    "class.games": (0x10c7b4, 0x10c7bc), "class.kills": (0x10c7cc, 0x10c7d2), "class.normal": (0x10c7dc, 0x10c7e4),
    "class.hard": (0x10c7ee, 0x10c7f4), "class.harder": (0x10c7fe, 0x10c808),
    "class.tab.0": (0x10c80e, 0x10c818), "class.tab.1": (0x10c822, 0x10c82a), "class.tab.2": (0x10c834, 0x10c83a),
    "class.tab.3": (0x10c844, 0x10c84a),
    "class.racial": (0x10b2fc, 0x10b2fe), "class.mortal": (0x10b408, 0x10b40a), "class.cooldown": (0x10bd0e, 0x10bd12),
    "class.apart": (0x10c02c, 0x10c034), "class.title": (0x10c044, 0x10c050),
    "class.text.class": (0x10c6c0, 0x10c6c6), "class.text.race0": (0x10c66c, 0x10c670), "class.text.race_locked": (0x10c73a, 0x10c740),
    "class.text.race": (0x10c67c, 0x10c684), "class.text.perks0": (0x10c57a, 0x10c580), "class.text.perks": (0x10c59a, 0x10c5a4),
    "class.text.perks_locked": (0x10c5b0, 0x10c5b8), "class.text.skills0": (0x10c5ec, 0x10c5f0),
    "class.text.skills_locked": (0x10c606, 0x10c60a), "class.text.skills": (0x10c632, 0x10c638),
    "class.adventurer": (0x10cc64, 0x10cc6c), "class.adventurer_levels": (0x10cc66, 0x10cc6e),
    "class.racial_help": (0x10cd02, 0x10cd08), "class.mortal_help": (0x10cd38, 0x10cd3e),
    "class.skill_fixed": (0x10dbc0, 0x10dbc4), "class.skill_locked": (0x10dc1e, 0x10dc20), "class.skill_max": (0x10dc4c, 0x10dc4e),
    "class.skill_more": (0x10dc6a, 0x10dc6c), "class.level": (0x10dd9c, 0x10dda2),
}
CLASS_HELP = [(0x10d160, 0x10d16e), (0x10d1da, 0x10d1f0), (0x10d282, 0x10d28a), (0x10d2be, 0x10d2cc), (0x10d2f6, 0x10d306),
              (0x10d344, 0x10d352), (0x10d3b6, 0x10d3c4), (0x10d454, 0x10d468), (0x10d4c6, 0x10d4d4),
              (0x10d55c, 0x10d56c), (0x10d5cc, 0x10d5e6), (0x10d640, 0x10d65c), (0x10d6b2, 0x10d6c0),
              (0x10d708, 0x10d716), (0x10d72e, 0x10d736), (0x10d790, 0x10d7a6), (0x10d7e6, 0x10d7ee), (0x10d808, 0x10d810)]
# Name tables read by calling the original's lookups: (key, function, indices).
LOOKUPS = [("race.name", "__ZN14CharacterClass11GetRaceNameE8RaceType", range(10)),
           ("class.name", "__ZN14CharacterClass12GetClassNameE9ClassType", range(10)),
           ("class.unlock", "__ZN14CharacterClass20GetUnlockDescriptionE9ClassType", range(10)),
           ("race.bonus", "__ZN14CharacterClass25GetRacialBonusDescriptionE8RaceType", range(10)),
           ("race.bonusname", "__ZN14CharacterClass18GetRacialBonusNameE8RaceType", range(10)),
           ("race.mortaldesc", "__ZN14CharacterClass25GetMortalEnemyDescriptionE8RaceType", range(10)),
           ("perk.name", "__ZN14CharacterClass11GetPerkNameE8PerkType", range(10)),
           ("flaw.name", "__ZN14CharacterClass11GetFlawNameE8FlawType", range(10)),
           ("perk.desc", "__ZN14CharacterClass18GetPerkDescriptionE8PerkType", range(10)),
           ("flaw.desc", "__ZN14CharacterClass18GetFlawDescriptionE8FlawType", range(10)),
           ("difficulty.name", "__ZN4Game17GetDifficultyNameEi", range(4)),
           ("mode.name", "__ZN4Game11GetModeNameEi", (0, 1, 3))]
# Item::MakeStats: the stats in the order it writes them (UpgradeType) with the (ldr, add) of each format.
ITEM_STATS = [(11, 0x28e88, 0x28e8e), (0, 0x28eee, 0x28ef4), (1, 0x28f56, 0x28f5c), (10, 0x28fbe, 0x28fc4),
              (8, 0x29022, 0x29028), (18, 0x29088, 0x2908e), (19, 0x290ee, 0x290f4), (9, 0x29154, 0x2915a),
              (2, 0x291b8, 0x291be), (3, 0x2921e, 0x29224), (4, 0x29284, 0x2928a), (5, None, None),
              (6, 0x29370, 0x29376), (7, 0x293fe, 0x29404), (13, 0x2948c, 0x29492), (12, 0x294fa, 0x294fe),
              (14, 0x2955c, 0x29562), (15, 0x295c2, 0x295c8), (16, 0x29628, 0x2962e), (17, 0x29690, 0x29696)]


def texts():
    """The game's English texts the drawing shows, read from the original program (local only, like the art):
    Skill::GetSkillName / GetSkillDescription tables (0x1d6888, 18 bytes each; 0x1d6b58, 120), the stat options'
    names (Skill::Initialise(StatType), 0x1d7eb8, 12), ItemUpgrade names / descriptions (0x1d8098, 17; 0x1d81ec, 32)
    and the labels of ItemUpgrade::InitStats 0x2d958 (by its case table, with the way each is written), the
    format strings above (with the stats menu's row names and Item::MakeStatLabels' lines), and, read from the
    running original, the item names Item::InitialiseNames builds at start-up (the prefix list 0x1ead24 and the name
    lists by icon range 0x1eadcc) and the race, class, perk, flaw, difficulty and mode names of LOOKUPS."""
    m = ARMv7(PROGRAM)
    out = []
    def table(key, base, stride, n):
        for i in range(n):
            out.append(("%s.%d" % (key, i), m.cstr(base + stride * i)))
    table("skill.name", pcrel(m, 0x2ab6e, 0x2ab70), 18, 40)
    table("skill.desc", pcrel(m, 0x2ab82, 0x2ab84), 120, 40)
    table("stat.name", pcrel(m, 0x2b46e, 0x2b474), 12, 8)
    table("upgrade.name", pcrel(m, 0x2daca, 0x2dacc), 17, 20)
    table("upgrade.desc", pcrel(m, 0x2d058, 0x2d05c), 32, 20)
    table("help.topic", pcrel(m, 0x380ea, 0x380f2), 190, 23)   # HelpMenu::Initialise 0x380b8: the 23 help topics
    table("setup.key", pcrel(m, 0x39636, 0x39668), 6, 30)      # NameScreen::Initialise: the 30 keys' texts
    table("story", pcrel(m, 0x2dfb4, 0x2dfb6), 560, 61)         # IntroScreen::Initialise: RandI(0, 60, stream 0)
    for mode in range(2):                                        # ModeScreen::ShowMode 0x112f84: each mode's lines
        table("mode.intro.%d" % mode, 0x1e6d4c + 0x100 * mode, 64, 4)
        table("mode.score.%d" % mode, 0x1e6f4c + 0x100 * mode, 64, 4)
        table("mode.special.%d" % mode, 0x1e714c + 0x300 * mode, 128, 6)
    for t, case in enumerate(m.tbb(0x2d976, 20)):   # each case: ldr r1, [pc, #i]; add r1, pc; then the writer
        if m.u16(case) & 0xf800 == 0x4800:
            label, after = pcrel(m, case, case + 2), case + 4
        else:
            label, after = pcrel(m, case, case + 4), case + 6
        ins = m.u16(after)
        target = after + 4 + ((ins & 0x7ff) << 1) - (0x1000 if ins & 0x400 else 0) if ins & 0xf800 == 0xe000 else after
        kind = {0x2d9e4: "float", 0x2d9f2: "percent", 0x2da18: "int"}[target]
        out.append(("upgrade.stat.%d" % t, m.cstr(label)))
        out.append(("upgrade.kind.%d" % t, kind))
    for key, (ldr, add) in NAMED.items():
        out.append((key, m.cstr(pcrel(m, ldr, add))))
    for key, (ldr, add) in CLASS_TEXTS.items():
        out.append((key, m.cstr(pcrel(m, ldr, add))))
    for i, (ldr, add) in enumerate(CLASS_HELP):
        out.append(("help.screen.%d" % (105 + i), m.cstr(pcrel(m, ldr, add))))
    for i, (t, ldr, add) in enumerate(ITEM_STATS):
        out.append(("item.stat.%d" % i, "%d" % t))
        if ldr is not None:
            out.append(("item.format.%d" % t, m.cstr(pcrel(m, ldr, add))))
    for i, (t, ldr, add) in enumerate(ITEM_LINES):
        out.append(("item.line.%d" % i, "%d" % t))
        out.append(("item.long.%d" % t, m.cstr(pcrel(m, ldr, add))))
    import original_frame as of
    o = of.Original()
    for f in o.m.init_functions():
        o.call(f)
    for key, name, indices in LOOKUPS:
        for i in indices:
            out.append(("%s.%d" % (key, i), o.cstr(o.call(o.fn(name), i), 300).decode("latin1")))
    for r in range(10):   # each race's mortal enemy
        e = o.call(o.fn("__ZN14CharacterClass18GetMortalEnemyTypeE8RaceType"), r)
        out.append(("race.enemy.%d" % r, "%d" % e))
    for e in range(33):   # every enemy's name and description (Tile::GetEnemyName / GetEnemyDescription: the tooltip)
        out.append(("enemy.name.%d" % e, o.cstr(o.call(o.fn("__ZN4Tile12GetEnemyNameE9EnemyType"), e), 300).decode("latin1")))
        out.append(("enemy.desc.%d" % e, o.cstr(o.call(o.fn("__ZN4Tile19GetEnemyDescriptionE9EnemyType"), e), 300).decode("latin1")))
    g = o.alloc(of.GAME_SIZE)
    o.call(o.fn("__ZN4GameC1Ev"), g)   # its Items run Item::InitialiseNames
    for c in range(10):   # CharacterClass::GetLevelDescription of a record CharacterClass::Initialise made for each class
        rec = o.alloc(0x184)
        o.call(o.fn("__ZN14CharacterClassC1Ev"), rec)
        o.call(o.fn("__ZN14CharacterClass10InitialiseE9ClassTypeP4Game"), rec, c, g)
        for level in range(1, 11):
            p = o.call(o.fn("__ZN14CharacterClass19GetLevelDescriptionEi"), rec, level)
            out.append(("class.leveldesc.%d.%d" % (c, level), o.cstr(p, 300).decode("latin1")))
    def vector(address, size=4):
        begin, end = o.r32(address), o.r32(address + 4)
        return [begin + size * k for k in range((end - begin) // size)]
    for i, p in enumerate(vector(0x1ead24)):
        out.append(("item.prefix.%d" % i, o.cstr(o.r32(p), 64).decode("latin1")))
    for i, e in enumerate(vector(0x1eadcc, 12)):
        names, lo, hi = o.r32(e), o.r32(e + 4), o.r32(e + 8)
        out.append(("item.range.%d" % i, "%d %d" % (lo, hi)))
        for k, p in enumerate(vector(names)):
            out.append(("item.names.%d.%d" % (i, k), o.cstr(o.r32(p), 64).decode("latin1")))
    def escape(v):
        return v.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t")
    with open(os.path.join(OUT, "texts.txt"), "w", encoding="utf-8") as f:
        f.write("# The original game's texts (frontend/tools/import_original_assets.py texts(); local only)\n")
        for k, v in out:
            f.write("%s\t%s\n" % (k, escape(v)))
    return len(out)


def keep_raw():
    """The pictures and fonts are read as plain files (original.gd, the library's fonts), not as Godot resources:
    Godot is told to keep them as they are, so an exported game (iOS) carries the files themselves."""
    for name in TEXTURES + FONTS:
        with open(os.path.join(OUT, name + ".import"), "w", encoding="utf-8") as f:
            f.write('[remap]\n\nimporter="keep"\n')


def main():
    if "--raw" in sys.argv:
        keep_raw()
        make_icns()
        return
    if "--texts" in sys.argv:
        print("wrote %d texts into %s" % (texts(), os.path.relpath(os.path.join(OUT, "texts.txt"), ROOT)))
        return
    for p in [DECODED, ORIGINAL, IPA, PROGRAM]:
        if not os.path.exists(p):
            sys.exit("missing local source: " + os.path.relpath(p, ROOT))
    os.makedirs(os.path.join(OUT, "sounds"), exist_ok=True)
    for t in TEXTURES:
        shutil.copy2(os.path.join(DECODED, t), os.path.join(OUT, t))
    for f in FONTS:
        shutil.copy2(os.path.join(ORIGINAL, f), os.path.join(OUT, f))
    table = sound_table()
    with zipfile.ZipFile(IPA) as z, tempfile.TemporaryDirectory() as tmp:
        names = set(z.namelist())
        for s in table:
            for k in range(1, s["variations"] + 1):
                src = "Payload/DungeonRaid.app/%s%d.caf" % (s["name"], k)
                if src not in names:
                    sys.exit("missing sound " + src)
                caf = os.path.join(tmp, "%s%d.caf" % (s["name"], k))
                with open(caf, "wb") as f:
                    f.write(z.read(src))
                wav = os.path.join(OUT, "sounds", "%s%d.wav" % (s["name"], k))
                subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16", caf, wav], check=True)
        for icon in ["icon.png", "icon@2x.png"]:
            with open(os.path.join(OUT, icon), "wb") as f:
                f.write(z.read("Payload/DungeonRaid.app/" + icon))
    with open(os.path.join(OUT, "sounds.json"), "w", encoding="utf-8") as f:
        json.dump(table, f, indent=1)
    make_icns()
    keep_raw()
    texts()
    print("imported %d textures, %d fonts, %d sounds into %s" % (len(TEXTURES), len(FONTS),
          sum(s["variations"] for s in table), os.path.relpath(OUT, ROOT)))


def make_icns():
    """The app icons for the Mac app and the iPhone app (from the original's 114-pixel icon, scaled; local only)."""
    with tempfile.TemporaryDirectory() as tmp:
        iconset = os.path.join(tmp, "icon.iconset")
        os.makedirs(iconset)
        src = os.path.join(OUT, "icon@2x.png")
        for size in [16, 32, 64, 128, 256, 512]:
            subprocess.run(["sips", "-z", str(size), str(size), src, "--out", os.path.join(iconset, "icon_%dx%d.png" % (size, size))],
                           check=True, capture_output=True)
            if size <= 256:
                subprocess.run(["sips", "-z", str(size * 2), str(size * 2), src, "--out",
                                os.path.join(iconset, "icon_%dx%d@2x.png" % (size, size))], check=True, capture_output=True)
        subprocess.run(["iconutil", "-c", "icns", iconset, "-o", os.path.join(OUT, "icon.icns")], check=True)
    # The iPhone app's icon (export_presets.cfg, icons/icon_1024x1024); Godot makes the other sizes from it.
    subprocess.run(["sips", "-z", "1024", "1024", src, "--out", os.path.join(OUT, "icon1024.png")], check=True, capture_output=True)


if __name__ == "__main__":
    main()
