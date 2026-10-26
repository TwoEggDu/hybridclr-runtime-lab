using System;
using System.Runtime.CompilerServices;
namespace SAMPLE_NS {
 public static class Targets {
  [MethodImpl(MethodImplOptions.NoInlining)] public static void Body(){EHEvents.Emit("throw","SAMPLE_SIDE");throw new InvalidOperationException("eh-body");}
  [MethodImpl(MethodImplOptions.NoInlining)] public static void Manual(){EHEvents.Emit("throw","SAMPLE_SIDE");throw new TypeInitializationException("manual",new InvalidOperationException("eh-manual"));}
  [MethodImpl(MethodImplOptions.NoInlining)] public static void CctorThunk(){Failed.Ping();}
  [MethodImpl(MethodImplOptions.NoInlining)] public static void CctorRetThunk(){Failed.PingRet();}
 }
 public static class Failed {
  static Failed(){EHEvents.Emit("init","SAMPLE_SIDE");throw new InvalidOperationException("eh-cctor");}
  [MethodImpl(MethodImplOptions.NoInlining)] public static void Ping(){EHEvents.Emit("unexpected_body","SAMPLE_SIDE");}
  [MethodImpl(MethodImplOptions.NoInlining)] public static int PingRet(){if(EHEvents.BranchFlag)return EHEvents.Value("SAMPLE_SIDE",7);return EHEvents.Value("SAMPLE_SIDE",8);}
 }
 public static class Cases {
  public static Action HotTarget;
  [MethodImpl(MethodImplOptions.NoInlining)] public static void RunOwn(string fault,int attempt){
   EHEvents.Emit("caller","SAMPLE_SIDE");
   try{if(fault=="body")Targets.Body();else if(fault=="manual")Targets.Manual();else if(fault=="cctor")Failed.Ping();else Failed.PingRet();}
   catch(TypeInitializationException e){EHEvents.Exception("caught","SAMPLE_SIDE",e);}
   catch(InvalidOperationException e){EHEvents.Exception("caught","SAMPLE_SIDE",e);}
   finally{EHEvents.Emit("finally","SAMPLE_SIDE");}
   EHEvents.Emit("after","SAMPLE_SIDE");
  }
  [MethodImpl(MethodImplOptions.NoInlining)] public static void RunAot(string fault,int attempt){
   EHEvents.Emit("caller","SAMPLE_SIDE");
   try{if(fault=="body")EHAot.Targets.Body();else if(fault=="manual")EHAot.Targets.Manual();else if(fault=="cctor")EHAot.Failed.Ping();else EHAot.Failed.PingRet();}
   catch(TypeInitializationException e){EHEvents.Exception("caught","SAMPLE_SIDE",e);}
   catch(InvalidOperationException e){EHEvents.Exception("caught","SAMPLE_SIDE",e);}
   finally{EHEvents.Emit("finally","SAMPLE_SIDE");}
   EHEvents.Emit("after","SAMPLE_SIDE");
  }
  [MethodImpl(MethodImplOptions.NoInlining)] public static void RunDelegate(string fault,int attempt){
   EHEvents.Emit("caller","SAMPLE_SIDE");
   try{HotTarget();}
   catch(TypeInitializationException e){EHEvents.Exception("caught","SAMPLE_SIDE",e);}
   catch(InvalidOperationException e){EHEvents.Exception("caught","SAMPLE_SIDE",e);}
   finally{EHEvents.Emit("finally","SAMPLE_SIDE");}
   EHEvents.Emit("after","SAMPLE_SIDE");
  }
 }
}
