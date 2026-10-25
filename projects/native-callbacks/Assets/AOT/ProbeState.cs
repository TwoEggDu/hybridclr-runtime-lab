using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Threading;
public static class ProbeState
{
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] public delegate int Callback(int a,int b);
 public static Callback Root;
 public static readonly ManualResetEvent Entered=new ManualResetEvent(false), Release=new ManualResetEvent(false);
 static readonly List<string> Calls=new List<string>();
 public static int Failures;
 public static bool NativeStarted;
 [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
 public static void Record(int a,int b,int result) {
  lock(Calls) Calls.Add("CB_CALL index="+Calls.Count+" managed="+Thread.CurrentThread.ManagedThreadId+" native="+GetCurrentThreadId()+" a="+a+" b="+b+" result="+result);
 }
 public static string[] Snapshot() { lock(Calls) return Calls.ToArray(); }
 public static void Hold() { Entered.Set(); if(!Release.WaitOne(30000)) throw new TimeoutException("Callback release timed out"); }
 [DllImport("NativeProbe",CallingConvention=CallingConvention.Cdecl)] public static extern int NP_Inline(IntPtr cb);
 [DllImport("NativeProbe",CallingConvention=CallingConvention.Cdecl)] public static extern int NP_Start(IntPtr cb);
 [DllImport("NativeProbe",CallingConvention=CallingConvention.Cdecl)] public static extern int NP_Stop();
 [DllImport("NativeProbe",CallingConvention=CallingConvention.Cdecl)] public static extern int NP_Join(uint ms);
 [DllImport("NativeProbe",CallingConvention=CallingConvention.Cdecl)] public static extern int NP_Count();
 [DllImport("NativeProbe",CallingConvention=CallingConvention.Cdecl)] public static extern int NP_Result(int index);
 [DllImport("NativeProbe",CallingConvention=CallingConvention.Cdecl)] public static extern uint NP_Thread();
}
