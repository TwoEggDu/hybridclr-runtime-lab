using System;
using System.Collections;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Threading;
using UnityEngine;
using UnityEngine.Scripting;
public sealed class LifetimeLauncher : MonoBehaviour
{
 [DllImport("kernel32.dll")] static extern uint GetCurrentThreadId();
 MethodInfo create, add;
 string mode;
 [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
 static void Boot() { new GameObject("LifetimeExperiment").AddComponent<LifetimeLauncher>(); }
 IEnumerator Start()
 {
  IEnumerator routine;
  try
  {
   mode=Array.IndexOf(Environment.GetCommandLineArgs(),"--threads")>=0 ? "threads" : "gc";
   Debug.Log("LIFE_ENV mode="+mode+" unity="+Application.unityVersion+" incremental="+GarbageCollector.isIncremental+" gcMode="+GarbageCollector.GCMode);
   var bytes=File.ReadAllBytes(Path.Combine(Application.streamingAssetsPath,"HotUpdate.dll.bytes"));
   var assembly=Assembly.Load(bytes);
   var type=assembly.GetType("LifetimeHot.Samples",true);
   create=type.GetMethod("CreateTargets"); add=type.GetMethod("Add");
   Debug.Log("LIFE_LOAD bytes="+bytes.Length+" assembly="+assembly.GetName().Name);
   routine=mode=="gc" ? GcExperiment() : ThreadExperiment();
  }
  catch(Exception e) { Debug.LogException(e); Application.Quit(2); yield break; }
  while(true)
  {
   bool more;
   try { more=routine.MoveNext(); }
   catch(Exception e) { Debug.LogException(e); Application.Quit(2); yield break; }
   if(!more) break;
   yield return routine.Current;
  }
  Debug.Log("LIFE_DONE mode="+mode+" failures=0");
  Application.Quit(0);
 }
 static void ShortWorker(Action action)
 {
  Exception failure=null;
  var thread=new Thread(()=> { try { action(); } catch(Exception ex) { failure=ex; } });
  thread.IsBackground=true; thread.Start();
  if(!thread.Join(30000)) throw new TimeoutException("Short worker timed out");
  if(failure!=null) throw new InvalidOperationException("Short worker failed",failure);
 }
 IEnumerator GcExperiment()
 {
  ShortWorker(()=>create.Invoke(null,null));
  foreach(var stage in new[]{"held","static-cleared","all-cleared"})
  {
   if(stage=="static-cleared") ShortWorker(RetentionHub.ClearStatic);
   if(stage=="all-cleared") ShortWorker(RetentionHub.ClearEvent);
   for(int round=0;round<3;round++) { yield return null; GC.Collect(); GC.WaitForPendingFinalizers(); }
   yield return null;
   int a=RetentionHub.Alive(0),b=RetentionHub.Alive(1),c=RetentionHub.Alive(2);
   Debug.Log("LIFE_GC stage="+stage+" none="+a+" static="+b+" event="+c+" rounds=3");
   if(stage=="held" && b!=16 || stage!="all-cleared" && c!=16) throw new Exception("Held target lost");
  }
 }
 sealed class WorkerResult { public int Managed,First,Second; public uint Native; public Exception Failure; public bool Joined; }
 IEnumerator ThreadExperiment()
 {
  int caller=Thread.CurrentThread.ManagedThreadId; uint native=GetCurrentThreadId();
  Debug.Log("LIFE_MAIN managed="+caller+" native="+native);
  using(var firstDone=new ManualResetEvent(false))
  using(var secondDone=new ManualResetEvent(false))
  using(var release=new ManualResetEvent(false))
  {
   var results=new[]{new WorkerResult(),new WorkerResult()};
   var workers=new Thread[2];
   for(int i=0;i<2;i++)
   {
    int index=i;
    workers[i]=new Thread(()=>
    {
     var r=results[index];
     try
     {
      r.Managed=Thread.CurrentThread.ManagedThreadId;r.Native=GetCurrentThreadId();
      if(index==1 && !firstDone.WaitOne(30000)) throw new TimeoutException("First worker not done");
      r.First=(int)add.Invoke(null,new object[]{2,3});
      r.Second=(int)add.Invoke(null,new object[]{7,8});
     }
     catch(Exception e) { r.Failure=e; }
     finally { (index==0 ? firstDone : secondDone).Set(); }
     if(!release.WaitOne(30000)) r.Failure=new TimeoutException("Release not signaled");
    });
    workers[i].IsBackground=true;workers[i].Start();
   }
   bool completed=secondDone.WaitOne(30000);release.Set();
   for(int i=0;i<2;i++) results[i].Joined=workers[i].Join(30000);
   if(!completed) throw new TimeoutException("Worker experiment timed out");
   for(int i=0;i<2;i++)
   {
    var r=results[i];
    if(r.Failure!=null) throw new InvalidOperationException("Worker failed",r.Failure);
    Debug.Log("LIFE_WORKER index="+i+" managed="+r.Managed+" native="+r.Native+" first="+r.First+" second="+r.Second+" joined="+r.Joined);
    if(!r.Joined || r.Managed==caller || r.Native==native || r.First!=5 || r.Second!=15) throw new Exception("Worker result mismatch");
   }
   if(results[0].Managed==results[1].Managed || results[0].Native==results[1].Native) throw new Exception("Workers must be distinct");
  }
  yield return null;
 }
}
