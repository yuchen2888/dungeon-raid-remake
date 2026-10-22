#!/usr/bin/env python3
"""Actual NameScreen::GenerateRandomName vs native dr_session_setup_random_name (recovered_session, T040-M3).

The original runs from its entry (0x3882c, R0 = a NameScreen in scratch memory) with RandI as original code on the
harness's random streams; the sprintf (%s only) and strlen stubs are modelled. The native side is a session whose
stream 0 gets the same seeds. 4000 draws from random seeds over a name box that holds random bytes beforehand; compared:
the box's 19 bytes (NameScreen+0x2935), the length (+0x2948) and the six random streams. Every part of both name tables
and both formats ("%s%s", "%s%s %s%s") must occur.
"""
import ctypes as C
import json
import random
import struct
from verify_skills import Original as SkillsOriginal, case as skills_case
from verify_stroke import HERE
from verify_match import Match
from verify_session import Objects, Host, Setup, RANDOM_NAME, SPRINTF, STRLEN, NAME_NAME, NAME_LENGTH, SEEDS

BOX=0x170c000
STARTS,ENDS=0x18da29,0x18d934   # the two name tables (five-byte entries)

class Original(SkillsOriginal):
    def __init__(self):super().__init__();self.naming=False;self.parts=[]
    def hook(self,u,address,size,context):
        if self.naming and address in (SPRINTF,STRLEN):
            r=[u.reg_read(x) for x in self.regs];sp=u.reg_read(self.SP);cstr=lambda a:bytes(u.mem_read(a,32)).split(b'\0')[0]
            if address==STRLEN:res=len(cstr(r[0]))
            else:
                fmt=cstr(r[1]);args=[r[2],r[3],self.read(sp),self.read(sp+4)];out=b'';i=k=0
                while i<len(fmt):
                    if fmt[i:i+2]==b'%s':self.parts.append(args[k]);out+=cstr(args[k]);k+=1;i+=2
                    else:out+=fmt[i:i+1];i+=1
                self.formats.add(fmt);u.mem_write(r[0],out+b'\0');res=len(out)
            u.reg_write(self.regs[0],res);u.reg_write(self.PC,u.reg_read(self.LR));return
        return super().hook(u,address,size,context)

def main():
    old=Original();old.load(skills_case(random.Random(1)));u=old.u;old.formats=set()
    lib=C.CDLL(str(HERE/'recovered_session_native.dylib'))
    lib.dr_session_create.argtypes=[C.POINTER(Host),C.c_int32];lib.dr_session_create.restype=C.c_void_p
    lib.dr_session_objects.argtypes=[C.c_void_p];lib.dr_session_objects.restype=Objects
    lib.dr_session_setup_random_name.argtypes=[C.c_void_p];lib.dr_session_setup_random_name.restype=None
    host=Host();session=lib.dr_session_create(C.byref(host),1);o=lib.dr_session_objects(session)
    match=Match.from_address(o.match);box=Setup.from_address(o.setup)
    rng=random.Random(0x3882c);starts=set();ends=set();longest=0
    for trial in range(4000):
        seeds=[rng.randrange(1,2**31) for _ in range(6)];fill=bytes(rng.randrange(256) for _ in range(19))
        u.mem_write(SEEDS,struct.pack('<6I',*seeds));match.random.seeds[:]=seeds
        u.mem_write(BOX+NAME_NAME,fill);C.memmove(box.name,fill,19);old.parts=[]
        u.reg_write(old.regs[0],BOX);u.reg_write(old.SP,0x140fe00);u.reg_write(old.LR,old.STOP|1);old.naming=True
        try:u.emu_start(RANDOM_NAME[0]|1,old.STOP,timeout=0,count=100000);assert u.reg_read(old.PC)==old.STOP,hex(u.reg_read(old.PC))
        finally:old.naming=False
        lib.dr_session_setup_random_name(session)
        a=[bytes(u.mem_read(BOX+NAME_NAME,19)).hex(),C.c_int32(old.read(BOX+NAME_LENGTH)).value,list(struct.unpack('<6I',u.mem_read(SEEDS,24)))]
        b=[bytes(box.name).hex(),box.length,list(match.random.seeds)]
        if a!=b:
            (HERE/'setup_names_failure.json').write_text(json.dumps(dict(trial=trial,seeds=seeds,original=a,native=b),indent=2))
            raise AssertionError('setup_names_failure.json')
        for i,p in enumerate(old.parts):(starts if i%2==0 else ends).add((p-(STARTS if i%2==0 else ENDS))//5)
        longest=max(longest,a[1])
    assert starts==set(range(50)) and ends==set(range(49)) and old.formats=={b'%s%s',b'%s%s %s%s'},(len(starts),len(ends),old.formats)
    print(json.dumps(dict(status='passed',draws=4000,start_parts=len(starts),end_parts=len(ends),formats=sorted(f.decode() for f in old.formats),
                          longest=longest,function='NameScreen::GenerateRandomName 0x3882c',native='dr_session_setup_random_name',
                          original='Actual function from its entry (RandI original code)',boundaries=['sprintf (%s) and strlen modelled'])))

if __name__=='__main__':main()
