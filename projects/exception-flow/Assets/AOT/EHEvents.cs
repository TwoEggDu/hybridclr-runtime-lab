using System;
using UnityEngine;
[Serializable] public sealed class EHRow {
 public int seq,value;public string kind,route,fault,variant,build,unity,origin,type,detail;public bool hot_before,completed;
}
public static class EHEvents {
 static int sequence;public static bool BranchFlag;
 public static int Value(string origin,int value){Emit("unexpected_body",origin);return value;}
 public static void Write(EHRow row){row.seq=++sequence;Debug.Log("EHF "+JsonUtility.ToJson(row));}
 public static void Emit(string kind,string origin){Write(new EHRow{kind=kind,origin=origin});}
 public static void Exception(string kind,string origin,Exception e){string chain=e.GetType().FullName;for(var x=e.InnerException;x!=null;x=x.InnerException)chain+=">"+x.GetType().FullName;Write(new EHRow{kind=kind,origin=origin,type=e.GetType().FullName,detail=chain});}
}
