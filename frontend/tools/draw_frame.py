#!/usr/bin/env python3
"""Paints a frame recorded by original_frame.py into a PNG (2 pixels per original point: 640 x 960), with the
local original textures: each draw's triangles are mapped from texture space to the screen and blended as recorded.

  python3 frontend/tools/draw_frame.py frame.json out.png
"""
import json
import os
import sys

from PIL import Image, ImageChops, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
ASSETS = os.path.join(ROOT, "frontend", "godot", "assets", "original")
W, H = 640, 960
S = 640.0   # pixels per session unit (the screen is 1 wide, 1.5 high)


def triangles(mode, verts):
    if mode == 5:     # strip
        return [(verts[i], verts[i + 1], verts[i + 2]) for i in range(len(verts) - 2)]
    if mode == 6:     # fan
        return [(verts[0], verts[i], verts[i + 1]) for i in range(1, len(verts) - 1)]
    return [tuple(verts[i:i + 3]) for i in range(0, len(verts) - 2, 3)]


def affine(tri, tw, th):
    """Coefficients mapping an output pixel (x, y) to a texture pixel (PIL's inverse AFFINE)."""
    (x0, y0), (x1, y1), (x2, y2) = [(v[0] * S, v[1] * S) for v in tri]
    (u0, v0), (u1, v1), (u2, v2) = [(v[2] * tw, v[3] * th) for v in tri]
    det = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    if abs(det) < 1e-9:
        return None
    # solve u = a x + b y + c, v = d x + e y + f
    a = ((u1 - u0) * (y2 - y0) - (u2 - u0) * (y1 - y0)) / det
    b = ((u2 - u0) * (x1 - x0) - (u1 - u0) * (x2 - x0)) / det
    c = u0 - a * x0 - b * y0
    d = ((v1 - v0) * (y2 - y0) - (v2 - v0) * (y1 - y0)) / det
    e = ((v2 - v0) * (x1 - x0) - (v1 - v0) * (x2 - x0)) / det
    f = v0 - d * x0 - e * y0
    return (a, b, c, d, e, f)


def paint(frame, out):
    canvas = Image.new("RGBA", (W, H), tuple(int(c * 255) for c in (frame.get("clear") or [0, 0, 0, 1])))
    textures = {}
    for d in frame["draws"]:
        tex = d["texture"]
        if tex and tex not in textures:
            textures[tex] = Image.open(os.path.join(ASSETS, tex + ".png")).convert("RGBA")
        for tri in triangles(d["mode"], d["verts"]):
            xs, ys = [v[0] * S for v in tri], [v[1] * S for v in tri]
            box = (max(int(min(xs)) - 1, 0), max(int(min(ys)) - 1, 0), min(int(max(xs)) + 2, W), min(int(max(ys)) + 2, H))
            if box[0] >= box[2] or box[1] >= box[3]:
                continue
            bw, bh = box[2] - box[0], box[3] - box[1]
            colour = tuple(int(sum(v[4 + k] for v in tri) / 3) for k in range(4))
            if tex:
                t = textures[tex]
                co = affine(tri, t.width, t.height)
                if co is None:
                    continue
                a, b, c, dd, e, f = co
                # shift to the box origin
                patch = t.transform((bw, bh), Image.AFFINE, (a, b, c + a * box[0] + b * box[1], dd, e, f + dd * box[0] + e * box[1]),
                                    resample=Image.BILINEAR)
                patch = ImageChops.multiply(patch, Image.new("RGBA", (bw, bh), colour))
            else:
                patch = Image.new("RGBA", (bw, bh), colour)
            mask = Image.new("L", (bw, bh), 0)
            ImageDraw.Draw(mask).polygon([(x - box[0], y - box[1]) for x, y in zip(xs, ys)], fill=255)
            alpha = ImageChops.multiply(patch.getchannel("A"), mask)
            patch.putalpha(alpha)
            region = canvas.crop(box)
            canvas.paste(Image.alpha_composite(region, patch), box)
    canvas.save(out)


if __name__ == "__main__":
    paint(json.load(open(sys.argv[1], encoding="utf-8")), sys.argv[2])
