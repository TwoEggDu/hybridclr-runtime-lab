using System;
using System.Threading;
using System.Runtime.InteropServices;
using System.Runtime.CompilerServices;
using UnityEngine;
[Serializable] public sealed class ConcurrentRow {
 public int seq,worker,managed,value,nworkers;
 public uint native;
 public string kind,subject,phase,detail,message,side,mode,build,unity;
 public bool bfi,cctor,joined,completed,hot_before;
}
public static class ConcurrentHub {
 [DllImport("kernel32.dll")] static extern uint GetCurrentThreadId();
 static readonly object sync=new object();static int seq;
 public static void Write(ConcurrentRow row){lock(sync){row.seq=++seq;row.managed=Thread.CurrentThread.ManagedThreadId;row.native=GetCurrentThreadId();Debug.Log("CIP "+JsonUtility.ToJson(row));}}
 public static void Begin(string subject){Write(new ConcurrentRow{kind="init_begin",subject=subject});}
 public static void End(string subject){Write(new ConcurrentRow{kind="init_end",subject=subject});}
 public static int Body(string subject,int value){Write(new ConcurrentRow{kind="body",subject=subject,value=value});return value;}
 [MethodImpl(MethodImplOptions.NoInlining)] public static void BeforeRelease(long method){GC.KeepAlive(method);}
 [MethodImpl(MethodImplOptions.NoInlining)] public static void AfterJoin(long method){GC.KeepAlive(method);}
 public static void Caught(string subject,int worker,Exception e){string chain="";Exception last=e;for(var x=e;x!=null;x=x.InnerException){chain+=(chain.Length>0?">":"")+x.GetType().FullName;last=x;}Write(new ConcurrentRow{kind="caught",subject=subject,worker=worker,detail=chain,message=last.Message});}
}
