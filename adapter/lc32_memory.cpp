#include "dynarmic_internal.h"
extern "C" bool RaidResolveGuestPage(uint32_t address,void** backing,uint32_t* permissions){
 std::lock_guard<std::recursive_mutex> lock(guestVmMutex);
 if(!sharedHandle.memory)return false;
 auto k=kh_get(memory,sharedHandle.memory,address);
 if(k==kh_end(sharedHandle.memory))return false;
 const auto p=kh_value(sharedHandle.memory,k);
 if(!p||!p->addr)return false;
 *backing=p->addr;*permissions=p->perms&7;
 return true;
}
