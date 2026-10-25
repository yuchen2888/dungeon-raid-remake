#!/usr/bin/env python3
"""Makes the launch picture (T050-I): the main menu's background with "Loading..." where the original's Default.png
has it, from the HD tiles picture so it is sharp on today's phones.

  python3 frontend/tools/make_splash.py

Writes frontend/godot/assets/hd/Default.png (project.godot application/boot_splash/image; the iOS export makes the
launch screen from it). It is cut from frontend/godot/assets/hd/tiles.png (frontend/tools/make_hd.py), or without
that from the original tiles.png, enlarged 4 times. Made from the original art, so local only like the rest of
assets/hd/.
"""
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "godot", "assets")
# tiles.png (1024 pixels): the main menu's background (screens.cpp MainMenuView background_) and its "Loading..."
# (title_), and where the original's Default.png shows that (its centre, in its 320 x 480 pixels)
BACKGROUND = (512, 512, 832, 992)
LOADING = (512, 996, 646, 1024)
LOADING_CENTRE = (253, 466)
SCALE = 4


def main():
    hd = os.path.join(ASSETS, "hd", "tiles.png")
    tiles = Image.open(hd if os.path.exists(hd) else os.path.join(ASSETS, "original", "tiles.png")).convert("RGBA")
    k = tiles.width // 1024
    if k != SCALE:
        tiles = tiles.resize((1024 * SCALE, 1024 * SCALE), Image.BICUBIC)
    cut = lambda box: tiles.crop(tuple(v * SCALE for v in box))
    out = cut(BACKGROUND)
    loading = cut(LOADING)
    cx, cy = (v * SCALE for v in LOADING_CENTRE)
    out.alpha_composite(loading, (cx - loading.width // 2, cy - loading.height // 2))
    os.makedirs(os.path.join(ASSETS, "hd"), exist_ok=True)
    path = os.path.join(ASSETS, "hd", "Default.png")
    out.convert("RGB").save(path)
    print("wrote %s (%dx%d)" % (path, out.width, out.height))


if __name__ == "__main__":
    main()
