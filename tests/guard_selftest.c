#include <sys/mman.h>
#include <assert.h>
#include <errno.h>
int main(void) {
 errno=0;
 void* p=mmap(0,16384,PROT_READ|PROT_WRITE|PROT_EXEC,MAP_PRIVATE|MAP_ANON,-1,0);
 assert(p==MAP_FAILED && errno==EPERM);
 p=mmap(0,16384,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);
 assert(p!=MAP_FAILED);
 assert(mprotect(p,16384,PROT_READ|PROT_EXEC)==-1 && errno==EPERM);
 return 0;
}
