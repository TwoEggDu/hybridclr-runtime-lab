// Self-authored Windows x64 observer. Numeric API constants are validated against this locked Player.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
static volatile LONG64 stats[8];
static volatile LONG phase,sequence;
struct Row {LONG64 event,starts,ends,phase,sequence;};
static Row events[65536];
extern "C" __declspec(dllexport) __declspec(noinline) void WB_Marker(int p,int seq,int kind){InterlockedExchange(&phase,p);InterlockedExchange(&sequence,seq);volatile int observed=kind;(void)observed;}
static void OnGC(void*,int event,int){
 if(event==0)InterlockedIncrement64(&stats[0]);if(event==5)InterlockedIncrement64(&stats[1]);
 if(event==1)InterlockedIncrement64(&stats[2]);if(event==2)InterlockedIncrement64(&stats[3]);
 LONG64 index=InterlockedIncrement64(&stats[6])-1;
 if(index>=65536){InterlockedIncrement64(&stats[5]);return;}
 events[index]={event,InterlockedCompareExchange64(&stats[0],0,0),InterlockedCompareExchange64(&stats[1],0,0),InterlockedCompareExchange(&phase,0,0),InterlockedCompareExchange(&sequence,0,0)};
}
static void OnHeap(void*,long long){InterlockedIncrement64(&stats[7]);}
static void Shutdown(void*){}
extern "C" __declspec(dllexport) int WB_Install(){
 HMODULE module=GetModuleHandleW(L"GameAssembly.dll");if(!module)return -1;
 using Install=void(*)(void*,void(*)(void*));using GCInstall=void(*)(void(*)(void*,int,int),void(*)(void*,long long));using SetEvents=void(*)(int);
 auto install=(Install)GetProcAddress(module,"il2cpp_profiler_install");auto gc=(GCInstall)GetProcAddress(module,"il2cpp_profiler_install_gc");auto enable=(SetEvents)GetProcAddress(module,"il2cpp_profiler_set_events");
 if(!install || !gc || !enable)return -2;install((void*)stats,Shutdown);gc(OnGC,OnHeap);enable(1<<8);return 1;
}
extern "C" __declspec(dllexport) LONG64 WB_Query(int item){return item>=0 && item<8?InterlockedCompareExchange64(&stats[item],0,0):-1;}
extern "C" __declspec(dllexport) LONG64 WB_Event(int index,int item){if(index<0 || index>=65536 || item<0 || item>4)return -1;return ((LONG64*)&events[index])[item];}

extern "C" __declspec(dllexport) __declspec(noinline) int WB_ScrubStack(){volatile ULONG_PTR clear[8192];for(int i=0;i<8192;i++)clear[i]=0;return (int)clear[8191];}
