using System;
using System.Threading;
using System.Runtime.CompilerServices;
namespace HotConcurrent {
 public static class Cold {
  [MethodImpl(MethodImplOptions.NoInlining)] public static int Read(){return ConcurrentHub.Body("HotConcurrent.Cold",7);}
 }
 public static class Strict {
  static int a,b;
  static Strict(){ConcurrentHub.Begin("HotConcurrent.Strict");a=41;Thread.Sleep(150);b=83;ConcurrentHub.End("HotConcurrent.Strict");}
  [MethodImpl(MethodImplOptions.NoInlining)] public static int Read(){return ConcurrentHub.Body("HotConcurrent.Strict",a*1000+b);}
 }
 public static class Failed {
  static Failed(){ConcurrentHub.Begin("HotConcurrent.Failed");Thread.Sleep(150);throw new InvalidOperationException("concurrent-init-failed:HotConcurrent.Failed");}
  public static int Read(){return ConcurrentHub.Body("HotConcurrent.Failed",-1);}
 }
 public static class Cache<T> {
  static int a,b;
  static string Subject(){return "HotConcurrent.Cache<"+typeof(T).FullName+">";}
  static Cache(){ConcurrentHub.Begin(Subject());a=typeof(T)==typeof(int)?41:81;Thread.Sleep(150);b=a+42;ConcurrentHub.End(Subject());}
  [MethodImpl(MethodImplOptions.NoInlining)] public static int Read(){return ConcurrentHub.Body(Subject(),a*1000+b);}
 }
}
