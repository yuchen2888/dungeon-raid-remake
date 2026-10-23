#!/usr/bin/env python3
"""Makes an arm64 simulator copy of Godot's iPhone engine library (T050-B; used by frontend/tools/ios.sh simulator).

  python3 frontend/tools/sim_retarget.py <device libgodot.a> <output libgodot.a>

Godot 4.7.2's official iOS export template carries the engine for the simulator as x86_64 only, and the iOS 27
simulator runs arm64 only. The device library is arm64 already; each of its objects names its platform once
(LC_BUILD_VERSION, platform 2 = iOS). The copy names platform 7 (iOS simulator) instead; the code is unchanged.
Only for trying the game in the simulator: the iPhone itself uses Godot's library unchanged.

The simulator's Metal also lacks two error-domain names the device's has (MTLIOErrorDomain, MTLTensorDomain, which
Godot's metal-cpp reads at start-up); the copy gets a small object defining them as empty (nil) names.
"""
import os
import struct
import subprocess
import sys
import tempfile

STUB = "const void *MTLIOErrorDomain = 0;\nconst void *MTLTensorDomain = 0;\n"

MH_MAGIC_64 = 0xFEEDFACF
LC_BUILD_VERSION = 0x32
PLATFORM_IOS, PLATFORM_IOSSIMULATOR = 2, 7


def retarget_object(data, start, end):
    """Patches the Mach-O object in data[start:end]; returns whether it named iOS."""
    magic, _cpu, _sub, _type, ncmds, _size = struct.unpack_from("<IiiIII", data, start)
    if magic != MH_MAGIC_64:
        return False
    off = start + 32
    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack_from("<II", data, off)
        if cmd == LC_BUILD_VERSION:
            (platform,) = struct.unpack_from("<I", data, off + 8)
            if platform == PLATFORM_IOS:
                struct.pack_into("<I", data, off + 8, PLATFORM_IOSSIMULATOR)
                return True
        off += cmdsize
        if off > end:
            break
    return False


def main(src, dst):
    data = bytearray(open(src, "rb").read())
    if data[:8] != b"!<arch>\n":
        sys.exit("not an ar archive: " + src)
    pos, patched, objects = 8, 0, 0
    while pos + 60 <= len(data):
        header = data[pos:pos + 60]
        name = header[:16].decode("ascii").strip()
        size = int(header[48:58].decode("ascii").strip())
        body = pos + 60
        if name.startswith("#1/"):          # BSD long name: the name precedes the member's bytes
            n = int(name[3:])
            name = data[body:body + n].rstrip(b"\0").decode("utf-8")
            start = body + n
        else:
            start = body
        end = body + size
        if not name.startswith("__.SYMDEF"):
            objects += 1
            patched += retarget_object(data, start, end)
        pos = end + (end & 1)
    if patched != objects:
        sys.exit("%d of %d objects named iOS; not retargeted" % (patched, objects))
    with tempfile.TemporaryDirectory() as tmp:
        lib, c, o = os.path.join(tmp, "retargeted.a"), os.path.join(tmp, "metal_domains.c"), os.path.join(tmp, "metal_domains.o")
        open(lib, "wb").write(data)
        open(c, "w").write(STUB)
        subprocess.run(["xcrun", "--sdk", "iphonesimulator", "clang", "-arch", "arm64", "-mios-simulator-version-min=15.0",
                        "-c", c, "-o", o], check=True)
        subprocess.run(["libtool", "-static", "-o", dst, lib, o], check=True, capture_output=True)
    print("retargeted %d objects to the arm64 simulator: %s" % (patched, dst))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
