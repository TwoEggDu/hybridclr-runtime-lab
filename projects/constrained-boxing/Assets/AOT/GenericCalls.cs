using System;
using System.Runtime.CompilerServices;
public static class GenericCalls {
 [MethodImpl(MethodImplOptions.NoInlining)]public static int ByValue<T>(T value)where T:IMutableCounter{
  BoxEvents.Body("AOT.ByValue");int r=value.Increment();if(value.Value!=r)throw new Exception("Value mismatch");return r;
 }
 [MethodImpl(MethodImplOptions.NoInlining)]public static int ByRef<T>(ref T value)where T:IMutableCounter{
  BoxEvents.Body("AOT.ByRef");int r=value.Increment();if(value.Value!=r)throw new Exception("Ref mismatch");return r;
 }
 [MethodImpl(MethodImplOptions.NoInlining)]public static string Text<T>(ref T value){BoxEvents.Body("AOT.Text");return value.ToString();}
}
