using System;
using System.Runtime.InteropServices;
using System.Runtime.CompilerServices;
using System.Threading;
using AOT;
namespace GcHot {
 public sealed class Node {
  public readonly int Id;
  public readonly byte[] Data=new byte[256];
  public Node Next;
  public Node(int id){Id=id;for(int i=0;i<Data.Length;i++)Data[i]=(byte)(id%251);}
  public void Check(){if(Data.Length!=256)throw new Exception("Length");for(int i=0;i<Data.Length;i++)if(Data[i]!=(byte)(Id%251))throw new Exception("Payload");}
 }
 public sealed class Context { public readonly int Tag=73;public readonly Node[] Slots=new Node[64];public Node Head; }
 public static class Entry {
  [MethodImpl(MethodImplOptions.NoInlining)]
  public static IntPtr CreateContext(){var value=new Context();GcState.Track(value);return GCHandle.ToIntPtr(GCHandle.Alloc(value,GCHandleType.Normal));}
  [MethodImpl(MethodImplOptions.NoInlining)]public static void IdleCreate(){var local=new Node(991);GcState.Track(local);local.Check();GC.KeepAlive(local);}
  [MonoPInvokeCallback(typeof(GcState.Callback))]
  public static int Call(IntPtr token,int seq,int mode){
   try {
    if(mode==1){
     if(token!=IntPtr.Zero)throw new Exception("Unexpected stack handle");
     var local=new Node(seq);GcState.Track(local);GcState.Checkpoint(seq);local.Check();GC.KeepAlive(local);return seq+256;
    }
    var context=(Context)GCHandle.FromIntPtr(token).Target;
    if(context.Tag!=73)throw new Exception("Context tag");
    if(mode==0){if(seq==GcState.Limit)GcState.Checkpoint(seq);return context.Tag+seq;}
    for(int i=0;i<32;i++){
     int slot=((seq-1)*32+i)%64;
     var node=new Node(seq*32+i);node.Next=context.Head;
     if(context.Head!=null)context.Head.Next=null;
     context.Slots[slot]=node;context.Head=node;node.Check();
    }
    if(seq%32==0)GcState.Checkpoint(seq);
    int currentStart=((seq-1)*32)%64;
    if(context.Slots.Length!=64)throw new Exception("Slot count");
    for(int slot=0;slot<64;slot++){
     bool current=slot>=currentStart && slot<currentStart+32;
     var node=context.Slots[slot];
     if(seq==1 && !current){if(node!=null)throw new Exception("Unexpected slot");continue;}
     int expected=current?seq*32+slot-currentStart:(seq-1)*32+slot-(currentStart==0?32:0);
     if(node==null || node.Id!=expected)throw new Exception("Missing or stale slot");
     node.Check();
     if(slot==currentStart+31){if(!object.ReferenceEquals(node.Next,context.Slots[currentStart+30]))throw new Exception("Head link");}
     else if(node.Next!=null)throw new Exception("Stale link");
    }
    if(!object.ReferenceEquals(context.Head,context.Slots[currentStart+31]))throw new Exception("Head identity");
    GC.KeepAlive(context);return seq+256;
   }catch(Exception){Interlocked.Increment(ref GcState.Failures);return -1;}
  }
 }
}
