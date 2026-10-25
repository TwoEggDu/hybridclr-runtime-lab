using System;
using System.Runtime.InteropServices;
using System.Runtime.CompilerServices;
using System.Threading;
public static class GcState {
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)]public delegate int Callback(IntPtr token,int seq,int mode);
 public static Callback Root;
 public static IntPtr Context;
 public static WeakReference Weak;
 public static readonly AutoResetEvent Ready=new AutoResetEvent(false),Resume=new AutoResetEvent(false);
 public static int Limit,Sequence,Failures;
 public static bool NativeStarted;
 [DllImport("kernel32.dll")]public static extern uint GetCurrentThreadId();
 [MethodImpl(MethodImplOptions.NoInlining)]public static void Track(object target){Weak=new WeakReference(target,false);}
 [MethodImpl(MethodImplOptions.NoInlining)]public static bool Alive(){return Weak!=null && Weak.IsAlive;}
 public static void Checkpoint(int seq){Volatile.Write(ref Sequence,seq);Ready.Set();if(!Resume.WaitOne(60000))throw new TimeoutException("Checkpoint resume");}
 public static void FreeContext(){if(Context!=IntPtr.Zero){GCHandle.FromIntPtr(Context).Free();Context=IntPtr.Zero;}}
 [DllImport("NativeProbe",CallingConvention=CallingConvention.Cdecl)]public static extern int NP_Start(IntPtr cb,IntPtr token,int mode,int maximum);
 [DllImport("NativeProbe",CallingConvention=CallingConvention.Cdecl)]public static extern int NP_Stop();
 [DllImport("NativeProbe",CallingConvention=CallingConvention.Cdecl)]public static extern int NP_Join(uint ms);
 [DllImport("NativeProbe",CallingConvention=CallingConvention.Cdecl)]public static extern int NP_Count();
 [DllImport("NativeProbe",CallingConvention=CallingConvention.Cdecl)]public static extern int NP_Errors();
 [DllImport("NativeProbe",CallingConvention=CallingConvention.Cdecl)]public static extern long NP_Checksum();
 [DllImport("NativeProbe",CallingConvention=CallingConvention.Cdecl)]public static extern uint NP_Thread();
}
