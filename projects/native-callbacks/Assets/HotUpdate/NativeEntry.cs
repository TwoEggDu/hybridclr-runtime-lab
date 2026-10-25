using System;
using System.Threading;
using AOT;
namespace CallbackHot {
 public static class NativeEntry {
  [MonoPInvokeCallback(typeof(ProbeState.Callback))]
  public static int Call(int a,int b) {
   try {
    if(a==11 && b==12) ProbeState.Hold();
    int value=a+b; ProbeState.Record(a,b,value); return value;
   } catch(Exception) { Interlocked.Increment(ref ProbeState.Failures); return int.MinValue; }
  }
 }
}
