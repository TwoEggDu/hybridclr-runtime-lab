using System;
using UnityEngine;
public interface IMutableCounter {int Increment();int Value{get;}}
[Serializable]public sealed class BoxRow {
 public int seq,value,a,b,c;
 public bool flag,hot_before;
 public string kind,label,route,mode,metadata,build,unity,type,detail,text;
}
public static class BoxEvents {
 static int sequence;
 public static void Write(BoxRow row){row.seq=++sequence;Debug.Log("CBX "+JsonUtility.ToJson(row));}
 public static void Body(string name){Write(new BoxRow{kind="body",label=name});}
 public static void Target(string name,int value){Write(new BoxRow{kind="target",label=name,value=value});}
 public static void Result(int a=0,int b=0,int c=0,bool flag=false,string text=""){Write(new BoxRow{kind="result",a=a,b=b,c=c,flag=flag,text=text});}
}
