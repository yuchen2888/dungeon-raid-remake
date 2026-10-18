// macOS audit interposer: reject new host executable mappings/protections.
#include <sys/mman.h>
#include <errno.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
static _Atomic unsigned mappings, protections, rejected;
static void* guarded_mmap(void* a,size_t n,int p,int f,int fd,off_t o) {
    atomic_fetch_add(&mappings,1);
    if(p&PROT_EXEC){atomic_fetch_add(&rejected,1);errno=EPERM;return MAP_FAILED;}
    return mmap(a,n,p,f,fd,o);
}
static int guarded_mprotect(void* a,size_t n,int p) {
    atomic_fetch_add(&protections,1);
    if(p&PROT_EXEC){atomic_fetch_add(&rejected,1);errno=EPERM;return -1;}
    return mprotect(a,n,p);
}
#define INTERPOSE(new,old) __attribute__((used)) static struct {const void* replacement;const void* original;} pair_##old __attribute__((section("__DATA,__interpose")))={(const void*)new,(const void*)old}
INTERPOSE(guarded_mmap,mmap);
INTERPOSE(guarded_mprotect,mprotect);
__attribute__((destructor)) static void report(void){
    fprintf(stderr,"NOEXEC_AUDIT mappings=%u protections=%u rejected=%u\n",mappings,protections,rejected);
    // Test processes must fail if an unexpected request was attempted.
    if(rejected && !getenv("RAID_GUARD_SELFTEST")) _Exit(87);
}
