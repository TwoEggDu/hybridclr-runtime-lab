using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading;
using UnityEngine;
public sealed class ConcurrentRunner:MonoBehaviour {
 [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)] static void Boot(){new GameObject("ConcurrentLab").AddComponent<ConcurrentRunner>();}
 static string Arg(string key){var a=Environment.GetCommandLineArgs();for(int i=0;i<a.Length-1;i++)if(a[i]==key)return a[i+1];throw new Exception("Missing "+key);}
 void Start(){try{Run();Application.Quit(0);}catch(Exception e){Debug.LogError("CIP_FATAL "+e);Application.Quit(2);}}
 void Run(){
  string side=Arg("--side"),mode=Arg("--mode");int n=int.Parse(Arg("--workers"));
  if(!(n==2||n==4)||!(side=="aot"||side=="hot"||side=="mixed")||!new[]{"cold","strict","failed","generic"}.Contains(mode)||side=="mixed"&&mode!="strict")throw new Exception("Unknown cell");
  ConcurrentHub.Write(new ConcurrentRow{kind="env",side=side,mode=mode,nworkers=n,unity=Application.unityVersion,build=File.ReadAllText(Path.Combine(Application.streamingAssetsPath,"concurrent-build-id.txt")).Trim(),hot_before=AppDomain.CurrentDomain.GetAssemblies().Any(a=>a.GetName().Name=="HotUpdate")});
  Assembly hot=side=="aot"?null:Assembly.Load(File.ReadAllBytes(Path.Combine(Application.streamingAssetsPath,"HotUpdate.dll.bytes")));
  var assembly=side=="hot"?hot:typeof(ConcurrentRunner).Assembly;string ns=side=="hot"?"HotConcurrent":"AotConcurrent";
  Type[] types=mode=="generic"?new[]{assembly.GetType(ns+".Cache`1",true).MakeGenericType(typeof(int)),assembly.GetType(ns+".Cache`1",true).MakeGenericType(typeof(string))}:new[]{assembly.GetType(ns+"."+char.ToUpper(mode[0])+mode.Substring(1),true)};
  string[] subjects=types.Select(t=>mode=="generic"?ns+".Cache<"+t.GetGenericArguments()[0].FullName+">":t.FullName).ToArray();
  var methods=types.Select(t=>t.GetMethod("Read")).ToArray();
  foreach(var t in types)ConcurrentHub.Write(new ConcurrentRow{kind="meta",subject=subjects[Array.IndexOf(types,t)],bfi=(t.Attributes&TypeAttributes.BeforeFieldInit)!=0,cctor=t.TypeInitializer!=null});
  MethodInfo bridge=side=="mixed"?hot.GetType("HotConcurrent.Bridge",true).GetMethod("Read"):null;
  using(var gate=new ManualResetEvent(false))using(var ready=new CountdownEvent(n)){
   var workers=new Thread[n];
   for(int i=0;i<n;i++){int w=i;workers[i]=new Thread(()=>{
    try{
     ConcurrentHub.Write(new ConcurrentRow{kind="ready",worker=w});ready.Signal();
     if(!gate.WaitOne(30000))throw new TimeoutException("Gate timeout");
     ConcurrentHub.Write(new ConcurrentRow{kind="attempt",worker=w});
     for(int k=0;k<methods.Length;k++)Invoke(side=="mixed"&&w%2==1?bridge:methods[k],subjects[k],w);
    }catch(Exception e){Debug.LogError("CIP_FATAL worker="+w+" "+e);}
   });workers[i].IsBackground=true;workers[i].Start();}
   if(!ready.Wait(30000))throw new TimeoutException("Ready timeout");
   foreach(var m in methods)ConcurrentHub.BeforeRelease(m.MethodHandle.Value.ToInt64());
   if(bridge!=null)ConcurrentHub.BeforeRelease(bridge.MethodHandle.Value.ToInt64());
   ConcurrentHub.Write(new ConcurrentRow{kind="gate",phase="open"});gate.Set();
   for(int w=0;w<n;w++){bool ok=workers[w].Join(30000);ConcurrentHub.Write(new ConcurrentRow{kind="join",worker=w,joined=ok});if(!ok)throw new TimeoutException("Join timeout");}
   if(mode=="failed")for(int w=n;w<n+2;w++)Invoke(methods[0],subjects[0],w);
   foreach(var m in methods)ConcurrentHub.AfterJoin(m.MethodHandle.Value.ToInt64());
   if(bridge!=null)ConcurrentHub.AfterJoin(bridge.MethodHandle.Value.ToInt64());
  }
  ConcurrentHub.Write(new ConcurrentRow{kind="done",completed=true});
 }
 static void Invoke(MethodInfo method,string subject,int worker){try{int v=(int)method.Invoke(null,null);ConcurrentHub.Write(new ConcurrentRow{kind="result",subject=subject,worker=worker,value=v});}catch(TargetInvocationException e){ConcurrentHub.Caught(subject,worker,e);}}
}
