#include <dynarmic/interface/A32/a32.h>
#include "arm_dynarmic_cp15.h"
#include <unicorn/unicorn.h>
#include <cassert>
#include <cstring>
#include <thread>
#include <vector>
#include <iostream>
#include <sys/mman.h>
static unsigned char* memory;
extern "C" bool RaidResolveGuestPage(uint32_t a,void** p,uint32_t* permissions){
 if(a!=0x1000 && a!=0x2000)return false;
 *p=memory+(a-0x1000);*permissions=a==0x1000?UC_PROT_READ|UC_PROT_EXEC:UC_PROT_READ|UC_PROT_WRITE;return true;
}
struct Callbacks: Dynarmic::A32::UserCallbacks {
 Dynarmic::A32::Jit* cpu=nullptr;unsigned calls=0;
 uint8_t MemoryRead8(uint32_t a)override{return memory[a-0x1000];}
 uint16_t MemoryRead16(uint32_t a)override{uint16_t v;memcpy(&v,memory+a-0x1000,2);return v;}
 uint32_t MemoryRead32(uint32_t a)override{uint32_t v;memcpy(&v,memory+a-0x1000,4);return v;}
 uint64_t MemoryRead64(uint32_t a)override{uint64_t v;memcpy(&v,memory+a-0x1000,8);return v;}
 void MemoryWrite8(uint32_t a,uint8_t v)override{memcpy(memory+a-0x1000,&v,1);}
 void MemoryWrite16(uint32_t a,uint16_t v)override{memcpy(memory+a-0x1000,&v,2);}
 void MemoryWrite32(uint32_t a,uint32_t v)override{memcpy(memory+a-0x1000,&v,4);}
 void MemoryWrite64(uint32_t a,uint64_t v)override{memcpy(memory+a-0x1000,&v,8);}
 void InterpreterFallback(uint32_t,size_t)override{std::abort();}
 void ExceptionRaised(uint32_t,Dynarmic::A32::Exception)override{std::abort();}
 void CallSVC(uint32_t n)override{assert(n==0x80);assert(cpu->IsExecuting());calls++;cpu->HaltExecution(Dynarmic::HaltReason::UserDefined1);}
 void AddTicks(uint64_t)override{}
 uint64_t GetTicksRemaining()override{return 1000;}
};
int main(){
 memory=(unsigned char*)mmap(nullptr,16384,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);assert(memory!=MAP_FAILED);
 uint32_t code[]={0xe1910f9f,0xe2800001,0xe1812f90,0xe3520000,0x1afffffa,0xef000080};memcpy(memory,code,sizeof code);
 std::vector<std::thread> threads;
 for(unsigned t=0;t<4;t++)threads.emplace_back([t]{
  Callbacks cb;Dynarmic::A32::UserConfig config;config.callbacks=&cb;
  auto cp=std::make_shared<DynarmicCP15>();cp->uro=0x70000000+t*0x1000;config.coprocessors[15]=cp;
  Dynarmic::A32::Jit cpu(config);cb.cpu=&cpu;
  for(unsigned i=0;i<1000;i++){
   cpu.Regs()[15]=0x1000;cpu.Regs()[1]=0x2000;
   Dynarmic::HaltReason reason{};do{reason=cpu.Run();}while(!reason);
   assert(Dynarmic::Has(reason,Dynarmic::HaltReason::UserDefined1));assert(cp->uro==0x70000000+t*0x1000);
   if(i==100)cpu.InvalidateCacheRange(0x1000,4096);
  }
  assert(cb.calls==1000);
 });
 for(auto& t:threads)t.join();uint32_t value;memcpy(&value,memory+4096,4);assert(value==4000);
 std::cout<<"PASS: 4 guest CPUs, 4000 shared LDREX/STREX increments, SVC stop/resume, TLS, mapping invalidation\n";
}
