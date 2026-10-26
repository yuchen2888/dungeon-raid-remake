#!/usr/bin/env python3
"""Makes the settings page's language names (T050-J): each language's name in its own words, a row each.

  python3 frontend/tools/make_names.py

Writes frontend/godot/assets/lang/names.png (1024 pixels wide, a 1024 x 128 row per language, white letters with a
dark outline: the page tints them; the texture LangNames) and names.txt (a language code a line, in the rows' order:
the game offers the ones whose folder is there, English always). Each name is drawn with the Source Han Sans of its
script (frontend/tools/fonts/: CN, TW, JP, KR). The list is the order the page shows them in: add a language here.
Local only, like the rest of assets/lang/ (the fonts are not in Git either).
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
LANG = os.path.join(os.path.dirname(HERE), "godot", "assets", "lang")
FONTS = os.path.join(HERE, "fonts")
# code, name in its own words, the Source Han Sans region its letters come from
LANGUAGES = [
    ("en", "English", "CN"),
    ("zh", "简体中文", "CN"),
    ("zh_TW", "繁體中文", "TW"),
    ("ja", "日本語", "JP"),
    ("ko", "한국어", "KR"),
    ("es", "Español", "CN"),
]
ROW_W, ROW_H = 1024, 128
FILL, OUTLINE = (255, 255, 255, 255), (28, 25, 53, 255)


def main():
    img = Image.new("RGBA", (ROW_W, ROW_H * 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for i, (code, name, region) in enumerate(LANGUAGES):
        path = os.path.join(FONTS, "SourceHanSans%s-Heavy.otf" % region)
        if not os.path.exists(path):
            path = os.path.join(FONTS, "SourceHanSansCN-Heavy.otf")
            print("no %s font: %s drawn with CN" % (region, name))
        font = ImageFont.truetype(path, 92)
        draw.text((ROW_W / 2, ROW_H * i + ROW_H / 2), name, font=font, fill=FILL, anchor="mm", stroke_width=5,
                  stroke_fill=OUTLINE)
    img.save(os.path.join(LANG, "names.png"))
    with open(os.path.join(LANG, "names.png.import"), "w", encoding="utf-8") as f:   # exported as is (iOS)
        f.write('[remap]\n\nimporter="keep"\n')
    with open(os.path.join(LANG, "names.txt"), "w", encoding="utf-8") as f:
        f.write("".join(code + "\n" for code, _, _ in LANGUAGES))
    print("wrote %d names into %s" % (len(LANGUAGES), os.path.join(LANG, "names.png")))


if __name__ == "__main__":
    main()
