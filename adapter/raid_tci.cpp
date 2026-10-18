#include "raid_tci.hpp"
#include <unicorn/arm.h>
#include <cstring>
#include <stdexcept>
#include <string>
#include <limits>
extern "C" void raid_arm_clear_exclusive(uc_engine*);
namespace raid {
static void check(uc_err e) {
    if(e!=UC_ERR_OK) throw std::runtime_error(std::string("TCI: ")+uc_strerror(e));
}
Interpreter::Interpreter() {
    check(uc_open(UC_ARCH_ARM,UC_MODE_ARM,&cpu));
    try {
        // Enable ARMv7 VFP/NEON for the original game's floating point code.
        uint32_t cpacr=0x00f00000, fpexc=0x40000000;
        check(uc_reg_write(cpu,UC_ARM_REG_C1_C0_2,&cpacr));
        check(uc_reg_write(cpu,UC_ARM_REG_FPEXC,&fpexc));
        check(uc_hook_add(cpu,&interruptHook,UC_HOOK_INTR,
                         reinterpret_cast<void*>(onInterrupt),this,1,0));
        check(uc_hook_add(cpu,&memoryHook,UC_HOOK_MEM_UNMAPPED,reinterpret_cast<void*>(onMemory),this,1,0));
        check(uc_hook_add(cpu,&blockHook,UC_HOOK_BLOCK,reinterpret_cast<void*>(onBlock),this,1,0));
    } catch(...) { uc_close(cpu); cpu=nullptr; throw; }
}
Interpreter::~Interpreter(){ if(cpu) uc_close(cpu); }
void Interpreter::map(uint32_t a,size_t n,void* p,uint32_t permissions){
    if(!n || uint64_t(a)+n>0x100000000ULL) throw std::invalid_argument("guest mapping range");
    check(uc_mem_map_ptr(cpu,a,n,permissions,p));
    for(uint64_t x=a;x<uint64_t(a)+n;x+=4096) pages.insert(uint32_t(x));
}
void Interpreter::unmap(uint32_t a,size_t n){ check(uc_mem_unmap(cpu,a,n)); for(uint64_t x=a;x<uint64_t(a)+n;x+=4096) pages.erase(uint32_t(x)); }
void Interpreter::clearMappings(){ auto old=pages;for(auto page:old)unmap(page,4096); }
void Interpreter::clearExclusive(){raid_arm_clear_exclusive(cpu);}
bool Interpreter::onMemory(uc_engine*,uc_mem_type,uint64_t address,int,int64_t,void* data){
 auto& self=*static_cast<Interpreter*>(data);
 if(address>0xffffffff || !self.resolve)return false;
 auto page=uint32_t(address)&~4095u;void* backing=nullptr;uint32_t perms=0;
 if(!self.resolve(page,backing,perms)||!backing)return false;
 try{ self.map(page,4096,backing,perms);return true; }catch(...){return false;}
}
void Interpreter::onBlock(uc_engine* uc,uint64_t,uint32_t,void* data){
 auto& self=*static_cast<Interpreter*>(data);if(self.shouldStop && self.shouldStop())uc_emu_stop(uc);
}
void Interpreter::invalidate(uint32_t a,size_t n){
    if(n) check(uc_ctl_remove_cache(cpu,a,uint64_t(a)+n));
}
void Interpreter::transfer(State& s,bool write) {
    static const int ids[]={UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,
      UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,
      UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11,UC_ARM_REG_R12,
      UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC};
    auto reg=[&](int id,void* value){ check(write?uc_reg_write(cpu,id,value):uc_reg_read(cpu,id,value)); };
    // CPSR mode selects the banked stack/registers; install it first.
    if(write) reg(UC_ARM_REG_CPSR,&s.cpsr);
    for(unsigned i=0;i<16;i++) {
        uint32_t value=s.regs[i];
        // Writing PC without Thumb bit clears T in Unicorn.
        if(write && i==15 && (s.cpsr&0x20)) value|=1;
        reg(ids[i],&value);
        if(!write) s.regs[i]=value;
    }
    if(!write) reg(UC_ARM_REG_CPSR,&s.cpsr);
    for(unsigned i=0;i<32;i++) {
        uint64_t value=0;
        if(write) std::memcpy(&value,&s.extRegs[i*2],8);
        reg(UC_ARM_REG_D0+i,&value);
        if(!write) std::memcpy(&s.extRegs[i*2],&value,8);
    }
    reg(UC_ARM_REG_FPSCR,&s.fpscr);
    for(unsigned i=0;i<2;i++) {
        uc_arm_cp_reg cp{};cp.cp=15;cp.crn=13;cp.crm=0;cp.opc1=0;cp.opc2=2+i;
        if(write) cp.val=i?s.uro:s.uprw;
        reg(UC_ARM_REG_CP_REG,&cp);
        if(!write) (i?s.uro:s.uprw)=uint32_t(cp.val);
    }
}
void Interpreter::onInterrupt(uc_engine* uc,uint32_t n,void* data) {
    auto& self=*static_cast<Interpreter*>(data);
    self.interrupted=true;self.interrupt=n;
    uc_emu_stop(uc);
}
Stop Interpreter::run(State& s,size_t instructions) {
    // Bounded runs are mandatory; zero means unbounded in Unicorn.
    if(!instructions) throw std::invalid_argument("zero instruction budget");
    transfer(s,true);interrupted=false;interrupt=0;
    auto error=uc_emu_start(cpu,s.regs[15]|((s.cpsr&0x20)?1:0),
                            std::numeric_limits<uint64_t>::max(),0,instructions);
    transfer(s,false);
    if(error!=UC_ERR_OK) return {StopKind::Fault,0,error,s.regs[15]};
    if(!interrupted) return {StopKind::Budget,0,UC_ERR_OK,s.regs[15]};
    if(interrupt!=2) return {StopKind::Fault,0,UC_ERR_EXCEPTION,s.regs[15]};
    uint32_t instruction=0, width=(s.cpsr&0x20)?2:4;
    error=uc_mem_read(cpu,s.regs[15]-width,&instruction,width);
    if(error!=UC_ERR_OK) return {StopKind::Fault,0,error,s.regs[15]};
    uint32_t svc=instruction&((width==2)?0xff:0xffffff);
    return {StopKind::Svc,svc,UC_ERR_OK,s.regs[15]};
}
}
