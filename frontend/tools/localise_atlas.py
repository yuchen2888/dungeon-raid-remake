#!/usr/bin/env python3
"""Redraws the English words baked into the original's pictures in another language (T050-D).

  python3 frontend/tools/localise_atlas.py [lang] [--base <folder>]

tiles.png and menus.png hold words as pictures (the main menu's buttons, "Level Up!", the popping labels' words, the
game menu's buttons ...). For each region the game samples (the places come from the drawing code: screens.cpp,
menu.cpp, interface.cpp, gameover.cpp, scores.cpp, setup.cpp and the rules' label glyphs in recovered_labels.cpp),
the English letters are found, taken away and the translation drawn in their place, in their colours: on a
transparent region the letters are cleared, on a button or panel they are painted over from the surrounding
picture. The layout is unchanged, so the game samples the same places. The pictures go to
frontend/godot/assets/lang/<lang>/ with atlas.txt (the drawn words, for make_cjk_font.py's character list); like the
originals they stay on this machine.

--base takes the pictures from another folder (e.g. HD versions of the same layout, any whole multiple of the size).
"""
import os
import sys

import numpy
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.dirname(HERE)
ORIGINAL = os.path.join(FRONTEND, "godot", "assets", "original")
FONTS = os.path.join(HERE, "fonts")
SIZES = {"tiles": 1024, "menus": 512}

# (atlas, (x0, y0, x1, y1) in the original's pixels, kind, rotation, weight, lines[, "left": the main menu's words
# start where the English did; others are centred])
# kind: "free" (letters on transparency: every letter touching the region is cleared, descenders too), "button" (a
# purple button: redrawn from the empty button picture at BUTTON, letters in the buttons' own colours), or a patch
# rectangle (letters on a panel: they are erased into the panel around them, erase_letters, with the grain of that
# clean piece of the panel)
# rotation: 0, or 90 when the word is stored turned (drawn turned back by the game: it reads top to bottom)
ZH = [
    # the main menu (screens.cpp MainMenuView)
    ("tiles", (881, 472, 1023, 511), "free", 0, "Heavy", ["挑战模式"], "left"),
    ("tiles", (833, 513, 964, 552), "free", 0, "Heavy", ["继续游戏"], "left"),
    ("tiles", (833, 553, 977, 592), "free", 0, "Heavy", ["新游戏"], "left"),
    ("tiles", (833, 593, 961, 633), "free", 0, "Heavy", ["新手教程"], "left"),
    ("tiles", (833, 634, 930, 675), "free", 0, "Heavy", ["最高分"], "left"),
    ("tiles", (1, 984, 145, 1023), "free", 0, "Heavy", ["设置"], "left"),           # was OpenFeint: the settings (language)
    ("tiles", (147, 983, 313, 1023), "free", 0, "Heavy", ["奖励物品！"], "left"),
    ("tiles", (837, 985, 1023, 1023), "free", 0, "Heavy", ["更多游戏！"]),
    ("tiles", (512, 996, 646, 1023), "free", 0, "Heavy", ["加载中…"]),
    ("tiles", (923, 676, 963, 815), "free", 90, "Heavy", ["声音：开"]),
    ("tiles", (983, 513, 1023, 660), "free", 90, "Heavy", ["声音：关"]),
    # menus, banners and titles
    ("tiles", (2, 262, 122, 297), "free", 0, "Heavy", ["升级了！"]),
    ("tiles", (125, 268, 249, 285), "free", 0, "Bold", ["选择 1 件装备购买"]),
    ("tiles", (251, 268, 406, 285), "free", 0, "Bold", ["选择 2 个技能提升"]),
    ("tiles", (2, 293, 141, 321), "free", 0, "Heavy", ["装备商店！"]),
    ("tiles", (2, 325, 127, 355), "free", 0, "Heavy", ["升级装备！"]),
    ("tiles", (2, 360, 159, 379), "free", 0, "Bold", ["选择 1 项升级"]),
    ("tiles", (197, 287, 446, 311), "free", 0, "Heavy", ["怪物发起攻击"]),
    ("tiles", (269, 312, 453, 336), "free", 0, "Heavy", ["反击！"]),
    ("tiles", (513, 351, 817, 387), "free", 0, "Heavy", ["麻花大师！！"]),
    ("tiles", (513, 388, 808, 424), "free", 0, "Heavy", ["麻花传奇！！！"]),
    ("tiles", (771, 425, 1023, 461), "free", 0, "Heavy", ["麻花英雄！"]),
    ("tiles", (73, 887, 303, 960), "free", 0, "Heavy", ["你逃出来了！"]),
    ("tiles", (833, 676, 922, 957), "free", 90, "Heavy", ["你被杀死了"]),
    ("tiles", (980, 677, 1023, 918), "free", 90, "Heavy", ["最高分"]),
    # the in-game buttons (interface.cpp) and the game menu's (menu.cpp GameMenuView)
    ("tiles", (269, 337, 341, 363), "button", 0, "Heavy", ["属性"]),
    ("tiles", (342, 337, 414, 363), "button", 0, "Heavy", ["菜单"]),
    ("tiles", (329, 364, 418, 390), "button", 0, "Heavy", ["继续"]),
    ("tiles", (422, 347, 511, 373), "button", 0, "Heavy", ["声音"]),
    ("tiles", (422, 374, 511, 400), "button", 0, "Heavy", ["帮助"]),
    ("tiles", (422, 401, 511, 427), "button", 0, "Heavy", ["退出"]),
    ("tiles", (647, 997, 736, 1023), "button", 0, "Heavy", ["时钟"]),
    ("tiles", (737, 997, 826, 1023), "button", 0, "Heavy", ["变暗"]),
    ("tiles", (388, 997, 477, 1023), "button", 0, "Heavy", ["流畅"]),
    # the stat flares' words
    ("tiles", (516, 212, 561, 233), "free", 0, "Bold", ["+力量"]),
    ("tiles", (564, 212, 612, 233), "free", 0, "Bold", ["+敏捷"]),
    ("tiles", (617, 212, 659, 233), "free", 0, "Bold", ["+体力"]),
    ("tiles", (663, 212, 712, 233), "free", 0, "Bold", ["+幸运"]),
    ("tiles", (715, 212, 764, 233), "free", 0, "Bold", ["+伤害"]),
    ("tiles", (767, 212, 810, 233), "free", 0, "Bold", ["+防御"]),
    ("tiles", (821, 212, 854, 233), "free", 0, "Bold", ["+生命"]),
    ("tiles", (865, 212, 913, 233), "free", 0, "Bold", ["+魅力"]),
    # the popping labels' words (recovered_labels.cpp type_glyphs, plural_glyph, type8_last_glyph)
    ("tiles", (424, 1, 463, 22), "free", 0, "Heavy", ["1经验"]),     # the XP token's picture (presenter.cpp XPVisual)
    ("tiles", (425, 23, 471, 36), "free", 0, "Bold", ["奖励!"]),
    ("tiles", (425, 93, 474, 113), "free", 0, "Bold", ["伤害"]),
    ("tiles", (425, 129, 499, 142), "free", 0, "Bold", ["再生"]),
    ("tiles", (444, 157, 484, 170), "free", 0, "Bold", ["钝化"]),
    ("tiles", (425, 171, 459, 184), "free", 0, "Bold", ["尖刺"]),
    ("tiles", (425, 115, 471, 128), "free", 0, "Bold", ["毒"]),
    ("tiles", (466, 143, 504, 156), "free", 0, "Bold", ["吸血"]),
    ("tiles", (425, 558, 465, 571), "free", 0, "Bold", ["火焰"]),
    ("tiles", (425, 513, 460, 526), "free", 0, "Bold", ["祝福"]),
    ("tiles", (461, 513, 493, 526), "free", 0, "Bold", ["治疗"]),
    ("tiles", (457, 527, 493, 540), "free", 0, "Bold", ["偷窃"]),
    ("tiles", (425, 527, 456, 540), "free", 0, "Bold", ["酸液"]),
    ("tiles", (463, 541, 498, 556), "free", 0, "Bold", ["跳跃"]),
    ("tiles", (466, 558, 508, 571), "free", 0, "Bold", ["冰冻"]),
    ("tiles", (425, 541, 462, 554), "free", 0, "Bold", ["集结"]),
    ("tiles", (462, 572, 494, 585), "free", 0, "Bold", ["刺击"]),
    ("tiles", (462, 586, 502, 599), "free", 0, "Bold", ["模仿"]),
    ("tiles", (425, 628, 483, 641), "free", 0, "Bold", ["炼金"]),
    ("tiles", (425, 656, 481, 669), "free", 0, "Bold", ["践踏"]),
    ("tiles", (462, 614, 507, 627), "free", 0, "Bold", ["油滑"]),
    ("tiles", (425, 670, 470, 683), "free", 0, "Bold", ["咆哮"]),
    ("tiles", (425, 684, 479, 697), "free", 0, "Bold", ["吸引"]),
    ("tiles", (462, 600, 505, 613), "free", 0, "Bold", ["鲜血"]),
    ("tiles", (425, 642, 479, 655), "free", 0, "Bold", ["复仇"]),
    ("tiles", (425, 831, 495, 844), "free", 0, "Bold", ["背水一战"]),
    ("tiles", (425, 845, 476, 858), "free", 0, "Bold", ["狂暴"]),
    ("tiles", (425, 859, 481, 872), "free", 0, "Bold", ["无伤害!"]),
    ("tiles", (425, 873, 473, 886), "free", 0, "Bold", ["投掷"]),
    ("tiles", (425, 887, 476, 900), "free", 0, "Bold", ["吞噬"]),
    ("tiles", (425, 901, 469, 914), "free", 0, "Bold", ["模仿!"]),
    ("tiles", (470, 901, 511, 914), "free", 0, "Bold", ["胆魄"]),
    ("tiles", (425, 915, 487, 928), "free", 0, "Bold", ["上撩"]),
    ("tiles", (425, 929, 481, 942), "free", 0, "Bold", ["致残"]),
    ("tiles", (425, 943, 453, 956), "free", 0, "Bold", ["逃跑"]),
    ("tiles", (425, 957, 492, 970), "free", 0, "Bold", ["复活"]),
    ("tiles", (425, 143, 465, 156), "free", 0, "Bold", ["尖刺"]),
    ("tiles", (425, 157, 443, 170), "free", 0, "Bold", ["生命"]),
    # menus.png: the confirmation box (main menu), its yes / no, the high scores' Return, Help, the modes' names
    ("menus", (1, 313, 50, 335), "free", 0, "Heavy", ["是"]),
    ("menus", (1, 336, 41, 354), "free", 0, "Heavy", ["否"]),
    ("menus", (18, 362, 232, 460), (80, 470, 160, 500), 0, "Heavy", ["开始新游戏会删除", "你当前的游戏。", "确定吗？"]),
    ("menus", (18, 462, 70, 494), (80, 470, 160, 500), 0, "Heavy", ["否"]),
    ("menus", (168, 462, 232, 494), (80, 470, 160, 500), 0, "Heavy", ["是"]),
    ("menus", (104, 1, 193, 27), "button", 0, "Heavy", ["返回"]),
    ("menus", (423, 286, 511, 310), "button", 0, "Heavy", ["帮助"]),
    ("menus", (408, 326, 511, 380), "free", 0, "Heavy", ["麻花", "英雄"]),
    ("menus", (398, 382, 511, 430), "free", 0, "Heavy", ["地牢", "冲刺"]),
]
# English keeps the original's pictures but for the settings button (was OpenFeint), lettered with the original's own
# menu font (fontMenu, small capitals) in the main menu's colours.
EN = [("tiles", (1, 984, 145, 1023), "bitmap", 0, "fontMenu", ["Settings"], "left")]
REGIONS = {"zh": ZH, "en": EN}
BUTTON = (425, 698, 497, 724)   # tiles.png: the empty purple button (interface.cpp, the menu button's "on" picture)
BUTTON_TEXT, BUTTON_OUTLINE = (122, 103, 211, 255), (28, 25, 53, 255)   # the buttons' letters (sampled)


def letters_style(region, bright_part=0.5):
    """The letters' fill (their bright part: the brightest bright_part of the pixels) and outline (their dark part)
    colours, as RGBA."""
    px = [p for p in region.get_flattened_data() if p[3] > 200]
    if not px:
        return (255, 255, 255, 255), None
    lum = lambda p: 0.3 * p[0] + 0.59 * p[1] + 0.11 * p[2]
    px.sort(key=lum)
    bright = px[int(len(px) * (1 - bright_part)):]
    fill = tuple(sum(p[k] for p in bright) // len(bright) for k in range(3)) + (255,)
    dark = px[:max(1, len(px) // 5)]
    outline = tuple(sum(p[k] for p in dark) // len(dark) for k in range(3)) + (255,)
    has_outline = lum(fill) - lum(outline) > 90
    return fill, outline if has_outline else None


def text_image(lines, weight, box_w, box_h, fill, outline, align="centre"):
    """The lines drawn as large as they fit box_w x box_h (centred, or from the left), with an outline when the
    original had one; placed by the letters' own ink (the font's line box sits lower than its letters)."""
    font_path = os.path.join(FONTS, "SourceHanSansCN-%s.otf" % weight)
    n = len(lines)
    size = max(4, int(box_h / n * 1.2))
    while True:
        font = ImageFont.truetype(font_path, size)
        stroke = max(1, round(size * 0.08)) if outline else 0
        boxes = [font.getbbox(l, stroke_width=stroke) for l in lines]
        gap = size * 0.12
        ink_h = [b[3] - b[1] for b in boxes]
        total_h = sum(ink_h) + gap * (n - 1)
        if size <= 4 or (max(b[2] - b[0] for b in boxes) <= box_w and total_h <= box_h):
            break
        size -= 1
    img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    y = (box_h - total_h) / 2
    for l, b, h in zip(lines, boxes, ink_h):
        w = b[2] - b[0]
        x = 0 if align == "left" else (box_w - w) / 2
        draw.text((x - b[0], y - b[1]), l, font=font, fill=fill, stroke_width=stroke, stroke_fill=outline if outline else fill)
        y += h + gap
    return img


def clear_letters(img, window, rect, original):
    """Clears (in img) every opaque piece of the window that reaches into rect in the original picture: the letters
    with their tails."""
    wx0, wy0, wx1, wy1 = window
    px = original.load()
    out = img.load()
    seen, stack = set(), []
    for y in range(rect[1], rect[3]):
        for x in range(rect[0], rect[2]):
            if px[x, y][3] > 20:
                stack.append((x, y))
    while stack:
        x, y = stack.pop()
        if (x, y) in seen or not (wx0 <= x < wx1 and wy0 <= y < wy1) or px[x, y][3] <= 20:
            continue
        seen.add((x, y))
        stack += [(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
    for x, y in seen:
        out[x, y] = (0, 0, 0, 0)


def bitmap_text(text, font_name, box_w, box_h, fill, outline, align):
    """text in one of the original's bitmap fonts (as Label::SetText lays it out: small capitals 0.75 for lower case,
    the font's spacing), coloured fill with an outline, scaled to fit box_w x box_h."""
    glyphs, lh, base = {}, 0, 0
    with open(os.path.join(ORIGINAL, font_name + ".fnt"), encoding="latin-1") as f:
        for line in f:
            p = dict(kv.split("=", 1) for kv in line.split()[1:] if "=" in kv)
            if line.startswith("common"):
                lh, base = int(p["lineHeight"]), int(p["base"])
            elif line.startswith("char "):
                glyphs[int(p["id"])] = tuple(int(p[k]) for k in ("x", "y", "width", "height", "xoffset", "yoffset", "xadvance"))
    sheet = Image.open(os.path.join(ORIGINAL, font_name + ".png")).convert("RGBA")
    spacing = {"fontMenu": -0.225, "fontScore": -0.05}.get(font_name, 0.0) * lh
    scale = 4   # drawn at 4x, then fitted
    pieces, pen = [], 0.0
    for ch in text:
        small = ch.islower() and font_name in ("fontMenu", "fontScore")
        g = glyphs.get(ord(ch.upper() if small else ch))
        if not g:
            pen += lh * 0.3
            continue
        x, y, w, h, ox, oy, adv = g
        s = 0.75 if small else 1.0
        centre = pen + w * s / 2
        # the glyph's centre, from the line's base (Font::LoadFont's offsets, scaled for a small capital)
        cy = base + s * (oy + h / 2 - base)
        pieces.append((sheet.crop((x, y, x + w, y + h)), centre + s * ox / 2, cy, s))
        pen = centre + s * adv / 2 + spacing
    width = int(pen + lh) * scale
    line = Image.new("RGBA", (width, lh * scale), (0, 0, 0, 0))
    for glyph, cx, cy, s in pieces:
        g = glyph.resize((max(1, round(glyph.width * s * scale)), max(1, round(glyph.height * s * scale))), Image.LANCZOS)
        line.alpha_composite(g, (round(cx * scale - g.width / 2), round(cy * scale - g.height / 2)))
    mask = line.getchannel("A")
    bbox = mask.getbbox()
    mask = mask.crop(bbox)
    ring = mask.filter(ImageFilter.MaxFilter(2 * scale + 1)) if outline else None
    out = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    if ring:
        out.paste(Image.new("RGBA", mask.size, outline), (0, 0), ring)
    out.paste(Image.new("RGBA", mask.size, fill), (0, 0), mask)
    k = min(box_w / out.width, box_h / out.height)
    out = out.resize((max(1, round(out.width * k)), max(1, round(out.height * k))), Image.LANCZOS)
    img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    img.alpha_composite(out, (0 if align == "left" else (box_w - out.width) // 2, (box_h - out.height) // 2))
    return img


def button_picture(tiles, k, w, h):
    """The empty purple button stretched to w x h: its ends kept, its middle repeated."""
    bx0, by0, bx1, by1 = (v * k for v in BUTTON)
    b = tiles.crop((bx0, by0, bx1, by1)).resize((bx1 - bx0, h)) if by1 - by0 != h else tiles.crop((bx0, by0, bx1, by1))
    end = 10 * k
    out = Image.new("RGBA", (w, h))
    out.paste(b.crop((0, 0, end, h)), (0, 0))
    out.paste(b.crop((b.width - end, 0, b.width, h)), (w - end, 0))
    mid = b.crop((end, 0, b.width - end, h))
    for x in range(end, w - end, mid.width):
        out.paste(mid.crop((0, 0, min(mid.width, w - end - x), h)), (x, 0))
    return out


base_tiles = None


def box_blur(a, r):
    """Each pixel the mean of the (2r+1)-square around it (rows and columns of a height x width x channels array; the
    edges repeat)."""
    for axis in (0, 1):
        pad = [(0, 0)] * a.ndim
        pad[axis] = (r + 1, r)
        c = numpy.cumsum(numpy.pad(a, pad, mode="edge"), axis=axis)
        n = a.shape[axis]
        a = (c.take(range(2 * r + 1, 2 * r + 1 + n), axis=axis) - c.take(range(0, n), axis=axis)) / (2 * r + 1)
    return a


def erase_letters(region, patch, k):
    """The panel without its yellow letters: the letters (and a rim for their shading) are filled with the colour
    around them (a blur of the rest, so the panel's light and its tilted border stay as they are) plus the grain of
    an empty piece of the panel (only its fine detail, so the repeats leave no seams)."""
    rgba = numpy.asarray(region, dtype=numpy.float32)
    letters = Image.fromarray(((rgba[:, :, 1] > 70) * 255).astype(numpy.uint8)).filter(ImageFilter.MaxFilter(2 * (3 * k) + 1))
    keep = 1.0 - numpy.asarray(letters, dtype=numpy.float32)[:, :, None] / 255.0
    blur = lambda a, r=5 * k: box_blur(box_blur(box_blur(a, r), r), r)   # (about a Gaussian)
    rgb = rgba[:, :, :3]
    keep3 = numpy.repeat(keep, 3, axis=2)
    near, around = blur(keep3), blur(keep3, 15 * k)
    smooth = blur(rgb * keep) / numpy.maximum(near, 1e-3)
    wide = blur(rgb * keep, 15 * k) / numpy.maximum(around, 1e-3)   # (where little is left nearby)
    t = numpy.clip(near / 0.3, 0.0, 1.0)
    smooth = smooth * t + wide * (1.0 - t)
    p = numpy.asarray(patch.convert("RGB"), dtype=numpy.float32)
    grain_piece = p - blur(p)
    reps = (-(-rgb.shape[0] // p.shape[0]), -(-rgb.shape[1] // p.shape[1]), 1)
    grain = numpy.tile(grain_piece, reps)[:rgb.shape[0], :rgb.shape[1]]
    filled = numpy.clip(smooth + grain, 0, 255)
    out = rgb * keep + filled * (1.0 - keep)
    return Image.fromarray(numpy.dstack([out, rgba[:, :, 3:]]).round().astype(numpy.uint8), "RGBA")


def localise(atlas, base, regions):
    """All the old letters are taken away first (from the unchanged picture's view of them), then every word drawn, so
    one word's clearing never takes a neighbour's new letters."""
    img = Image.open(base).convert("RGBA")
    original = img.copy()
    k = img.width // SIZES[atlas]
    drawn = []
    for name, rect, kind, rotation, weight, lines, *align in regions:
        if name != atlas:
            continue
        align = align[0] if align else "centre"
        x0, y0, x1, y1 = (v * k for v in rect)
        region = original.crop((x0, y0, x1, y1))
        if rotation:
            region = region.rotate(90, expand=True)   # read it as it is shown
        w, h = region.size
        if kind == "free":
            window = (max(0, x0 - 4 * k), max(0, y0 - 4 * k), min(img.width, x1 + 4 * k), min(img.height, y1 + 4 * k))
            clear_letters(img, window, (x0, y0, x1, y1), original)
            bbox = region.getchannel("A").point(lambda a: 255 if a > 40 else 0).getbbox() or (0, 0, w, h)
            fill, outline = letters_style(region.crop(bbox), 0.25)
            out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            out.alpha_composite(text_image(lines, weight, bbox[2] - bbox[0], bbox[3] - bbox[1], fill, outline, align), (bbox[0], bbox[1]))
        elif kind == "bitmap":
            window = (max(0, x0 - 4 * k), max(0, y0 - 4 * k), min(img.width, x1 + 4 * k), min(img.height, y1 + 4 * k))
            clear_letters(img, window, (x0, y0, x1, y1), original)
            bbox = region.getchannel("A").point(lambda a: 255 if a > 40 else 0).getbbox() or (0, 0, w, h)
            fill, outline = letters_style(region.crop(bbox))
            out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            out.alpha_composite(bitmap_text(lines[0], weight, bbox[2] - bbox[0], bbox[3] - bbox[1], fill, outline, align),
                                (bbox[0], bbox[1]))
            kind = "free"
        elif kind == "button":
            out = button_picture(base_tiles, k, w, h)
            out.alpha_composite(text_image(lines, weight, w - 12 * k, h - 6 * k, BUTTON_TEXT, BUTTON_OUTLINE), (6 * k, 3 * k))
        else:   # letters on a panel
            fill, outline = letters_style(region, 0.12)
            px0, py0, px1, py1 = (v * k for v in kind)
            out = erase_letters(region, original.crop((px0, py0, px1, py1)), k)
            mx, my = round(w * 0.08), round(h * 0.12)   # (a margin: the panel's words smaller than the place)
            out.alpha_composite(text_image(lines, weight, w - 2 * mx, h - 2 * my, fill, outline), (mx, my))
        if rotation:
            out = out.rotate(-90, expand=True)
        drawn.append((kind in ("free", "bitmap"), out, (x0, y0)))
    for over, out, at in drawn:
        if over:
            img.alpha_composite(out, at)   # (on the cleared picture: whatever else is there stays)
        else:
            img.paste(out, at)
    return img


def make_names(lang_root):
    """lang/names.png: each language's name in its own words (the settings page's buttons, texture LangNames): 128 x 32
    pixels each, one below the other in a 256 x 256 picture, in the purple buttons' letters."""
    names = ["English", "中文"]
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    for i, n in enumerate(names):
        img.alpha_composite(text_image([n], "Heavy", 128, 32, BUTTON_TEXT, BUTTON_OUTLINE), (0, 32 * i))
    img.save(os.path.join(lang_root, "names.png"))
    with open(os.path.join(lang_root, "names.png.import"), "w", encoding="utf-8") as f:
        f.write('[remap]\n\nimporter="keep"\n')


def main():
    lang = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "zh"
    base_dir = sys.argv[sys.argv.index("--base") + 1] if "--base" in sys.argv else ORIGINAL
    out = os.path.join(FRONTEND, "godot", "assets", "lang", lang)
    os.makedirs(out, exist_ok=True)
    regions = REGIONS[lang]
    global base_tiles
    base_tiles = Image.open(os.path.join(base_dir, "tiles.png")).convert("RGBA")   # (the empty button's picture)
    for atlas in SIZES:
        if not any(r[0] == atlas for r in regions):
            continue   # (no words to change: the game uses the original)
        localise(atlas, os.path.join(base_dir, atlas + ".png"), regions).save(os.path.join(out, atlas + ".png"))
        with open(os.path.join(out, atlas + ".png.import"), "w", encoding="utf-8") as f:
            f.write('[remap]\n\nimporter="keep"\n')   # (read as a plain file, exported as it is)
    if lang == "en":
        make_names(os.path.dirname(out))
        print("wrote the settings button into %s/tiles.png" % os.path.relpath(out, FRONTEND))
        return
    with open(os.path.join(out, "atlas.txt"), "w", encoding="utf-8") as f:
        f.write("# the words localise_atlas.py drew (make_cjk_font.py's character list)\n")
        for i, r in enumerate(regions):
            f.write("atlas.%d\t%s\n" % (i, " ".join(r[5])))
    make_names(os.path.dirname(out))
    print("wrote %d words into %s/tiles.png, menus.png" % (len(regions), os.path.relpath(out, FRONTEND)))


if __name__ == "__main__":
    main()
