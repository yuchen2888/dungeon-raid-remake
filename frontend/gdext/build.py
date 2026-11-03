#!/usr/bin/env python3
"""Builds the Dungeon Raid front end's native parts (T050-A) with plain clang++ (no SCons / CMake needed).

  python3 frontend/gdext/build.py test        the bridge's headless test (no Godot needed), built and run
  python3 frontend/gdext/build.py extension   the GDExtension library into frontend/godot/bin/
  python3 frontend/gdext/build.py check       build/libdrf_check.dylib, the bridge's C face for the reference checks
  python3 frontend/gdext/build.py app         a stand-alone "Dungeon Raid.app" in frontend/dist/ (A5)
  python3 frontend/gdext/build.py ios         the GDExtension for iPhone (device and simulator) as an xcframework in
                                              frontend/godot/bin/, for Godot's iOS export (T050-B)

The rules are compiled straight from recovered/ (the source list of recovered/run_session_demo.sh, so a module the
backend adds there is picked up); nothing is copied. The extension also needs godot-cpp in frontend/gdext/godot-cpp
(10.0.0-stable, downloaded with the user's consent on 2026-10-21); its bindings are generated into build/ for the
API version below, trimmed to the classes in build_profile.json.
"""
import concurrent.futures
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RECOVERED = os.path.join(ROOT, "recovered")
GODOT_CPP = os.path.join(HERE, "godot-cpp")
BUILD = os.path.join(HERE, "build")
BIN = os.path.join(ROOT, "frontend", "godot", "bin")
API_VERSION = "4.5"   # the oldest Godot the library loads in (compatibility_minimum in dungeon_raid.gdextension)
# Each target: its SDK, its compiler flags, the platform's define and its own object folder (macOS keeps build/'s top).
TARGETS = {
    "macos": ("macosx", ["-arch", "arm64", "-mmacosx-version-min=11.0"], "-DMACOS_ENABLED", ""),
    "ios": ("iphoneos", ["-arch", "arm64", "-miphoneos-version-min=15.0"], "-DIOS_ENABLED", "ios"),
    "ios-simulator": ("iphonesimulator", ["-arch", "arm64", "-mios-simulator-version-min=15.0"], "-DIOS_ENABLED", "ios-simulator"),
}
target = "macos"
# The rules' own flags (run_session_demo.sh): strict float contraction keeps results identical to the tests.
RULE_FLAGS = ["-std=c++17", "-O2", "-ffp-contract=off", "-Wall", "-Wextra"]
GODOT_DEFINES = ["-DUNIX_ENABLED", "-DTHREADS_ENABLED", "-DDEBUG_ENABLED", "-DNDEBUG", "-DGDEXTENSION"]
GODOT_FLAGS = ["-std=c++17", "-O2", "-fno-exceptions", "-fvisibility=hidden", "-fPIC"] + GODOT_DEFINES


UI_SOURCES = ["ui/gl.cpp", "ui/quad.cpp", "ui/text.cpp", "ui/interface.cpp", "ui/arrow.cpp", "ui/effects.cpp", "ui/texts.cpp", "ui/menu.cpp", "ui/help.cpp", "ui/screens.cpp", "ui/strip.cpp", "ui/setup.cpp", "ui/mode.cpp", "ui/class_screen.cpp", "ui/intro.cpp", "ui/gameover.cpp", "ui/scores.cpp", "ui/unlock.cpp", "ui/tooltip.cpp", "ui/presenter.cpp", "ui/settings.cpp"]   # the recovered drawing (frontend/gdext/src/ui)


def recovered_sources():
    with open(os.path.join(RECOVERED, "run_session_demo.sh"), encoding="utf-8") as f:
        names = re.findall(r"\b(recovered_\w+\.cpp)\b", f.read())
    return [os.path.join(RECOVERED, n) for n in dict.fromkeys(names)]


def clang():
    return ["xcrun", "--sdk", TARGETS[target][0], "clang++"] + TARGETS[target][1]


def godot_flags():
    return GODOT_FLAGS + [TARGETS[target][2]]


def build_dir():
    return os.path.join(BUILD, TARGETS[target][3]) if TARGETS[target][3] else BUILD


def stale(obj, dep):
    if not os.path.exists(obj) or not os.path.exists(dep):
        return True
    t = os.path.getmtime(obj)
    with open(dep, encoding="utf-8") as f:
        text = f.read().replace("\\\n", " ")
    files = text.split(":", 1)[1].split() if ":" in text else []
    return any(not os.path.exists(p) or os.path.getmtime(p) > t for p in files)


def compile_all(jobs, label):
    todo = [j for j in jobs if stale(j[1], j[1] + ".d")]
    print(f"{label}: {len(todo)} of {len(jobs)} files to compile", flush=True)

    def run(job):
        src, obj, flags = job
        os.makedirs(os.path.dirname(obj), exist_ok=True)
        cmd = clang() + flags + ["-MMD", "-MF", obj + ".d", "-c", src, "-o", obj]
        r = subprocess.run(cmd, capture_output=True, text=True)
        return src, r

    failed = 0
    with concurrent.futures.ThreadPoolExecutor(os.cpu_count() or 4) as pool:
        for src, r in pool.map(run, todo):
            if r.returncode or r.stderr.strip():
                sys.stderr.write(r.stderr)
            failed += r.returncode != 0
    if failed:
        sys.exit(f"{label}: {failed} files failed to compile")
    return [j[1] for j in jobs]


def obj_path(src, group):
    rel = os.path.relpath(src, ROOT if group != "godot-cpp" else GODOT_CPP)
    return os.path.join(build_dir(), group, rel.replace(os.sep, "_") + ".o")


def rule_objects(group, extra_flags=()):
    flags = RULE_FLAGS + list(extra_flags)
    return compile_all([(s, obj_path(s, group), flags) for s in recovered_sources()], "rules")


def build_test():
    inc = ["-I" + RECOVERED, "-I" + os.path.join(HERE, "src")]
    objs = rule_objects("test-rules")
    objs += compile_all([(os.path.join(HERE, "src", "dr_bridge.cpp"), obj_path(os.path.join(HERE, "src", "dr_bridge.cpp"), "test"), RULE_FLAGS + ["-Werror"] + inc),
                         (os.path.join(HERE, "test", "bridge_test.cpp"), obj_path(os.path.join(HERE, "test", "bridge_test.cpp"), "test"), RULE_FLAGS + ["-Werror"] + inc)], "bridge")
    exe = os.path.join(BUILD, "bridge_test")
    subprocess.run(clang() + objs + ["-o", exe], check=True)
    r = subprocess.run([exe])
    sys.exit(r.returncode)


def build_check():
    """The bridge with its C face (drf_capi.cpp) as a dylib for frontend/tools/lockstep.py."""
    inc = ["-I" + RECOVERED, "-I" + os.path.join(HERE, "src")]
    objs = rule_objects("check-rules", ["-fPIC"])
    own = ["dr_bridge.cpp", "drf_capi.cpp"] + UI_SOURCES
    objs += compile_all([(os.path.join(HERE, "src", f), obj_path(os.path.join(HERE, "src", f), "check"), RULE_FLAGS + ["-fPIC", "-Werror"] + inc)
                         for f in own], "check")
    lib = os.path.join(BUILD, "libdrf_check.dylib")
    subprocess.run(clang() + ["-dynamiclib"] + objs + ["-o", lib], check=True)
    print("built " + os.path.relpath(lib, ROOT))


def generate_bindings():
    """godot-cpp's own generator (what its SConstruct runs), output in build/godot-cpp-gen, trimmed by build_profile.json."""
    gen = os.path.join(BUILD, "godot-cpp-gen")
    api_file = os.path.join(GODOT_CPP, "gdextension", "extension_api-%s.json" % API_VERSION.replace(".", "-"))
    interface = os.path.join(GODOT_CPP, "gdextension", "gdextension_interface.json")
    profile = os.path.join(HERE, "build_profile.json")
    stamp = os.path.join(gen, "stamp.json")
    key = {"api": api_file, "profile": open(profile, encoding="utf-8").read(), "generator": os.path.getmtime(os.path.join(GODOT_CPP, "binding_generator.py"))}
    if os.path.exists(stamp) and json.load(open(stamp, encoding="utf-8")) == key:
        return gen
    print("generating godot-cpp bindings for API " + API_VERSION, flush=True)
    sys.path.insert(0, GODOT_CPP)
    from binding_generator import _generate_bindings   # noqa: E402 (godot-cpp's module)
    from build_profile import generate_trimmed_api      # noqa: E402
    api = generate_trimmed_api(api_file, profile)
    _generate_bindings(api, api_file, interface, False, "64", "single", gen)
    with open(stamp, "w", encoding="utf-8") as f:
        json.dump(key, f)
    return gen


def build_extension(lib_name="libdungeonraid.macos.template_debug.arm64.dylib", out_dir=BIN):
    if not os.path.isdir(GODOT_CPP):
        sys.exit("frontend/gdext/godot-cpp is missing (godot-cpp 10.0.0-stable, see frontend/README.md)")
    gen = generate_bindings()
    inc = ["-I" + os.path.join(GODOT_CPP, "include"), "-I" + os.path.join(gen, "gen", "include")]
    cpp_sources = []
    for d in ["src", "src/classes", "src/core", "src/templates", "src/variant"]:
        p = os.path.join(GODOT_CPP, d)
        cpp_sources += [os.path.join(p, f) for f in sorted(os.listdir(p)) if f.endswith(".cpp")]
    for base, _, files in os.walk(os.path.join(gen, "gen", "src")):
        cpp_sources += [os.path.join(base, f) for f in sorted(files) if f.endswith(".cpp")]
    jobs = []
    for s in cpp_sources:
        group = "godot-cpp" if s.startswith(GODOT_CPP) else "godot-cpp-gen"
        rel = os.path.relpath(s, GODOT_CPP if group == "godot-cpp" else gen)
        jobs.append((s, os.path.join(build_dir(), group, rel.replace(os.sep, "_") + ".o"), godot_flags() + inc))
    objs = compile_all(jobs, "godot-cpp")
    objs += rule_objects("ext-rules", ["-fPIC", "-fvisibility=hidden"])
    own = ["dr_bridge.cpp", "dungeon_raid_session.cpp", "ios_png.cpp", "register_types.cpp"] + UI_SOURCES
    # godot-cpp's headers as system headers: their warnings are not ours.
    own_inc = [f.replace("-I", "-isystem", 1) for f in inc] + ["-I" + RECOVERED, "-I" + os.path.join(HERE, "src")]
    objs += compile_all([(os.path.join(HERE, "src", f), obj_path(os.path.join(HERE, "src", f), "ext"),
                          godot_flags() + ["-Wall", "-Wextra", "-ffp-contract=off"] + own_inc) for f in own], "extension")
    os.makedirs(out_dir, exist_ok=True)
    lib = os.path.join(out_dir, lib_name)
    subprocess.run(clang() + ["-dynamiclib", "-fvisibility=hidden", "-install_name", "@rpath/" + os.path.basename(lib)]
                   + objs + ["-lz", "-o", lib], check=True)   # (zlib: the import's pictures, ios_png.cpp)
    print("built " + os.path.relpath(lib, ROOT))
    return lib


def build_ios():
    """The extension for the iPhone and for the simulator (both arm64), joined into one xcframework; Godot's iOS
    export copies it into the Xcode project and wraps each dylib as a framework."""
    import shutil
    global target
    libs = []
    for t in ["ios", "ios-simulator"]:
        target = t
        libs.append(build_extension("libdungeonraid.ios.template_debug.dylib", os.path.join(BUILD, t, "lib")))
    target = "macos"
    xcf = os.path.join(BIN, "libdungeonraid.ios.template_debug.xcframework")
    shutil.rmtree(xcf, ignore_errors=True)
    cmd = ["xcodebuild", "-create-xcframework"]
    for lib in libs:
        cmd += ["-library", lib]
    subprocess.run(cmd + ["-output", xcf], check=True, capture_output=True)
    print("built " + os.path.relpath(xcf, ROOT))


GODOT_APP = "/Applications/Godot.app"
DIST = os.path.join(ROOT, "frontend", "dist")
PROJECT = os.path.join(ROOT, "frontend", "godot")


def build_app():
    """A5 without Godot's export templates (a 1 GB download that needs the user's consent): the installed Godot's own
    runtime (arm64 part only) runs the project copied into the app; the app needs nothing else installed."""
    import plistlib
    import shutil
    godot = os.path.join(GODOT_APP, "Contents", "MacOS", "Godot")
    if not os.path.exists(godot):
        sys.exit("Godot is not installed in /Applications (godotengine.org/download/macos)")
    build_extension()
    # Refresh Godot's import cache (textures, the extension list) before copying the project.
    subprocess.run([godot, "--headless", "--path", PROJECT, "--import"], check=False, capture_output=True)
    app = os.path.join(DIST, "Dungeon Raid.app")
    shutil.rmtree(app, ignore_errors=True)
    macos, res = os.path.join(app, "Contents", "MacOS"), os.path.join(app, "Contents", "Resources")
    os.makedirs(macos)
    subprocess.run(["lipo", godot, "-thin", "arm64", "-output", os.path.join(macos, "Godot")], check=True)
    game = os.path.join(res, "game")
    skip = {".godot", "dist", "tests"}
    shutil.copytree(PROJECT, game, ignore=lambda d, names: [n for n in names if d == PROJECT and n in skip])
    for keep in ["imported", "extension_list.cfg", "global_script_class_cache.cfg", "uid_cache.bin"]:
        src = os.path.join(PROJECT, ".godot", keep)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(game, ".godot", keep))
        elif os.path.exists(src):
            os.makedirs(os.path.join(game, ".godot"), exist_ok=True)
            shutil.copy2(src, os.path.join(game, ".godot", keep))
    launcher = os.path.join(macos, "DungeonRaid")
    with open(launcher, "w", encoding="utf-8") as f:
        f.write('#!/bin/sh\nHERE="$(cd "$(dirname "$0")" && pwd)"\nexec "$HERE/Godot" --path "$HERE/../Resources/game" "$@"\n')
    os.chmod(launcher, 0o755)
    info = {"CFBundleExecutable": "DungeonRaid", "CFBundleIdentifier": "local.dungeonraid.remake.prototype",
            "CFBundleName": "Dungeon Raid", "CFBundleDisplayName": "Dungeon Raid", "CFBundlePackageType": "APPL",
            "CFBundleShortVersionString": "0.1", "CFBundleVersion": "1", "LSMinimumSystemVersion": "11.0",
            "NSHighResolutionCapable": True, "LSApplicationCategoryType": "public.app-category.games"}
    icon = os.path.join(ROOT, "frontend", "godot", "assets", "original", "icon.icns")
    if os.path.exists(icon):
        shutil.copy2(icon, os.path.join(res, "icon.icns"))
        info["CFBundleIconFile"] = "icon"
    with open(os.path.join(app, "Contents", "Info.plist"), "wb") as f:
        plistlib.dump(info, f)
    subprocess.run(["codesign", "--force", "--deep", "-s", "-", app], check=True, capture_output=True)
    print("built " + os.path.relpath(app, ROOT))


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    if what == "test":
        build_test()
    elif what == "extension":
        build_extension()
    elif what == "check":
        build_check()
    elif what == "app":
        build_app()
    elif what == "ios":
        build_ios()
    else:
        sys.exit(__doc__)
