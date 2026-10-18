// Source-compatible implementation of the public Dynarmic A32 interface.
// Executes exclusively through the TCI interpreter; no Dynarmic backend linked.
#include <dynarmic/interface/A32/a32.h>
#include <dynarmic/interface/A32/coprocessor.h>
#include "raid_tci.hpp"
#include <atomic>
#include <mutex>
#include <stdexcept>
#include <cstdlib>
#include <algorithm>
#include <thread>
extern "C" bool RaidResolveGuestPage(uint32_t,void**,uint32_t*);
namespace Dynarmic::A32 {
static std::mutex executionMutex;
static const raid::Interpreter* lastCpu=nullptr;
struct Jit::Impl {
    UserConfig config;
    raid::Interpreter machine;
    raid::State state;
    std::atomic<uint32_t> halt{0};
    std::atomic<bool> mappingsDirty{false};
    explicit Impl(UserConfig c):config(c){
        machine.resolve=[](uint32_t a,void*& p,uint32_t& flags){return RaidResolveGuestPage(a,&p,&flags);};
        machine.shouldStop=[this]{return halt.load(std::memory_order_acquire)!=0 || mappingsDirty.load();};
    }
    void tls(bool write){
        auto cp=config.coprocessors[15];if(!cp)return;
        for(unsigned n=2;n<=3;n++){
            auto access=cp->CompileGetOneWord(false,0,CoprocReg::C13,CoprocReg::C0,n);
            auto pointer=std::get_if<uint32_t*>(&access);
            if(!pointer || !*pointer)throw std::runtime_error("TCI needs pointer-backed CP15 TLS");
            auto& value=n==2?state.uprw:state.uro;
            if(write)value=**pointer;else **pointer=value;
        }
    }
};
Jit::Jit(UserConfig c):impl(std::make_unique<Impl>(c)){}
Jit::~Jit()=default;
HaltReason Jit::Run(){
    if(is_executing)throw std::runtime_error("recursive TCI execution before host unwind");
    is_executing=true;
    struct End{bool& b;~End(){b=false;}}end{is_executing};
    size_t remaining=std::min<uint64_t>(impl->config.callbacks->GetTicksRemaining(),100000);
    if(!remaining)remaining=1;
    while(!impl->halt.load(std::memory_order_acquire)){
        if(impl->mappingsDirty.exchange(false))impl->machine.clearMappings();
        impl->tls(true);
        std::unique_lock<std::mutex> execution(executionMutex,std::defer_lock);
        while(!execution.try_lock()){
            if(impl->halt.load())return static_cast<HaltReason>(impl->halt.exchange(0));
            std::this_thread::yield();
        }
        // Serialize guest instruction slices, but never hold this mutex over
        // host callbacks. Different host pthreads still deliver UI/dispatch.
        // Losing a local exclusive reservation on a CPU switch is permitted.
        if(lastCpu!=&impl->machine)impl->machine.clearExclusive();
        lastCpu=&impl->machine;
        auto result=impl->machine.run(impl->state,remaining);
        execution.unlock();
        impl->tls(false);
        if(result.kind==raid::StopKind::Svc){
            impl->config.callbacks->CallSVC(result.svc);
            // Yield at every syscall, bounding this invocation without inventing
            // instruction counts for an early stop. Outer LC32 loop resumes.
            break;
        }
        if(result.kind==raid::StopKind::Fault){
            auto e=(result.error==UC_ERR_FETCH_UNMAPPED||result.error==UC_ERR_FETCH_PROT)
                ?Exception::NoExecuteFault:Exception::UndefinedInstruction;
            impl->config.callbacks->ExceptionRaised(result.pc,e);
            impl->halt.fetch_or(uint32_t(HaltReason::MemoryAbort));
            break;
        }
        break;
    }
    return static_cast<HaltReason>(impl->halt.exchange(0));
}
HaltReason Jit::Step(){
    impl->tls(true);if(impl->mappingsDirty.exchange(false))impl->machine.clearMappings();
    std::unique_lock<std::mutex> execution(executionMutex);
    if(lastCpu!=&impl->machine)impl->machine.clearExclusive();lastCpu=&impl->machine;
    auto stop=impl->machine.run(impl->state,1);execution.unlock();impl->tls(false);
    if(stop.kind==raid::StopKind::Svc){is_executing=true;impl->config.callbacks->CallSVC(stop.svc);is_executing=false;}
    if(stop.kind==raid::StopKind::Fault)impl->config.callbacks->ExceptionRaised(stop.pc,Exception::UndefinedInstruction);
    return HaltReason::Step|static_cast<HaltReason>(impl->halt.exchange(0));
}
void Jit::ClearCache(){impl->mappingsDirty=true;}
void Jit::InvalidateCacheRange(uint32_t,size_t){impl->mappingsDirty=true;}
void Jit::Reset(){impl->state={};impl->machine.clearExclusive();}
void Jit::HaltExecution(HaltReason r){impl->halt.fetch_or(uint32_t(r));}
void Jit::ClearHalt(HaltReason r){impl->halt.fetch_and(~uint32_t(r));}
std::array<uint32_t,16>& Jit::Regs(){return impl->state.regs;}
const std::array<uint32_t,16>& Jit::Regs()const{return impl->state.regs;}
std::array<uint32_t,64>& Jit::ExtRegs(){return impl->state.extRegs;}
const std::array<uint32_t,64>& Jit::ExtRegs()const{return impl->state.extRegs;}
uint32_t Jit::Cpsr()const{return impl->state.cpsr;}
void Jit::SetCpsr(uint32_t v){impl->state.cpsr=v;}
uint32_t Jit::Fpscr()const{return impl->state.fpscr;}
void Jit::SetFpscr(uint32_t v){impl->state.fpscr=v;}
void Jit::ClearExclusiveState(){impl->machine.clearExclusive();}
void Jit::DumpDisassembly()const{}
std::vector<std::string> Jit::Disassemble()const{return {};}
}
