using System;
using System.Collections;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using UnityEngine;
using UnityEngine.Scripting;
using Debug=UnityEngine.Debug;
public sealed class GcLauncher:MonoBehaviour {
 [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]static void Boot(){new GameObject("IncrementalBarrierExperiment").AddComponent<GcLauncher>();}
 static void Full(){GC.Collect();GC.WaitForPendingFinalizers();}
 static long Q(int i){return WbState.WB_Query(i);}
 static void Sample(string label,int seq,bool more){Debug.Log(label+" seq="+seq+" more="+more+" starts="+Q(0)+" ends="+Q(1)+" marks="+Q(2)+" markEnds="+Q(3)+" frame="+Time.frameCount);}
 IEnumerator Start(){
  var routine=Experiment();while(true){bool next;try{next=routine.MoveNext();}catch(Exception e){Debug.LogException(e);try{WbState.StopWorker();}catch(Exception stop){Debug.LogException(stop);}GarbageCollector.GCMode=GarbageCollector.Mode.Enabled;Application.Quit(2);yield break;}if(!next)break;yield return routine.Current;}
 }
 IEnumerator Experiment(){
  var args=Environment.GetCommandLineArgs();bool hot=Array.IndexOf(args,"--hot")>=0,probe=Array.IndexOf(args,"--probe")>=0;
  int heapCount=250000;int at=Array.IndexOf(args,"--heap");if(at>=0)heapCount=int.Parse(args[at+1]);if(heapCount<10000 || heapCount>1000000)throw new Exception("Heap bound");
  ulong budget=1000;at=Array.IndexOf(args,"--budget");if(at>=0)budget=ulong.Parse(args[at+1]);if(budget<1 || budget>1000000)throw new Exception("Budget bound");
  if(WbState.WB_Install()!=1)throw new Exception("GC profiler exports unavailable");
  GarbageCollector.GCMode=GarbageCollector.Mode.Manual;
  Debug.Log("WBI_ENV writer="+(hot?"hot":"aot")+" unity="+Application.unityVersion+" incremental="+GarbageCollector.isIncremental+" mode="+GarbageCollector.GCMode+" heap="+heapCount+" budget="+budget);
  if(!GarbageCollector.isIncremental)throw new Exception("Incremental disabled");
  var bytes=File.ReadAllBytes(Path.Combine(Application.streamingAssetsPath,"HotUpdate.dll.bytes"));var asm=Assembly.Load(bytes);
  var hotWriter=(WbState.Writer)Delegate.CreateDelegate(typeof(WbState.Writer),asm.GetType("WbHot.Entry",true).GetMethod("Write"));WbState.Writer writer=hot?hotWriter:WbState.Write;
  WbState.StartWorker(writer);WbState.PrepareOwner();Full();yield return null;WbState.PrepareHeap(heapCount);
  // Creator's native stack is gone before collection; candidate targets have only short weak handles here.
  WbState.PrepareCandidates();long completed=Q(3),starts=Q(0),ends=Q(1);Debug.Log("WBI_BASE completed="+completed+" starts="+starts+" ends="+ends);WbState.il2cpp_gc_set_max_time_slice_ns((long)budget);WbState.WB_Marker(1,0,0);WbState.il2cpp_gc_start_incremental_collection();Debug.Log("WBI_BEGIN requested=True completed="+Q(3));
 int writes=0,slices=0;var clock=Stopwatch.StartNew();
  for(int seq=1;seq<=12;seq++){
   bool more=GarbageCollector.CollectIncremental(budget);slices++;Sample("WBI_SLICE",seq,more);
   if(probe){yield return null;continue;}
   if(!more || Q(0)!=starts || Q(1)!=ends || Q(3)!=completed)throw new Exception("No same unfinished cycle at mutation");
   int kind=(seq-1)%3;WbState.WB_Marker(2,seq,kind);WbState.RunWriter(writer,seq,kind);writes++;
   Debug.Log("WBI_WRITE seq="+seq+" kind="+kind+" candidate="+(1000+seq)+" starts="+Q(0)+" ends="+Q(1)+" markEnds="+Q(3));
   if(Q(0)!=starts || Q(1)!=ends || Q(3)!=completed)throw new Exception("Cycle changed inside writer");yield return null;
  }
  while(true){bool more=WbState.il2cpp_gc_collect_a_little()!=0;slices++;if(!more)break;if(slices>8192 || clock.ElapsedMilliseconds>60000)throw new TimeoutException("Cycle did not finish");}
  WbState.WB_Marker(7,12,0);int checksum=probe?0:WbState.CheckGraph();int alive=WbState.Alive();Sample("WBI_END",slices,false);
  if(!probe && Q(3)!=completed+1)throw new Exception("Expected exactly one completed marking cycle");WbState.StopWorker();
  if(!probe){Debug.Log("WBI_GRAPH writes="+writes+" checksum="+checksum+" alive="+alive);if(checksum!=12078 || writes!=12)throw new Exception("Graph mismatch");}
  WbState.WB_Marker(5,0,0);for(int i=0;i<Q(6);i++)Debug.Log("WBI_EVENT index="+i+" event="+WbState.WB_Event(i,0)+" starts="+WbState.WB_Event(i,1)+" ends="+WbState.WB_Event(i,2)+" phase="+WbState.WB_Event(i,3)+" seq="+WbState.WB_Event(i,4));
  if(Q(5)!=0)throw new Exception("Observer event overflow");
  WbState.Release();for(int i=0;i<3;i++){Full();yield return null;}
  Debug.Log("WBI_RELEASE alive="+WbState.Alive());writer=null;hotWriter=null;GarbageCollector.GCMode=GarbageCollector.Mode.Enabled;
  Debug.Log("WBI_DONE writer="+(hot?"hot":"aot")+" probe="+probe+" failures=0");Application.Quit(0);
 }
}
