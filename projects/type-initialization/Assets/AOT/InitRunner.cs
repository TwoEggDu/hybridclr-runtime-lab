using System;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEngine;
public sealed class InitRunner:MonoBehaviour {
 [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)] static void Boot(){new GameObject("InitLab").AddComponent<InitRunner>();}
 static string Argument(string name){var args=Environment.GetCommandLineArgs();for(int i=0;i+1<args.Length;i++)if(args[i]==name)return args[i+1];throw new Exception("Missing "+name);}
 void Start(){
  try {
   string side=Argument("--init-side"),mode=Argument("--init-mode");
   if(!new[]{"aot","hot"}.Contains(side)||!new[]{"strict","relaxed","generic","failed","failed-outer"}.Contains(mode))throw new Exception("Unknown case");
   InitEvents.Write(new InitRow{kind="env",side=side,mode=mode,build=File.ReadAllText(Path.Combine(Application.streamingAssetsPath,"init-build-id.txt")).Trim(),unity=Application.unityVersion,hot_before=AppDomain.CurrentDomain.GetAssemblies().Any(a=>a.GetName().Name=="HotUpdate")});
   InitEvents.Stage("before_load");
   Assembly assembly=side=="hot"?Assembly.Load(File.ReadAllBytes(Path.Combine(Application.streamingAssetsPath,"HotUpdate.dll.bytes"))):typeof(InitRunner).Assembly;
   InitEvents.Stage("after_load");
   var type=assembly.GetType((side=="hot"?"HotInit":"AotInit")+".Cases",true);
   var entry=type.GetMethod("Run",BindingFlags.Public|BindingFlags.Static);
   InitEvents.Stage("after_resolve");
   if(mode=="failed-outer"){
    var failed=assembly.GetType((side=="hot"?"HotInit":"AotInit")+".Failed",true);
    InitEvents.Write(new InitRow{kind="meta",subject=failed.Name,bfi=(failed.Attributes&TypeAttributes.BeforeFieldInit)!=0,cctor=failed.TypeInitializer!=null});
    var access=type.GetMethod("AccessFailed",BindingFlags.Public|BindingFlags.Static);
    for(int n=1;n<=2;n++){
     InitEvents.Stage("before_call"+n);
     try{access.Invoke(null,null);throw new Exception("Expected failure was absent");}
     catch(TargetInvocationException e){InitEvents.Caught("call"+n,e);}
    }
   }else{
    try{entry.Invoke(null,new object[]{mode});}
    catch(TargetInvocationException e){
     if(mode!="failed")throw;
     InitEvents.Caught("outer_entry",e,"escaped");InitEvents.Write(new InitRow{kind="done",completed=false});Application.Quit(2);return;
    }
   }
   InitEvents.Write(new InitRow{kind="done",completed=true});Application.Quit(0);
  }catch(Exception e){Debug.LogError("TIP_FATAL "+e);Application.Quit(2);}
 }
}
