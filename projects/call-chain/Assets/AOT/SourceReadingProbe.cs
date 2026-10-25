using System;
using System.IO;
using System.Reflection;
using UnityEngine;
public static class SourceReadingProbe {
 [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
 static void Run() {
  try {
   var path=Path.Combine(Application.streamingAssetsPath,"HotUpdate.dll.bytes");
   var bytes=File.ReadAllBytes(path);
   Debug.Log("PROBE_LOAD bytes="+bytes.Length);
   var assembly=Assembly.Load(bytes);
   var method=assembly.GetType("HotUpdate.ReadingProbe",true).GetMethod("Add",BindingFlags.Public|BindingFlags.Static);
   Debug.Log("PROBE_BEFORE_FIRST "+method);
   var first=(int)method.Invoke(null,new object[]{2,3});
   Debug.Log("PROBE_FIRST="+first);
   Debug.Log("PROBE_BEFORE_SECOND "+method);
   var second=(int)method.Invoke(null,new object[]{7,8});
   Debug.Log("PROBE_SECOND="+second);
   if(first!=5 || second!=15) throw new Exception("Unexpected result");
   Debug.Log("PROBE_PASS"); Application.Quit(0);
  } catch(Exception e) { Debug.LogException(e); Application.Quit(2); }
 }
}
