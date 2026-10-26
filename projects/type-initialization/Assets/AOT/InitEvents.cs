using System;
using UnityEngine;
[Serializable] public sealed class InitRow {
 public int seq,value;
 public string kind,side,mode,build,unity,phase,subject,type,detail;
 public bool hot_before,bfi,cctor,completed;
}
public static class InitEvents {
 static int sequence;
 public static void Write(InitRow row){row.seq=++sequence;Debug.Log("TIP "+JsonUtility.ToJson(row));}
 public static void Stage(string phase){Write(new InitRow{kind="stage",phase=phase});}
 public static int Initial(string subject,int value){Write(new InitRow{kind="init",subject=subject,value=value});return value;}
 public static int Method(string subject,int value){Write(new InitRow{kind="method",subject=subject,value=value});return value;}
 public static void Read(string subject,int value){Write(new InitRow{kind="read",subject=subject,value=value});}
 public static void Caught(string subject,Exception e,string kind="caught"){
  string chain=e.GetType().FullName;var inner=e.InnerException;
  while(inner!=null){chain+=">"+inner.GetType().FullName;inner=inner.InnerException;}
  Write(new InitRow{kind=kind,subject=subject,type=e.GetType().FullName,detail=chain});
 }
}
