using System;
using System.IO;
using System.Linq;
using System.Reflection;
using HybridCLR;
using UnityEngine;
public sealed class BoxDriver:MonoBehaviour {
 [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]static void Boot(){new GameObject("BoxLab").AddComponent<BoxDriver>();}
 static string Arg(string name){var a=Environment.GetCommandLineArgs();for(int i=0;i+1<a.Length;i++)if(a[i]==name)return a[i+1];throw new Exception("Missing "+name);}
 void Start(){
  try{
   string route=Arg("--box-route"),mode=Arg("--box-mode"),metadata=Arg("--box-metadata");
   if(!new[]{"aot","hot","cross"}.Contains(route)||!new[]{"value","ref","box","text-override","text-fallback","reference"}.Contains(mode)||!new[]{"off","on"}.Contains(metadata))throw new Exception("Unknown mode");
   BoxEvents.Write(new BoxRow{kind="env",route=route,mode=mode,metadata=metadata,build=File.ReadAllText(Path.Combine(Application.streamingAssetsPath,"box-build-id.txt")).Trim(),unity=Application.unityVersion,hot_before=AppDomain.CurrentDomain.GetAssemblies().Any(a=>a.GetName().Name=="HotUpdate")});
   if(metadata=="on"){
    var code=RuntimeApi.LoadMetadataForAOTAssembly(File.ReadAllBytes(Path.Combine(Application.streamingAssetsPath,"Probe.AOT.dll.bytes")),HomologousImageMode.SuperSet);
    BoxEvents.Write(new BoxRow{kind="metadata",label="Probe.AOT",value=(int)code,detail="Superset"});if(code!=LoadImageErrorCode.OK)throw new Exception("Metadata rejected");
   }
   Action<string,string> entry;
   if(route=="aot")entry=AotBox.Cases.Run;
   else{var asm=Assembly.Load(File.ReadAllBytes(Path.Combine(Application.streamingAssetsPath,"HotUpdate.dll.bytes")));entry=(Action<string,string>)Delegate.CreateDelegate(typeof(Action<string,string>),asm.GetType("HotBox.Cases",true).GetMethod("Run"));}
   try{entry(mode,route);}catch(Exception e){BoxEvents.Write(new BoxRow{kind="error",type=e.GetType().FullName,detail=e.Message});}
   BoxEvents.Write(new BoxRow{kind="done",value=0});Application.Quit(0);
  }catch(Exception e){Debug.LogError("CBX_FATAL "+e);Application.Quit(2);}
 }
}
