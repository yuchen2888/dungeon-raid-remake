#!/usr/bin/env python3
"""Runs the original (emulated, original_frame.py) and the front end's bridge (build/libdrf_check.dylib) side by
side on the same inputs and checks they stay in the same game state (T050-A: the base of the look checks).

  python3 frontend/gdext/build.py check && python3 frontend/tools/lockstep.py [turns]

The original is played as EAGLView does it (touches through Game::TouchStart / TouchEnd) up to the board; the
bridge takes the same steps through its calls (new game, random name, Begin, the story's Begin). From then on each
frame gets the same touch: written into the original's Game touch fields (Game+0x10 phase, +0x14 position, as the
rules' own tests do) and given to the bridge's frame. Game::UpdateTime is replaced by dt = 1/60 (Game+0x4) and
Game::CalculateFPS skipped, as in recovered/verify_game_frames.py.
"""
import ctypes as C
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import original_frame as of  # noqa: E402
from unicorn import UC_HOOK_CODE  # noqa: E402
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC  # noqa: E402

TIME = 1287619200          # what the emulated time() returns
DT = 1.0 / 60
TILES, STRIDE = 0x5e58, 608
TILE_FIELDS = (0x9c, 0xa0, 0x24c, 0x250, 0x22c, 0x224)   # type, special, enemy type, enemy state, variant, glow flag
N = len(TILE_FIELDS)


class Lockstep:
    def __init__(self):
        self.lib = C.CDLL(os.path.join(ROOT, "frontend", "gdext", "build", "libdrf_check.dylib"))
        L = self.lib
        L.drf_create.restype = C.c_void_p
        L.drf_create.argtypes = [C.c_char_p]
        L.drf_render.argtypes = [C.c_void_p]
        L.drf_draw.argtypes = [C.c_void_p, C.c_int32, C.POINTER(C.c_int32)]
        L.drf_vertices.argtypes = [C.c_void_p, C.POINTER(C.c_double)]
        L.drf_frame.argtypes = [C.c_void_p, C.c_float, C.c_int32, C.c_float, C.c_float, C.c_int32, C.c_int32]
        for n in ("drf_new_game",):
            getattr(L, n).argtypes = [C.c_void_p, C.c_int32, C.c_uint32]
        L.drf_setup_start.argtypes = [C.c_void_p, C.c_uint32]
        L.drf_set_time.argtypes = [C.c_void_p, C.c_uint32]
        L.drf_seed.argtypes = [C.c_void_p, C.c_uint32]
        L.drf_screens.argtypes = [C.c_void_p, C.POINTER(C.c_int32)]
        L.drf_restore.argtypes = [C.c_void_p, C.c_char_p, C.c_char_p, C.c_uint32]
        L.drf_test_unlock.argtypes = [C.c_void_p, C.c_int32, C.c_int32]
        L.drf_sounds.argtypes = [C.c_void_p, C.POINTER(C.c_int32), C.c_int32]
        for n in ("drf_setup_random_name", "drf_intro_done", "drf_destroy"):
            getattr(L, n).argtypes = [C.c_void_p]
        L.drf_board.argtypes = [C.c_void_p, C.POINTER(C.c_int32)]
        L.drf_counters.argtypes = [C.c_void_p, C.POINTER(C.c_int32)]
        self.b = L.drf_create(of.ASSETS.encode())
        L.drf_seed(self.b, TIME)   # Game::Start's seeding (the emulated time())
        self.s = of.Script()
        o, g = self.s.o, self.s.game.g
        self.g = g
        for name, action in (("__ZN4Game10UpdateTimeEv", self.update_time), ("__ZN4Game12CalculateFPSEv", None)):
            addr = o.fn(name)
            o.u.hook_add(UC_HOOK_CODE, self.skipper(action), begin=addr, end=addr)

    def skipper(self, action):
        def hook(u, address, size, data):
            if action:
                action()
            u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))
        return hook

    def update_time(self):
        self.s.o.u.mem_write(self.g + 4, struct.pack("<f", DT))

    # ---- state ----------------------------------------------------------------------------------------
    def original_board(self):
        u = self.s.o.u
        out = []
        for i in range(36):
            base = self.g + TILES + STRIDE * i
            out += [struct.unpack("<i", u.mem_read(base + f, 4))[0] for f in TILE_FIELDS[:5]] + [u.mem_read(base + 0x224, 1)[0]]
        return out

    def bridge_board(self):
        a = (C.c_int32 * (36 * N))()
        self.lib.drf_board(self.b, a)
        return list(a)

    def counters(self):
        a = (C.c_int32 * 8)()
        self.lib.drf_counters(self.b, a)
        return list(a)

    # ---- drawing --------------------------------------------------------------------------------------
    def front_draws(self):
        """The front end's Game::Render as the recorder's draws (texture names, vertices x, y, u, v, r, g, b, a)."""
        n = self.lib.drf_render(self.b)
        verts = (C.c_double * (8 * 20000))()
        self.lib.drf_vertices(self.b, verts)
        out = []
        for i in range(n):
            d = (C.c_int32 * 6)()
            self.lib.drf_draw(self.b, i, d)
            texture, mode, first, count = d[0], d[1], d[2], d[3]
            vs = [[verts[8 * k + j] for j in range(4)] + [int(verts[8 * k + j]) for j in range(4, 8)] for k in range(first, first + count)]
            out.append(dict(texture=of.TEXTURES.get(texture, texture), mode=mode, verts=vs, tag=d[5]))
        return out

    def compare(self, label, quiet=False, screen=None):
        """The original's draws of the recovered drawing functions against the front end's, in order; screen: only
        one screen's (an entry of SCREENS: the original's owner and the front end's draw tag)."""
        self.last_label = label
        original = [d for d in self.s.game.render()["draws"] if owner(d) in RECOVERED]
        front = self.front_draws()
        if screen:
            name, tag = SCREENS[screen]
            original = [d for d in original if owner(d) == name]
            front = [d for d in front if d["tag"] == tag]
        for d in original:
            COVERAGE[owner(d)] = COVERAGE.get(owner(d), 0) + 1
        problems = []
        if len(original) != len(front):
            problems.append("%d draws, front end %d" % (len(original), len(front)))
        for i, (a, b) in enumerate(zip(original, front)):
            if (a["texture"], a["mode"], len(a["verts"])) != (b["texture"], b["mode"], len(b["verts"])):
                problems.append("draw %d (%s): texture/mode/count %s/%s/%d vs %s/%s/%d" % (i, owner(a), a["texture"], a["mode"], len(a["verts"]),
                                b["texture"], b["mode"], len(b["verts"])))
            else:
                for k, (va, vb) in enumerate(zip(a["verts"], b["verts"])):
                    if any(abs(x - y) > 1e-9 for x, y in zip(va[:4], vb[:4])) or va[4:] != vb[4:]:
                        problems.append("draw %d (%s) vertex %d: %s vs %s" % (i, owner(a), k, va, vb))
                        break
            if len(problems) > 6:
                break
        if not quiet or problems:
            print("%s: %d recovered draws %s" % (label, len(original), "match" if not problems else "DIFFER"))
        for p in problems[:6]:
            print("   " + p)
        return not problems

    # ---- driving --------------------------------------------------------------------------------------
    def screens(self):
        a = (C.c_int32 * 6)()
        self.lib.drf_screens(self.b, a)
        return list(a)

    def begin(self):
        """The main menu at start-up (its title fading out, the buttons in), New game tapped (as the original's
        EAGLView would: touch frames), then the setup screen's Random and Start and the story's Begin."""
        s, L, b = self.s, self.lib, self.b
        L.drf_set_time(b, TIME)
        if CLASS_SCREEN:
            self.class_progress()
        ok = True
        for f in range(30):
            self.frame(0, 0.22, 0.53)
            ok &= self.compare("main menu frame %d" % f, quiet=True, screen="main menu")
        ok &= self.play_challenge_setup()
        start = (0.2, 0.62) if CHALLENGE is not None else (0.22, 0.53)   # Challenge or New game
        for phase in (1, 1, 2, 0):
            self.frame(phase, *start)
            ok &= self.compare("main menu, %s, touch phase %d" % ("Challenge" if CHALLENGE is not None else "New game", phase),
                               quiet=True, screen="main menu")
        for f in range(30):   # the setup screen over the main menu
            self.frame(0, 0.22, 0.53)
            ok &= self.compare("setup screen frame %d" % f, quiet=True, screen="main menu")
            ok &= self.compare("setup screen frame %d" % f, quiet=True, screen="setup")
        if not self.screens()[4]:   # the session's main menu did not open the setup screen (T040-M7 not there yet)
            print("the front end's main menu did not start a game: started directly")
            L.drf_new_game(b, 0, TIME)
        # the setup screen's touches, through the front end's NameScreen (its session calls after each frame): the name
        # box (the keyboard comes up), Q, W, delete, OK, Random, the class panel's Help (five bubbles), Normal, Begin
        cmp = lambda what: self.compare(what, quiet=True, screen="setup")
        kb = 0.853125   # the keyboard's place once up
        steps = (("name box", 0.3, 0.14, 30), ("Q", 0.05, 0.0703125 + kb, 10), ("W", 0.15, 0.0703125 + kb, 10),
                 ("delete", 0.934375, 0.4078125 + kb, 10), ("OK", 0.875, 0.5765625 + kb, 30),
                 ("Random", 0.86, 0.145, 20), ("Help", 0.88, 0.567, 2), ("Normal", 0.38, 0.4, 10))
        if CHALLENGE is not None:   # Random, then the challenge's mode button (NameScreen+0x6b4 + 0x4c x mode)
            mx, my = self.strip_at(self.g + self.NAME + 0x6b4 + 0x4c * CHALLENGE)
            steps = (("Random", 0.86, 0.145, 20), ("mode %d" % CHALLENGE, mx, my, 60))   # (Begin shows fully after ~51 frames)
        for what, x, y, wait in steps:
            ok &= self.menu_tap(x, y, "setup %s" % what, cmp)
            for f in range(wait):
                self.frame(0, x, y)
                ok &= cmp("setup after %s frame %d" % (what, f))
            if self.help_open():
                ok &= self.play_help("setup Help")
        if CLASS_SCREEN:   # (its Return makes the session copy its unsynced views into the record: docs/T050_GODOT_PLAN.md 24)
            ok &= self.play_class_screen()
        ok &= self.menu_tap(0.5, 1.41, "setup Begin", cmp)
        if self.screens()[4]:
            print("the front end's setup screen did not start the game: started directly")
            L.drf_setup_start(b, TIME)
        self.begin_ok = ok
        # the story screen over the setup screen and the main menu (fading in), its Begin (the front end's IntroScreen
        # closes the session's story as its fade ends), and the fade out (the screens beneath hidden)
        story = lambda what: all([self.compare(what, quiet=True, screen=s) for s in ("story", "setup", "main menu")])
        for f in range(180):
            self.frame(0)
            ok &= story("story frame %d" % f)
        for phase in (1, 1, 2, 0):
            self.frame(phase, 0.5, 1.41)
            ok &= story("story Begin, touch phase %d" % phase)
        for f in range(60):
            if not self.s.o.u.mem_read(self.g + 0xc3f0, 1)[0]:
                break
            self.frame(0)
            ok &= story("story closing frame %d" % f)
        if self.screens()[5]:
            print("the front end's story screen was still open as the original's closed: closed directly")
            ok = False
            L.drf_intro_done(b)
        self.begin_ok = ok

    NAME = 0x102dc   # NameScreen in Game; its ModeScreen at +0x36f4

    def strip_at(self, address, dx=0.03, dy=0.03):
        """A point inside the original's QuadStrip at address (its top-left corner +0x44, plus a little)."""
        x, y = struct.unpack("<ff", self.s.o.u.mem_read(address + 0x44, 8))
        return x + dx, y + dy

    def play_challenge_setup(self):
        """Challenge from the main menu, the setup screen in its challenge form, its Help (the mode screen: fading in,
        the second mode, the first, Back), then the setup screen's Back to the main menu, comparing every frame."""
        both = lambda what: all([self.compare(what, quiet=True, screen=s) for s in ("setup", "main menu")])
        ok = True
        for phase in (1, 1, 2, 0):
            self.frame(phase, 0.2, 0.62)
            ok &= both("main menu, Challenge, touch phase %d" % phase)
        for f in range(30):
            self.frame(0, 0.2, 0.62)
            ok &= both("challenge setup frame %d" % f)
        if not self.screens()[4]:
            print("the front end's main menu did not open the challenge setup screen")
            return False
        name, mode = self.g + self.NAME, self.g + self.NAME + 0x36f4
        for what, at, wait in (("Help", name + 0x630, 30), ("second mode", mode + 0x210, 15), ("first mode", mode + 0x1c4, 15),
                               ("mode screen Back", mode + 0xf0, 20), ("setup Back", name + 0x154, 40)):
            x, y = self.strip_at(at)
            ok &= self.menu_tap(x, y, "challenge %s" % what, both)
            for f in range(wait):
                self.frame(0, x, y)
                ok &= both("challenge after %s frame %d" % (what, f))
        if self.screens()[4]:
            print("the front end's setup screen did not go back to the main menu")
            ok = False
        return ok

    CLASS = 0x12c78   # ClassScreen in Game (NameScreen+0x299c)

    def class_strip(self, k, tab=None):
        """A point in the original ClassScreen's strip k (+0x4 + 0x4c k), or in strip k of a tab's list (+0xa10 + 12 tab)."""
        c = self.g + self.CLASS
        if tab is None:
            return self.strip_at(c + 4 + 0x4c * k, 0.02, 0.02)
        begin = struct.unpack("<I", self.s.o.u.mem_read(c + 0xa10 + 12 * tab, 4))[0]
        return self.strip_at(begin + 0x4c * k, 0.02, 0.02)

    # Class progress for the class screen pass (level, games, kills, normal, hard, harder), written into the
    # original's records, saved by Game::SerialiseClasses, read back by Game::DeserialiseClasses, and given to the front
    # end's session as the platform would at start-up.
    PROGRESS = {1: (6, 12, 340, 1200, 0, 0), 2: (3, 4, 80, 300, 0, 0), 3: (10, 30, 999, 5600, 2100, 900), 5: (5, 7, 150, 800, 10, 0),
                8: (9, 21, 700, 4100, 1500, 0)}

    def class_progress(self):
        o, u, g = self.s.o, self.s.o.u, self.g
        for k, (level, games, kills, normal, hard, harder) in self.PROGRESS.items():
            rec = g + 0x15564 + 0x184 * k
            u.mem_write(rec + 0x54, bytes([level]))
            u.mem_write(rec + 0x58, struct.pack("<5I", games, kills, normal, hard, harder))
        o.call(o.fn("__ZN4Game16SerialiseClassesEv"), g)
        length = struct.unpack("<i", u.mem_read(g + 0x14ad8, 4))[0]
        data = bytes(u.mem_read(g + 0x146d5, length))
        o.call(o.fn("__ZN4Game18DeserialiseClassesEv"), g)
        self.lib.drf_restore(self.b, b"classes", data, length)

    def drag(self, start, end, label, compare, steps=8):
        """A touch down on start, moved to end over steps frames, let go there (comparing every frame)."""
        ok = True
        (x0, y0), (x1, y1) = start, end
        for phase in (1, 1):
            self.frame(phase, x0, y0)
            ok &= compare("%s, down" % label)
        for i in range(1, steps + 1):
            x, y = x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps
            self.frame(1, x, y)
            ok &= compare("%s, moved %d" % (label, i))
        for phase in (2, 0):
            self.frame(phase, x1, y1)
            ok &= compare("%s, let go %d" % (label, phase))
        return ok

    def play_class_screen(self):
        """The setup screen's Edit: the class screen fading in, each tab, its pictures and panels tapped (their texts),
        the class button pressed and let go on, Help (its bubbles), Return (fading out), comparing every frame."""
        cmp = lambda what: self.compare(what, quiet=True, screen="setup")
        ok = True
        steps = [("Edit", self.strip_at(self.g + self.NAME + 0x12f8), 30),
                 ("race tab", self.class_strip(1), 10), ("race 0", self.class_strip(0, 1), 6), ("race panel", self.class_strip(20, 1), 6),
                 ("enemy panel", self.class_strip(21, 1), 6),
                 ("perks tab", self.class_strip(2), 10), ("perk 0", self.class_strip(0, 2), 6), ("flaw 0", self.class_strip(10, 2), 6),
                 ("perk 1", self.class_strip(1, 2), 6),
                 ("skills tab", self.class_strip(3), 10), ("class skill 0", self.class_strip(0, 3), 6),
                 ("class skill 5", self.class_strip(5, 3), 6), ("other skill 0", self.class_strip(20, 3), 6),
                 ("class tab", self.class_strip(0), 10), ("level 1", self.class_strip(23, 0), 6), ("level 2", self.class_strip(24, 0), 6),
                 ("class 0", self.class_strip(0, 0), 6), ("Help", self.class_strip(9), 4)]
        if self.PROGRESS:   # class 3: chosen, its tabs, a race chosen, a perk and a skill dragged in and out
            steps += [("class 3", self.class_strip(3, 0), 6), ("class 3 level", self.class_strip(25, 0), 6),
                      ("race tab again", self.class_strip(1), 10), ("Elf", self.class_strip(1, 1), 6),
                      ("perks tab again", self.class_strip(2), 10), ("skills tab again", self.class_strip(3), 10),
                      ("class tab again", self.class_strip(0), 10)]
        before = COVERAGE.get("__ZN10NameScreen6RenderEv", 0)
        for what, (x, y), wait in steps:
            ok &= self.menu_tap(x, y, "class screen %s" % what, cmp)
            if what == "Edit" and not self.s.o.u.mem_read(self.g + self.CLASS + 0xa6c, 1)[0]:
                print("the original's class screen did not open")
                return False
            for f in range(wait):
                self.frame(0, x, y)
                ok &= cmp("class screen after %s frame %d" % (what, f))
            if self.help_open():
                ok &= self.play_help("class screen Help")
        if self.PROGRESS:
            c, u = self.g + self.CLASS, self.s.o.u
            ok &= self.menu_tap(*self.class_strip(2), "class screen perks tab (drags)", cmp)
            for f in range(10):
                self.frame(0, *self.class_strip(2))
                ok &= cmp("class screen perks tab (drags) frame %d" % f)
            free = [k for k in range(20) if u.mem_read(c + 0xa84 + k, 1)[0]]
            if free:   # a perk (or flaw) into the class's second slot, then taken out again and dropped outside
                k = free[0]
                slot = 44 if k < 10 else 48
                ok &= self.drag(self.class_strip(k, 2), self.class_strip(slot, 2), "class screen drag %d in" % k, cmp)
                for f in range(6):
                    self.frame(0, *self.class_strip(slot, 2))
                    ok &= cmp("class screen after drag in frame %d" % f)
                ok &= self.drag(self.class_strip(slot, 2), (0.5, 0.05), "class screen drag %d out" % k, cmp)
                for f in range(6):
                    self.frame(0, 0.5, 0.05)
                    ok &= cmp("class screen after drag out frame %d" % f)
            else:
                print("no perk or flaw can be dragged in")
            ok &= self.menu_tap(*self.class_strip(3), "class screen skills tab (drags)", cmp)
            for f in range(10):
                self.frame(0, *self.class_strip(3))
                ok &= cmp("class screen skills tab (drags) frame %d" % f)
            free = [k for k in range(20) if u.mem_read(c + 0xaac + k, 1)[0]]
            if free:   # another skill onto the class's fourth, then taken out again
                k = free[0]
                ok &= self.drag(self.class_strip(20 + k, 3), self.class_strip(3, 3), "class screen skill %d in" % k, cmp)
                for f in range(6):
                    self.frame(0, *self.class_strip(3, 3))
                    ok &= cmp("class screen after skill in frame %d" % f)
                ok &= self.drag(self.class_strip(3, 3), (0.5, 0.05), "class screen skill %d out" % k, cmp)
                for f in range(6):
                    self.frame(0, 0.5, 0.05)
                    ok &= cmp("class screen after skill out frame %d" % f)
            else:
                print("no skill can be dragged in")
        x, y = self.class_strip(10)
        ok &= self.menu_tap(x, y, "class screen Return", cmp)
        for f in range(20):
            self.frame(0, x, y)
            ok &= cmp("class screen closing frame %d" % f)
        if self.s.o.u.mem_read(self.g + self.CLASS + 0xa6c, 1)[0]:
            print("the original's class screen did not close")
            ok = False
        print("class screen: %d setup screen draws compared, %s" % (COVERAGE.get("__ZN10NameScreen6RenderEv", 0) - before,
                                                                     "all match" if ok else "DIFFERENT"))
        return ok

    def frame(self, phase, x=0.5, y=1.45):
        u = self.s.o.u
        u.mem_write(self.g + 0x10, struct.pack("<iff", phase, x, y))
        self.s.game.frame()
        self.lib.drf_frame(self.b, DT, phase, x, y, -2, -2)   # -2: the skill / menu button as the front end hit-tests it
        self.check_sounds()

    def check_sounds(self):
        """The frame's sound queue (Game+0x13e9c: begin; Game+0x13ea8: the count, emptied as Game::Process begins)
        against the one the front end collected."""
        u, g = self.s.o.u, self.g
        n = struct.unpack("<i", u.mem_read(g + 0x13ea8, 4))[0]
        begin = struct.unpack("<I", u.mem_read(g + 0x13e9c, 4))[0]
        original = list(struct.unpack("<%di" % n, u.mem_read(begin, 4 * n))) if n > 0 else []
        out = (C.c_int32 * 64)()
        m = self.lib.drf_sounds(self.b, out, 64)
        front = list(out[:min(m, 64)])
        SOUNDS[0] += len(original)
        if original != front:
            SOUNDS[1] += 1
            if SOUNDS[1] <= 20:
                print("  sounds differ (frame %d, after %s): original %s, front end %s" % (SOUNDS[2], getattr(self, "last_label", "-"),
                                                                                    original, front))
        SOUNDS[2] += 1
        # EAGLView drawView plays each (GetSoundMapping: RandI(0, recordings - 1, stream 0)); the front end drew the same
        # in its frame
        o = self.s.o
        for sound in original:
            o.call(o.fn("__Z5RandIii8RandType"), 0, RECORDINGS[sound] - 1, 0)

    def idle(self, frames):
        for _ in range(frames):
            self.frame(0)

    # ---- the level-up / shop / upgrade menu (FoldoutMenu, Interface+0xd10 = Game+0x59ec) ------------------------
    MENU = 0x59ec
    def menu_open(self):
        return self.s.o.u.mem_read(self.g + self.MENU + 0x8, 1)[0] != 0

    def menu_tap(self, x, y, label, compare):
        """A touch held two frames and released, then frames until the menu takes input again, comparing each."""
        ok = True
        for phase in (1, 1, 2, 0):
            self.frame(phase, x, y)
            ok &= compare("%s, touch phase %d" % (label, phase))
        return ok

    def play_menu(self, label):
        """Waits for the menu to slide in, chooses the first option (and the second in the level-up menu), confirms,
        and waits for it to close, comparing every frame (as the original lays it out: options 57 points apart from
        (18, 33) in points of 320, the panel at (0.071875, 0.28125); the confirm button at (18, 261), 53 x 35)."""
        u, g = self.s.o.u, self.g
        cmp = lambda what: self.compare(what, quiet=True)
        ok = True
        kind = struct.unpack("<i", u.mem_read(g + self.MENU + 0xc, 4))[0]
        for f in range(60):
            if struct.unpack("<f", u.mem_read(g + self.MENU + 0x24, 4))[0] < 0:
                break
            self.frame(0)
            ok &= cmp("%s, menu %d opening frame %d" % (label, kind, f))
        option_y = lambda k: 0.28125 + (33 + 57 * k + 26) / 320.0
        ok &= self.menu_tap(0.5, option_y(0), "%s, menu %d option 14" % (label, kind), cmp)
        if kind == 0:
            ok &= self.menu_tap(0.5, option_y(1), "%s, menu %d option 15" % (label, kind), cmp)
        ok &= self.menu_tap(0.071875 + 44 / 320.0, 0.28125 + 278 / 320.0, "%s, menu %d confirm" % (label, kind), cmp)
        for f in range(60):
            if not self.menu_open():
                break
            self.frame(0)
            ok &= cmp("%s, menu %d closing frame %d" % (label, kind, f))
        MENUS.append(kind)
        return ok

    # ---- the in-game menu (GameMenu, Interface+0xe24 = Game+0x5b00), opened by Interface's menu button ------------
    GAME_MENU = 0x5b00
    def play_game_menu(self, label, buttons, close=True):
        """Taps the menu button (Interface+0xbd4 at (0.86875, 0.05625)), waits for the fade-in, taps the buttons
        (9 close, 10 sound, 11 help, 12 clock, 13 attack dimming, 14 high frame rate; GameMenu::GameMenu lays them
        out 89 x 26 points from (116, 123 / 157 + 28 k / 303)) and the close button, and waits for the fade-out,
        comparing every frame."""
        u, g = self.s.o.u, self.g
        cmp = lambda what: self.compare(what, quiet=True)
        is_open = lambda: u.mem_read(g + self.GAME_MENU + 0xc, 1)[0] != 0
        timer = lambda: struct.unpack("<f", u.mem_read(g + self.GAME_MENU + 0x1c, 4))[0]
        ok = self.menu_tap(0.86875, 0.05625, "%s, menu button" % label, cmp)
        if not is_open():
            print("%s: the game menu did not open" % label)
            return False
        def wait(what):
            good = True
            for f in range(30):
                if timer() <= 0 or not is_open():
                    break
                self.frame(0)
                good &= cmp("%s, game menu %s frame %d" % (label, what, f))
            return good
        ok &= wait("fade-in")
        top = {9: 123, 15: 303}
        for b in list(buttons) + ([9] if close else []):
            y = top.get(b, 157 + 28 * (b - 10))
            ok &= self.menu_tap((116 + 44.5) / 320, (y + 13) / 320, "%s, game menu button %d" % (label, b), cmp)
        if not close:
            return ok
        ok &= wait("fade-out")
        for f in range(3):
            self.frame(0)
            ok &= cmp("%s, after the game menu %d" % (label, f))
        MENUS.append("game menu")
        return ok

    # ---- the help bubble (HelpMenu, Game+0x10298; open byte Game+0x102a4) ------------------------------------------
    HELP = 0x10298
    def help_open(self):
        return self.s.o.u.mem_read(self.g + self.HELP + 0xc, 1)[0] != 0

    def play_help(self, label):
        """While a help bubble shows: waits for its fade-in, taps its middle (HelpMenu+0x14 position, +0x1c / +0x20 size)
        and waits for it to fade out, comparing every frame; a queued one may follow."""
        u, g = self.s.o.u, self.g
        cmp = lambda what: self.compare(what, quiet=True)
        f32 = lambda off: struct.unpack("<f", u.mem_read(g + self.HELP + off, 4))[0]
        ok = True
        for n in range(30):
            if not self.help_open():
                break
            for f in range(30):
                if f32(0x10) <= 0:
                    break
                self.frame(0)
                ok &= cmp("%s, help %d fade-in frame %d" % (label, n, f))
            x, y, w, h = f32(0x14), f32(0x18), f32(0x1c), f32(0x20)
            ok &= self.menu_tap(x + w / 2, y + h / 2, "%s, help %d tap" % (label, n), cmp)
            for f in range(30):
                if not self.help_open() or (f32(0x10) <= 0 and not u.mem_read(g + self.HELP + 0xd, 1)[0]):
                    break
                self.frame(0)
                ok &= cmp("%s, help %d fade-out frame %d" % (label, n, f))
            HELPS.append(n)
        return ok

    # ---- back to the main menu (MainMenu, Game+0xc3fc; active byte Game+0xc400) and Continue ---------------------------
    def play_main_menu(self, label):
        """The game menu's Exit (the main menu fades in over the game), New game (with a saved game: the box asking to
        overwrite it fades in), No, then Continue (the main menu fades out, the saved game goes on), comparing every
        frame. The buttons' places: MainMenu::MainMenu's quads (New game at (0.228, 0.525), Continue (0.208, 0.353)),
        the box's No (0.247, 0.647)."""
        u, g = self.s.o.u, self.g
        cmp = lambda what: self.compare(what, quiet=True)
        ok = self.play_game_menu(label, (), close=False)
        ok &= self.menu_tap((116 + 44.5) / 320, (303 + 13) / 320, "%s, game menu Exit" % label, cmp)
        for f in range(40):
            self.frame(0)
            ok &= cmp("%s, main menu fade-in frame %d" % (label, f))
        for what, x, y, wait in (("New game", 0.228125, 0.525, 30), ("No", 0.247, 0.647, 30), ("Continue", 0.2078125, 0.353125, 40)):
            ok &= self.menu_tap(x, y, "%s, main menu %s" % (label, what), cmp)
            for f in range(wait):
                self.frame(0, x, y)
                ok &= cmp("%s, after %s frame %d" % (label, what, f))
        if u.mem_read(g + 0xc400, 1)[0]:
            print("%s: the main menu is still open" % label)
            ok = False
        MENUS.append("main menu")
        return ok

    # ---- the stats menu (StatsMenu, Interface+0xeb4 = Game+0x5b90), opened by Interface's stats button --------------
    STATS_MENU = 0x5b90
    def play_stats_menu(self, label, tabs=(10, 11, 12, 13, 14, 15)):
        """Taps the stats button (Interface+0xc44 at (0.86875, 0.14375)), waits for the fade-in, taps the tabs (53
        points square from (23, 63), 57 apart, two to a row: the items 10..14, the class 15), then outside the panel,
        and waits for the fade-out, comparing every frame."""
        u, g = self.s.o.u, self.g
        cmp = lambda what: self.compare(what, quiet=True)
        is_open = lambda: u.mem_read(g + self.STATS_MENU + 0xc, 1)[0] != 0
        timer = lambda: struct.unpack("<f", u.mem_read(g + self.STATS_MENU + 0x1c, 4))[0]
        ok = self.menu_tap(0.86875, 0.14375, "%s, stats button" % label, cmp)
        if not is_open():
            print("%s: the stats menu did not open" % label)
            return False
        def wait(what):
            good = True
            for f in range(30):
                if timer() <= 0 or not is_open():
                    break
                self.frame(0)
                good &= cmp("%s, stats menu %s frame %d" % (label, what, f))
            return good
        ok &= wait("fade-in")
        for t in tabs:
            k = t - 10
            ok &= self.menu_tap((23 + 57 * (k % 2) + 26.5) / 320, (63 + 57 * (k // 2) + 26.5) / 320, "%s, stats tab %d" % (label, t), cmp)
        ok &= self.menu_tap(0.5, 1.45, "%s, outside the stats menu" % label, cmp)
        ok &= wait("fade-out")
        for f in range(3):
            self.frame(0)
            ok &= cmp("%s, after the stats menu %d" % (label, f))
        MENUS.append("stats menu")
        return ok

    # ---- the tooltip (Tooltip, Interface+0x1038 = Game+0x5d14) of a pressed skill button ------------------------------
    def play_skill_tooltip(self, label, slot=0):
        """A touch held on an equipped skill button (Interface::ProcessInput shows its tooltip: name, description,
        cooldown), then let go there (the press ends, the tooltip fades out), comparing every frame. The buttons:
        Interface::GetSkillPosition (0.1015625 + 0.184375 x slot, 0.1015625)."""
        cmp = lambda what: self.compare(what, quiet=True)
        x, y = 0.1015625 + 0.184375 * slot, 0.1015625
        ok = True
        for f in range(40):
            self.frame(1, x, y)
            ok &= cmp("%s, skill %d held frame %d" % (label, slot, f))
        self.frame(2, x, y)
        for f in range(40):
            self.frame(0, x, y)
            ok &= cmp("%s, skill %d let go frame %d" % (label, slot, f))
        print("%s: skill %d tooltip %s" % (label, slot, "the same" if ok else "DIFFERENT"))
        return ok

    # ---- the unlock popup (UnlockMenu, Game+0x164d8; open while Game+0x165a0) ---------------------------------------
    def play_unlock(self, label, kind, level):
        """UnlockMenu::Show(kind, level) as a class scroll calls it (the original's own call; the front end's test hook
        does what the session's UnlockMenu release does), then its fade-in, a tap once fully shown and the fade-out,
        comparing every frame."""
        u, g = self.s.o.u, self.g
        cmp = lambda what: self.compare(what, quiet=True)
        self.s.o.call(self.s.o.fn("__ZN10UnlockMenu4ShowE9ClassTypei"), g + 0x164d8, kind, level)
        self.lib.drf_test_unlock(self.b, kind, level)
        ok = True
        for f in range(30):
            self.frame(0)
            ok &= cmp("%s, unlock %d/%d frame %d" % (label, kind, level, f))
        for phase in (1, 1, 2):
            self.frame(phase, 0.5, 0.75)
            ok &= cmp("%s, unlock tap %d" % (label, phase))
        for f in range(30):
            self.frame(0, 0.5, 0.75)
            ok &= cmp("%s, unlock closing frame %d" % (label, f))
        if u.mem_read(g + 0x165a0, 1)[0] or self.screens()[1]:
            print("%s: the unlock popup is still open" % label)
            ok = False
        print("%s: unlock popup %d/%d %s" % (label, kind, level, "the same" if ok else "DIFFERENT"))
        MENUS.append("unlock %d/%d" % (kind, level))
        return ok

    # ---- the game-over tally (GameOverScreen, Game+0xcac0; open while Game+0xcac4) and the high scores after it ------
    def play_game_over(self, label, every=1):
        """Frames until the tally has faded out over the high-score screen (it counts on its own; no taps), comparing
        every few frames."""
        u, g = self.s.o.u, self.g
        ok, f = True, 0
        while u.mem_read(g + 0xcac4, 1)[0] and f < 60 * 300:
            self.frame(0)
            if f % every == 0:
                ok &= self.compare("%s, game-over frame %d" % (label, f), quiet=True)
            f += 1
        print("%s: the game-over screen closed after %d frames, %s" % (label, f, "the same" if ok else "DIFFERENT"))
        return ok

    def play_scores(self, label):
        """The high scores the game-over screen leaves open (shown from the game: no fade-in): a drag to the next page,
        the left arrow back, the right arrow on again, Back (the main menu fades in over them); then the main menu's
        High scores (a fade-in) and Back again, comparing every frame. The places: ScoreScreen::CreatePage's arrows
        (0.059, 0.2125) / (0.941, 0.2125), the screen's Back (0.85, 1.45), MainMenu's High scores (0.155, 0.864)."""
        cmp = lambda what: self.compare(what, quiet=True)
        ok = True
        for f in range(10):
            self.frame(0)
            ok &= cmp("%s, high scores frame %d" % (label, f))
        xs = [0.8 - 0.1 * i for i in range(7)]
        for i, x in enumerate(xs):
            self.frame(1, x, 0.8)
            ok &= cmp("%s, high scores drag %d" % (label, i))
        self.frame(2, xs[-1], 0.8)
        for f in range(40):
            self.frame(0, xs[-1], 0.8)
            ok &= cmp("%s, high scores after the drag frame %d" % (label, f))
        for what, x, y in (("left arrow", 0.059375, 0.2125), ("right arrow", 0.940625, 0.2125), ("Back", 0.85, 1.45),
                           ("main menu High scores", 0.1546875, 0.8640625), ("Back again", 0.85, 1.45)):
            ok &= self.menu_tap(x, y, "%s, %s" % (label, what), cmp)
            for f in range(40):
                self.frame(0, x, y)
                ok &= cmp("%s, after %s frame %d" % (label, what, f))
        print("%s: high scores played, %s" % (label, "the same" if ok else "DIFFERENT"))
        return ok

# The original drawing functions recovered in frontend/gdext/src/ui (the owner of a draw: the function that called
# Quad::Render, or Label::Render for text).
SCREENS = {"main menu": ("__ZN8MainMenu6RenderEv", 1), "setup": ("__ZN10NameScreen6RenderEv", 2), "story": ("__ZN11IntroScreen6RenderEv", 3),
           "game over": ("__ZN14GameOverScreen6RenderEv", 6), "scores": ("__ZN11ScoreScreen6RenderEv", 5),
           "unlock": ("__ZN10UnlockMenu6RenderEv", 7)}   # (the original's owner, the front end's draw tag: gl.hpp DrawTag)
RECOVERED = {"__ZN7Tooltip6RenderEv", "__ZN10UnlockMenu6RenderEv", "__ZN14GameOverScreen6RenderEv", "__ZN11ScoreScreen6RenderEv", "__ZN8MainMenu6RenderEv", "__ZN10NameScreen6RenderEv", "__ZN11IntroScreen6RenderEv", "__ZN4Tile6RenderEv", "__ZN4Tile10RenderTextEv", "__ZN4Tile13RenderOverlayEv", "__ZN4Tile11RenderCrossEv",
             "__ZN9Interface6RenderEv", "__ZN5Arrow6RenderEv",
             "Game::Render@d4a4", "__ZN9Particles6RenderEv", "Game::Render@d3e6",   # tokens, particles, flares
             "Game::Render@d3a0", "Game::Render@d410", "Game::Render@d41c", "SimpleLabel@d436", "SimpleLabel@d44c",   # attack
             "Game::Render@d58c", "Game::Render@d598",   # the shield shatter
             "__ZN11FoldoutMenu6RenderEv",               # the level-up, shop and upgrade menus
             "__ZN8GameMenu6RenderEv",                   # the in-game menu
             "__ZN9StatsMenu6RenderEv",                  # the stats menu
             "__ZN8HelpMenu6RenderEv",                   # the help bubble
             "SimpleLabel@d520", "SimpleLabel@d560",   # the cross labels, Game::AddSimpleLabel's pool
             "SimpleLabel@d5c4", "SimpleLabel@d5e8", "SimpleLabel@d60a", "SimpleLabel@d62c"}   # current, leech, flame, spike
# Game::Render draws several of its own quads (tokens, the attack flash, shield chunks, attack visuals): those draws
# are named by the return address of their Quad::Render call.


STROKE_TURNS = int(os.environ.get("STROKE_TURNS", "12"))
CHALLENGE = int(os.environ["CHALLENGE"]) if os.environ.get("CHALLENGE", "") in ("0", "1") else None   # a challenge game of that mode
CLASS_SCREEN = os.environ.get("CLASS_SCREEN", "0") == "1"   # the setup screen's class screen pass (lockstep.py: CLASS_SCREEN=1)   # turns whose strokes are compared at every tile
AFTER_RELEASE = tuple(range(1, 240))   # frames after a release that are compared (printed for the first turns)
COVERAGE = {}   # compared original draws by owner
SOUNDS = [0, 0, 0]   # sounds the original queued, frames whose queues differed, frames
RECORDINGS = [1, 3, 3, 3, 3, 3, 3, 3, 3, 3, 1, 1, 1, 1, 3, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 3, 3, 3, 1, 4, 1, 1, 1, 1, 1]   # GetSoundVariations
MENUS = []      # the menus played (0 level-up, 1 shop, 2 upgrade)
HELPS = []      # the help bubbles closed


def owner(d):
    c = d["callers"]
    for whole in ("__ZN11FoldoutMenu6RenderEv", "__ZN9StatsMenu6RenderEv", "__ZN8HelpMenu6RenderEv", "__ZN10NameScreen6RenderEv",
                  "__ZN9Interface6RenderEv", "__ZN14GameOverScreen6RenderEv", "__ZN11ScoreScreen6RenderEv",
                  "__ZN10UnlockMenu6RenderEv", "__ZN7Tooltip6RenderEv"):   # with their icons and labels
        if whole in c:
            return whole
    if c[0] == "__ZN4Quad6RenderEv" and len(c) > 1:
        if c[1] == "__ZN5Label6RenderEv" and len(c) > 2:
            return c[2]
        if c[1] == "__ZN4Game6RenderEv":
            return "Game::Render@%x" % d["sites"][1]
        return c[1]
    if c[0] == "__ZN11SimpleLabel6RenderEv" and len(c) > 1 and c[1] == "__ZN4Game6RenderEv":
        return "SimpleLabel@%x" % d["sites"][1]
    return c[0]


def diff(ob, bb):
    names = ("type", "special", "enemy", "state", "variant", "glow")
    for i in range(36):
        o, b = ob[N * i:N * i + N], bb[N * i:N * i + N]
        if o != b:
            print("  tile %d: %s" % (i, ", ".join("%s %d/%d" % (names[k], o[k], b[k]) for k in range(N) if o[k] != b[k])))


def main():
    turns = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    ls = Lockstep()
    ls.begin()
    same = ls.original_board() == ls.bridge_board()
    print("board after the story screen: %s" % ("same" if same else "DIFFERENT"))
    if not same:
        diff(ls.original_board(), ls.bridge_board())
    ls.idle(60)
    ok = ls.compare("board") and ls.begin_ok
    ok &= ls.play_game_menu("start", (12, 13, 10, 14, 12, 10, 14, 11))   # clock on, dimming on, sound off, ... and back; help on
    ok &= ls.play_help("start")
    ok &= ls.play_stats_menu("start")
    ok &= ls.play_unlock("start", 3, 1)   # (the unlock popup: class 3 unlocked)
    for turn in range(turns):
        frame = ls.s.game.render()
        path = of.longest_path(of.board_from(frame))
        if len(path) < 3:
            break
        ok &= ls.play_help("turn %d" % turn)
        for n, t in enumerate(path):
            for _ in range(3):
                ls.frame(1, t["x"], t["y"])
            if n >= 1 and turn < STROKE_TURNS:
                ok &= ls.compare("turn %d, stroke at tile %d" % (turn, n), quiet=True)
        ls.frame(2, path[-1]["x"], path[-1]["y"])
        for f in range(240):
            if ls.menu_open():
                ok &= ls.play_menu("turn %d" % turn)
            if ls.help_open():
                ok &= ls.play_help("turn %d" % turn)
            ls.frame(0)
            if f in AFTER_RELEASE:
                ok &= ls.compare("turn %d, %d frames after release" % (turn, f), quiet=turn >= 3 or f not in (5, 20))
        ok &= ls.compare("turn %d, idle" % turn)
        if turn == 4:
            ok &= ls.play_game_menu("turn %d" % turn, (13,))   # attack dimming off again (the next attacks undimmed)
        if turn in (8, 30):
            ok &= ls.play_main_menu("turn %d" % turn)
        if turn == 10:
            ok &= ls.play_unlock("turn %d" % turn, 0, 2)   # (the unlock popup: class 0 levels up)
        if turn in (30, 50):   # (equipped skills by then)
            ok &= ls.play_skill_tooltip("turn %d" % turn, 0 if turn == 30 else 1)
        if turn in (6, 20, 40):
            ok &= ls.play_stats_menu("turn %d" % turn, (15, 10, 12, 14, 11, 13))
        ob, bb = ls.original_board(), ls.bridge_board()
        print("turn %d: %d-tile path; board %s; bridge counters %s" % (turn, len(path), "same" if ob == bb else "DIFFERENT", ls.counters()))
        if ob != bb:
            diff(ob, bb)
            return 1
        if ls.s.o.u.mem_read(ls.g + 0xcac4, 1)[0]:   # the game ended: the tally, then the high scores
            print("the game ended at turn %d" % turn)
            ok &= ls.play_game_over("turn %d" % turn, int(os.environ.get("GAME_OVER_EVERY", "1")))
            ok &= ls.play_scores("turn %d" % turn)
            break
    print("compared: " + ", ".join("%s %d" % (k, v) for k, v in sorted(COVERAGE.items())))
    print("sounds: %d queued by the original in %d frames, %d frames differ" % (SOUNDS[0], SOUNDS[2], SOUNDS[1]))
    print("menus played: %s" % (MENUS or "none"))
    print("help bubbles closed: %d" % len(HELPS))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
