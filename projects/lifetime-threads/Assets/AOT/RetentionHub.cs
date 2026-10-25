using System;
using System.Runtime.CompilerServices;
// AOT roots intentionally hold objects whose concrete type is defined only in HotUpdate.
public static class RetentionHub
{
 public const int Count = 16;
 static readonly object[] Keep = new object[Count];
 static Action Subscribers;
 static readonly WeakReference[][] Weak = { new WeakReference[Count], new WeakReference[Count], new WeakReference[Count] };
 public static int Calls;
 [MethodImpl(MethodImplOptions.NoInlining)]
 public static void Track(int group, int index, object target, Action callback)
 {
  Weak[group][index] = new WeakReference(target, false);
  if (group == 1) Keep[index] = target;
  if (group == 2) Subscribers += callback;
 }
 [MethodImpl(MethodImplOptions.NoInlining)]
 public static void ClearStatic() { Array.Clear(Keep, 0, Keep.Length); }
 [MethodImpl(MethodImplOptions.NoInlining)]
 public static void ClearEvent() { Subscribers = null; }
 [MethodImpl(MethodImplOptions.NoInlining)]
 public static int Alive(int group)
 {
  int n=0;
  for(int i=0;i<Count;i++) if(Weak[group][i].IsAlive) n++;
  return n;
 }
}
