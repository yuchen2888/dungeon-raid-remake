import struct, sys
class ARMv7:
    """The armv7 slice of a universal Mach-O: VM address -> bytes."""
    def __init__(self, path):
        data = open(path, 'rb').read()
        magic, n = struct.unpack('>II', data[:8])
        assert magic == 0xcafebabe
        for i in range(n):
            cputype, sub, off, size, align = struct.unpack('>IIIII', data[8 + 20 * i: 28 + 20 * i])
            if cputype == 12 and sub == 9:
                self.d = data[off:off + size]
        ncmds = struct.unpack('<I', self.d[16:20])[0]
        p = 28
        self.segs = []
        for _ in range(ncmds):
            cmd, sz = struct.unpack('<II', self.d[p:p + 8])
            if cmd == 1:
                vmaddr, vmsize, fileoff, filesize = struct.unpack('<IIII', self.d[p + 24:p + 40])
                self.segs.append((vmaddr, vmsize, fileoff, filesize))
            p += sz
    def off(self, a):
        for v, vs, fo, fs in self.segs:
            if v <= a < v + fs:
                return fo + a - v
        raise KeyError(hex(a))
    def u8(self, a): return self.d[self.off(a)]
    def u16(self, a): return struct.unpack('<H', self.d[self.off(a):self.off(a) + 2])[0]
    def u32(self, a): return struct.unpack('<I', self.d[self.off(a):self.off(a) + 4])[0]
    def cstr(self, a):
        o = self.off(a); e = self.d.index(b'\0', o)
        return self.d[o:e].decode('latin1')
    def ldr_add_pc(self, a):
        """Thumb 'ldr rX, [pc, #i]; add rX, pc' at a: the address it computes."""
        ins = self.u16(a)
        assert ins & 0xf800 == 0x4800, hex(ins)
        lit = ((a + 4) & ~3) + (ins & 0xff) * 4
        return (self.u32(lit) + a + 2 + 4) & 0xffffffff
    def tbb(self, at, count):
        """Case targets of 'tbb [pc, r0]' at 'at' (table follows the instruction)."""
        base = at + 4
        return [base + 2 * self.u8(base + i) for i in range(count)]
