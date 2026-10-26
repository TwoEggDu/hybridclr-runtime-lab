using System;
using System.Threading;
using System.Runtime.CompilerServices;
namespace AotConcurrent {
 public static class Cold {
  [MethodImpl(MethodImplOptions.NoInlining)] public static int Read(){return ConcurrentHub.Body("AotConcurrent.Cold",7);}
 }
 public static class Strict {
  static int a,b;
  static Strict(){ConcurrentHub.Begin("AotConcurrent.Strict");a=41;Thread.Sleep(150);b=83;ConcurrentHub.End("AotConcurrent.Strict");}
  [MethodImpl(MethodImplOptions.NoInlining)] public static int Read(){return ConcurrentHub.Body("AotConcurrent.Strict",a*1000+b);}
 }
 public static class Failed {
  static Failed(){ConcurrentHub.Begin("AotConcurrent.Failed");Thread.Sleep(150);throw new InvalidOperationException("concurrent-init-failed:AotConcurrent.Failed");}
  public static int Read(){return ConcurrentHub.Body("AotConcurrent.Failed",-1);}
 }
 public static class Cache<T> {
  static int a,b;
  static string Subject(){return "AotConcurrent.Cache<"+typeof(T).FullName+">";}
  static Cache(){ConcurrentHub.Begin(Subject());a=typeof(T)==typeof(int)?41:81;Thread.Sleep(150);b=a+42;ConcurrentHub.End(Subject());}
  [MethodImpl(MethodImplOptions.NoInlining)] public static int Read(){return ConcurrentHub.Body(Subject(),a*1000+b);}
 }
}
