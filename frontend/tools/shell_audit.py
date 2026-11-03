#!/usr/bin/env python3
"""Checks the shell app's package holds none of the original's content (T081), before it is published.

  python3 frontend/tools/shell_audit.py [frontend/dist/shell/DungeonRaid-Remake-unsigned.ipa]

Lists every file of the IPA and of the Godot package inside it (DungeonRaid.pck), and fails when:
- a path is one of the original's or made from it (assets/original/, assets/hd/, a language's tiles.png / menus.png,
  the Spanish letters assets/lang/es/font*, assets/lang/en/);
- any file's bytes are those of a file of the original IPA, of assets/original/, assets/hd/ or of a language's
  pictures made from the original (by SHA-256);
- the package's bytes contain any of the original's longer English texts (assets/original/texts.txt, 24 letters up).
"""
import hashlib
import os
import re
import struct
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
ASSETS = os.path.join(ROOT, "frontend", "godot", "assets")
ORIGINAL_IPA = os.path.join(ROOT, "DungeonRaid-independent-experimental-unsigned.ipa")
# Files that may equal one of the original's, and why: every iPhone app's 8-byte "APPL????" PkgInfo; the sound table,
# which the shell carries on purpose (names of the .caf files, their number and volume: make_shell_data.py).
ALLOWED = {"Payload/DungeonRaid.app/PkgInfo": "every app's PkgInfo", "pck:assets/shell/sounds.json": "the sound table"}
BANNED = re.compile(r"^(res://)?(assets/original/|assets/hd/|assets/lang/en/|assets/lang/[^/]+/(tiles|menus)\.png|assets/lang/es/font)")


def pck_files(data):
    """(path, bytes) of each file of a Godot 4 .pck (format 2 or 3)."""
    assert data[:4] == b"GDPC", "not a Godot package"
    version, = struct.unpack_from("<I", data, 4)
    flags, base = struct.unpack_from("<IQ", data, 20)
    if version >= 3:
        directory, = struct.unpack_from("<Q", data, 32)
        p = directory
    else:
        p = 32 + 16 * 4
    count, = struct.unpack_from("<I", data, p)
    p += 4
    out = []
    for _ in range(count):
        n, = struct.unpack_from("<I", data, p)
        path = data[p + 4:p + 4 + n].rstrip(b"\0").decode("utf-8")
        p += 4 + n
        offset, size = struct.unpack_from("<QQ", data, p)
        p += 16 + 16 + 4
        out.append((path, data[base + offset:base + offset + size]))
    return out


def main():
    ipa = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "frontend", "dist", "shell", "DungeonRaid-Remake-unsigned.ipa")
    banned_hashes = {}
    with zipfile.ZipFile(ORIGINAL_IPA) as z:
        for n in z.namelist():
            if not n.endswith("/"):
                banned_hashes[hashlib.sha256(z.read(n)).hexdigest()] = "original IPA " + n
    for folder in ["original", "hd"]:
        for base, _, files in os.walk(os.path.join(ASSETS, folder)):
            for f in files:
                if not f.endswith(".import"):
                    path = os.path.join(base, f)
                    banned_hashes[hashlib.sha256(open(path, "rb").read()).hexdigest()] = os.path.relpath(path, ASSETS)
    for code in os.listdir(os.path.join(ASSETS, "lang")):
        for f in ["tiles.png", "menus.png", "font.png", "fontMenu.png", "fontScore.png"]:
            path = os.path.join(ASSETS, "lang", code, f)
            if os.path.isfile(path) and (code == "es" or f in ("tiles.png", "menus.png")):
                banned_hashes[hashlib.sha256(open(path, "rb").read()).hexdigest()] = os.path.relpath(path, ASSETS)
    texts = []
    for line in open(os.path.join(ASSETS, "original", "texts.txt"), encoding="utf-8"):
        if "\t" in line and not line.startswith("#"):
            v = line.rstrip("\n").split("\t", 1)[1].replace("\\n", "\n")
            if len(v) >= 24:
                texts.append(v.encode("latin1"))
    problems, count = [], 0
    with zipfile.ZipFile(ipa) as z:
        entries = [(n, z.read(n)) for n in z.namelist() if not n.endswith("/")]
    everything = list(entries)
    for n, data in entries:
        if n.endswith(".pck"):
            everything += [("pck:" + p, d) for p, d in pck_files(data)]
    for name, data in everything:
        count += 1
        path = name[4:] if name.startswith("pck:") else name
        if BANNED.search(path):
            problems.append("original path: " + name)
        h = hashlib.sha256(data).hexdigest()
        if h in banned_hashes and name not in ALLOWED:
            problems.append("%s is %s" % (name, banned_hashes[h]))
        for t in texts:
            if t in data:
                problems.append("%s holds the original's text %r" % (name, t[:40]))
                break
    print("%d files checked (%d in the IPA)" % (count, len(entries)))
    for p in problems:
        print("PROBLEM: " + p)
    print("clean" if not problems else "%d problems" % len(problems))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
