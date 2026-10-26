using System.Runtime.CompilerServices;
namespace HotConcurrent {public static class Bridge {[MethodImpl(MethodImplOptions.NoInlining)] public static int Read(){return AotConcurrent.Strict.Read();}}}
