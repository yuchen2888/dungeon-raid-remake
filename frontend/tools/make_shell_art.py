#!/usr/bin/env python3
"""Draws the shell app's own icon and launch picture (T081): the shell carries nothing of the original's, so neither
its icon nor its launch picture can be the original's. Plain shapes and the words "Dungeon Raid" in Source Han Sans
(SIL Open Font License 1.1, frontend/tools/fonts/); the results are this project's own and kept in Git.

  python3 frontend/tools/make_shell_art.py     -> frontend/godot/shell/icon.png (1024), splash.png (1280 x 1920),
                                                  text/<key>.<zh|en>.png (the import screen's words, importer.gd)

The import screen's words are pictures too: a phone's own fonts cannot be counted on (Godot's SystemFont finds none on
iOS), and the game's fonts are the original's, which the shell does not have yet.
"""
import os
import re

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "godot", "shell")
FONT = os.path.join(HERE, "fonts", "SourceHanSansCN-Heavy.otf")
GOLD, DARK, PURPLE = (255, 206, 84), (28, 18, 48), (70, 44, 120)


def background(w, h):
    img = Image.new("RGB", (w, h), DARK)
    glow = Image.new("L", (w, h), 0)
    ImageDraw.Draw(glow).ellipse((-w * 0.2, h * 0.15, w * 1.2, h * 1.1), fill=255)
    glow = glow.filter(ImageFilter.GaussianBlur(w * 0.18))
    img.paste(Image.new("RGB", (w, h), PURPLE), (0, 0), glow)
    return img


def tiles(draw, cx, cy, r):
    """Three round tiles side by side, chained by a line: a coin, a potion, a shield (the game's kinds)."""
    xs = [cx - 2.4 * r, cx, cx + 2.4 * r]
    draw.line([(xs[0], cy), (xs[2], cy)], fill=(120, 230, 120), width=max(4, int(r * 0.22)))
    for x, colour in zip(xs, [GOLD, (210, 50, 60), (110, 130, 220)]):
        draw.ellipse((x - r, cy - r, x + r, cy + r), fill=colour, outline=DARK, width=max(3, int(r * 0.12)))


def words(draw, text, cx, cy, size):
    font = ImageFont.truetype(FONT, size)
    draw.text((cx, cy), text, font=font, fill=GOLD, anchor="mm", stroke_width=max(2, size // 14), stroke_fill=DARK)


# importer.gd's words (keep the two in step): key -> (Chinese, English)
WORDS = {
    "intro": ("这是 Dungeon Raid 的非官方重制版，不带原版游戏的任何内容。第一次玩之前，需要你自己的原版 Dungeon Raid 1.3.4（未加密的 IPA 文件）。\n\n"
              "打开“文件”App →“我的 iPhone”→“Dungeon Raid”，把 IPA 放进去，再点下面的“导入”。",
              "This is an unofficial remake of Dungeon Raid, and it holds none of the original game's content. Before the "
              "first game it needs your own copy of the original Dungeon Raid 1.3.4 (an unencrypted IPA file).\n\n"
              "Open the Files app, go to On My iPhone > Dungeon Raid, put the IPA there, then tap Import."),
    "import": ("导入", "Import"),
    "choose": ("选择文件…", "Choose file..."),
    "none": ("没找到 IPA：请把它放进“文件”App 里的“我的 iPhone → Dungeon Raid”文件夹。",
             "No IPA found: put it in the Files app, On My iPhone > Dungeon Raid."),
    "reading": ("正在导入，请稍等…", "Importing, one moment..."),
    "wrong": ("这个文件不是 Dungeon Raid 1.3.4 的未加密原版，没有导入。",
              "This is not the unencrypted original Dungeon Raid 1.3.4; nothing was imported."),
    "encrypted": ("这个 IPA 的程序还是加密的（App Store 下载的都是这样），需要已解密的版本，没有导入。",
                  "This IPA's program is still encrypted (as every App Store download is); a decrypted copy is needed. "
                  "Nothing was imported."),
    "bad_zip": ("打不开这个文件：它不是 IPA。", "This file cannot be opened: it is not an IPA."),
    "done": ("导入完成！", "Imported!"),
    "legal": ("Dungeon Raid 属于 Firemint / EA。本重制版与其无关，只读取你自己的那份原版，不会上传任何东西。",
              "Dungeon Raid belongs to Firemint / EA. This remake has nothing to do with them; it only reads your own "
              "copy of the original and uploads nothing."),
}
TEXT_WIDTH = 1088   # pixels: the screen's width less its margins, at 2x the game's 640


def wrap(draw, text, font, width, cjk):
    lines = []
    for para in text.split("\n"):
        if para == "":
            lines.append("")
            continue
        # Chinese: a character at a time, but a Latin word (Dungeon, IPA, 1.3.4) and the punctuation after it whole
        units = re.findall(r"[A-Za-z0-9.()/'-]+[，。、：；）”]?|.", para) if cjk else para.split(" ")
        line = ""
        for u in units:
            trial = line + u if cjk else (line + " " + u if line else u)
            if draw.textlength(trial, font=font) > width and line:
                lines.append(line)
                line = u
            else:
                line = trial
        lines.append(line)
    return lines


def text_picture(text, size, cjk):
    font = ImageFont.truetype(FONT.replace("Heavy", "Medium"), size)
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    lines = wrap(probe, text, font, TEXT_WIDTH, cjk)
    step = round(size * 1.45)
    img = Image.new("RGBA", (TEXT_WIDTH, max(1, step * len(lines))), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        d.text((0, i * step), line, font=font, fill=(255, 255, 255, 255))
    return img


def main():
    os.makedirs(OUT, exist_ok=True)
    icon = background(1024, 1024)
    d = ImageDraw.Draw(icon)
    words(d, "Dungeon", 512, 340, 180)
    words(d, "Raid", 512, 545, 220)
    tiles(d, 512, 780, 80)
    icon.save(os.path.join(OUT, "icon.png"))
    splash = background(1280, 1920)
    d = ImageDraw.Draw(splash)
    words(d, "Dungeon", 640, 760, 250)
    words(d, "Raid", 640, 1010, 280)
    tiles(d, 640, 1300, 90)
    splash.save(os.path.join(OUT, "splash.png"))
    os.makedirs(os.path.join(OUT, "text"), exist_ok=True)
    names = ["icon.png", "splash.png"]
    for key, (zh, en) in WORDS.items():
        size = 56 if key in ("import", "choose") else (34 if key == "legal" else 44)
        for lang, text in (("zh", zh), ("en", en)):
            name = "text/%s.%s.png" % (key, lang)
            img = text_picture(text, size, lang == "zh")
            if key in ("import", "choose"):   # (a button's word: just its letters, the button centres them)
                img = img.crop(img.getchannel("A").getbbox())
            img.save(os.path.join(OUT, name))
            names.append(name)
    for name in names:
        with open(os.path.join(OUT, name + ".import"), "w") as f:   # (read as the files they are)
            f.write('[remap]\n\nimporter="keep"\n')
    print("wrote", OUT)


if __name__ == "__main__":
    main()
