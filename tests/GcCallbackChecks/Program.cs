// Tests actual hot-source data invariants on desktop .NET; not Unity/GC acceptance.
using System;
using System.Runtime.InteropServices;
using GcHot;
namespace AOT { public sealed class MonoPInvokeCallbackAttribute:Attribute { public MonoPInvokeCallbackAttribute(Type type){} } }
public static class GcState {
 public delegate int Callback(IntPtr token,int seq,int mode);
 public static int Failures,Limit=1024;
 public static Action Hook;
 public static void Track(object value){}
 public static void Checkpoint(int seq){if(Hook!=null)Hook();}
}
public static class Program {
 static int failures;
 static void Require(bool condition,string label){if(!condition){Console.WriteLine("FAIL "+label);failures++;}}
 static void Check(string kind){
  var context=new Context();var handle=GCHandle.Alloc(context);var token=GCHandle.ToIntPtr(handle);GcState.Failures=0;GcState.Hook=null;
  try {
   if(kind=="slot-null" || kind=="slot-stale"){
    Require(Entry.Call(token,1,2)==257,"setup");context.Slots[0]=kind=="slot-null"?null:new Node(999);
    Require(Entry.Call(token,2,2)==-1,kind);
   }else{
    GcState.Hook=()=>{if(kind=="next-null")context.Head.Next=null;else context.Head=new Node(999);};
    int result=0;for(int seq=1;seq<=32;seq++)result=Entry.Call(token,seq,2);
    Require(result==-1,kind);
   }
  }finally{GcState.Hook=null;handle.Free();}
 }
 public static int Main(){foreach(var kind in new[]{"slot-null","slot-stale","next-null","head-stale"})Check(kind);Console.WriteLine("Invariant negative checks: "+(4-failures)+"/4");return failures==0?0:1;}
}
