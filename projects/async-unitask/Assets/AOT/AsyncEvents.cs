using System;
using System.Threading;
using Cysharp.Threading.Tasks;
using UnityEngine;
[Serializable] public sealed class AsyncRow {
 public int seq,frame,thread,value;
 public string kind,side,mode,metadata,build,unity,label,type,detail;
 public bool hot_before;
}
public static class AsyncEvents {
 static int sequence;
 public static ProbeGate Gate;
 public static void Write(AsyncRow row){row.seq=++sequence;row.frame=Time.frameCount;row.thread=Thread.CurrentThread.ManagedThreadId;Debug.Log("AUT "+JsonUtility.ToJson(row));}
 public static void Log(string kind,string label="",int value=0){Write(new AsyncRow{kind=kind,label=label,value=value});}
 public static void Error(string kind,Exception e){Write(new AsyncRow{kind=kind,type=e.GetType().FullName,detail=e.Message});}
}
public sealed class ProbeGate:IUniTaskSource<int> {
 UniTaskCompletionSourceCore<int> core;
 public UniTask<int> Task {get{return new UniTask<int>(this,core.Version);}}
 public UniTaskStatus GetStatus(short token){return core.GetStatus(token);}
 public UniTaskStatus UnsafeGetStatus(){return core.UnsafeGetStatus();}
 public int GetResult(short token){AsyncEvents.Log("gate_result");return core.GetResult(token);}
 void IUniTaskSource.GetResult(short token){GetResult(token);}
 public void OnCompleted(Action<object> continuation,object state,short token){
  AsyncEvents.Log("register",state==null?"null":state.GetType().FullName);
  core.OnCompleted(s=>{AsyncEvents.Log("dispatch_begin");continuation(s);AsyncEvents.Log("dispatch_end");},state,token);
 }
 public void Complete(){AsyncEvents.Log("complete");if(!core.TrySetResult(7))throw new Exception("Gate double completion");}
}
