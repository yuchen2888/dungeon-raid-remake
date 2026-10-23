#!/usr/bin/env python3
"""Runs the original game's own start-up, frame and render code in the Unicorn emulator and records what it draws
(T050-A: the reference for the front end's look; original instructions are used only to measure, never shipped).

The original program (DungeonRaid-original, ARMv7 slice, local only) runs as the iOS app does it (EAGLView
initWithCoder: and drawView:): Game::Game, the settings, Game::CreateFont with the local .fnt files, Game::Start,
then per frame Game::Process and Game::Render, touches through Game::TouchStart / TouchDrag / TouchEnd. The system
libraries it imports are modelled here (memory, C strings, sprintf / sscanf, the libstdc++ string, red-black tree
and list helpers, math, time); Objective-C messages return 0; OpenGL ES 1.1 calls are recorded: every glDrawArrays
becomes a draw (texture, blend, vertices in screen units after the model-view matrix, texture coordinates,
colours). Textures are the original's fixed names (GetTextureName: 1 tiles, 2 font, 3 icons, 4 menus, 5 fontMenu,
6 fontScore).

  python3 frontend/tools/original_frame.py main_menu out.json      the main menu after start-up
"""
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED, UC_PROT_ALL  # noqa: E402
from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_R7,  # noqa: E402
                               UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_C1_C0_2, UC_ARM_REG_FPEXC)

PROGRAM = os.path.join(ROOT, "DungeonRaid-original")
ASSETS = os.path.join(ROOT, "frontend", "godot", "assets", "original")
TEXTURES = {1: "tiles", 2: "font", 3: "icons", 4: "menus", 5: "fontMenu", 6: "fontScore"}
GAME_SIZE = 0x16614
IMPORTS, IMPORT_SIZE = 0x30000000, 0x100000      # one fake address per imported symbol (functions trap there)
DATA, DATA_SIZE = 0x31000000, 0x1000000          # storage for imported data symbols
HEAP, HEAP_SIZE = 0x4a5a0000, 0x8000000   # (no common float has these bits, so pointers and floats read apart)
STACK, STACK_SIZE = 0x7f000000, 0x100000
STOP = 0x7e000000
R = [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3]
GL_TEXTURE_2D, GL_BLEND = 0xde1, 0xbe2
GL_VERTEX_ARRAY, GL_COLOR_ARRAY, GL_TEXTURE_COORD_ARRAY = 0x8074, 0x8076, 0x8078
GL_MODELVIEW, GL_PROJECTION = 0x1700, 0x1701


def f32(bits):
    return struct.unpack("<f", struct.pack("<I", bits & 0xffffffff))[0]


def bits32(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


class MachO:
    """The ARMv7 slice: segments, sections, symbols and the indirect (imported) symbol slots."""
    def __init__(self, path):
        data = open(path, "rb").read()
        magic, n = struct.unpack(">II", data[:8])
        assert magic == 0xcafebabe
        for i in range(n):
            cpu, sub, off, size, _ = struct.unpack(">5I", data[8 + 20 * i:28 + 20 * i])
            if cpu == 12 and sub == 9:
                self.d = data[off:off + size]
        ncmds = struct.unpack_from("<I", self.d, 16)[0]
        p = 28
        self.segments, self.sections = [], []
        symoff = nsyms = stroff = indoff = nind = 0
        for _ in range(ncmds):
            cmd, sz = struct.unpack_from("<II", self.d, p)
            if cmd == 1:
                name = self.d[p + 8:p + 24].split(b"\0")[0].decode()
                vmaddr, vmsize, fileoff, filesize, _, _, nsects, _ = struct.unpack_from("<8I", self.d, p + 24)
                self.segments.append((name, vmaddr, vmsize, fileoff, filesize))
                q = p + 56
                for _ in range(nsects):
                    sect = self.d[q:q + 16].split(b"\0")[0].decode()
                    addr, size, offset, align, reloff, nreloc, flags, res1, res2 = struct.unpack_from("<9I", self.d, q + 32)
                    self.sections.append(dict(name=sect, addr=addr, size=size, offset=offset, flags=flags, res1=res1, res2=res2))
                    q += 68
            elif cmd == 2:
                symoff, nsyms, stroff, _ = struct.unpack_from("<4I", self.d, p + 8)
            elif cmd == 0xb:
                vals = struct.unpack_from("<18I", self.d, p + 8)
                indoff, nind = vals[12], vals[13]
            p += sz
        self.symbols = []
        for i in range(nsyms):
            strx, ntype, nsect, desc, value = struct.unpack_from("<IBBHI", self.d, symoff + 12 * i)
            e = self.d.index(b"\0", stroff + strx)
            self.symbols.append((self.d[stroff + strx:e].decode("latin1"), ntype, nsect, value))
        self.indirect = [struct.unpack_from("<I", self.d, indoff + 4 * i)[0] for i in range(nind)]

    def imported_slots(self):
        """(slot address, symbol name) of every lazy / non-lazy pointer."""
        out = []
        for s in self.sections:
            kind = s["flags"] & 0xff
            if kind in (6, 7):
                for k in range(s["size"] // 4):
                    idx = self.indirect[s["res1"] + k]
                    if idx & 0xc0000000:
                        continue
                    out.append((s["addr"] + 4 * k, self.symbols[idx][0]))
        return out

    def init_functions(self):
        out = []
        for s in self.sections:
            if s["flags"] & 0xff == 9:
                out += [struct.unpack_from("<I", self.d, s["offset"] + 4 * k)[0] for k in range(s["size"] // 4)]
        return out

    def address(self, name):
        for n, t, sect, v in self.symbols:
            if n == name and sect:
                return v
        raise KeyError(name)


class Original:
    def __init__(self):
        self.m = MachO(PROGRAM)
        u = self.u = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
        for name, vmaddr, vmsize, fileoff, filesize in self.m.segments:
            if not vmsize or name == "__PAGEZERO":
                continue
            start, end = vmaddr & ~0xfff, (vmaddr + vmsize + 0xfff) & ~0xfff
            u.mem_map(start, end - start, UC_PROT_ALL)
            u.mem_write(vmaddr, self.m.d[fileoff:fileoff + filesize])
        for base, size in [(IMPORTS, IMPORT_SIZE), (DATA, DATA_SIZE), (HEAP, HEAP_SIZE), (STACK, STACK_SIZE), (STOP, 0x1000)]:
            u.mem_map(base, size, UC_PROT_ALL)
        u.reg_write(UC_ARM_REG_C1_C0_2, u.reg_read(UC_ARM_REG_C1_C0_2) | (0xf << 20))   # VFP on
        u.reg_write(UC_ARM_REG_FPEXC, 0x40000000)
        self.heap = HEAP
        self.data = DATA
        self.functions = {}       # fake address -> name
        self.data_symbols = {}
        names = {}
        for slot, name in self.m.imported_slots():
            if name not in names:
                if self.is_data(name):
                    names[name] = self.data_symbol(name)
                else:
                    names[name] = IMPORTS + 4 * len(self.functions)
                    self.functions[names[name]] = name
            self.w32(slot, names[name])
        u.hook_add(UC_HOOK_CODE, self.trap, begin=IMPORTS, end=IMPORTS + IMPORT_SIZE)
        u.hook_add(UC_HOOK_MEM_UNMAPPED, self.unmapped)
        self.files = {}
        self.clock = 0
        self.unknown = {}
        self.gl_reset()

    # ---- memory ---------------------------------------------------------------------------------------
    def r32(self, a): return struct.unpack("<I", self.u.mem_read(a, 4))[0]
    def w32(self, a, v): self.u.mem_write(a, struct.pack("<I", v & 0xffffffff))
    def rf(self, a): return struct.unpack("<f", self.u.mem_read(a, 4))[0]
    def cstr(self, a, limit=4096):
        out = bytearray()
        while len(out) < limit:
            b = self.u.mem_read(a + len(out), 64)
            i = b.find(b"\0")
            if i >= 0:
                out += b[:i]
                break
            out += b
        return bytes(out)
    def alloc(self, n, align=16):
        self.heap = (self.heap + align - 1) & ~(align - 1)
        a = self.heap
        self.heap += max(n, 1)
        if self.heap > HEAP + HEAP_SIZE:
            raise MemoryError("emulated heap exhausted")
        self.u.mem_write(a, b"\0" * max(n, 1))
        return a
    def put_cstr(self, s):
        b = s.encode("latin1") if isinstance(s, str) else s
        a = self.alloc(len(b) + 1)
        self.u.mem_write(a, b + b"\0")
        return a

    def is_data(self, name):
        return name in ("__ZNSs4_Rep20_S_empty_rep_storageE", "__DefaultRuneLocale", "___stack_chk_guard", "___sF") or \
            name.startswith("_OBJC_CLASS_$_") or name.startswith("_OBJC_METACLASS_$_") or name.startswith("__ZTV") or \
            name.startswith("__ZTI") or name.startswith("_kCA") or name.startswith("_NS") or name.startswith("_UI") or \
            name.startswith("_kCF") or name.startswith("_kAudio") or name.startswith("__NSConcrete") or name == "___CFConstantStringClassReference"

    def data_symbol(self, name):
        size = 0x2000 if name == "__DefaultRuneLocale" else 0x400
        a = self.data
        self.data += size
        self.data_symbols[name] = a
        if name == "__DefaultRuneLocale":   # __runetype[256] at +0x34 (Apple's _RuneLocale)
            for c in range(256):
                self.w32(a + 0x34 + 4 * c, ctype_bits(c))
        return a

    def unmapped(self, u, access, address, size, value, data):
        pc = u.reg_read(UC_ARM_REG_PC)
        print("unmapped access 0x%x (size %d) at pc 0x%x lr 0x%x" % (address, size, pc, u.reg_read(UC_ARM_REG_LR)), file=sys.stderr)
        return False

    # ---- calls ----------------------------------------------------------------------------------------
    def arg(self, i):
        if i < 4:
            return self.u.reg_read(R[i])
        return self.r32(self.u.reg_read(UC_ARM_REG_SP) + 4 * (i - 4))

    def call(self, address, *args, count=0):
        u = self.u
        sp = STACK + STACK_SIZE - 0x100
        extra = list(args[4:])
        sp -= 4 * len(extra)
        for i, v in enumerate(extra):
            self.w32(sp + 4 * i, v)
        for i, v in enumerate(args[:4]):
            u.reg_write(R[i], v & 0xffffffff)
        u.reg_write(UC_ARM_REG_SP, sp)
        u.reg_write(UC_ARM_REG_LR, STOP | 1)
        try:
            u.emu_start(address | 1 if not address & 1 else address, STOP, count=count)
        except UcError as e:
            raise RuntimeError("emulation failed at pc 0x%x lr 0x%x: %s" % (u.reg_read(UC_ARM_REG_PC), u.reg_read(UC_ARM_REG_LR), e))
        return u.reg_read(UC_ARM_REG_R0)

    def fn(self, name):
        return self.m.address(name)

    def ret(self, value=None, double=None):
        u = self.u
        if double is not None:
            lo, hi = struct.unpack("<II", struct.pack("<d", double))
            u.reg_write(UC_ARM_REG_R0, lo)
            u.reg_write(UC_ARM_REG_R1, hi)
        elif value is not None:
            u.reg_write(UC_ARM_REG_R0, value & 0xffffffff)
        u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))

    def trap(self, u, address, size, data):
        name = self.functions.get(address)
        if name is None:
            raise RuntimeError("jump to unknown import address 0x%x" % address)
        handler = getattr(self, "f" + name.replace("$", "_").replace(".", "_"), None)
        if handler is None:
            handler = LIBC.get(name)
            if handler is None:
                if name.startswith("_objc_msgSend") or name.startswith("_gl") or name.startswith("_OF") or name.startswith("_CF") \
                        or name.startswith("_NS") or name.startswith("_UI") or name.startswith("_Audio") or name.startswith("_al"):
                    self.unknown[name] = self.unknown.get(name, 0) + 1
                    self.ret(0)
                    return
                raise RuntimeError("unmodelled import %s (lr 0x%x)" % (name, u.reg_read(UC_ARM_REG_LR)))
            handler(self)
            return
        handler()

    # ---- libc / libstdc++ ------------------------------------------------------------------------------
    def f__Znwm(self): self.ret(self.alloc(self.arg(0)))
    f__Znam = f__Znwm
    def f_malloc(self): self.ret(self.alloc(self.arg(0)))
    def f_calloc(self): self.ret(self.alloc(self.arg(0) * self.arg(1)))
    def f_realloc(self):
        old, n = self.arg(0), self.arg(1)
        a = self.alloc(n)
        if old:
            self.u.mem_write(a, bytes(self.u.mem_read(old, n)))
        self.ret(a)
    def f__ZdlPv(self): self.ret()
    f__ZdaPv = f__ZdlPv
    f_free = f__ZdlPv
    def f_memcpy(self):
        d, s, n = self.arg(0), self.arg(1), self.arg(2)
        if n:
            self.u.mem_write(d, bytes(self.u.mem_read(s, n)))
        self.ret(d)
    f_memmove = f_memcpy
    def f_memset(self):
        d, c, n = self.arg(0), self.arg(1), self.arg(2)
        if n:
            self.u.mem_write(d, bytes([c & 0xff]) * n)
        self.ret(d)
    def f_bzero(self):
        d, n = self.arg(0), self.arg(1)
        if n:
            self.u.mem_write(d, b"\0" * n)
        self.ret()
    def f_memcmp(self):
        a, b, n = self.arg(0), self.arg(1), self.arg(2)
        x, y = bytes(self.u.mem_read(a, n)), bytes(self.u.mem_read(b, n))
        self.ret(0 if x == y else (-1 if x < y else 1))
    def f_strlen(self): self.ret(len(self.cstr(self.arg(0))))
    def f_strcpy(self):
        d, s = self.arg(0), self.arg(1)
        self.u.mem_write(d, self.cstr(s) + b"\0")
        self.ret(d)
    def f_strncpy(self):
        d, s, n = self.arg(0), self.arg(1), self.arg(2)
        b = self.cstr(s)[:n]
        self.u.mem_write(d, b + b"\0" * (n - len(b)))
        self.ret(d)
    def f_strcat(self):
        d, s = self.arg(0), self.arg(1)
        self.u.mem_write(d + len(self.cstr(d)), self.cstr(s) + b"\0")
        self.ret(d)
    def f_strcmp(self):
        a, b = self.cstr(self.arg(0)), self.cstr(self.arg(1))
        self.ret(0 if a == b else (-1 if a < b else 1))
    def f_strncmp(self):
        n = self.arg(2)
        a, b = self.cstr(self.arg(0))[:n], self.cstr(self.arg(1))[:n]
        self.ret(0 if a == b else (-1 if a < b else 1))
    def f_sprintf(self):
        out = self.format(self.arg(1), 2)
        self.u.mem_write(self.arg(0), out + b"\0")
        self.ret(len(out))
    def f_snprintf(self):
        out = self.format(self.arg(2), 3)
        n = self.arg(1)
        if n:
            self.u.mem_write(self.arg(0), out[:n - 1] + b"\0")
        self.ret(len(out))
    def format(self, fmt_addr, first):
        fmt = self.cstr(fmt_addr).decode("latin1")
        i, k, out = 0, first, []
        while i < len(fmt):
            c = fmt[i]
            if c != "%":
                out.append(c)
                i += 1
                continue
            j = i + 1
            while j < len(fmt) and fmt[j] in "-+ #0123456789.lhqz":
                j += 1
            spec, conv = fmt[i:j], fmt[j]
            i = j + 1
            if conv == "%":
                out.append("%")
                continue
            flags = spec.replace("l", "").replace("h", "").replace("q", "").replace("z", "")
            if conv in "di":
                out.append((flags + "d") % struct.unpack("<i", struct.pack("<I", self.arg(k)))[0])
                k += 1
            elif conv in "uxXoc":
                out.append((flags + conv) % self.arg(k))
                k += 1
            elif conv == "s":
                out.append((flags + "s") % self.cstr(self.arg(k)).decode("latin1"))
                k += 1
            elif conv in "feEgG":
                lo, hi = self.arg(k), self.arg(k + 1)
                out.append((flags + conv) % struct.unpack("<d", struct.pack("<II", lo, hi))[0])
                k += 2
            else:
                raise RuntimeError("sprintf conversion %" + conv)
        return "".join(out).encode("latin1")
    def f_sscanf(self):
        text = self.cstr(self.arg(0)).decode("latin1")
        fmt = self.cstr(self.arg(1)).decode("latin1")
        k, pos, i, count = 2, 0, 0, 0
        while i < len(fmt):
            c = fmt[i]
            if c.isspace():
                while pos < len(text) and text[pos].isspace():
                    pos += 1
                i += 1
                continue
            if c != "%":
                if pos >= len(text) or text[pos] != c:
                    break
                pos += 1
                i += 1
                continue
            j = i + 1
            while fmt[j] in "0123456789l":
                j += 1
            conv = fmt[j]
            i = j + 1
            if conv != "c":
                while pos < len(text) and text[pos].isspace():
                    pos += 1
            start = pos
            if conv in "di":
                if pos < len(text) and text[pos] in "+-":
                    pos += 1
                while pos < len(text) and text[pos].isdigit():
                    pos += 1
                if pos == start:
                    break
                self.w32(self.arg(k), int(text[start:pos]))
            elif conv == "f":
                while pos < len(text) and (text[pos].isdigit() or text[pos] in "+-.eE"):
                    pos += 1
                if pos == start:
                    break
                self.w32(self.arg(k), bits32(float(text[start:pos])))
            elif conv == "s":
                while pos < len(text) and not text[pos].isspace():
                    pos += 1
                self.u.mem_write(self.arg(k), text[start:pos].encode("latin1") + b"\0")
            elif conv == "c":
                self.u.mem_write(self.arg(k), text[pos].encode("latin1"))
                pos += 1
            else:
                raise RuntimeError("sscanf conversion %" + conv)
            k += 1
            count += 1
        self.ret(count)
    def f_fopen(self):
        path = self.cstr(self.arg(0)).decode("latin1")
        if not os.path.exists(path):
            self.ret(0)
            return
        h = 0x100 + len(self.files)
        self.files[h] = open(path, "rb").read().split(b"\n")
        self.files[h] = [line + b"\n" for line in self.files[h]]
        self.ret(h)
    def f_fgets(self):
        buf, n, h = self.arg(0), self.arg(1), self.arg(2)
        lines = self.files.get(h)
        if not lines:
            self.ret(0)
            return
        line = lines.pop(0)[:n - 1]
        self.u.mem_write(buf, line + b"\0")
        self.ret(buf)
    def f_fclose(self):
        self.files.pop(self.arg(0), None)
        self.ret(0)
    def f_time(self):
        if self.arg(0):
            self.w32(self.arg(0), 1287619200)
        self.ret(1287619200)
    def f_mach_absolute_time(self):
        lo, hi = self.clock & 0xffffffff, self.clock >> 32
        self.u.reg_write(UC_ARM_REG_R1, hi)
        self.ret(lo)
    def f_mach_timebase_info(self):
        self.w32(self.arg(0), 1)
        self.w32(self.arg(0) + 4, 1)
        self.ret(0)
    def f___floatundidf(self):
        self.ret(double=float(self.arg(0) | (self.arg(1) << 32)))
    def f___divsi3(self):
        a, b = (struct.unpack("<i", struct.pack("<I", self.arg(i)))[0] for i in (0, 1))
        q = abs(a) // abs(b) * (1 if (a < 0) == (b < 0) else -1)
        self.ret(q)
    def f___modsi3(self):
        a, b = (struct.unpack("<i", struct.pack("<I", self.arg(i)))[0] for i in (0, 1))
        q = abs(a) // abs(b) * (1 if (a < 0) == (b < 0) else -1)
        self.ret(a - q * b)
    def f___udivsi3(self): self.ret(self.arg(0) // self.arg(1))
    def f___umodsi3(self): self.ret(self.arg(0) % self.arg(1))
    def f___toupper(self):
        c = self.arg(0)
        self.ret(ord(chr(c).upper()) if c < 128 else c)
    def f___tolower(self):
        c = self.arg(0)
        self.ret(ord(chr(c).lower()) if c < 128 else c)
    def f___maskrune(self): self.ret(ctype_bits(self.arg(0)) & self.arg(1))
    def mathf(self, fn):
        self.ret(bits32(fn(f32(self.arg(0)))))
    def f_cosf(self): self.mathf(math.cos)
    def f_sinf(self): self.mathf(math.sin)
    def f_floorf(self): self.mathf(math.floor)
    def f_ceilf(self): self.mathf(math.ceil)
    def f_sqrtf(self): self.mathf(math.sqrt)
    def f_fabsf(self): self.mathf(abs)
    def f_powf(self): self.ret(bits32(math.pow(f32(self.arg(0)), f32(self.arg(1)))))
    def f_atan2f(self): self.ret(bits32(math.atan2(f32(self.arg(0)), f32(self.arg(1)))))
    def f_fmodf(self): self.ret(bits32(math.fmod(f32(self.arg(0)), f32(self.arg(1)))))
    def f__Unwind_SjLj_Register(self): self.ret()
    f__Unwind_SjLj_Unregister = f__Unwind_SjLj_Register
    def f___cxa_guard_acquire(self):
        g = self.arg(0)
        first = self.u.mem_read(g, 1)[0] == 0
        self.ret(1 if first else 0)
    def f___cxa_guard_release(self):
        self.u.mem_write(self.arg(0), b"\1")
        self.ret()
    def f___cxa_atexit(self): self.ret(0)
    def f___stack_chk_fail(self): raise RuntimeError("stack check failed")
    def f_srand(self): self.ret()
    def f_rand(self): self.ret(0)
    def f_random(self): self.ret(0)
    def f_srandom(self): self.ret()
    # std::string (libstdc++ copy-on-write): the object holds the character pointer; length, capacity and the
    # reference count sit in the 12 bytes before it. Every string here gets its own representation.
    def new_string(self, b):
        rep = self.alloc(12 + len(b) + 1)
        self.w32(rep, len(b))
        self.w32(rep + 4, len(b))
        self.w32(rep + 8, 0)
        self.u.mem_write(rep + 12, b + b"\0")
        return rep + 12
    def string_bytes(self, obj):
        p = self.r32(obj)
        return bytes(self.u.mem_read(p, self.r32(p - 12)))
    def f__ZNSsC1EPKcRKSaIcE(self):
        self.w32(self.arg(0), self.new_string(self.cstr(self.arg(1))))
        self.ret(self.arg(0))
    f__ZNSsC2EPKcRKSaIcE = f__ZNSsC1EPKcRKSaIcE
    def f__ZNSsC1EPKcmRKSaIcE(self):
        self.w32(self.arg(0), self.new_string(bytes(self.u.mem_read(self.arg(1), self.arg(2)))))
        self.ret(self.arg(0))
    def f__ZNSsC1ERKSs(self):
        self.w32(self.arg(0), self.new_string(self.string_bytes(self.arg(1))))
        self.ret(self.arg(0))
    def f__ZNSsD1Ev(self): self.ret(self.arg(0))
    f__ZNSsD2Ev = f__ZNSsD1Ev
    def f__ZNSs6assignERKSs(self):
        self.w32(self.arg(0), self.new_string(self.string_bytes(self.arg(1))))
        self.ret(self.arg(0))
    def f__ZNSs6assignEPKcm(self):
        self.w32(self.arg(0), self.new_string(bytes(self.u.mem_read(self.arg(1), self.arg(2)))))
        self.ret(self.arg(0))
    def f__ZNSs6appendERKSs(self):
        self.w32(self.arg(0), self.new_string(self.string_bytes(self.arg(0)) + self.string_bytes(self.arg(1))))
        self.ret(self.arg(0))
    def f__ZNSs6appendEPKcm(self):
        self.w32(self.arg(0), self.new_string(self.string_bytes(self.arg(0)) + bytes(self.u.mem_read(self.arg(1), self.arg(2)))))
        self.ret(self.arg(0))
    def f__ZNKSs7compareEPKc(self):
        a, b = self.string_bytes(self.arg(0)), self.cstr(self.arg(1))
        self.ret(0 if a == b else (-1 if a < b else 1))
    def f__ZNSs12_M_leak_hardEv(self): self.ret()
    def f__ZNSs7reserveEm(self): self.ret()
    # std::_List_node_base (next +0, prev +4)
    def f__ZNSt15_List_node_base4hookEPS_(self):
        this, pos = self.arg(0), self.arg(1)
        prev = self.r32(pos + 4)
        self.w32(this, pos)
        self.w32(this + 4, prev)
        self.w32(prev, this)
        self.w32(pos + 4, this)
        self.ret()
    def f__ZNSt15_List_node_base6unhookEv(self):
        this = self.arg(0)
        nxt, prev = self.r32(this), self.r32(this + 4)
        self.w32(prev, nxt)
        self.w32(nxt + 4, prev)
        self.ret()
    # std::_Rb_tree_node_base (colour +0: 0 red, 1 black; parent +4, left +8, right +12), as libstdc++'s tree.cc
    def rb(self, n, k): return self.r32(n + 4 * k)
    def rb_set(self, n, k, v): self.w32(n + 4 * k, v)
    def f__ZSt18_Rb_tree_incrementPSt18_Rb_tree_node_base(self): self.ret(self.rb_increment(self.arg(0)))
    f__ZSt18_Rb_tree_incrementPKSt18_Rb_tree_node_base = f__ZSt18_Rb_tree_incrementPSt18_Rb_tree_node_base
    def f__ZSt18_Rb_tree_decrementPSt18_Rb_tree_node_base(self): self.ret(self.rb_decrement(self.arg(0)))
    f__ZSt18_Rb_tree_decrementPKSt18_Rb_tree_node_base = f__ZSt18_Rb_tree_decrementPSt18_Rb_tree_node_base
    def rb_increment(self, x):
        if self.rb(x, 3):
            x = self.rb(x, 3)
            while self.rb(x, 2):
                x = self.rb(x, 2)
        else:
            y = self.rb(x, 1)
            while x == self.rb(y, 3):
                x, y = y, self.rb(y, 1)
            if self.rb(x, 3) != y:
                x = y
        return x
    def rb_decrement(self, x):
        if self.rb(x, 0) == 0 and self.rb(self.rb(x, 1), 1) == x:
            x = self.rb(x, 3)
        elif self.rb(x, 2):
            y = self.rb(x, 2)
            while self.rb(y, 3):
                y = self.rb(y, 3)
            x = y
        else:
            y = self.rb(x, 1)
            while x == self.rb(y, 2):
                x, y = y, self.rb(y, 1)
            x = y
        return x
    def rb_rotate_left(self, x, root_ref):
        y = self.rb(x, 3)
        self.rb_set(x, 3, self.rb(y, 2))
        if self.rb(y, 2):
            self.rb_set(self.rb(y, 2), 1, x)
        self.rb_set(y, 1, self.rb(x, 1))
        if x == self.r32(root_ref):
            self.w32(root_ref, y)
        elif x == self.rb(self.rb(x, 1), 2):
            self.rb_set(self.rb(x, 1), 2, y)
        else:
            self.rb_set(self.rb(x, 1), 3, y)
        self.rb_set(y, 2, x)
        self.rb_set(x, 1, y)
    def rb_rotate_right(self, x, root_ref):
        y = self.rb(x, 2)
        self.rb_set(x, 2, self.rb(y, 3))
        if self.rb(y, 3):
            self.rb_set(self.rb(y, 3), 1, x)
        self.rb_set(y, 1, self.rb(x, 1))
        if x == self.r32(root_ref):
            self.w32(root_ref, y)
        elif x == self.rb(self.rb(x, 1), 3):
            self.rb_set(self.rb(x, 1), 3, y)
        else:
            self.rb_set(self.rb(x, 1), 2, y)
        self.rb_set(y, 3, x)
        self.rb_set(x, 1, y)
    def f__ZSt29_Rb_tree_insert_and_rebalancebPSt18_Rb_tree_node_baseS0_RS_(self):
        left, x, p, header = self.arg(0) & 0xff, self.arg(1), self.arg(2), self.arg(3)
        root_ref = header + 4
        self.rb_set(x, 1, p)
        self.rb_set(x, 2, 0)
        self.rb_set(x, 3, 0)
        self.rb_set(x, 0, 0)
        if left:
            self.rb_set(p, 2, x)
            if p == header:
                self.rb_set(header, 1, x)
                self.rb_set(header, 3, x)
            elif p == self.rb(header, 2):
                self.rb_set(header, 2, x)
        else:
            self.rb_set(p, 3, x)
            if p == self.rb(header, 3):
                self.rb_set(header, 3, x)
        while x != self.r32(root_ref) and self.rb(self.rb(x, 1), 0) == 0:
            xp = self.rb(x, 1)
            xpp = self.rb(xp, 1)
            if xp == self.rb(xpp, 2):
                y = self.rb(xpp, 3)
                if y and self.rb(y, 0) == 0:
                    self.rb_set(xp, 0, 1)
                    self.rb_set(y, 0, 1)
                    self.rb_set(xpp, 0, 0)
                    x = xpp
                else:
                    if x == self.rb(xp, 3):
                        x = xp
                        self.rb_rotate_left(x, root_ref)
                        xp = self.rb(x, 1)
                        xpp = self.rb(xp, 1)
                    self.rb_set(xp, 0, 1)
                    self.rb_set(xpp, 0, 0)
                    self.rb_rotate_right(xpp, root_ref)
            else:
                y = self.rb(xpp, 2)
                if y and self.rb(y, 0) == 0:
                    self.rb_set(xp, 0, 1)
                    self.rb_set(y, 0, 1)
                    self.rb_set(xpp, 0, 0)
                    x = xpp
                else:
                    if x == self.rb(xp, 2):
                        x = xp
                        self.rb_rotate_right(x, root_ref)
                        xp = self.rb(x, 1)
                        xpp = self.rb(xp, 1)
                    self.rb_set(xp, 0, 1)
                    self.rb_set(xpp, 0, 0)
                    self.rb_rotate_left(xpp, root_ref)
        self.rb_set(self.r32(root_ref), 0, 1)
        self.ret()
    def f__ZSt28_Rb_tree_rebalance_for_erasePSt18_Rb_tree_node_baseRS_(self):
        z, header = self.arg(0), self.arg(1)
        root_ref, leftmost_ref, rightmost_ref = header + 4, header + 8, header + 12
        y = z
        x = 0
        x_parent = 0
        if not self.rb(y, 2):
            x = self.rb(y, 3)
        elif not self.rb(y, 3):
            x = self.rb(y, 2)
        else:
            y = self.rb(y, 3)
            while self.rb(y, 2):
                y = self.rb(y, 2)
            x = self.rb(y, 3)
        if y != z:
            self.rb_set(self.rb(z, 2), 1, y)
            self.rb_set(y, 2, self.rb(z, 2))
            if y != self.rb(z, 3):
                x_parent = self.rb(y, 1)
                if x:
                    self.rb_set(x, 1, self.rb(y, 1))
                self.rb_set(self.rb(y, 1), 2, x)
                self.rb_set(y, 3, self.rb(z, 3))
                self.rb_set(self.rb(z, 3), 1, y)
            else:
                x_parent = y
            if self.r32(root_ref) == z:
                self.w32(root_ref, y)
            elif self.rb(self.rb(z, 1), 2) == z:
                self.rb_set(self.rb(z, 1), 2, y)
            else:
                self.rb_set(self.rb(z, 1), 3, y)
            self.rb_set(y, 1, self.rb(z, 1))
            cy, cz = self.rb(y, 0), self.rb(z, 0)
            self.rb_set(y, 0, cz)
            self.rb_set(z, 0, cy)
            y = z
        else:
            x_parent = self.rb(y, 1)
            if x:
                self.rb_set(x, 1, self.rb(y, 1))
            if self.r32(root_ref) == z:
                self.w32(root_ref, x)
            elif self.rb(self.rb(z, 1), 2) == z:
                self.rb_set(self.rb(z, 1), 2, x)
            else:
                self.rb_set(self.rb(z, 1), 3, x)
            if self.r32(leftmost_ref) == z:
                if not self.rb(z, 3):
                    self.w32(leftmost_ref, self.rb(z, 1))
                else:
                    m = x
                    while self.rb(m, 2):
                        m = self.rb(m, 2)
                    self.w32(leftmost_ref, m)
            if self.r32(rightmost_ref) == z:
                if not self.rb(z, 2):
                    self.w32(rightmost_ref, self.rb(z, 1))
                else:
                    m = x
                    while self.rb(m, 3):
                        m = self.rb(m, 3)
                    self.w32(rightmost_ref, m)
        if self.rb(y, 0) != 0:
            black = lambda n: n == 0 or self.rb(n, 0) == 1
            while x != self.r32(root_ref) and black(x):
                if x == self.rb(x_parent, 2):
                    w = self.rb(x_parent, 3)
                    if self.rb(w, 0) == 0:
                        self.rb_set(w, 0, 1)
                        self.rb_set(x_parent, 0, 0)
                        self.rb_rotate_left(x_parent, root_ref)
                        w = self.rb(x_parent, 3)
                    if black(self.rb(w, 2)) and black(self.rb(w, 3)):
                        self.rb_set(w, 0, 0)
                        x = x_parent
                        x_parent = self.rb(x_parent, 1)
                    else:
                        if black(self.rb(w, 3)):
                            self.rb_set(self.rb(w, 2), 0, 1)
                            self.rb_set(w, 0, 0)
                            self.rb_rotate_right(w, root_ref)
                            w = self.rb(x_parent, 3)
                        self.rb_set(w, 0, self.rb(x_parent, 0))
                        self.rb_set(x_parent, 0, 1)
                        if self.rb(w, 3):
                            self.rb_set(self.rb(w, 3), 0, 1)
                        self.rb_rotate_left(x_parent, root_ref)
                        break
                else:
                    w = self.rb(x_parent, 2)
                    if self.rb(w, 0) == 0:
                        self.rb_set(w, 0, 1)
                        self.rb_set(x_parent, 0, 0)
                        self.rb_rotate_right(x_parent, root_ref)
                        w = self.rb(x_parent, 2)
                    if black(self.rb(w, 3)) and black(self.rb(w, 2)):
                        self.rb_set(w, 0, 0)
                        x = x_parent
                        x_parent = self.rb(x_parent, 1)
                    else:
                        if black(self.rb(w, 2)):
                            self.rb_set(self.rb(w, 3), 0, 1)
                            self.rb_set(w, 0, 0)
                            self.rb_rotate_left(w, root_ref)
                            w = self.rb(x_parent, 2)
                        self.rb_set(w, 0, self.rb(x_parent, 0))
                        self.rb_set(x_parent, 0, 1)
                        if self.rb(w, 2):
                            self.rb_set(self.rb(w, 2), 0, 1)
                        self.rb_rotate_right(x_parent, root_ref)
                        break
            if x:
                self.rb_set(x, 0, 1)
        self.ret(y)

    # ---- OpenGL ES 1.1 recorder ----------------------------------------------------------------------
    def gl_reset(self):
        """The GL state at start-up (it persists between frames; begin_frame only clears the recorded draws)."""
        self.draws = []
        self.texture = 0
        self.enabled = set()
        self.client = set()
        self.blend = (1, 0)
        self.matrix_mode = GL_MODELVIEW
        self.mv = [[1, 0, 0, 1, 0, 0]]   # 2D affine (a, b, c, d, e, f): x' = a x + c y + e, y' = b x + d y + f
        self.pointers = {}
        self.colour = (255, 255, 255, 255)
        self.ortho = None
        self.clear = None
    def top(self): return self.mv[-1]
    def mul(self, n):
        a, b, c, d, e, f = self.top()
        A, B, C, D, E, F = n
        self.mv[-1] = [a * A + c * B, b * A + d * B, a * C + c * D, b * C + d * D, a * E + c * F + e, b * E + d * F + f]
    def f_glBindTexture(self): self.texture = self.arg(1); self.ret()
    def f_glEnable(self): self.enabled.add(self.arg(0)); self.ret()
    def f_glDisable(self): self.enabled.discard(self.arg(0)); self.ret()
    def f_glEnableClientState(self): self.client.add(self.arg(0)); self.ret()
    def f_glDisableClientState(self): self.client.discard(self.arg(0)); self.ret()
    def f_glBlendFunc(self): self.blend = (self.arg(0), self.arg(1)); self.ret()
    def f_glMatrixMode(self): self.matrix_mode = self.arg(0); self.ret()
    def f_glLoadIdentity(self):
        if self.matrix_mode == GL_MODELVIEW:
            self.mv[-1] = [1, 0, 0, 1, 0, 0]
        self.ret()
    def f_glPushMatrix(self):
        if self.matrix_mode == GL_MODELVIEW:
            self.mv.append(list(self.top()))
        self.ret()
    def f_glPopMatrix(self):
        if self.matrix_mode == GL_MODELVIEW and len(self.mv) > 1:
            self.mv.pop()
        self.ret()
    def f_glTranslatef(self):
        if self.matrix_mode == GL_MODELVIEW:
            self.mul([1, 0, 0, 1, f32(self.arg(0)), f32(self.arg(1))])
        self.ret()
    def f_glScalef(self):
        if self.matrix_mode == GL_MODELVIEW:
            self.mul([f32(self.arg(0)), 0, 0, f32(self.arg(1)), 0, 0])
        self.ret()
    def f_glRotatef(self):
        if self.matrix_mode == GL_MODELVIEW:
            angle, z = math.radians(f32(self.arg(0))), f32(self.arg(3))
            if z < 0:
                angle = -angle
            c, s = math.cos(angle), math.sin(angle)
            self.mul([c, s, -s, c, 0, 0])
        self.ret()
    def f_glOrthof(self):
        self.ortho = [f32(self.arg(0)), f32(self.arg(1)), f32(self.arg(2)), f32(self.arg(3))]
        self.ret()
    def f_glViewport(self): self.ret()
    def f_glClearColor(self): self.clear = [round(f32(self.arg(i)), 4) for i in range(4)]; self.ret()
    def f_glClear(self): self.ret()
    def f_glColor4f(self): self.colour = tuple(int(round(f32(self.arg(i)) * 255)) for i in range(4)); self.ret()
    def f_glColor4ub(self): self.colour = tuple(self.arg(i) & 0xff for i in range(4)); self.ret()
    def f_glVertexPointer(self): self.pointers["v"] = (self.arg(0), self.arg(1), self.arg(2), self.arg(3)); self.ret()
    def f_glColorPointer(self): self.pointers["c"] = (self.arg(0), self.arg(1), self.arg(2), self.arg(3)); self.ret()
    def f_glTexCoordPointer(self): self.pointers["t"] = (self.arg(0), self.arg(1), self.arg(2), self.arg(3)); self.ret()
    def fetch(self, key, i):
        size, kind, stride, base = self.pointers[key]
        width = {0x1406: 4, 0x1401: 1, 0x1402: 2, 0x1400: 1}[kind]
        stride = stride or size * width
        raw = bytes(self.u.mem_read(base + i * stride, size * width))
        if kind == 0x1406:
            return struct.unpack("<%df" % size, raw)
        if kind == 0x1402:
            return struct.unpack("<%dh" % size, raw)
        return tuple(raw)
    def sites(self, depth=6):
        """The drawing call chain: the return addresses along the frame-pointer (r7) chain."""
        out = [self.u.reg_read(UC_ARM_REG_LR) & ~1]
        fp = self.u.reg_read(UC_ARM_REG_R7)
        for _ in range(depth):
            if not (STACK <= fp < STACK + STACK_SIZE):
                break
            lr = self.r32(fp + 4)
            if lr & ~1 == STOP:
                break
            out.append(lr & ~1)
            fp = self.r32(fp)
        return out
    def callers(self, depth=6):
        """The drawing call chain: function names of the return addresses along the frame-pointer (r7) chain."""
        return [self.function_at(a) for a in self.sites(depth)]
    def function_at(self, address):
        if not hasattr(self, "starts"):
            import bisect
            self.bisect = bisect
            text = [(v, n) for n, t, sect, v in self.m.symbols if sect == 1 and t & 0x0e == 0x0e]
            text.sort()
            self.starts = [v & ~1 for v, n in text]
            self.start_names = [n for v, n in text]
        i = self.bisect.bisect_right(self.starts, address & ~1) - 1
        return self.start_names[i] if i >= 0 else hex(address)
    def f_glDrawArrays(self):
        mode, first, count = self.arg(0), self.arg(1), self.arg(2)
        a, b, c, d, e, f = self.top()
        verts = []
        sites = self.sites()
        for i in range(first, first + count):
            x, y = self.fetch("v", i)[:2]
            u, v = self.fetch("t", i)[:2] if GL_TEXTURE_COORD_ARRAY in self.client and "t" in self.pointers else (0, 0)
            col = self.fetch("c", i) if GL_COLOR_ARRAY in self.client and "c" in self.pointers else self.colour
            verts.append([a * x + c * y + e, b * x + d * y + f, u, v] + list(col))
        self.draws.append(dict(texture=TEXTURES.get(self.texture, self.texture) if GL_TEXTURE_2D in self.enabled else None,
                               mode=mode, blend=list(self.blend) if GL_BLEND in self.enabled else None,
                               verts=verts, callers=[self.function_at(a) for a in sites], sites=sites))
        self.ret()


def ctype_bits(c):
    """Apple's _CTYPE_* bits for an ASCII character (A 0x100, C 0x200, D 0x400, G 0x800, L 0x1000, P 0x2000,
    S 0x4000, U 0x8000, X 0x10000, B 0x20000, R 0x40000)."""
    if c >= 128:
        return 0
    ch = chr(c)
    bits = 0
    if ch.isalpha(): bits |= 0x100
    if c < 32 or c == 127: bits |= 0x200
    if ch.isdigit(): bits |= 0x400 | 0x10000
    if 33 <= c <= 126: bits |= 0x800 | 0x40000
    if ch.islower(): bits |= 0x1000
    if 33 <= c <= 126 and not ch.isalnum(): bits |= 0x2000
    if ch in " \t\n\r\v\f": bits |= 0x4000
    if ch.isupper(): bits |= 0x8000
    if ch in "abcdefABCDEF": bits |= 0x10000
    if ch in " \t": bits |= 0x20000
    if c == 32: bits |= 0x40000
    return bits


LIBC = {}


class Game:
    """The original Game object driven as EAGLView does it."""
    def __init__(self, o):
        self.o = o
        self.g = o.alloc(GAME_SIZE)
        for f in o.m.init_functions():
            o.call(f)
        o.call(o.fn("__ZN4GameC1Ev"), self.g)
        font = lambda n: o.put_cstr(os.path.join(ASSETS, n))
        o.call(o.fn("__ZN4Game10CreateFontEPKcS1_S1_"), self.g, font("font.fnt"), font("fontMenu.fnt"), font("fontScore.fnt"))
        o.call(o.fn("__ZN4Game5StartEb"), self.g, 1)
        o.call(o.fn("__ZN4Game13SetupRendererEv"), self.g)
    def frame(self, dt=1 / 60):
        o = self.o
        o.clock += int(dt * 1e9)
        o.call(o.fn("__ZN4Game7ProcessEv"), self.g)
    def render(self):
        o = self.o
        o.draws = []
        o.call(o.fn("__ZN4Game6RenderEv"), self.g)
        return dict(clear=o.clear, ortho=o.ortho, draws=o.draws)
    def touch(self, phase, x=0.0, y=0.0):
        """x, y in screen units (1 wide, 1.5 high); EAGLView passes y as a fraction of the height (TouchStart
        multiplies it by 1.5)."""
        o = self.o
        y = y / 1.5
        if phase == 1:
            o.call(o.fn("__ZN4Game10TouchStartEff"), self.g, bits32(x), bits32(y))
        elif phase == 2:
            o.call(o.fn("__ZN4Game9TouchDragEff"), self.g, bits32(x), bits32(y))
        else:
            o.call(o.fn("__ZN4Game8TouchEndEv"), self.g)


TILE_UV = 0.0517578125   # a tile cell in tiles.png (53 pixels of 1024): u = variant, v = type


def board_from(frame):
    """The 36 tiles as drawn (the first draws of a game frame are Tile::Render): centre and the type row of the
    UV; types 0 potion, 1 skull, 2 coin, 3 shield, 4 sword (the special rows count as their base type here)."""
    tiles = []
    for d in frame["draws"][:36]:
        xs, ys = [v[0] for v in d["verts"]], [v[1] for v in d["verts"]]
        v0 = min(v[3] for v in d["verts"])
        row = int(round(v0 / TILE_UV))
        tiles.append(dict(x=(min(xs) + max(xs)) / 2, y=(min(ys) + max(ys)) / 2, row=row))
    return tiles


def longest_path(tiles):
    """A long path of linkable tiles by the drawn board (same type; skulls with swords), for driving the game."""
    cells = {}
    for t in tiles:
        cx, cy = int(t["x"] * 6), int((t["y"] - 0.246875) * 6)
        group = {0: "p", 1: "s", 2: "c", 3: "h", 4: "s", 10: "p", 11: "p"}.get(t["row"] % 12, "?")
        if t["row"] >= 12:   # enemy rows below the base tiles: skulls
            group = "s"
        cells[(cx, cy)] = (group, t)
    best = []
    def walk(path, seen):
        nonlocal best
        if len(path) > len(best):
            best = list(path)
        if len(best) >= 10:
            return
        x, y = path[-1]
        g = cells[path[-1]][0]
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (x + dx, y + dy)
                if n in cells and n not in seen and cells[n][0] == g and g != "?":
                    seen.add(n)
                    path.append(n)
                    walk(path, seen)
                    path.pop()
                    seen.discard(n)
    for c in cells:
        walk([c], {c})
    return [cells[c][1] for c in best]


# Game fields that tell which screen shows (named in recovered/: FrameScreens, EndGameState, MenuState ...).
FLAGS = dict(main_menu=0xc400, name=0x12c09, intro=0xc3f0, help=0x102a4, unlock=0x165a0, score=0xef6c,
             game_over=0xcac4, menu=0x59f4)


class Script:
    """Plays the original by touches, saving frames on the way (frames: [(name, frame dict)])."""
    def __init__(self):
        self.o = Original()
        self.game = Game(self.o)
        self.frames = []
    def flag(self, name):
        return self.o.u.mem_read(self.game.g + FLAGS[name], 1)[0]
    def run(self, n):
        for _ in range(n):
            self.game.frame()
    def tap(self, x, y, hold=2, after=30):
        self.game.touch(1, x, y)
        self.run(hold)
        self.game.touch(0)
        self.run(after)
    def stroke(self, tiles):
        """Press on the first tile, drag through the others, release (a few frames per tile)."""
        g = self.game
        g.touch(1, tiles[0]["x"], tiles[0]["y"])
        self.run(3)
        for t in tiles[1:]:
            g.touch(2, t["x"], t["y"])
            self.run(3)
    def release(self):
        self.game.touch(0)
    def play_turn(self, save_stroke=None):
        tiles = longest_path(board_from(self.game.render()))
        if len(tiles) < 3:
            return False
        self.stroke(tiles)
        if save_stroke:
            self.save(save_stroke)
        self.release()
        return True
    def save(self, name):
        f = self.game.render()
        f["scene"] = name
        self.frames.append((name, f))
        print("%s: %d draws, screens %s" % (name, len(f["draws"]), {k: self.flag(k) for k in FLAGS if self.flag(k)}))
        return f


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out, exist_ok=True)
    s = Script()
    s.run(30)
    s.save("main_menu")
    s.tap(0.22, 0.53)        # New Game
    s.save("setup")
    s.tap(0.86, 0.145)       # Random
    s.save("setup_named")
    s.run(120)               # Begin fades in
    s.tap(0.5, 1.41)         # Begin
    s.run(60)
    s.save("intro")
    s.run(120)
    s.tap(0.5, 1.41)         # the story's Begin
    s.run(120)
    s.save("board")
    s.play_turn(save_stroke="stroke")
    seen = set()
    for turn in range(400):
        for _ in range(240):
            s.run(1)
            if s.flag("menu") and "menu" not in seen:
                s.run(40)
                seen.add("menu")
                s.save("menu")
            if s.flag("game_over"):
                break
        if s.flag("game_over"):
            s.run(60)
            s.save("game_over")
            break
        if turn == 5:
            s.save("turn5")
        if s.flag("menu"):
            break
        s.play_turn()
    for name, f in s.frames:
        with open(os.path.join(out, name + ".json"), "w", encoding="utf-8") as fp:
            json.dump(f, fp)
    print("unmodelled imports", s.o.unknown)


if __name__ == "__main__":
    main()
