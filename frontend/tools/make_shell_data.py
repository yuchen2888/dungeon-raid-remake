#!/usr/bin/env python3
"""Makes the shell app's import data (T081): what the game needs to rebuild, on the player's phone and from the
player's own copy of the original, every original file it reads, with none of the original's content in it.

  python3 frontend/tools/make_shell_data.py

Writes frontend/godot/assets/shell/ (local, like the rest of assets/; the shell IPA carries it):
- manifest.json: the original files the import takes from the player's IPA (Payload/*.app/<name>), each by its size
  and SHA-256, so an IPA of another version is refused rather than misread; for the program only the bytes the game
  reads count (T082: copies decrypted by different tools differ elsewhere, and some keep only the armv7 code): the
  SHA-256 of every text texts.map gives, each followed by a 0;
- texts.map: each English text of assets/original/texts.txt as where its bytes sit in the original program's armv7
  code (offset:length pieces from the start of that code, joined); only positions, no text;
- sounds.json: the original's sound table (names of its .caf files, recordings, volumes: numbers read from its
  program by import_original_assets.py);
- patch/<lang>/<picture>.png: each language's pictures with the original's words redrawn (tiles, menus) as the
  difference from the original picture, byte by byte (new - original, mod 256): like a translation patch, it only
  gives the picture back added to the player's own original.

Checks itself: rebuilds texts.txt from the program and every patched picture from the original, and compares them
with the files the Mac version uses (assets/original/, assets/lang/).
"""
import hashlib
import json
import os
import shutil
import struct
import sys
import zipfile

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
ASSETS = os.path.join(ROOT, "frontend", "godot", "assets")
ORIGINAL = os.path.join(ASSETS, "original")
OUT = os.path.join(ASSETS, "shell")
IPA = os.path.join(ROOT, "DungeonRaid-independent-experimental-unsigned.ipa")
PROGRAM = os.path.join(ROOT, "DungeonRaid-original")
PICTURES = ["tiles.png", "font.png", "icons.png", "menus.png", "fontMenu.png", "fontScore.png"]
FONTS = ["font.fnt", "fontMenu.fnt", "fontScore.fnt"]
LOCALISED = ["tiles.png", "menus.png"]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def armv7(program):
    """The armv7 code of a Mach-O file: the slice of a universal file, or the file itself when it has only that."""
    if program[:4] == b"\xca\xfe\xba\xbe":
        for i in range(struct.unpack_from(">I", program, 4)[0]):
            cpu, sub, offset, size, _ = struct.unpack_from(">5I", program, 8 + 20 * i)
            if cpu == 12 and sub == 9:
                return program[offset:offset + size]
    elif program[:4] == b"\xce\xfa\xed\xfe" and struct.unpack_from("<II", program, 4) == (12, 9):
        return program
    return None


def pieces(value, program):
    """value (bytes) as the fewest offset:length pieces of program, longest first from the left."""
    whole = program.find(value + b"\0")
    if whole >= 0:
        return [(whole, len(value))]
    out, i = [], 0
    while i < len(value):
        lo, hi = i + 1, len(value)   # the longest value[i:j] in the program (a longer one found means a shorter one is)
        if program.find(value[i:lo]) < 0:
            sys.exit("not in the program: %r" % value[i:lo])
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if program.find(value[i:mid]) >= 0:
                lo = mid
            else:
                hi = mid - 1
        out.append((program.find(value[i:lo]), lo - i))
        i = lo
    return out


def text_lines():
    """texts.txt's entries: (key, raw value as written, value as bytes)."""
    out = []
    with open(os.path.join(ORIGINAL, "texts.txt"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or "\t" not in line:
                continue
            key, written = line.rstrip("\n").split("\t", 1)
            value = written.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")
            out.append((key, written, value.encode("latin1")))
    return out


def escape(v):
    return v.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t")


def main():
    program = armv7(open(PROGRAM, "rb").read())
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    # the files the import takes, by name, size and hash
    files = {}
    sounds = json.load(open(os.path.join(ORIGINAL, "sounds.json")))
    with zipfile.ZipFile(IPA) as z:
        names = {os.path.basename(n): n for n in z.namelist() if n.count("/") == 2}
        wanted = PICTURES + FONTS + ["%s%d.caf" % (s["name"], v + 1) for s in sounds for v in range(s["variations"])]
        for name in wanted:
            data = z.read(names[name])
            files[name] = {"size": len(data), "sha256": sha(data)}
    shutil.copy(os.path.join(ORIGINAL, "sounds.json"), os.path.join(OUT, "sounds.json"))
    # the texts as positions
    lines = text_lines()
    with open(os.path.join(OUT, "texts.map"), "w", encoding="utf-8") as f:
        for key, _, value in lines:
            f.write("%s\t%s\n" % (key, ",".join("%d:%d" % p for p in pieces(value, program))))
    texts = b"".join(value + b"\0" for _, _, value in lines)
    json.dump({"version": "1.3.4", "program": {"arch": "armv7", "texts_sha256": sha(texts)}, "files": files},
              open(os.path.join(OUT, "manifest.json"), "w"), indent=1)
    rebuilt = rebuild_texts(os.path.join(OUT, "texts.map"), program)
    expected = "".join("%s\t%s\n" % (k, w) for k, w, _ in lines)
    assert rebuilt == expected, "texts.map does not give texts.txt back"
    # the pictures' patches
    count = 0
    for code in sorted(os.listdir(os.path.join(ASSETS, "lang"))):
        for name in LOCALISED:
            new = os.path.join(ASSETS, "lang", code, name)
            if not os.path.isfile(new):
                continue
            a = np.array(Image.open(os.path.join(ORIGINAL, name)).convert("RGBA"))
            b = np.array(Image.open(new).convert("RGBA"))
            assert a.shape == b.shape, new
            os.makedirs(os.path.join(OUT, "patch", code), exist_ok=True)
            patch = (b.astype(np.int16) - a.astype(np.int16)) % 256
            Image.fromarray(patch.astype(np.uint8), "RGBA").save(os.path.join(OUT, "patch", code, name), optimize=True)
            with open(os.path.join(OUT, "patch", code, name + ".import"), "w") as f:   # exported as the file it is
                f.write('[remap]\n\nimporter="keep"\n')
            back = (a.astype(np.int16) + np.array(Image.open(os.path.join(OUT, "patch", code, name)))) % 256
            assert (back.astype(np.uint8) == b).all(), new
            count += 1
    print("manifest: %d files; texts.map: %d texts; %d picture patches; in %s" % (len(files), len(lines), count, OUT))


def rebuild_texts(path, program):
    """texts.txt as the game rebuilds it from texts.map and the program (frontend/godot/importer.gd does the same)."""
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            key, spec = line.rstrip("\n").split("\t", 1)
            value = b"".join(program[o:o + n] for o, n in (map(int, p.split(":")) for p in spec.split(",")))
            out.append("%s\t%s\n" % (key, escape(value.decode("latin1"))))
    return "".join(out)


if __name__ == "__main__":
    main()
