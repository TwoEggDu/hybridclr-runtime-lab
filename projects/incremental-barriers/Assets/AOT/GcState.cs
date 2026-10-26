using System;
using System.Runtime.InteropServices;
using System.Runtime.CompilerServices;
using System.Threading;
public sealed class WbNode {
 public readonly int Id;public readonly byte[] Data=new byte[32];public WbNode Next;
 public WbNode(int id){Id=id;for(int i=0;i<Data.Length;i++)Data[i]=(byte)(id%251);}
 public void Check(int id){if(Id!=id || Next!=null || Data.Length!=32)throw new Exception("Node identity");for(int i=0;i<32;i++)if(Data[i]!=(byte)(id%251))throw new Exception("Payload");}
}
public struct WbPair {public WbNode Left,Right;public int Tag;}
public sealed class WbBox {public WbNode Field;public readonly WbNode[] Slots=new WbNode[64];public WbPair Pair;public readonly WbPair[] Pairs=new WbPair[64];}
public static class WbState {
 public delegate void Writer(WbBox box,int seq,int kind);
 public static WbNode[] Heap;public static WbBox Box;public static WeakReference[] Candidates;
 [DllImport("NativeProbe",CallingConvention=CallingConvention.Cdecl)]public static extern int WB_Install();
 [DllImport("NativeProbe",CallingConvention=CallingConvention.Cdecl)]public static extern long WB_Query(int item);
 [DllImport("NativeProbe",CallingConvention=CallingConvention.Cdecl)]public static extern void WB_Marker(int phase,int seq,int kind);
 [DllImport("NativeProbe",CallingConvention=CallingConvention.Cdecl)]public static extern long WB_Event(int index,int item);
 [DllImport("GameAssembly",CallingConvention=CallingConvention.Cdecl)]public static extern void il2cpp_gc_start_incremental_collection();
 [DllImport("GameAssembly",CallingConvention=CallingConvention.Cdecl)]public static extern void il2cpp_gc_set_max_time_slice_ns(long nanos);
 [DllImport("GameAssembly",CallingConvention=CallingConvention.Cdecl)]public static extern int il2cpp_gc_collect_a_little();
 [DllImport("NativeProbe",CallingConvention=CallingConvention.Cdecl)]public static extern int WB_ScrubStack();
 [MethodImpl(MethodImplOptions.NoInlining)]public static void Observe(WbBox box,WbNode node,int kind,int seq){WB_Marker(3,seq,kind);GC.KeepAlive(box);GC.KeepAlive(node);}
 [MethodImpl(MethodImplOptions.NoInlining)]public static void Write(WbBox box,int seq,int kind){
  if(seq==0)return;var value=(WbNode)Candidates[seq].Target;if(value==null)throw new Exception("Candidate lost before write");
  Observe(box,value,kind,seq);
  if(kind==0)box.Field=value;
  else if(kind==1)box.Slots[seq]=value;
  else {var pair=new WbPair{Left=value,Right=box.Field,Tag=seq};box.Pair=pair;box.Pairs[seq]=pair;}
  WB_Marker(4,seq,kind);GC.KeepAlive(value);
 }
 static Thread worker;static Writer currentWriter;static Exception workerFailure;static int requestedSeq,requestedKind,stopping;
 static readonly AutoResetEvent signal=new AutoResetEvent(false),done=new AutoResetEvent(false);
 public static void StartWorker(Writer writer){
  currentWriter=writer;workerFailure=null;stopping=0;
  worker=new Thread(()=>{try{currentWriter(null,0,-1);done.Set();while(true){signal.WaitOne();if(Volatile.Read(ref stopping)!=0)break;int seq=Volatile.Read(ref requestedSeq),kind=Volatile.Read(ref requestedKind);currentWriter(Box,seq,kind);if(WB_ScrubStack()!=0)throw new Exception("Stack scrub");WB_Marker(6,seq,kind);done.Set();}}catch(Exception e){workerFailure=e;done.Set();}});
  worker.IsBackground=true;worker.Start();if(!done.WaitOne(60000))throw new TimeoutException("Worker warm");if(workerFailure!=null)throw workerFailure;
 }
 public static void RunWriter(Writer writer,int seq,int kind){
  Volatile.Write(ref requestedSeq,seq);Volatile.Write(ref requestedKind,kind);signal.Set();if(!done.WaitOne(60000))throw new TimeoutException("Writer completion");if(workerFailure!=null)throw workerFailure;
 }
 public static void StopWorker(){if(worker==null)return;Volatile.Write(ref stopping,1);signal.Set();if(!worker.Join(60000))throw new TimeoutException("Worker join");worker=null;currentWriter=null;if(workerFailure!=null)throw workerFailure;}
 public static void PrepareOwner(){Box=new WbBox();}
 public static void PrepareHeap(int count){Heap=new WbNode[count];for(int i=0;i<count;i++){Heap[i]=new WbNode(-i);if(i>0)Heap[i].Next=Heap[i-1];}}
 public static void PrepareCandidates(){
  Exception failure=null;var worker=new Thread(()=>{try{Candidates=new WeakReference[13];for(int i=1;i<=12;i++)Candidates[i]=new WeakReference(new WbNode(1000+i),false);}catch(Exception e){failure=e;}});worker.IsBackground=true;worker.Start();if(!worker.Join(60000))throw new TimeoutException("Candidate creator");if(failure!=null)throw failure;
 }
 [MethodImpl(MethodImplOptions.NoInlining)]public static int CheckGraph(){
  if(Box==null || Box.Slots.Length!=64 || Box.Pairs.Length!=64)throw new Exception("Owner graph");
  Box.Field.Check(1010);if(Box.Pair.Tag!=12 || !object.ReferenceEquals(Box.Pair.Left,Box.Pairs[12].Left) || !object.ReferenceEquals(Box.Pair.Right,Box.Field))throw new Exception("Pair identity");
  int sum=0;for(int i=1;i<=12;i++){int kind=(i-1)%3;WbNode n=kind==0?Box.Pairs[i+2].Right:kind==1?Box.Slots[i]:Box.Pairs[i].Left;n.Check(1000+i);sum+=n.Id;}
  for(int i=0;i<64;i++){
   bool array=i>=1 && i<=12 && (i-1)%3==1;bool pair=i>=1 && i<=12 && (i-1)%3==2;
   if(!array && Box.Slots[i]!=null)throw new Exception("Unexpected array slot");
   if(pair){if(Box.Pairs[i].Tag!=i)throw new Exception("Struct tag");Box.Pairs[i].Left.Check(1000+i);Box.Pairs[i].Right.Check(998+i);}
   else if(Box.Pairs[i].Left!=null || Box.Pairs[i].Right!=null || Box.Pairs[i].Tag!=0)throw new Exception("Unexpected struct slot");
  }
  return sum;
 }
 [MethodImpl(MethodImplOptions.NoInlining)]public static void Release(){Box=null;Heap=null;}
 public static int Alive(){int n=0;for(int i=1;i<=12;i++)if(Candidates[i].IsAlive)n++;return n;}
}
