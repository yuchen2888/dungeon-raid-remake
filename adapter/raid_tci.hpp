#pragma once
#include <array>
#include <cstdint>
#include <cstddef>
#include <functional>
#include <set>
#include <unicorn/unicorn.h>

namespace raid {
// Register layout mirrors the existing LC32 context. This is an execution
// adapter, not yet a replacement for LC32's scheduler and memory callbacks.
struct State {
    std::array<uint32_t,16> regs{};
    std::array<uint32_t,64> extRegs{};
    uint32_t cpsr=0x10, fpscr=0, uro=0, uprw=0;
};
enum class StopKind { Budget, Svc, Fault };
struct Stop { StopKind kind; uint32_t svc; uc_err error; uint32_t pc; };
class Interpreter {
public:
    Interpreter();
    ~Interpreter();
    Interpreter(const Interpreter&)=delete;
    Interpreter& operator=(const Interpreter&)=delete;
    void map(uint32_t address, size_t size, void* backing, uint32_t permissions);
    void unmap(uint32_t address, size_t size);
    void invalidate(uint32_t address, size_t size);
    Stop run(State&, size_t instructions);
    std::function<bool(uint32_t,void*&,uint32_t&)> resolve;
    std::function<bool()> shouldStop;
    void clearExclusive();
    void clearMappings();
private:
    uc_engine* cpu=nullptr;
    uc_hook interruptHook=0, memoryHook=0, blockHook=0;
    std::set<uint32_t> pages;
    static bool onMemory(uc_engine*,uc_mem_type,uint64_t,int,int64_t,void*);
    static void onBlock(uc_engine*,uint64_t,uint32_t,void*);
    bool interrupted=false;
    uint32_t interrupt=0;
    static void onInterrupt(uc_engine*, uint32_t, void*);
    void transfer(State&, bool write);
};
}
