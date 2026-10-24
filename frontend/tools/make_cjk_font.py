#!/usr/bin/env python3
"""Makes the Chinese glyph atlases the game's three fonts draw their wide characters from (T050-D).

  python3 frontend/tools/make_cjk_font.py [lang]        (default zh)

For each of the original's bitmap fonts (font, fontMenu, fontScore) it writes frontend/godot/assets/lang/<lang>/<name>.fnt
and <name>.png in the BMFont text layout Font::load_wide reads (frontend/gdext/src/ui/text.cpp): every character from
128 up that the language's texts use (texts.txt and atlas.txt in the same folder, plus EXTRA), drawn white (the game
tints them, as the original's), fontScore with a black outline like its own.

The glyphs come from Source Han Sans (Adobe, SIL Open Font License 1.1; downloaded with the owner's consent on
2026-10-23 into frontend/tools/fonts/, not in Git). Their size follows the original font: the Chinese em square spans
a set multiple of the height of the original's capitals (STYLES), centred on them, so a Chinese line sits where an English one does.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.dirname(HERE)
ORIGINAL = os.path.join(FRONTEND, "godot", "assets", "original")
FONTS = os.path.join(HERE, "fonts")
# name: (weight, pixels per em, outline in em, the Chinese em square over the original capitals' height, the small
# capitals' scale or 1, the step from one character to the next in ems): fontMenu's and fontScore's English is mostly
# small capitals (0.75, Font::UseSmallCaps), whose middle sits lower, so their Chinese is smaller and centred where
# they are (fontScore: the challenge's "Score" and "Turn" over the board); the steps leave a little room between
# characters (the owner: "字和字之间拉开一点")
STYLES = {"font": ("Medium", 56, 0.0, 1.3, 1.0, 1.04), "fontMenu": ("Heavy", 56, 0.0, 0.8, 0.75, 1.12),
          "fontScore": ("Bold", 48, 0.07, 0.85, 0.75, 1.08)}
PAD = 4         # empty pixels around each glyph in the atlas
WIDTH = 2048    # atlas width; the height is what the characters take
EXTRA = "，。！？；：、（）《》「」『』…—·％＋－"


def original_metrics(name):
    """The original .fnt's line height, base and its capitals' top and bottom (pixels from the line's top)."""
    lh = base = 0
    tops, bottoms = [], []
    with open(os.path.join(ORIGINAL, name + ".fnt"), encoding="latin-1") as f:
        for line in f:
            p = dict(kv.split("=", 1) for kv in line.split()[1:] if "=" in kv)
            if line.startswith("common"):
                lh, base = int(p["lineHeight"]), int(p["base"])
            elif line.startswith("char ") and 65 <= int(p["id"]) <= 90:
                tops.append(int(p["yoffset"]))
                bottoms.append(int(p["yoffset"]) + int(p["height"]))
    return lh, base, sum(tops) / len(tops), sum(bottoms) / len(bottoms)


def characters(folder):
    chars = set(EXTRA)
    for name in ("texts.txt", "atlas.txt"):
        path = os.path.join(folder, name)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("#"):
                        continue
                    chars.update(line.rstrip("\n").split("\t", 1)[-1])
    return sorted(c for c in chars if ord(c) >= 128)


def make(name, chars, out):
    weight, px, outline, em_ratio, small, step = STYLES[name]
    font = ImageFont.truetype(os.path.join(FONTS, "SourceHanSansCN-%s.otf" % weight), px)
    lh, base, cap_top, cap_bottom = original_metrics(name)
    em_orig = em_ratio * (cap_bottom - cap_top)         # the em square in the original's pixels
    k = px / em_orig                                    # Chinese pixels per original pixel
    line_height, base_px = round(lh * k), round(base * k)
    middle = base + small * ((cap_top + cap_bottom) / 2 - base)   # (a small capital's middle: scaled about the base)
    em_top = (middle - em_orig / 2) * k   # the em square's top, from the line's top
    stroke = round(outline * px)
    cell = px + 2 * PAD + 2 * stroke
    per_row = WIDTH // cell
    rows = (len(chars) + per_row - 1) // per_row
    height = rows * cell
    atlas = Image.new("RGBA", (WIDTH, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(atlas)
    ascent = font.getmetrics()[0]
    lines = []
    for n, ch in enumerate(chars):
        x, y = (n % per_row) * cell, (n // per_row) * cell
        # the em square (ascent above the baseline: Source Han's 0.88 em) at the cell's padding
        origin = (x + PAD + stroke, y + PAD + stroke + px * 0.88 - ascent)
        if stroke:
            draw.text(origin, ch, font=font, fill=(255, 255, 255, 255), stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
        else:
            draw.text(origin, ch, font=font, fill=(255, 255, 255, 255))
        advance = (font.getlength(ch) or px) * step
        # Label::SetText moves the pen by half the width plus the stored (halved) advance: the stored advance makes
        # the whole step the glyph's own advance.
        xadvance = round(2 * advance - cell)
        yoffset = round(em_top - PAD - stroke)
        lines.append("char id=%d x=%d y=%d width=%d height=%d xoffset=0 yoffset=%d xadvance=%d page=0 chnl=15"
                     % (ord(ch), x, y, cell, cell, yoffset, xadvance))
    atlas.save(os.path.join(out, name + ".png"))
    with open(os.path.join(out, name + ".fnt"), "w", encoding="utf-8") as f:
        f.write('info face="Source Han Sans CN %s" size=%d bold=0 italic=0 charset="" unicode=1 stretchH=100 smooth=1 '
                'aa=1 padding=%d,%d,%d,%d spacing=0,0 outline=%d\n' % (weight, px, PAD, PAD, PAD, PAD, stroke))
        f.write("common lineHeight=%d base=%d scaleW=%d scaleH=%d pages=1 packed=0\n" % (line_height, base_px, WIDTH, height))
        f.write('page id=0 file="%s.png"\n' % name)
        f.write("chars count=%d\n" % len(lines))
        f.write("\n".join(lines) + "\n")
    return len(lines), (WIDTH, height)


def main():
    lang = sys.argv[1] if len(sys.argv) > 1 else "zh"
    out = os.path.join(FRONTEND, "godot", "assets", "lang", lang)
    if not os.path.isdir(FONTS):
        sys.exit("frontend/tools/fonts/ is missing (Source Han Sans, see frontend/README.md)")
    chars = characters(out)
    for name in STYLES:
        n, size = make(name, chars, out)
        print("%s: %d characters, atlas %dx%d" % (name, n, *size))
    keep_files(out)


def keep_files(folder):
    """The language folder's pictures and fonts are read as plain files (like assets/original's): Godot is told to
    keep them as they are, so an exported game (iOS) carries the files themselves."""
    for name in os.listdir(folder):
        if name.endswith((".png", ".fnt")):
            with open(os.path.join(folder, name + ".import"), "w", encoding="utf-8") as f:
                f.write('[remap]\n\nimporter="keep"\n')


if __name__ == "__main__":
    main()
