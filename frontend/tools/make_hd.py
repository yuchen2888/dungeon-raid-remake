#!/usr/bin/env python3
"""The HD pictures (T050-C): the original atlases upscaled 4x by an AI upscaler into frontend/godot/assets/hd/, which
original.gd loads in place of the originals (_texture_path). Local only, like assets/original/ (never in Git).

  python3 frontend/tools/make_hd.py <realesrgan-ncnn-vulkan folder> [names...]
  python3 frontend/tools/make_hd.py --lang [codes...]   the languages' own pictures in HD, from the HD tiles / menus
                                                       (below; all languages, or the ones named)

The upscaler is Real-ESRGAN's macOS build (github.com/xinntao/Real-ESRGAN, release v0.2.5.0,
realesrgan-ncnn-vulkan-20220424-macos.zip, downloaded with the owner's consent on 2026-10-23; kept outside the
project), with its realesrgan-x4plus-anime model, which keeps the drawn outlines and the lettering cleanest.

The atlases are packed tightly (the font glyphs even touch), and an upscaler looks a few pixels around each pixel,
so upscaling an atlas whole would bleed neighbours into each other. Instead every separate piece (8-connected
non-transparent pixels) is cut out with transparent space around it, upscaled on its own, and put back exactly 4x
where it was; where two pieces' edges meet, the more opaque one wins. The layout (and so every UV and the fonts'
.fnt pixel coordinates, which original.gd's drawing reads relative to the texture size) stays the same.

The model also shifts colours a little (a panel's gradient, which the game stretches across the screen from a strip
a pixel wide, came out flat and bluer), so each piece's broad colour is corrected back to the original's (the HD
piece shrunk to the original's size is compared with the original and the blurred difference, enlarged, added).
The model smooths away fine texture, so a few areas are fixed afterwards (FIXES, found by checking every atlas): in
"texture" areas (grainy painted pictures) what the upscaler lost is put back (back-projection: the HD picture shrunk
to the original's size is compared with the original and the difference, enlarged, added, twice), which keeps the
sharper edges and the original's grain; in "other model" areas the pieces come from OTHER_MODEL, which keeps
a soft pattern the main model turns into dark lines (the coins' rims); "plain" areas (small repeating patterns the model garbles) are simply
enlarged (Lanczos) instead. Needs Pillow and numpy.

--lang: the languages' pictures (T050-D's localise_atlas.py: tiles / menus with the English words redrawn, and the
settings page's language names) made again on the HD tiles and menus, into assets/hd/lang/<code>/ and
assets/hd/lang/names.png, where original.gd's _texture_path looks for them. localise_atlas.py is run as it is, but
writing into a temporary folder, so the normal-size pictures in assets/lang/ stay untouched.
"""
import collections
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "godot", "assets")
ORIGINAL = os.path.join(ASSETS, "original")
HD = os.path.join(ASSETS, "hd")
NAMES = ["tiles", "icons", "menus", "font", "fontMenu", "fontScore"]   # original.gd TEXTURES
SCALE = 4
MODEL = "realesrgan-x4plus-anime"
OTHER_MODEL = "realesr-animevideov3"   # for "other model" areas (FIXES)
PAD = 6   # transparent pixels around each piece
# Areas (x0, y0, x1, y1 in the original's pixels) fixed after the upscale; see the docstring.
FIXES = {
    "tiles": [("other model", (0, 104, 424, 160)),   # the coins: the main model draws dark lines into their rims
              ("texture", (512, 512, 832, 992)),   # the main menu's picture (title and door): its grain
              ("plain", (397, 490, 497, 511))],    # the experience / health bar fills: rows of small arrows / crosses
    "menus": [("other model", (0, 222, 155, 302)),   # the help picture of a path over four coins: as the coins
              ("texture", (0, 354, 248, 512))],    # the "Starting the new game..." box: its grain
}


def pieces(alpha):
    """Labels (1..n) of the 8-connected pieces of non-transparent pixels, and n."""
    h, w = alpha.shape
    label = np.zeros((h, w), np.int32)
    solid = alpha > 0
    n = 0
    for y0, x0 in zip(*np.nonzero(solid)):
        if label[y0, x0]:
            continue
        n += 1
        label[y0, x0] = n
        todo = collections.deque([(y0, x0)])
        while todo:
            y, x = todo.popleft()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    v, u = y + dy, x + dx
                    if 0 <= v < h and 0 <= u < w and solid[v, u] and not label[v, u]:
                        label[v, u] = n
                        todo.append((v, u))
    return label, n


def grow(mask):
    """The mask with its 8 neighbours added (one pixel wider all round)."""
    out = mask.copy()
    out[1:, :] |= mask[:-1, :]
    out[:-1, :] |= mask[1:, :]
    m = out.copy()
    out[:, 1:] |= m[:, :-1]
    out[:, :-1] |= m[:, 1:]
    return out


def premultiplied(rgba):
    a = rgba.astype(np.float32) / 255.0
    a[..., :3] *= a[..., 3:4]
    return a


def smooth(a):
    """a blurred by about a pixel (binomial 1 4 6 4 1 across and down), edges repeated."""
    k = np.array([1, 4, 6, 4, 1], np.float32) / 16
    for axis in (0, 1):
        p = np.pad(a, [(2, 2) if i == axis else (0, 0) for i in range(a.ndim)], mode="edge")
        n = a.shape[axis]
        a = sum(k[i] * np.take(p, range(i, i + n), axis=axis) for i in range(5))
    return a


def back_project(original, hd, rounds=2, colours_only=False):
    """hd (SCALE x original) corrected until, shrunk to the original's size, it matches the original again; with
    colours_only only the broad colour is corrected (the difference blurred first), not the fine detail."""
    o, h = premultiplied(original), premultiplied(hd)
    rows, cols = o.shape[:2]
    for _ in range(rounds):
        lost = o - h.reshape(rows, SCALE, cols, SCALE, 4).mean(axis=(1, 3))
        if colours_only:
            lost = smooth(lost)
        h += np.stack([np.array(Image.fromarray(lost[..., c]).resize((cols * SCALE, rows * SCALE), Image.BICUBIC))
                       for c in range(4)], -1)
        h[..., 3] = np.clip(h[..., 3], 0.0, 1.0)
        h[..., :3] = np.clip(h[..., :3], 0.0, h[..., 3:4])
    a = h[..., 3:4]
    h[..., :3] = np.where(a > 0, h[..., :3] / np.maximum(a, 1e-6), 0.0)
    return (h * 255.0 + 0.5).astype(np.uint8)


def fix(image, out, mode, box):
    """One FIXES area of out (the assembled HD atlas) redone from the original, with a margin for the filters."""
    h, w = image.shape[:2]
    x0, y0, x1, y1 = box
    m0, n0, m1, n1 = max(x0 - 4, 0), max(y0 - 4, 0), min(x1 + 4, w), min(y1 + 4, h)
    source = image[n0:n1, m0:m1]
    if mode == "texture":
        done = back_project(source, out[n0 * SCALE:n1 * SCALE, m0 * SCALE:m1 * SCALE])
    else:
        done = np.array(Image.fromarray(source).resize(((m1 - m0) * SCALE, (n1 - n0) * SCALE), Image.LANCZOS))
    out[y0 * SCALE:y1 * SCALE, x0 * SCALE:x1 * SCALE] = \
        done[(y0 - n0) * SCALE:(y1 - n0) * SCALE, (x0 - m0) * SCALE:(x1 - m0) * SCALE]


def upscale(upscaler, name):
    image = np.array(Image.open(os.path.join(ORIGINAL, name + ".png")).convert("RGBA"))
    h, w = image.shape[:2]
    label, n = pieces(image[..., 3])
    work = tempfile.mkdtemp(prefix="make_hd_")
    src, dst = os.path.join(work, "in"), os.path.join(work, "out")
    os.makedirs(src)
    boxes = {}
    for k in range(1, n + 1):
        ys, xs = np.nonzero(label == k)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        boxes[k] = (y0, y1, x0, x1)
        crop = np.zeros((y1 - y0 + 2 * PAD, x1 - x0 + 2 * PAD, 4), np.uint8)
        own = (label[y0:y1, x0:x1] == k)[..., None]
        crop[PAD:PAD + y1 - y0, PAD:PAD + x1 - x0] = image[y0:y1, x0:x1] * own
        Image.fromarray(crop).save(os.path.join(src, "%05d.png" % k))
    other = [box for mode, box in FIXES.get(name, []) if mode == "other model"]
    for model, folder in [(MODEL, dst)] + ([(OTHER_MODEL, dst + "2")] if other else []):
        os.makedirs(folder, exist_ok=True)
        subprocess.run([os.path.join(upscaler, "realesrgan-ncnn-vulkan"), "-i", src, "-o", folder, "-n", model,
                        "-s", str(SCALE), "-m", os.path.join(upscaler, "models")], check=True, capture_output=True)
    out = np.zeros((h * SCALE, w * SCALE, 4), np.uint8)
    for k, (y0, y1, x0, x1) in boxes.items():
        inside = any(b[0] <= x0 and x1 <= b[2] and b[1] <= y0 and y1 <= b[3] for b in other)
        big = np.array(Image.open(os.path.join(dst + "2" if inside else dst, "%05d.png" % k)).convert("RGBA"))
        big = back_project(np.array(Image.open(os.path.join(src, "%05d.png" % k))), big, colours_only=True)
        # the piece's pixels and their neighbours (its anti-aliased edge), each source pixel SCALE x SCALE
        g0, g1, f0, f1 = max(y0 - 1, 0), min(y1 + 1, h), max(x0 - 1, 0), min(x1 + 1, w)
        own = grow(label[g0:g1, f0:f1] == k).repeat(SCALE, 0).repeat(SCALE, 1)
        part = big[(PAD - (y0 - g0)) * SCALE:(PAD + g1 - y0) * SCALE, (PAD - (x0 - f0)) * SCALE:(PAD + f1 - x0) * SCALE]
        here = out[g0 * SCALE:g1 * SCALE, f0 * SCALE:f1 * SCALE]
        take = own & (part[..., 3] > here[..., 3])
        here[take] = part[take]
    shutil.rmtree(work)
    for mode, box in FIXES.get(name, []):
        if mode != "other model":
            fix(image, out, mode, box)
    os.makedirs(HD, exist_ok=True)
    Image.fromarray(out).save(os.path.join(HD, name + ".png"), optimize=True)
    keep(os.path.join(HD, name + ".png"))
    print("%s: %d pieces, %dx%d -> %dx%d" % (name, n, w, h, w * SCALE, h * SCALE), flush=True)


def languages(codes=None):
    sys.path.insert(0, HERE)
    import localise_atlas
    work = tempfile.mkdtemp(prefix="make_hd_lang_")
    localise_atlas.FRONTEND = work   # (its output folder: <FRONTEND>/godot/assets/lang/<code>)
    out = os.path.join(work, "godot", "assets", "lang")
    for code in codes or localise_atlas.REGIONS:
        sys.argv = ["localise_atlas.py", code, "--base", HD]
        localise_atlas.main()
        os.makedirs(os.path.join(HD, "lang", code), exist_ok=True)
        for name in os.listdir(os.path.join(out, code)):
            if name.endswith(".png"):
                shutil.copy(os.path.join(out, code, name), os.path.join(HD, "lang", code, name))
                keep(os.path.join(HD, "lang", code, name))
    # the language names (make_names) at SCALE x their size
    names = Image.new("RGBA", (256 * SCALE, 256 * SCALE), (0, 0, 0, 0))
    for i, n in enumerate(["English", "中文"]):
        names.alpha_composite(localise_atlas.text_image([n], "Heavy", 128 * SCALE, 32 * SCALE, localise_atlas.BUTTON_TEXT,
                                                        localise_atlas.BUTTON_OUTLINE), (0, 32 * SCALE * i))
    names.save(os.path.join(HD, "lang", "names.png"))
    keep(os.path.join(HD, "lang", "names.png"))
    shutil.rmtree(work)
    print("wrote the languages' HD pictures into %s" % os.path.join(HD, "lang"))


def keep(png):
    with open(png + ".import", "w", encoding="utf-8") as f:   # exported as is (iOS)
        f.write('[remap]\n\nimporter="keep"\n')


def main():
    if sys.argv[1:2] == ["--lang"]:
        languages(sys.argv[2:])
        return
    if len(sys.argv) < 2 or not os.path.exists(os.path.join(sys.argv[1], "realesrgan-ncnn-vulkan")):
        sys.exit(__doc__)
    for name in sys.argv[2:] or NAMES:
        upscale(sys.argv[1], name)


if __name__ == "__main__":
    main()
