using System;
using UnityEngine;
[Serializable] public sealed class ResourceRow {
 public string @event,mode,build,name,value,label,anchor,payload,type,assembly,unity,stage,payload_name;
 public int instance,number,typed,missing;
 public bool hot_before,registration,restored,hot_loaded,completed,assembly_name_before,anchor_matches;
}
public static class ResourceEvents {
 public static bool Active;
 public static void Write(ResourceRow row){Debug.Log("RMP "+JsonUtility.ToJson(row));}
 public static void Life(string name,Component c,int number,string label,Transform anchor,TextAsset payload){
  if(!Active)return;
  Write(new ResourceRow{@event="life",name=name,instance=c.GetInstanceID(),number=number,label=label,anchor=anchor?anchor.name:"",payload=payload?payload.text.Trim():"",type=c.GetType().FullName,assembly=c.GetType().Assembly.GetName().Name});
 }
}
