using System;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEngine;
public sealed class EHRunner:MonoBehaviour {
 [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)] static void Boot(){new GameObject("ExceptionLab").AddComponent<EHRunner>();}
 static string Arg(string name){var a=Environment.GetCommandLineArgs();for(int i=0;i+1<a.Length;i++)if(a[i]==name)return a[i+1];throw new Exception("Missing "+name);}
 void Start(){
  try{
   string route=Arg("--eh-route"),fault=Arg("--eh-fault");if(!new[]{"aa","hh","ha","ah"}.Contains(route)||!new[]{"body","manual","cctor","cctor-ret"}.Contains(fault))throw new Exception("Unknown case");
   var env=JsonUtility.FromJson<EHRow>(File.ReadAllText(Path.Combine(Application.streamingAssetsPath,"eh-build.json")));env.kind="env";env.route=route;env.fault=fault;env.unity=Application.unityVersion;env.hot_before=AppDomain.CurrentDomain.GetAssemblies().Any(a=>a.GetName().Name=="HotUpdate");EHEvents.Write(env);
   Action<string,int> run;
   if(route=="aa")run=EHAot.Cases.RunOwn;
   else{
    var hot=Assembly.Load(File.ReadAllBytes(Path.Combine(Application.streamingAssetsPath,"HotUpdate.dll.bytes")));var cases=hot.GetType("EHHot.Cases",true);
    if(route=="ah"){
     var targets=hot.GetType("EHHot.Targets",true);string name=fault=="body"?"Body":fault=="manual"?"Manual":fault=="cctor"?"CctorThunk":"CctorRetThunk";
     EHAot.Cases.HotTarget=(Action)Delegate.CreateDelegate(typeof(Action),targets.GetMethod(name));run=EHAot.Cases.RunDelegate;
    }else run=(Action<string,int>)Delegate.CreateDelegate(typeof(Action<string,int>),cases.GetMethod(route=="hh"?"RunOwn":"RunAot"));
   }
   for(int n=1;n<=2;n++){
    EHEvents.Write(new EHRow{kind="attempt",value=n});
    try{run(fault,n);EHEvents.Write(new EHRow{kind="return"});}catch(Exception e){EHEvents.Exception("escape","driver",e);}
   }
   EHEvents.Write(new EHRow{kind="done",completed=true});Application.Quit(0);
  }catch(Exception e){Debug.LogError("EHF_FATAL "+e);Application.Quit(2);}
 }
}
