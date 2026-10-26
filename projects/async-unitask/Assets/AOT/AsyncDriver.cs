using System;
using System.IO;
using System.Linq;
using System.Reflection;
using Cysharp.Threading.Tasks;
using HybridCLR;
using UnityEngine;
public sealed class AsyncDriver:MonoBehaviour {
 UniTask consumer;bool ready,entryError,released;int startFrame;float started;
 [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]static void Boot(){new GameObject("AsyncLab").AddComponent<AsyncDriver>();}
 static string Arg(string name){var a=Environment.GetCommandLineArgs();for(int i=0;i+1<a.Length;i++)if(a[i]==name)return a[i+1];throw new Exception("Missing "+name);}
 void Start(){
  started=Time.realtimeSinceStartup;
  UniTaskScheduler.UnobservedTaskException+=e=>{Debug.LogError("AUT_UNOBSERVED "+e);Application.Quit(3);};
  try {
   string side=Arg("--async-side"),mode=Arg("--async-mode"),metadata=Arg("--async-metadata");
   if(!new[]{"aot","hot-dev","hot-release"}.Contains(side)||!new[]{"sync","frame","throw-before","throw-after"}.Contains(mode)||!new[]{"on","off"}.Contains(metadata))throw new Exception("Unknown mode");
   AsyncEvents.Write(new AsyncRow{kind="env",side=side,mode=mode,metadata=metadata,build=File.ReadAllText(Path.Combine(Application.streamingAssetsPath,"async-build-id.txt")).Trim(),unity=Application.unityVersion,hot_before=AppDomain.CurrentDomain.GetAssemblies().Any(a=>a.GetName().Name=="HotUpdate")});
   if(metadata=="on"){
    var code=RuntimeApi.LoadMetadataForAOTAssembly(File.ReadAllBytes(Path.Combine(Application.streamingAssetsPath,"UniTask.dll.bytes")),HomologousImageMode.SuperSet);
    AsyncEvents.Write(new AsyncRow{kind="metadata",label="UniTask",value=(int)code,detail="Superset"});
    if(code!=LoadImageErrorCode.OK)throw new Exception("Metadata rejected "+code);
   }
   Func<string,UniTask<int>> entry;
   if(side=="aot")entry=AotAsync.Cases.Work;
   else {
    var assembly=Assembly.Load(File.ReadAllBytes(Path.Combine(Application.streamingAssetsPath,side+".dll.bytes")));
    entry=(Func<string,UniTask<int>>)Delegate.CreateDelegate(typeof(Func<string,UniTask<int>>),assembly.GetType("HotAsync.Cases",true).GetMethod("Work"));
   }
   AsyncEvents.Gate=new ProbeGate();startFrame=Time.frameCount;
   UniTask<int> task;
   try{task=entry(mode);}
   catch(Exception e){AsyncEvents.Error("entry_error",e);entryError=true;ready=true;return;}
   AsyncEvents.Log("entry_return",task.Status.ToString());
   consumer=Consume(task);AsyncEvents.Log("waiting",consumer.Status.ToString());ready=true;
  }catch(Exception e){Debug.LogError("AUT_FATAL "+e);Application.Quit(2);}
 }
 static async UniTask Consume(UniTask<int> task){
  AsyncEvents.Log("consumer_begin");
  try{int result=await task;AsyncEvents.Log("consumer_result","",result);}
  catch(Exception e){AsyncEvents.Error("consumer_caught",e);}
  finally{AsyncEvents.Log("consumer_finally");}
 }
 void Update(){
  if(!ready)return;
  try{
   if(!entryError && consumer.Status==UniTaskStatus.Pending && !released && Time.frameCount>=startFrame+2){released=true;AsyncEvents.Gate.Complete();}
   if(entryError || consumer.Status!=UniTaskStatus.Pending){
    ready=false;if(!entryError)consumer.GetAwaiter().GetResult();AsyncEvents.Log("done","",0);Application.Quit(0);
   }
   else if(Time.realtimeSinceStartup-started>20)throw new Exception("Async timeout");
  }catch(Exception e){ready=false;Debug.LogError("AUT_FATAL "+e);Application.Quit(2);}
 }
}
