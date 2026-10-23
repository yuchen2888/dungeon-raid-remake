#!/usr/bin/env python3
"""Lists what one original function does directly while the original runs in the emulator (T050-A, a reading aid
for recovering the drawing code): the calls it makes (callee, arguments: object offsets, floats, the floats behind
GLfloat2 / GLcolour4 references, strings) and the stores it makes itself (offset in the object, value).

  python3 frontend/tools/trace_function.py '__ZN9InterfaceC2EP4Game' [start|newgame|board|stroke|menu|menu0|menu1|menu2]

The function is traced the first time it runs on the way to the chosen point (start-up, a new game's board, the
first menu that opens; menu0 / menu1 / menu2 open that FoldoutMenu type after four turns); TRACE_SKIP=n skips its first n runs, TRACE_STACK=n shows n stack arguments (default 2).
"""
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import original_frame as of  # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE  # noqa: E402
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC  # noqa: E402


def u8(o, address):
    return o.u.mem_read(address, 1)[0]


def demangle(names):
    out = subprocess.run(["c++filt"], input="\n".join(names), capture_output=True, text=True).stdout.split("\n")
    return dict(zip(names, out))


class Tracer:
    def __init__(self, o, target):
        self.o = o
        self.target = o.fn(target)
        starts = sorted({v & ~1 for n, t, s, v in o.m.symbols if s == 1 and t & 0x0e == 0x0e})
        i = starts.index(self.target & ~1)
        self.end = starts[i + 1]
        self.active = False
        self.done = False
        self.skip = int(os.environ.get("TRACE_SKIP", "0"))
        self.stack = int(os.environ.get("TRACE_STACK", "2"))
        self.this = None
        self.lines = []
        o.u.hook_add(UC_HOOK_CODE, self.code, begin=0x1000, end=0x195000)
        o.u.hook_add(UC_HOOK_MEM_WRITE, self.store)

    def describe(self, v):
        o, g = self.o, getattr(self, "game", None)
        if self.this is not None and self.this <= v < self.this + 0x4000:
            return "this+0x%x" % (v - self.this)
        if g is not None and g <= v < g + of.GAME_SIZE:
            return "game+0x%x" % (v - g)
        if of.STACK <= v < of.STACK + of.STACK_SIZE:
            raw = bytes(o.u.mem_read(v, 8))
            a, b = struct.unpack("<ff", raw)
            text = raw.split(b"\0")[0]
            c = tuple(raw[:4])
            return "&(%.9g, %.9g | rgba %s)" % (a, b, c)
        if 0x1000 <= v < 0x200000 or of.HEAP <= v < of.HEAP + 0x4000000:
            try:
                s = o.cstr(v, 80)
                if s and all(32 <= ch < 127 for ch in s):
                    return repr(s.decode())
            except Exception:
                pass
        f = of.f32(v)
        if v and 1e-6 < abs(f) < 1e6 and (v & 0xff) != v:
            return "%d|%.9g" % (struct.unpack("<i", struct.pack("<I", v))[0], f)
        return "%d" % struct.unpack("<i", struct.pack("<I", v))[0]

    def code(self, u, address, size, data):
        if self.done:
            return
        if not self.active:
            if address == self.target & ~1:
                if self.skip > 0:
                    self.skip -= 1
                    return
                self.active = True
                self.this = u.reg_read(UC_ARM_REG_R0)
                self.sp = u.reg_read(UC_ARM_REG_SP)
                self.ret = u.reg_read(UC_ARM_REG_LR) & ~1
            return
        if address == self.ret and u.reg_read(UC_ARM_REG_SP) >= self.sp:
            self.active = False
            self.done = True
            return
        lr = u.reg_read(UC_ARM_REG_LR) & ~1
        if self.target & ~1 <= lr - 4 < self.end and address != lr and not (self.target & ~1 <= address < self.end):
            # entering a function called directly from the target (its return address is inside the target)
            if self.last_call == lr:
                return
            self.last_call = lr
            sp = u.reg_read(UC_ARM_REG_SP)
            args = [u.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)]
            args += [self.o.r32(sp + 4 * k) for k in range(self.stack)]
            name = self.o.functions.get(address) or self.o.function_at(address)
            self.lines.append(("call", lr, name, [self.describe(a) for a in args]))
        elif self.target & ~1 <= address < self.end:
            self.last_call = None

    last_call = None

    def store(self, u, access, address, size, value, data):
        if not self.active:
            return
        pc = u.reg_read(UC_ARM_REG_PC)
        if not (self.target & ~1 <= pc < self.end):
            return
        if of.STACK <= address < of.STACK + of.STACK_SIZE:
            return
        v = value & ((1 << (8 * size)) - 1)
        self.lines.append(("store", pc, self.describe(address), size, v))


def main():
    target = sys.argv[1]
    point = sys.argv[2] if len(sys.argv) > 2 else "start"
    o = of.Original()
    t = Tracer(o, target)
    g = of.Game.__new__(of.Game)
    g.o = o
    g.g = o.alloc(of.GAME_SIZE)
    t.game = g.g
    for f in o.m.init_functions():
        o.call(f)
    o.call(o.fn("__ZN4GameC1Ev"), g.g)
    font = lambda n: o.put_cstr(os.path.join(of.ASSETS, n))
    o.call(o.fn("__ZN4Game10CreateFontEPKcS1_S1_"), g.g, font("font.fnt"), font("fontMenu.fnt"), font("fontScore.fnt"))
    o.call(o.fn("__ZN4Game5StartEb"), g.g, 1)
    o.call(o.fn("__ZN4Game13SetupRendererEv"), g.g)
    if point != "start" and not t.done:
        s = of.Script.__new__(of.Script)
        s.o, s.game, s.frames = o, g, []
        s.run(30)
        s.tap(0.22, 0.53)
        s.tap(0.86, 0.145)
        s.run(120)
        s.tap(0.5, 1.41)
        if point in ("board", "stroke", "menu", "menu0", "menu1", "menu2"):
            s.run(180)
            s.tap(0.5, 1.41)
            s.run(60)
        if point == "stroke":   # press and drag through the first long path of the board
            tiles = of.longest_path(of.board_from(g.render()))[:3]
            g.touch(1, tiles[0]["x"], tiles[0]["y"])
            s.run(3)
            for tt in tiles[1:]:
                g.touch(2, tt["x"], tt["y"])
                s.run(3)
    if point in ("menu0", "menu1", "menu2"):   # a few turns, then FoldoutMenu::Initialise(type) on Interface+0xd10
        for _ in range(4):
            if not s.play_turn():
                break
            s.run(240)
        o.call(o.fn("__ZN11FoldoutMenu10InitialiseE8MenuType"), g.g + 0x4cdc + 0xd10, int(point[-1]))
        s.run(40)
    if point == "menu":   # strokes until the level-up menu opens (Game+0x59f4), then its opening frames
        for _ in range(60):
            if t.done or u8(o, g.g + 0x59f4):
                break
            if not s.play_turn():
                break
            s.run(240)
        s.run(30)
    names = demangle(sorted({l[2] for l in t.lines if l[0] == "call"}))
    where = "this = game+0x%x" % (t.this - g.g) if t.this and g.g <= t.this < g.g + of.GAME_SIZE else "this = %s" % (hex(t.this) if t.this else None)
    print("# %s (%s), %d calls / stores" % (demangle([target])[target], where, len(t.lines)))
    for l in t.lines:
        if l[0] == "call":
            print("%05x  %s(%s)" % (l[1], names.get(l[2], l[2]), ", ".join(l[3])))
        else:
            print("%05x  [%s] = %s (%d bytes)" % (l[1], l[2], t.describe(l[4]) if l[3] == 4 else l[4], l[3]))


if __name__ == "__main__":
    main()
