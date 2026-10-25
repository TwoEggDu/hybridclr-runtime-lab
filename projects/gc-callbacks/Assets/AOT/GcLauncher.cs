using System;
using System.Collections;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Threading;
using UnityEngine;
using UnityEngine.Scripting;
using Debug=UnityEngine.Debug;
public sealed class GcLauncher:MonoBehaviour {
 [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]static void Boot(){new GameObject("GcCallbackExperiment").AddComponent<GcLauncher>();}
 static void ShortWorker(Action action){Exception failure=null;var t=new Thread(()=>{try{action();}catch(Exception e){failure=e;}});t.IsBackground=true;t.Start();if(!t.Join(60000))throw new TimeoutException("Creator");if(failure!=null)throw new Exception("Creator failed",failure);}
 static void Full(){GC.Collect();GC.WaitForPendingFinalizers();}
 static void Abort(Exception e){
  Debug.LogException(e);bool safe=!GcState.NativeStarted;
  if(!safe){GcState.NP_Stop();GcState.Resume.Set();safe=GcState.NP_Join(30000)==1;}
  if(safe){GcState.NativeStarted=false;GcState.FreeContext();GcState.Root=null;}
  Application.Quit(2);
 }
 IEnumerator Start(){
  IEnumerator routine;
  try{routine=Experiment();}catch(Exception e){Abort(e);yield break;}
  while(true){bool more;try{more=routine.MoveNext();}catch(Exception e){Abort(e);yield break;}if(!more)break;yield return routine.Current;}
 }
 IEnumerator Experiment(){
  var args=Environment.GetCommandLineArgs();string mode="handle";
  if(Array.IndexOf(args,"--stack")>=0)mode="stack";if(Array.IndexOf(args,"--stress")>=0)mode="stress";
  int kind=mode=="handle"?0:mode=="stack"?1:2;GcState.Limit=kind==0?2:kind==1?1:1024;
  Debug.Log("GCP_ENV mode="+mode+" unity="+Application.unityVersion+" incremental="+GarbageCollector.isIncremental+" gcMode="+GarbageCollector.GCMode);
  var bytes=File.ReadAllBytes(Path.Combine(Application.streamingAssetsPath,"HotUpdate.dll.bytes"));var assembly=Assembly.Load(bytes);var entry=assembly.GetType("GcHot.Entry",true);
  GcState.Root=(GcState.Callback)Delegate.CreateDelegate(typeof(GcState.Callback),entry.GetMethod("Call"));
  var pointer=Marshal.GetFunctionPointerForDelegate(GcState.Root);
  if(kind!=1){var create=entry.GetMethod("CreateContext");ShortWorker(()=>GcState.Context=(IntPtr)create.Invoke(null,null));}
  Debug.Log("GCP_LOAD bytes="+bytes.Length+" assembly="+assembly.GetName().Name+" pointer="+pointer.ToInt64()+" context="+GcState.Context.ToInt64());
  Debug.Log("GCP_MAIN managed="+Thread.CurrentThread.ManagedThreadId+" native="+GcState.GetCurrentThreadId());
  if(kind!=1){for(int i=0;i<3;i++){Full();yield return null;}bool held=GcState.Alive();Debug.Log("GCP_HELD stage=before alive="+held+" full=3");if(!held)throw new Exception("Context lost before callbacks");}
  int cyclesBefore=GC.CollectionCount(0);
  if(GcState.NP_Start(pointer,GcState.Context,kind,GcState.Limit)!=1)throw new Exception("Start failed");GcState.NativeStarted=true;
  var watch=Stopwatch.StartNew();int checkpoints=0;
  while(true){
   while(!GcState.Ready.WaitOne(0)){if(watch.ElapsedMilliseconds>60000 || GcState.NP_Errors()!=0)throw new Exception("Checkpoint missing");yield return null;}
   int seq=Volatile.Read(ref GcState.Sequence);int full=0,slices=0,more=0;
   if(kind==2){for(int i=0;i<4;i++){if(GarbageCollector.CollectIncremental(1000000))more++;slices++;yield return null;}}
   else {for(int i=0;i<3;i++){Full();full++;yield return null;}}
   bool alive=GcState.Alive();Debug.Log("GCP_CHECK seq="+seq+" alive="+alive+" full="+full+" slices="+slices+" more="+more);if(!alive)throw new Exception("Live target lost");checkpoints++;
   if(seq==GcState.Limit){
    int stopped=GcState.NP_Stop();int before=GcState.NP_Join(0);
    Debug.Log("GCP_STOP joinedBefore="+(before==1)+" requested="+stopped);
    if(before!=0 || stopped!=1)throw new Exception("Stop protocol");
    yield return null;GcState.Resume.Set();break;
   }
   GcState.Resume.Set();yield return null;
  }
  int joined;
  while((joined=GcState.NP_Join(0))==0){if(watch.ElapsedMilliseconds>60000)throw new TimeoutException("Join");yield return null;}
  if(joined!=1)throw new Exception("Join failed");GcState.NativeStarted=false;
  int cyclesAfter=GC.CollectionCount(0);
  Debug.Log("GCP_GC before="+cyclesBefore+" after="+cyclesAfter+" delta="+(cyclesAfter-cyclesBefore));
  int count=GcState.NP_Count(),errors=GcState.NP_Errors();long checksum=GcState.NP_Checksum();
  Debug.Log("GCP_JOIN count="+count+" checksum="+checksum+" errors="+errors+" native="+GcState.NP_Thread()+" joined=True");
  if(count!=GcState.Limit || errors!=0 || GcState.Failures!=0 || checksum!=(kind==0?149:kind==1?257:786944) || checkpoints!=(kind==2?32:1))throw new Exception("Result mismatch");
  if(kind!=1){
   for(int i=0;i<3;i++){Full();yield return null;}bool held=GcState.Alive();Debug.Log("GCP_HELD stage=after alive="+held+" full=3");if(!held)throw new Exception("Held context lost after join");
   ShortWorker(GcState.FreeContext);Debug.Log("GCP_HANDLE_FREE afterJoin=True");
  }
  for(int i=0;i<3;i++){Full();yield return null;}
  Debug.Log("GCP_RELEASED alive="+GcState.Alive()+" full=3");
  GcState.Root=null;Debug.Log("GCP_DELEGATE_RELEASE afterJoin=True");Debug.Log("GCP_DONE mode="+mode+" failures=0");Application.Quit(0);
 }
}
