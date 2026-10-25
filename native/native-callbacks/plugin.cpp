// Self-authored minimal Windows x64 callback driver; contains no Unity implementation.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
using Callback = int (__cdecl *)(int, int);
static Callback callback;
static HANDLE worker;
static volatile LONG stopping, count;
static DWORD workerId;
static int results[4];
extern "C" __declspec(dllexport) __declspec(noinline) void NP_Event(int phase,int a,int b,int value) {
    // Stable debugger boundary for this experiment; intentionally no logging or runtime APIs.
    volatile int observed=phase+a+b+value; (void)observed;
}
static int Invoke(int a,int b) {
    NP_Event(1,a,b,0); int result=callback(a,b); NP_Event(2,a,b,result);
    int index=InterlockedCompareExchange(&count,0,0); results[index]=result; InterlockedIncrement(&count);
    return result;
}
extern "C" __declspec(dllexport) int __cdecl NP_Inline(Callback cb) {
    callback=cb; int a=Invoke(2,3),b=Invoke(7,8); callback=nullptr; return a*10000+b;
}
static DWORD WINAPI Work(void*) {
    workerId=GetCurrentThreadId(); NP_Event(5,0,0,0);
    Invoke(2,3); Invoke(7,8); Invoke(11,12);
    if(!InterlockedCompareExchange(&stopping,0,0)) Invoke(20,30);
    NP_Event(6,0,0,0); return 0;
}
extern "C" __declspec(dllexport) int __cdecl NP_Start(Callback cb) {
    if(worker || !cb) return 0;
    callback=cb; count=0; stopping=0; workerId=0;
    worker=CreateThread(nullptr,0,Work,nullptr,0,nullptr); return worker ? 1 : 0;
}
extern "C" __declspec(dllexport) int __cdecl NP_Stop() {
    InterlockedExchange(&stopping,1); NP_Event(3,0,0,0); return 1;
}
extern "C" __declspec(dllexport) int __cdecl NP_Join(unsigned milliseconds) {
    if(!worker) return -1;
    DWORD status=WaitForSingleObject(worker,milliseconds);
    if(status==WAIT_TIMEOUT) return 0;
    if(status!=WAIT_OBJECT_0) return -1;
    CloseHandle(worker); worker=nullptr; callback=nullptr; NP_Event(4,0,0,0); return 1;
}
extern "C" __declspec(dllexport) int __cdecl NP_Count() { return InterlockedCompareExchange(&count,0,0); }
extern "C" __declspec(dllexport) int __cdecl NP_Result(int index) { return index>=0 && index<4 ? results[index] : -1; }
extern "C" __declspec(dllexport) unsigned __cdecl NP_Thread() { return workerId; }
