using System;
using System.Runtime.CompilerServices;
namespace SAMPLE_NS {
 public struct Counter:IMutableCounter {
  public int Count;public int Value{get{return Count;}}
  [MethodImpl(MethodImplOptions.NoInlining)]public int Increment(){++Count;BoxEvents.Target("Counter.Increment",Count);return Count;}
  [MethodImpl(MethodImplOptions.NoInlining)]public override string ToString(){BoxEvents.Target("Counter.ToString",Count);return "counter:"+Count;}
 }
 public struct PlainCounter {public int Count;}
 public sealed class RefCounter:IMutableCounter {
  public int Count;public int Value{get{return Count;}}
  [MethodImpl(MethodImplOptions.NoInlining)]public int Increment(){++Count;BoxEvents.Target("RefCounter.Increment",Count);return Count;}
 }
 public static class Cases {
  [MethodImpl(MethodImplOptions.NoInlining)]public static int ByValueLocal<T>(T value)where T:IMutableCounter{BoxEvents.Body("Local.ByValue");return value.Increment();}
  [MethodImpl(MethodImplOptions.NoInlining)]public static int ByRefLocal<T>(ref T value)where T:IMutableCounter{BoxEvents.Body("Local.ByRef");return value.Increment();}
  [MethodImpl(MethodImplOptions.NoInlining)]public static string TextLocal<T>(ref T value){BoxEvents.Body("Local.Text");return value.ToString();}
  public static void Run(string mode,string route){
   BoxEvents.Write(new BoxRow{kind="begin",value=10});
   Counter counter=new Counter{Count=10};
   if(mode=="value"){int n=CALL_VALUE;BoxEvents.Result(a:counter.Count,b:n);}
   else if(mode=="ref"){int n=CALL_REF;BoxEvents.Result(a:counter.Count,b:n);}
   else if(mode=="box"){
    IMutableCounter boxed=counter;IMutableCounter alias=(IMutableCounter)(object)boxed;
    boxed.Increment();alias.Increment();Counter copy=(Counter)boxed;copy.Increment();
    BoxEvents.Result(a:counter.Count,b:boxed.Value,c:copy.Count,flag:object.ReferenceEquals(boxed,alias));
   }
   else if(mode=="text-override"){string s=CALL_TEXT_COUNTER;BoxEvents.Result(a:counter.Count,text:s);}
   else if(mode=="text-fallback"){PlainCounter plain=new PlainCounter{Count=10};string s=CALL_TEXT_PLAIN;BoxEvents.Result(a:plain.Count,text:s);}
   else if(mode=="reference"){
    RefCounter obj=new RefCounter{Count=10};var alias=obj;int a=CALL_CLASS_VALUE;int b=CALL_CLASS_REF;
    BoxEvents.Result(a:obj.Count,b:a,c:b,flag:object.ReferenceEquals(alias,obj));
   }else throw new Exception("Unknown mode");
  }
 }
}
