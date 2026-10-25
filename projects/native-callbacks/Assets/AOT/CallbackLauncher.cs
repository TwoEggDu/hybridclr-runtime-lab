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
public sealed class CallbackLauncher:MonoBehaviour {
 [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
 static void Boot() { new GameObject("CallbackExperiment").AddComponent<CallbackLauncher>(); }
 IEnumerator Start() {
  string mode=Array.IndexOf(Environment.GetCommandLineArgs(),"--raw")>=0 ? "raw" : "registered";
  IEnumerator work;
  try {
   Debug.Log("CB_ENV mode="+mode+" unity="+Application.unityVersion+" incremental="+GarbageCollector.isIncremental+" gcMode="+GarbageCollector.GCMode);
   var bytes=File.ReadAllBytes(Path.Combine(Application.streamingAssetsPath,"HotUpdate.dll.bytes"));
   var assembly=Assembly.Load(bytes); var method=assembly.GetType("CallbackHot.NativeEntry",true).GetMethod("Call");
   ProbeState.Root=(ProbeState.Callback)Delegate.CreateDelegate(typeof(ProbeState.Callback),method);
   var pointer=Marshal.GetFunctionPointerForDelegate(ProbeState.Root);
   Debug.Log("CB_LOAD bytes="+bytes.Length+" assembly="+assembly.GetName().Name+" pointer="+pointer.ToInt64());
   Debug.Log("CB_MAIN managed="+Thread.CurrentThread.ManagedThreadId+" native="+ProbeState.GetCurrentThreadId());
   work=mode=="raw" ? Raw(pointer) : Registered(pointer);
  } catch(Exception e) { Abort(e);yield break; }
  while(true) {
   bool more;
   try { more=work.MoveNext(); }
   catch(Exception e) { Abort(e);yield break; }
   if(!more) break; yield return work.Current;
  }
  foreach(var line in ProbeState.Snapshot()) Debug.Log(line);
  if(ProbeState.Failures!=0) { Debug.LogError("Callback failure");Application.Quit(2);yield break; }
  ProbeState.Root=null; Debug.Log("CB_RELEASE afterJoin=True");
  Debug.Log("CB_DONE mode="+mode+" failures=0");Application.Quit(0);
 }
 static void Abort(Exception e) {
  Debug.LogException(e);
  if(ProbeState.NativeStarted) {
   ProbeState.NP_Stop();ProbeState.Release.Set();
   if(ProbeState.NP_Join(30000)==1) { ProbeState.NativeStarted=false;ProbeState.Root=null; }
  }
  Application.Quit(2);
 }
 static IEnumerator Registered(IntPtr cb) {
  int before=0,after=0,result=0;uint native=0;Exception failure=null;
  var worker=new Thread(()=> {
   try { before=Thread.CurrentThread.ManagedThreadId;native=ProbeState.GetCurrentThreadId();result=ProbeState.NP_Inline(cb);after=Thread.CurrentThread.ManagedThreadId; }
   catch(Exception e) { failure=e; }
  });worker.IsBackground=true;worker.Start();
  bool joined=worker.Join(30000);
  if(!joined || failure!=null || before!=after || result!=50015) throw new Exception("Registered worker failed",failure);
  Debug.Log("CB_OWNER before="+before+" after="+after+" native="+native+" result="+result+" joined="+joined);
  yield return null;
 }
 static IEnumerator Raw(IntPtr cb) {
  if(ProbeState.NP_Start(cb)!=1) throw new Exception("Native start failed");
  ProbeState.NativeStarted=true;
  var watch=Stopwatch.StartNew();
  while(!ProbeState.Entered.WaitOne(0)) { if(watch.ElapsedMilliseconds>30000) throw new TimeoutException("No in-flight callback");yield return null; }
  int stopped=ProbeState.NP_Stop();bool joinedBefore=ProbeState.NP_Join(0)==1;
  Debug.Log("CB_STOP entered=True joinedBefore="+joinedBefore+" requested="+stopped);
  // A frame passes with the callback held and the delegate still rooted.
  yield return null;ProbeState.Release.Set();
  int joined=0;
  while((joined=ProbeState.NP_Join(0))==0) { if(watch.ElapsedMilliseconds>30000) throw new TimeoutException("Native join timed out");yield return null; }
  if(joined!=1 || joinedBefore || stopped!=1 || ProbeState.NP_Count()!=3 || ProbeState.NP_Result(0)!=5 || ProbeState.NP_Result(1)!=15 || ProbeState.NP_Result(2)!=23) throw new Exception("Raw worker failed");
  ProbeState.NativeStarted=false;
  Debug.Log("CB_RAW native="+ProbeState.NP_Thread()+" count="+ProbeState.NP_Count()+" first="+ProbeState.NP_Result(0)+" second="+ProbeState.NP_Result(1)+" third="+ProbeState.NP_Result(2)+" joined=True");
 }
}
