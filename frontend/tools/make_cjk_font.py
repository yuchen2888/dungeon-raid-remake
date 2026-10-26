#!/usr/bin/env python3
"""Makes the glyph atlases the game's three fonts draw their wide characters from (T050-D; T050-K: other languages).

  python3 frontend/tools/make_cjk_font.py [lang]        (default zh; zh_TW, ja, ko, es)

For each of the original's bitmap fonts (font, fontMenu, fontScore) it writes frontend/godot/assets/lang/<lang>/<name>.fnt
and <name>.png in the BMFont text layout Font::load_wide reads (frontend/gdext/src/ui/text.cpp): every character from
128 up that the language's texts use (texts.txt and atlas.txt in the same folder, plus EXTRA), drawn white (the game
tints them, as the original's), fontScore with a black outline like its own.

The glyphs come from Source Han Sans (Adobe, SIL Open Font License 1.1; downloaded with the owner's consent on
2026-10-23 into frontend/tools/fonts/, not in Git). Their size follows the original font: the Chinese em square spans
a set multiple of the height of the original's capitals (STYLES), centred on them, so a Chinese line sits where an English one does.
Each language takes the Source Han Sans of its region (REGION: Traditional Chinese, Japanese and Korean got theirs with
the owner's consent on 2026-10-26), so the characters the scripts share take that region's shapes.

A Latin-script language (LATIN: Spanish) needs only a few letters the original lacks (á, ñ, ¡ ...): they are put
together from the original fonts' own strokes (LatinFont), so they look like the letters around them.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

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
# the Source Han Sans region each language's characters come from (frontend/tools/fonts/SourceHanSans<region>-*.otf)
REGION = {"zh": "CN", "zh_TW": "TW", "ja": "JP", "ko": "KR"}
LATIN = {"es"}
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


def characters(folder, extra=EXTRA):
    chars = set(extra)
    for name in ("texts.txt", "atlas.txt"):
        path = os.path.join(folder, name)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("#"):
                        continue
                    chars.update(line.rstrip("\n").split("\t", 1)[-1])
    return sorted(c for c in chars if ord(c) >= 128)


def make(name, chars, out, region="CN"):
    weight, px, outline, em_ratio, small, step = STYLES[name]
    font = ImageFont.truetype(os.path.join(FONTS, "SourceHanSans%s-%s.otf" % (region, weight)), px)
    missing = [c for c in chars if not has_glyph(font, c)]
    if missing:
        print("%s: not in Source Han Sans %s: %s" % (name, region, "".join(missing)))
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
        f.write('info face="Source Han Sans %s %s" size=%d bold=0 italic=0 charset="" unicode=1 stretchH=100 smooth=1 '
                'aa=1 padding=%d,%d,%d,%d spacing=0,0 outline=%d\n' % (region, weight, px, PAD, PAD, PAD, PAD, stroke))
        f.write("common lineHeight=%d base=%d scaleW=%d scaleH=%d pages=1 packed=0\n" % (line_height, base_px, WIDTH, height))
        f.write('page id=0 file="%s.png"\n' % name)
        f.write("chars count=%d\n" % len(lines))
        f.write("\n".join(lines) + "\n")
    return len(lines), (WIDTH, height)


def has_glyph(font, ch):
    """Whether the font draws ch as itself (not its empty-box .notdef)."""
    return font.getmask(ch).getbbox() is None or bytes(font.getmask(ch)) != bytes(font.getmask("\U000f0000"))


# ---- Latin-script languages ---------------------------------------------------------------------------------------
HD = os.path.join(FRONTEND, "godot", "assets", "hd")
SPACING = {"font": 0.0, "fontMenu": -0.225, "fontScore": -0.05}   # presenter.cpp: each font's spacing
SMALL_CAPS = {"fontMenu": 0.75, "fontScore": 0.75}   # presenter.cpp: lower case drawn as small capitals
LATIN_EXTRA = "áéíóúñüÁÉÍÓÚÑÜ¡¿"
MARKS = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n", "ü": "u"}   # the letters under the accents
ACCENT_OF = {"á": "acute", "é": "acute", "í": "acute", "ó": "acute", "ú": "acute", "ñ": "tilde", "ü": "dots"}
# each font's accents: the font and glyph they are cut from, turned how (mirror: left to right), their height over the
# font's capitals' (None: as the glyph is) and how much thicker their strokes are made (over the capitals' height).
# font has the marks themselves (` ~ .); fontMenu and fontScore have only capitals and a few signs: the acute is
# fontMenu's slash made thicker and fontScore's comma (a wedge), the dots their full stop, the tilde font's, drawn as
# thick as their strokes (fontScore's with its black outline).
ACCENTS = {
    "font": {"acute": ("font", "`", "mirror", None, 0), "tilde": ("font", "~", None, None, 0),
             "dots": ("font", ".", None, None, 0)},
    "fontMenu": {"acute": ("fontMenu", "/", None, 0.4, 0.035), "tilde": ("font", "~", None, 0.24, 0.04),
                 "dots": ("fontMenu", ".", None, 0.24, 0)},
    "fontScore": {"acute": ("fontScore", ",", None, 0.42, 0), "tilde": ("font", "~", None, 0.22, 0.03),
                  "dots": ("fontScore", ".", None, 0.3, 0)},
}
OUTLINE = {"fontScore": 0.09}   # its black outline's width over its capitals' height


class LatinFont:
    """One of the original's bitmap fonts with the accented letters put together from its own glyphs, at the HD
    fonts' scale where they are here (k pixels for each of the original's)."""

    def __init__(self, name):
        self.name = name
        self.glyphs = {}
        with open(os.path.join(ORIGINAL, name + ".fnt"), encoding="latin-1") as f:
            for line in f:
                p = dict(kv.split("=", 1) for kv in line.split()[1:] if "=" in kv)
                if line.startswith("common"):
                    self.lh, self.base, size = int(p["lineHeight"]), int(p["base"]), int(p["scaleW"])
                elif line.startswith("char "):
                    self.glyphs[chr(int(p["id"]))] = tuple(int(p[k]) for k in ("x", "y", "width", "height", "xoffset",
                                                                              "yoffset", "xadvance"))
        hd = os.path.join(HD, name + ".png")
        sheet = Image.open(hd if os.path.exists(hd) else os.path.join(ORIGINAL, name + ".png")).convert("RGBA")
        self.sheet, self.k = sheet, sheet.width // size
        caps = [self.glyphs[c] for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]
        self.cap_top = sum(g[5] for g in caps) / len(caps)
        self.cap_h = sum(g[3] for g in caps) / len(caps)
        self.small = SMALL_CAPS.get(name)

    def piece(self, ch):
        x, y, w, h = (v * self.k for v in self.glyphs[ch][:4])
        return self.sheet.crop((x, y, x + w, y + h))

    def accent(self, kind, capital=False):
        source, src, turn, height, thicker = ACCENTS[self.name][kind]
        img = (self if source == self.name else LatinFont(source)).piece(src)
        img = img.crop(ink(img) or (0, 0, img.width, img.height))
        if turn == "mirror":
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        s = height * self.cap_h * self.k / img.height if height else 1.0
        if capital:   # (a capital's accent flatter, so the letter stays tall in the same room)
            img = img.resize((img.width, max(1, round(img.height * 0.75))), Image.LANCZOS)
        if s != 1.0:
            img = img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)
        if thicker:   # restyled: its white strokes made thicker (and outlined) like this font's
            grow = round(thicker * self.cap_h * self.k)
            ring = round(OUTLINE.get(self.name, 0) * self.cap_h * self.k)
            m = 2 * (grow + ring) + 2
            mask = Image.new("L", (img.width + 2 * m, img.height + 2 * m), 0)
            mask.paste(img.getchannel("A"), (m, m))
            mask = mask.filter(ImageFilter.MaxFilter(2 * grow + 1)).filter(ImageFilter.GaussianBlur(self.k / 2))
            img = Image.new("RGBA", mask.size, (0, 0, 0, 0))
            if ring:
                img.paste((0, 0, 0, 255), (0, 0), mask.filter(ImageFilter.MaxFilter(2 * ring + 1)))
            img.paste((255, 255, 255, 255), (0, 0), mask)
            img = img.crop(ink(img))
        if kind == "dots":   # two of them, a dot apart
            two = Image.new("RGBA", (img.width * 3, img.height), (0, 0, 0, 0))
            two.alpha_composite(img, (0, 0))
            two.alpha_composite(img, (img.width * 2, 0))
            img = two
        return img

    def glyph(self, ch):
        """The glyph's picture and its .fnt numbers in this font's pixels times k (an atlas with lineHeight
        lh * k), or (None, None) when the font has no letter to build it from."""
        lower = ch.islower() and self.small
        letter = MARKS.get(ch.lower(), ch.lower()) if ch.isalpha() else ch
        if ch in ("¡", "¿"):
            letter = {"¡": "!", "¿": "?"}[ch]
        base_ch = letter.upper() if (self.small or ch.isupper()) else letter
        if base_ch not in self.glyphs:
            return None, None
        x, y, w, h, ox, oy, adv = self.glyphs[base_ch]
        k = self.k
        base = self.piece(base_ch)
        if ch in ("¡", "¿"):   # turned over and lowered (they hang below the line)
            canvas, (x0, y0) = base.rotate(180), (0, round(0.3 * self.cap_h * k))
        elif ch.lower() not in ACCENT_OF:   # (a letter of the font's own)
            canvas, (x0, y0) = base, (0, 0)
        else:
            if base_ch == "i" or (base_ch == "I" and self.name == "fontMenu"):   # (fontMenu's I has a dot too)
                # the dotless i: its dot (the piece above the stem) taken off
                base = without_dot(base)
            mark = self.accent(ACCENT_OF[ch.lower()], base_ch.isupper())
            bx0, by0, bx1, by1 = ink(base)
            gap = max(1, round((0.05 if base_ch.isupper() else 0.08) * self.cap_h * k))
            ax = round((bx0 + bx1) / 2 - mark.width / 2 + (0.1 * mark.width if ACCENT_OF[ch.lower()] == "acute" else 0))
            ay = by0 - gap - mark.height
            x0, y0 = min(0, ax), min(0, ay)
            x1, y1 = max(base.width, ax + mark.width), max(base.height, ay + mark.height)
            canvas = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
            canvas.alpha_composite(base, (-x0, -y0))
            canvas.alpha_composite(mark, (ax - x0, ay - y0))
        left, right = -x0, canvas.width - base.width + x0   # how far it reaches beyond the letter's own cell
        if ch in ("¡", "¿"):
            left = right = 0
        # (Label::SetText centres a glyph on the pen plus half its width: a wider glyph keeps the letter where it was
        # by its offset and the pen where it was by its advance; the font's spacing, which a wide glyph does not get,
        # is in the advance)
        m = {"xoffset": ox * k - 2 * left, "yoffset": oy * k + y0, "xadvance": adv * k - (left + right),
             "width": canvas.width, "height": canvas.height}
        if lower:   # a small capital (Font::UseSmallCaps): everything scaled about the line's base
            s = self.small
            canvas = canvas.resize((max(1, round(canvas.width * s)), max(1, round(canvas.height * s))), Image.LANCZOS)
            centre = m["yoffset"] + m["height"] / 2 - self.base * k
            m = {"xoffset": round(m["xoffset"] * s), "yoffset": round(s * centre + self.base * k - canvas.height / 2),
                 "xadvance": round(m["xadvance"] * s), "width": canvas.width, "height": canvas.height}
        m["xadvance"] += round(2 * SPACING[self.name] * self.lh * k)
        return canvas, m


def ink(img):
    return img.getchannel("A").point(lambda a: 255 if a > 60 else 0).getbbox()


def without_dot(img):
    """img with its topmost separate piece (an i's dot) made transparent."""
    a = img.getchannel("A").point(lambda v: 255 if v > 128 else 0)
    px, h, w = a.load(), img.height, img.width
    rows = [any(px[x, y] for x in range(w)) for y in range(h)]
    top = rows.index(True)
    bottom = h - 1 - rows[::-1].index(True)
    gap = next((y for y in range(top, bottom) if not rows[y]), None)   # the empty row between the dot and the stem
    if gap is None:
        return img
    out = img.copy()
    out.paste((0, 0, 0, 0), (0, 0, w, gap))
    return out


def make_latin(name, chars, out):
    font = LatinFont(name)
    built = [(c, *font.glyph(c)) for c in chars]
    built = [b for b in built if b[1] is not None]
    width = 512
    x = y = row = 0
    places = []
    for c, img, m in built:
        if x + img.width + PAD > width:
            x, y, row = 0, y + row + PAD, 0
        places.append((x, y))
        x, row = x + img.width + PAD, max(row, img.height)
    atlas = Image.new("RGBA", (width, y + row), (255, 255, 255, 0))
    lines = []
    for (c, img, m), (px, py) in zip(built, places):
        atlas.alpha_composite(img, (px, py))
        lines.append("char id=%d x=%d y=%d width=%d height=%d xoffset=%d yoffset=%d xadvance=%d page=0 chnl=15"
                     % (ord(c), px, py, m["width"], m["height"], m["xoffset"], m["yoffset"], m["xadvance"]))
    atlas.save(os.path.join(out, name + ".png"))
    with open(os.path.join(out, name + ".fnt"), "w", encoding="utf-8") as f:
        f.write('info face="%s accented" size=%d bold=0 italic=0 charset="" unicode=1 stretchH=100 smooth=1 aa=1 '
                'padding=0,0,0,0 spacing=0,0 outline=0\n' % (name, font.lh * font.k))
        f.write("common lineHeight=%d base=%d scaleW=%d scaleH=%d pages=1 packed=0\n"
                % (font.lh * font.k, font.base * font.k, atlas.width, atlas.height))
        f.write('page id=0 file="%s.png"\n' % name)
        f.write("chars count=%d\n" % len(lines))
        f.write("\n".join(lines) + "\n")
    return len(lines), atlas.size


def main():
    lang = sys.argv[1] if len(sys.argv) > 1 else "zh"
    out = os.path.join(FRONTEND, "godot", "assets", "lang", lang)
    if lang in LATIN:
        chars = characters(out, LATIN_EXTRA)
        for name in STYLES:
            n, size = make_latin(name, chars, out)
            print("%s: %d characters, atlas %dx%d" % (name, n, *size))
        keep_files(out)
        return
    if not os.path.isdir(FONTS):
        sys.exit("frontend/tools/fonts/ is missing (Source Han Sans, see frontend/README.md)")
    chars = characters(out)
    for name in STYLES:
        n, size = make(name, chars, out, REGION[lang])
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
