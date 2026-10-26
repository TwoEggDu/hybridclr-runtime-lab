using System;
using System.IO;
using System.Linq;
using System.Collections;
using System.Reflection;
using UnityEngine;
public sealed class ResourceRunner:MonoBehaviour {
 const string TypeName="ResourceHot.MountProbe";
 GameObject instance;AssetBundle bundle;Component restored;string mode,currentStage;bool loaded;int typed,missing;
 [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]static void Boot(){new GameObject("ResourceLabDriver").AddComponent<ResourceRunner>();}
 static Type ExistingType(){foreach(var a in AppDomain.CurrentDomain.GetAssemblies())if(a.GetName().Name=="HotUpdate"){var t=a.GetType(TypeName,false);if(t!=null)return t;}return null;}
 static string Argument(string name){var a=Environment.GetCommandLineArgs();for(int i=0;i+1<a.Length;i++)if(a[i]==name)return a[i+1];throw new Exception("Missing argument "+name);}
 IEnumerator Start(){
  Exception failure=null;
  try{Prepare();}catch(Exception e){failure=e;}
  if(failure!=null){Debug.LogError("RMP_FATAL stage="+currentStage+" "+failure);Application.Quit(2);yield break;}
  if(restored){instance.SetActive(true);yield return null;instance.SetActive(false);}
  if(instance)Destroy(instance);
  yield return null;
  if(bundle)bundle.Unload(false);
  ResourceEvents.Write(new ResourceRow{@event="result",restored=typed==1,typed=typed,missing=missing,hot_loaded=loaded});
  ResourceEvents.Write(new ResourceRow{@event="done",completed=true});
  Application.Quit(0);
 }
 void Stage(string s){currentStage=s;ResourceEvents.Write(new ResourceRow{@event="stage",stage=s});}
 void Prepare(){
  mode=Argument("--resource-mode");
  if(!new[]{"code","bundle","late","unregistered","resources"}.Contains(mode))throw new Exception("Invalid mode");
  string build=File.ReadAllText(Path.Combine(Application.streamingAssetsPath,"resource-build-id.txt")).Trim();
  string list=File.ReadAllText(Path.Combine(Application.dataPath,"ScriptingAssemblies.json"));
  ResourceEvents.Active=true;
  ResourceEvents.Write(new ResourceRow{@event="env",mode=mode,build=build,hot_before=ExistingType()!=null,assembly_name_before=AppDomain.CurrentDomain.GetAssemblies().Any(a=>a.GetName().Name=="HotUpdate"),registration=list.Contains("\"HotUpdate.dll\""),unity=Application.unityVersion});
  Type type=null;
  if(mode!="late"){
   Stage("Assembly.Load");var a=Assembly.Load(File.ReadAllBytes(Path.Combine(Application.streamingAssetsPath,"HotUpdate.dll.bytes")));loaded=true;
   type=a.GetType(TypeName,true);ResourceEvents.Write(new ResourceRow{@event="dll",name=a.GetName().Name});
   var ping=(string)type.GetMethod("Ping",BindingFlags.Public|BindingFlags.Static).Invoke(null,null);
   ResourceEvents.Write(new ResourceRow{@event="ping",value=ping});
  }
  if(mode=="code"){
   instance=new GameObject("CodeProbe");instance.SetActive(false);var anchor=new GameObject("Anchor").transform;anchor.SetParent(instance.transform,false);
   var c=instance.AddComponent(type);type.GetField("Number").SetValue(c,7);type.GetField("Label").SetValue(c,"code-runtime");type.GetField("Anchor").SetValue(c,anchor);type.GetField("Payload").SetValue(c,new TextAsset("resource-payload-v1"){name="Payload"});
  }else{
   GameObject prefab;
   if(mode=="resources"){Stage("Resources.Load");prefab=Resources.Load<GameObject>("MainPackageProbe");}
   else {Stage("AssetBundle.LoadFromFile");bundle=AssetBundle.LoadFromFile(Path.Combine(Application.streamingAssetsPath,"resource-probe.bundle"));if(!bundle)throw new Exception("Bundle load failed");Stage("AssetBundle.LoadAsset");prefab=bundle.LoadAsset<GameObject>("Assets/Fixtures/BundleProbe.prefab");}
   int assetTyped=0,assetMissing=0;if(prefab)foreach(var c in prefab.GetComponents<Component>()){if(!c)assetMissing++;else if(c.GetType().FullName==TypeName)assetTyped++;}
   ResourceEvents.Write(new ResourceRow{@event="asset",stage=mode=="resources"?"Resources.Load":"AssetBundle.LoadAsset",value=prefab?prefab.name:"null",typed=assetTyped,missing=assetMissing,restored=assetTyped==1});
   if(!prefab)throw new Exception("Prefab load failed");Stage("Instantiate");instance=Instantiate(prefab);instance.name="ResourceInstance";
  }
  ResourceEvents.Write(new ResourceRow{@event="instantiate",value="ResourceInstance"});
  foreach(var c in instance.GetComponents<Component>()){
   if(!c){missing++;continue;}
   if(c.GetType().FullName==TypeName){typed++;restored=c;}
  }
  if(restored){
   var t=restored.GetType();var anchor=(Transform)t.GetField("Anchor").GetValue(restored);var payload=(TextAsset)t.GetField("Payload").GetValue(restored);
   ResourceEvents.Write(new ResourceRow{@event="snapshot",instance=restored.GetInstanceID(),number=(int)t.GetField("Number").GetValue(restored),label=(string)t.GetField("Label").GetValue(restored),anchor=anchor?anchor.name:"",payload=payload?payload.text.Trim():"",payload_name=payload?payload.name:"",anchor_matches=anchor==instance.transform.Find("Anchor"),type=t.FullName,assembly=t.Assembly.GetName().Name});
  }
 }
}
