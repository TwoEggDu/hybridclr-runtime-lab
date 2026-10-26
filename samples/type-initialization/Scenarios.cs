using System;
using System.Reflection;
using System.Runtime.CompilerServices;
namespace SAMPLE_NAMESPACE {
 public static class Cases {
  [MethodImpl(MethodImplOptions.NoInlining)] public static void AccessFailed(){Failed.Ping();}
  [MethodImpl(MethodImplOptions.NoInlining)] public static void Run(string mode){
   Type target=mode=="strict"?typeof(Strict):mode=="relaxed"?typeof(Relaxed):mode=="generic"?typeof(Cache<>):typeof(Failed);
   InitEvents.Write(new InitRow{kind="meta",subject=target.Name,bfi=(target.Attributes&TypeAttributes.BeforeFieldInit)!=0,cctor=target.TypeInitializer!=null});
   if(mode=="strict")RunStrict();else if(mode=="relaxed")RunRelaxed();else if(mode=="generic")RunGeneric();else if(mode=="failed")RunFailed();else throw new Exception("Unknown mode");
  }
  [MethodImpl(MethodImplOptions.NoInlining)] static void RunStrict(){
   InitEvents.Stage("before_call1");InitEvents.Read("call1",Strict.Ping());
   InitEvents.Stage("before_field");InitEvents.Read("field",Strict.Value);
   InitEvents.Stage("before_call2");InitEvents.Read("call2",Strict.Ping());
  }
  [MethodImpl(MethodImplOptions.NoInlining)] static void RunRelaxed(){
   InitEvents.Stage("before_call1");InitEvents.Read("call1",Relaxed.Ping());
   InitEvents.Stage("before_field");InitEvents.Read("field",Relaxed.Value);
   InitEvents.Stage("before_call2");InitEvents.Read("call2",Relaxed.Ping());
  }
  [MethodImpl(MethodImplOptions.NoInlining)] static void RunGeneric(){
   InitEvents.Stage("before_int1");InitEvents.Read("int1",Cache<int>.Next());
   InitEvents.Stage("before_string1");InitEvents.Read("string1",Cache<string>.Next());
   InitEvents.Stage("before_int2");InitEvents.Read("int2",Cache<int>.Next());
   InitEvents.Stage("before_string2");InitEvents.Read("string2",Cache<string>.Next());
  }
  [MethodImpl(MethodImplOptions.NoInlining)] static void RunFailed(){
   for(int n=1;n<=2;n++){
    InitEvents.Stage("before_call"+n);
    try{Failed.Ping();throw new Exception("Expected initializer failure was absent");}
    catch(TypeInitializationException e){InitEvents.Caught("call"+n,e);}
   }
  }
 }
 public static class Strict {
  public static int Value=InitEvents.Initial("Strict.field",41);
  static Strict(){InitEvents.Initial("Strict.cctor",Value);}
  [MethodImpl(MethodImplOptions.NoInlining)] public static int Ping(){return InitEvents.Method("Ping",7);}
 }
 public static class Relaxed {
  public static int Value=InitEvents.Initial("Relaxed.field",41);
  [MethodImpl(MethodImplOptions.NoInlining)] public static int Ping(){return InitEvents.Method("Ping",7);}
 }
 public static class Cache<T> {
  public static int Value=InitEvents.Initial("Cache<"+typeof(T).FullName+">.field",typeof(T)==typeof(int)?41:81);
  static Cache(){InitEvents.Initial("Cache<"+typeof(T).FullName+">.cctor",Value);}
  [MethodImpl(MethodImplOptions.NoInlining)] public static int Next(){return InitEvents.Method("Next",++Value);}
 }
 public static class Failed {
  static Failed(){InitEvents.Initial("Failed.cctor",1);throw new InvalidOperationException("init-probe-failure");}
  [MethodImpl(MethodImplOptions.NoInlining)] public static int Ping(){return InitEvents.Method("Ping",7);}
 }
}
