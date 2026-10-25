using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Collections.Generic;
using UnityEngine;
public static class UnitySnapshotCheck {
 [Serializable] public class Row {public string file;public int entry;public long count;public string sha256;}
 [Serializable] public class Result {public string package="com.unity.memoryprofiler@1.1.0";public List<Row> entries=new List<Row>();}
 static string Hash(byte[] data){using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(data)).Replace("-","").ToLowerInvariant();}
 public static unsafe void Run(){
  var args=Environment.GetCommandLineArgs();string root=args[Array.IndexOf(args,"--lab-root")+1];
  var type=AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType("Unity.MemoryProfiler.Editor.Format.QueriedSnapshot.FileReader",false)).First(t=>t!=null);
  var entryType=type.Assembly.GetType("Unity.MemoryProfiler.Editor.Format.QueriedSnapshot.EntryType",true);
  var result=new Result();
  foreach(var file in Directory.GetFiles(Path.Combine(root,"artifacts/gc-roots/snapshots"),"*.snap",SearchOption.AllDirectories)){
   object reader=Activator.CreateInstance(type,true);
   try{
    if(type.GetMethod("Open").Invoke(reader,new object[]{file}).ToString()!="Success")throw new Exception("Official reader open failed");
    foreach(int index in new[]{0,3,4,15,18,19,21,23,29}){
     object entry=Enum.ToObject(entryType,index);long count=Convert.ToInt64(type.GetMethod("GetEntryCount").Invoke(reader,new[]{entry}));
     long size=Convert.ToInt64(type.GetMethod("GetSizeForEntryRange").Invoke(reader,new object[]{entry,0L,count,false}));
     var data=new byte[size];
     if(size>0){var pinned=GCHandle.Alloc(data,GCHandleType.Pinned);try{
      object pointer=pinned.AddrOfPinnedObject();
      if(type.GetMethod("ReadUnsafe").Invoke(reader,new object[]{entry,pointer,size,0L,count,false}).ToString()!="Success")throw new Exception("Official reader read failed");
     }finally{pinned.Free();}}
     result.entries.Add(new Row{file=file.Substring(root.Length+1).Replace('\\','/'),entry=index,count=count,sha256=Hash(data)});
    }
   }finally{type.GetMethod("Dispose").Invoke(reader,null);}
  }
  File.WriteAllText(Path.Combine(root,"artifacts/gc-roots/unity-reader-results.json"),JsonUtility.ToJson(result,true));
  Debug.Log("GCR_OFFICIAL_READER_PASS entries="+result.entries.Count);
 }
}
