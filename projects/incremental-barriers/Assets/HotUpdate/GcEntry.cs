using System;
using System.Runtime.CompilerServices;
namespace WbHot {
 public static class Entry {
  [MethodImpl(MethodImplOptions.NoInlining)]public static void Write(WbBox box,int seq,int kind){
   if(seq==0)return;var value=(WbNode)WbState.Candidates[seq].Target;if(value==null)throw new Exception("Candidate lost before hot write");
   WbState.Observe(box,value,kind,seq);
   if(kind==0)box.Field=value;
   else if(kind==1)box.Slots[seq]=value;
   else {var pair=new WbPair{Left=value,Right=box.Field,Tag=seq};box.Pair=pair;box.Pairs[seq]=pair;}
   WbState.WB_Marker(4,seq,kind);GC.KeepAlive(value);
  }
 }
}
