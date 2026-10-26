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

T050-K: the other languages draw their words in the same places (WORDS): Traditional Chinese, Japanese and Korean in
their region's Source Han Sans, Spanish in the original's own bitmap fonts (bitmap_text), with the accented letters
make_cjk_font.py puts together from their strokes.
"""
import os
import sys

import numpy
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from make_cjk_font import REGION, LatinFont

HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.dirname(HERE)
ORIGINAL = os.path.join(FRONTEND, "godot", "assets", "original")
FONTS = os.path.join(HERE, "fonts")
SIZES = {"tiles": 1024, "menus": 512}

# (atlas, (x0, y0, x1, y1) in the original's pixels, kind, rotation, weight, lines[, "left": the main menu's words
# start where the English did; others are centred])
# kind: "free" (letters on transparency: every letter touching the region is cleared, descenders too; "bitmap": the
# same), "inside" (the
# same, clearing nothing outside the region: letters close to a frame), "button" (a
# purple button: redrawn from the empty button picture at BUTTON, letters in the buttons' own colours), or a patch
# rectangle (letters on a panel: they are erased into the panel around them, erase_letters, with the grain of that
# clean piece of the panel)
# rotation: 0, or 90 when the word is stored turned (drawn turned back by the game: it reads top to bottom)
# weight: Source Han Sans's (Heavy, Bold), or one of the original's bitmap fonts (font, fontMenu, fontScore)
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
    # the stat upgrades' icons (menu.cpp ItemUpgrade: rows 5 and 6 of the skill icons, kinds 8, 9, 18, 19)
    ("tiles", (922, 269, 953, 281), "inside", 0, "Heavy", ["+力量"]),
    ("tiles", (970, 269, 1004, 281), "inside", 0, "Heavy", ["+幸运"]),
    ("tiles", (921, 319, 954, 331), "inside", 0, "Heavy", ["+敏捷"]),
    ("tiles", (973, 319, 1002, 331), "inside", 0, "Heavy", ["+体力"]),
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
# T050-K: the words of the other languages, ZH's places one by one
WORDS = {
    "zh_TW": [["挑戰模式"], ["繼續遊戲"], ["新遊戲"], ["新手教學"], ["最高分"], ["設定"], ["獎勵物品！"], ["更多遊戲！"],
              ["載入中…"], ["聲音：開"], ["聲音：關"], ["升級了！"], ["選擇 1 件裝備購買"], ["選擇 2 個技能提升"],
              ["裝備商店！"], ["升級裝備！"], ["選擇 1 項升級"], ["怪物發動攻擊"], ["反擊！"], ["麻花大師！！"],
              ["麻花傳奇！！！"], ["麻花英雄！"], ["你逃出來了！"], ["你被殺死了"], ["最高分"], ["屬性"], ["選單"],
              ["繼續"], ["聲音"], ["說明"], ["離開"], ["時鐘"], ["變暗"], ["流暢"], ["+力量"], ["+敏捷"], ["+體力"],
              ["+幸運"], ["+傷害"], ["+防禦"], ["+生命"], ["+魅力"], ["+力量"], ["+幸運"], ["+敏捷"], ["+體力"],
              ["1經驗"], ["獎勵!"], ["傷害"], ["再生"], ["鈍化"], ["尖刺"], ["毒"], ["吸血"], ["火焰"], ["祝福"],
              ["治療"], ["偷竊"], ["酸液"], ["跳躍"], ["冰凍"], ["集結"], ["刺擊"], ["模仿"], ["鍊金"], ["踐踏"],
              ["油滑"], ["咆哮"], ["吸引"], ["鮮血"], ["復仇"], ["背水一戰"], ["狂暴"], ["無傷害!"], ["投擲"], ["吞噬"],
              ["模仿!"], ["膽魄"], ["上撩"], ["致殘"], ["逃跑"], ["復活"], ["尖刺"], ["生命"], ["是"], ["否"],
              ["開始新遊戲會刪除", "你目前的遊戲。", "確定嗎？"], ["否"], ["是"], ["返回"], ["說明"], ["麻花", "英雄"],
              ["地城", "衝刺"]],
    "ja": [["チャレンジ"], ["つづきから"], ["はじめから"], ["チュートリアル"], ["ハイスコア"], ["設定"],
           ["ボーナスアイテム！"], ["ほかのゲーム！"], ["ロード中…"], ["サウンド：オン"], ["サウンド：オフ"],
           ["レベルアップ！"], ["買う装備を1つ選ぼう"], ["強化するスキルを2つ選ぼう"], ["装備屋！"], ["装備強化！"],
           ["強化を1つ選ぼう"], ["モンスターの攻撃"], ["反撃！"], ["プレッツェルマスター！！"], ["プレッツェル伝説！！！"],
           ["プレッツェルヒーロー！"], ["脱出成功！"], ["やられてしまった"], ["ハイスコア"], ["ステータス"], ["メニュー"],
           ["続ける"], ["サウンド"], ["ヘルプ"], ["やめる"], ["時計"], ["暗転"], ["なめらか"], ["+力"], ["+器用"],
           ["+体力"], ["+運"], ["+ダメージ"], ["+防御"], ["+HP"], ["+魅力"], ["+力"], ["+運"], ["+器用"], ["+体力"],
           ["1EXP"], ["ボーナス!"], ["ダメージ"], ["再生"], ["鈍化"], ["トゲ"], ["毒"], ["吸血"], ["炎"], ["祝福"],
           ["回復"], ["盗む"], ["酸"], ["ジャンプ"], ["凍結"], ["集結"], ["突き"], ["模倣"], ["錬金"], ["踏みつけ"],
           ["ぬるぬる"], ["咆哮"], ["引き寄せ"], ["血"], ["復讐"], ["背水の陣"], ["バーサーク"], ["ノーダメージ!"],
           ["投げ"], ["貪食"], ["模倣!"], ["根性"], ["切り上げ"], ["足払い"], ["逃走"], ["復活"], ["トゲ"], ["HP"],
           ["はい"], ["いいえ"], ["新しいゲームを始めると", "今のゲームは消えます。", "よろしいですか？"], ["いいえ"],
           ["はい"], ["戻る"], ["ヘルプ"], ["プレッツェル", "ヒーロー"], ["ダンジョン", "スプリント"]],
    "ko": [["도전 모드"], ["이어하기"], ["새 게임"], ["튜토리얼"], ["최고 점수"], ["설정"], ["보너스 아이템!"],
           ["더 많은 게임!"], ["로딩 중…"], ["소리: 켬"], ["소리: 끔"], ["레벨 업!"], ["구매할 장비 1개 선택"],
           ["강화할 스킬 2개 선택"], ["장비 상점!"], ["장비 강화!"], ["업그레이드 1개 선택"], ["몬스터의 공격"],
           ["반격!"], ["프레첼 마스터!!"], ["프레첼 전설!!!"], ["프레첼 영웅!"], ["탈출 성공!"], ["당신은 죽었다"],
           ["최고 점수"], ["능력치"], ["메뉴"], ["계속"], ["소리"], ["도움말"], ["나가기"], ["시계"], ["어둡게"],
           ["부드럽게"], ["+힘"], ["+민첩"], ["+활력"], ["+행운"], ["+피해"], ["+방어"], ["+생명"], ["+매력"], ["+힘"],
           ["+행운"], ["+민첩"], ["+활력"], ["1EXP"], ["보너스!"], ["피해"], ["재생"], ["둔화"], ["가시"], ["독"],
           ["흡혈"], ["화염"], ["축복"], ["치유"], ["훔치기"], ["산성"], ["점프"], ["빙결"], ["집결"], ["찌르기"],
           ["모방"], ["연금"], ["짓밟기"], ["미끌미끌"], ["포효"], ["끌어당김"], ["피"], ["복수"], ["배수진"],
           ["광폭화"], ["피해 없음!"], ["투척"], ["포식"], ["모방!"], ["배짱"], ["올려 베기"], ["불구"], ["도주"],
           ["부활"], ["가시"], ["생명"], ["예"], ["아니요"], ["새 게임을 시작하면", "현재 게임이 삭제됩니다.", "계속할까요?"],
           ["아니요"], ["예"], ["돌아가기"], ["도움말"], ["프레첼", "영웅"], ["던전", "스프린트"]],
    "es": [["Desafío"], ["Continuar"], ["Nueva partida"], ["Tutorial"], ["Récords"], ["Ajustes"], ["¡Objeto extra!"],
           ["¡Más juegos!"], ["Cargando..."], ["Sonido: sí"], ["Sonido: no"], ["¡Nuevo nivel!"],
           ["Elige 1 objeto para comprar"], ["Elige 2 habilidades para mejorar"], ["¡Tienda!"], ["¡Mejora!"],
           ["Elige 1 mejora"], ["Ataque enemigo"], ["¡Contraataque!"], ["¡¡Maestro Pretzel!!"],
           ["¡¡¡Leyenda Pretzel!!!"], ["¡Héroe Pretzel!"], ["¡Escapaste!"], ["Moriste"], ["Récords"], ["Estado"],
           ["Menú"], ["Seguir"], ["Sonido"], ["Ayuda"], ["Salir"], ["Reloj"], ["Oscurecer"], ["Fluido"], ["+FUE"],
           ["+DES"], ["+VIT"], ["+SUE"], ["+DAÑO"], ["+DEF"], ["+PV"], ["+CAR"], ["+FUE"], ["+SUE"], ["+DES"],
           ["+VIT"], ["1EXP"], ["¡EXTRA!"], ["DAÑO"], ["REGENERA"], ["EMBOTA"], ["PÚAS"], ["VENENO"], ["ROBO"],
           ["FUEGO"], ["BENDICE"], ["CURA"], ["ROBA"], ["ÁCIDO"], ["SALTO"], ["HIELO"], ["REÚNE"], ["PUNZA"],
           ["IMITA"], ["ALQUIMIA"], ["PISOTÓN"], ["GRASA"], ["RUGIDO"], ["ATRAE"], ["SANGRE"], ["VENGANZA"],
           ["¡AGUANTE!"], ["FURIA"], ["¡ILESO!"], ["LANZA"], ["DEVORA"], ["¡IMITA!"], ["AGALLAS"], ["¡GANCHO!"],
           ["LISIADO"], ["HUYE"], ["REVIVE"], ["PÚAS"], ["PV"], ["Sí"], ["No"],
           ["Empezar de nuevo", "borrará tu partida", "actual. ¿Seguro?"], ["No"], ["Sí"], ["Volver"], ["Ayuda"],
           ["Héroe", "Pretzel"], ["Carrera de", "mazmorra"]],
}
# Spanish: the bitmap font each place's words take (by ZH's index): the popping labels and stat words in fontScore
# (bold capitals with a black outline, as theirs), the "Choose ..." lines in font (they need lower case and digits),
# the rest in fontMenu (as the main menu's words and the English settings button)
ES_FONTS = {i: "fontScore" for i in range(34, 84)}
ES_FONTS.update({12: "font", 13: "font", 16: "font"})


def language_regions(code):
    """The places and words of a language (ZH's places with WORDS for the T050-K languages)."""
    if code in ("zh", "en"):
        return {"zh": ZH, "en": EN}[code]
    out = []
    for i, (atlas, rect, kind, rotation, weight, lines, *align) in enumerate(ZH):
        if code == "es":
            weight = ES_FONTS.get(i, "fontMenu")
        out.append((atlas, rect, kind, rotation, weight, WORDS[code][i], *align))
    return out


REGIONS = ["zh", "en"] + list(WORDS)   # (the languages with pictures)
LANG = "zh"   # (the language main() draws: text_image's Source Han Sans region)
BITMAP_FONTS = ("font", "fontMenu", "fontScore")
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
    font_path = os.path.join(FONTS, "SourceHanSans%s-%s.otf" % (REGION.get(LANG, "CN"), weight))
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


def clear_letters(img, window, rect, original, k=1):
    """Clears (in img) every opaque piece of the window that reaches into rect in the original picture: the letters
    with their tails, and the faint shadow around them (the see-through pixels within 3k of a cleared one, which
    otherwise leave a ghost of the old word)."""
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
    if not seen:
        return
    near = Image.new("L", (wx1 - wx0, wy1 - wy0), 0)
    mark = near.load()
    for x, y in seen:
        mark[x - wx0, y - wy0] = 255
    near = near.filter(ImageFilter.MaxFilter(2 * (3 * k) + 1)).load()
    for y in range(wy0, wy1):
        for x in range(wx0, wx1):
            if near[x - wx0, y - wy0] and 0 < px[x, y][3] <= 60:
                out[x, y] = (0, 0, 0, 0)


def bitmap_text(lines, font_name, box_w, box_h, fill, outline, align):
    """lines in one of the original's bitmap fonts (as Label::SetText lays them out: small capitals for lower case,
    the font's spacing; T050-K: the accented letters make_cjk_font.py builds from its strokes, a sign the font lacks
    from font), coloured fill with an outline (fontScore: its own black one), scaled to fit box_w x box_h."""
    font, plain = LatinFont(font_name), None
    k = font.k
    rows = []
    for text in lines:
        pieces, pen = [], 0.0
        for ch in text:
            img, m = font.glyph(ch)
            s = 1.0
            if img is None:   # (not in this font: font's, as tall as this font's capitals)
                plain = plain or LatinFont("font")
                img, m = plain.glyph(ch)
                if img is None:
                    continue
                s = font.cap_h / plain.cap_h
                img = img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)
                top = (font.cap_top + (m["yoffset"] / plain.k - plain.cap_top) * s) * k
            else:
                top = m["yoffset"]
            if ch == " ":   # (a space a little wider than the font's, as the pictures' own words have them)
                m = dict(m, xadvance=round((2.0 if font_name == "font" else 1.4) * (m["xadvance"] + img.width)) - img.width)
            centre = pen + img.width / 2
            if img.width:
                pieces.append((img, centre + m["xoffset"] * s / 2, top))
            pen = centre + m["xadvance"] * s / 2
        line = Image.new("RGBA", (int(pen + font.lh * k), 2 * font.lh * k), (0, 0, 0, 0))
        for img, cx, top in pieces:
            line.alpha_composite(img, (max(0, round(cx - img.width / 2)), round(top + font.lh * k / 2)))
        rows.append(line)
    lum = lambda im: im.convert("RGB").convert("L")
    masks, rings = [], []
    for line in rows:
        a = line.getchannel("A")
        if font_name == "fontScore":   # (white letters on their own black outline)
            masks.append(Image.composite(lum(line), Image.new("L", line.size, 0), a))
            rings.append(a)
        else:
            masks.append(a)
            rings.append(a.filter(ImageFilter.MaxFilter(2 * k + 1)) if outline else None)
    boxes = [(rings[i] or masks[i]).getbbox() or (0, 0, 1, 1) for i in range(len(rows))]
    gap = round(0.1 * font.lh * k)
    width = max(b[2] - b[0] for b in boxes)
    height = sum(b[3] - b[1] for b in boxes) + gap * (len(rows) - 1)
    out = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    y = 0
    for mask, ring, b in zip(masks, rings, boxes):
        x = 0 if align == "left" else (width - (b[2] - b[0])) // 2
        if ring is not None:
            out.paste(Image.new("RGBA", (b[2] - b[0], b[3] - b[1]), outline or (0, 0, 0, 255)), (x, y), ring.crop(b))
        out.paste(Image.new("RGBA", (b[2] - b[0], b[3] - b[1]), fill), (x, y), mask.crop(b))
        y += b[3] - b[1] + gap
    f = min(box_w / out.width, box_h / out.height)
    out = out.resize((max(1, round(out.width * f)), max(1, round(out.height * f))), Image.LANCZOS)
    img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    img.alpha_composite(out, (0 if align == "left" else (box_w - out.width) // 2, (box_h - out.height) // 2))
    return img


def words_image(lines, weight, box_w, box_h, fill, outline, align="centre"):
    if weight in BITMAP_FONTS:
        return bitmap_text(lines, weight, box_w, box_h, fill, outline, align)
    return text_image(lines, weight, box_w, box_h, fill, outline, align)


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
        if kind in ("free", "inside", "bitmap"):
            window = (max(0, x0 - 4 * k), max(0, y0 - 4 * k), min(img.width, x1 + 4 * k), min(img.height, y1 + 4 * k))
            if kind == "inside":   # (letters close to a frame: nothing outside the region is cleared)
                window = (x0, y0, x1, y1)
            kind = "free"
            clear_letters(img, window, (x0, y0, x1, y1), original, k)
            bbox = region.getchannel("A").point(lambda a: 255 if a > 40 else 0).getbbox() or (0, 0, w, h)
            fill, outline = letters_style(region.crop(bbox), 0.5 if weight in BITMAP_FONTS else 0.25)
            out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            out.alpha_composite(words_image(lines, weight, bbox[2] - bbox[0], bbox[3] - bbox[1], fill, outline, align),
                                (bbox[0], bbox[1]))
        elif kind == "button":
            out = button_picture(base_tiles, k, w, h)
            out.alpha_composite(words_image(lines, weight, w - 12 * k, h - 6 * k, BUTTON_TEXT, BUTTON_OUTLINE), (6 * k, 3 * k))
        else:   # letters on a panel
            fill, outline = letters_style(region, 0.12)
            px0, py0, px1, py1 = (v * k for v in kind)
            out = erase_letters(region, original.crop((px0, py0, px1, py1)), k)
            mx, my = round(w * 0.08), round(h * 0.12)   # (a margin: the panel's words smaller than the place)
            out.alpha_composite(words_image(lines, weight, w - 2 * mx, h - 2 * my, fill, outline), (mx, my))
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
    global LANG
    LANG = lang
    regions = language_regions(lang)
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
