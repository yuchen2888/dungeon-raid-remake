#include "raid_tci.hpp"
#include <unicorn/arm.h>
#include <cassert>
#include <cstring>
#include <iostream>
#include <sys/mman.h>
using namespace raid;
int main(){
    auto* memory=static_cast<unsigned char*>(mmap(nullptr,16384,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0));
    assert(memory!=MAP_FAILED);
    Interpreter cpu;cpu.map(0x1000,4096,memory,UC_PROT_READ|UC_PROT_EXEC);
    cpu.map(0x2000,4096,memory+4096,UC_PROT_READ|UC_PROT_WRITE);
    // ARM: add r0,r0,#3; svc #0x80; add r0,r0,#4; svc #0x80.
    uint32_t arm[]={0xe2800003,0xef000080,0xe2800004,0xef000080};
    memcpy(memory,arm,sizeof arm);
    State s;s.regs[15]=0x1000;s.regs[0]=7;s.uro=0x12340000;s.uprw=0x56780000;
    for(unsigned i=0;i<64;i++)s.extRegs[i]=0x33440000+i;
    auto original=s;
    auto stop=cpu.run(s,100);assert(stop.kind==StopKind::Svc && stop.svc==0x80 && s.regs[0]==10 && s.regs[15]==0x1008);
    assert(s.extRegs==original.extRegs && s.uro==original.uro && s.uprw==original.uprw);
    // Host call changes registers between slices; nested guest call preserves outer state.
    State outer=s, nested=original; nested.regs[0]=20;
    stop=cpu.run(nested,100);assert(stop.kind==StopKind::Svc && nested.regs[0]==23);
    s=outer;s.regs[0]=100;stop=cpu.run(s,100);assert(stop.kind==StopKind::Svc && s.regs[0]==104);
    // Thumb mode + SVC continuation.
    uint16_t thumb[]={0x3002,0xdf80,0x3005,0xdf80};memcpy(memory+0x100,thumb,sizeof thumb);
    s={};s.cpsr=0x30;s.regs[15]=0x1100;s.regs[0]=5;
    stop=cpu.run(s,100);assert(stop.kind==StopKind::Svc && s.regs[0]==7 && s.regs[15]==0x1104 && (s.cpsr&0x20));
    stop=cpu.run(s,100);assert(stop.kind==StopKind::Svc && s.regs[0]==12);
    // Shared backing and protection failure: str r0,[r1]; svc.
    uint32_t store[]={0xe5810000,0xef000080};memcpy(memory+0x200,store,sizeof store);
    s={};s.regs[15]=0x1200;s.regs[0]=0x76543210;s.regs[1]=0x2000;
    stop=cpu.run(s,100);uint32_t value;memcpy(&value,memory+4096,4);assert(value==s.regs[0] && stop.kind==StopKind::Svc);
    s.regs[15]=0x1200;s.regs[1]=0x1000;stop=cpu.run(s,100);assert(stop.kind==StopKind::Fault && stop.error==UC_ERR_WRITE_PROT);
    // Host-side code changes must invalidate the translated bytecode.
    arm[0]=0xe2800009;memcpy(memory,arm,sizeof arm);cpu.invalidate(0x1000,sizeof arm);
    s={};s.regs[15]=0x1000;stop=cpu.run(s,100);assert(s.regs[0]==9 && stop.kind==StopKind::Svc);
    // Execute from a non-executable guest page must fail (host is always RW).
    s={};s.regs[15]=0x2000;stop=cpu.run(s,100);assert(stop.kind==StopKind::Fault && stop.error==UC_ERR_FETCH_PROT);
    // Bounded loops return to the scheduler.
    uint32_t branch=0xeafffffe;memcpy(memory+0x300,&branch,4);s={};s.regs[15]=0x1300;
    stop=cpu.run(s,1000);assert(stop.kind==StopKind::Budget && s.regs[15]==0x1300);
    cpu.unmap(0x2000,4096);s={};s.regs[15]=0x1200;s.regs[1]=0x2000;
    stop=cpu.run(s,100);assert(stop.kind==StopKind::Fault && stop.error==UC_ERR_WRITE_UNMAPPED);
    std::cout<<"PASS: ARM/Thumb SVC, resume, nested state, VFP/TLS state, shared memory, permissions, invalidation, scheduler budget, unmap\n";
}
