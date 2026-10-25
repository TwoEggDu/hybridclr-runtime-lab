// Self-authored Windows x64 driver. Context is an opaque GCHandle token, never an object address.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
using Callback=int (__cdecl *)(void*,int,int);
static Callback callback;
static void* context;
static HANDLE worker;
static int mode,limit;
static DWORD workerId;
static volatile LONG stopping,count,errors;
static volatile LONG64 checksum;
extern "C" __declspec(dllexport) __declspec(noinline) void NP_Event(int phase,int seq,int result) {
 volatile int observed=phase+seq+result;(void)observed;
}
static DWORD WINAPI Work(void*) {
 workerId=GetCurrentThreadId();NP_Event(5,0,0);
 // The extra iteration detects a missing final stop; the expected protocol stops while limit is held.
 for(int seq=1;seq<=limit+1 && !InterlockedCompareExchange(&stopping,0,0);seq++) {
  NP_Event(1,seq,0);int value=callback(context,seq,mode);NP_Event(2,seq,value);
  InterlockedIncrement(&count);InterlockedAdd64(&checksum,value);
  if(value<0) { InterlockedIncrement(&errors);break; }
 }
 NP_Event(6,0,0);return 0;
}
extern "C" __declspec(dllexport) int __cdecl NP_Start(Callback cb,void* token,int kind,int maximum) {
 if(worker || !cb || kind<0 || kind>2 || maximum<1 || maximum>1024) return 0;
 callback=cb;context=token;mode=kind;limit=maximum;stopping=count=errors=0;checksum=0;workerId=0;
 worker=CreateThread(nullptr,0,Work,nullptr,0,nullptr);return worker ? 1 : 0;
}
extern "C" __declspec(dllexport) int __cdecl NP_Stop() { InterlockedExchange(&stopping,1);NP_Event(3,0,0);return 1; }
extern "C" __declspec(dllexport) int __cdecl NP_Join(unsigned milliseconds) {
 if(!worker)return -1;
 DWORD status=WaitForSingleObject(worker,milliseconds);
 if(status==WAIT_TIMEOUT)return 0;
 if(status!=WAIT_OBJECT_0)return -1;
 CloseHandle(worker);worker=nullptr;callback=nullptr;context=nullptr;NP_Event(4,0,0);return 1;
}
extern "C" __declspec(dllexport) int __cdecl NP_Count(){return InterlockedCompareExchange(&count,0,0);}
extern "C" __declspec(dllexport) int __cdecl NP_Errors(){return InterlockedCompareExchange(&errors,0,0);}
extern "C" __declspec(dllexport) long long __cdecl NP_Checksum(){return InterlockedCompareExchange64(&checksum,0,0);}
extern "C" __declspec(dllexport) unsigned __cdecl NP_Thread(){return workerId;}
