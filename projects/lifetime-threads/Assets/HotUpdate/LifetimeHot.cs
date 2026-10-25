using System;
using System.Runtime.CompilerServices;
namespace LifetimeHot
{
 public sealed class Target
 {
  public readonly int Id;
  public Target(int id) { Id = id; }
  public void OnEvent() { RetentionHub.Calls += Id; }
 }
 public static class Samples
 {
  public static void CreateTargets()
  {
   for(int group=0;group<3;group++)
    for(int i=0;i<RetentionHub.Count;i++)
    {
     var target=new Target(group*100+i);
     RetentionHub.Track(group,i,target,group==2 ? (Action)target.OnEvent : null);
    }
  }
  [MethodImpl(MethodImplOptions.NoInlining)]
  public static int Add(int a, int b) { return a+b; }
 }
}
