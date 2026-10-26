using System;
using System.IO;
using System.Security.Cryptography;
using HybridCLR;
using HybridCLR.Installer;
public static class EHRuntime {
 const string Relative="hybridclr/interpreter/Interpreter_Execute.cpp";
 const string Marker="Library/eh-runtime-variant.txt";
 static string Hash(string file){using(var s=File.OpenRead(file))using(var h=SHA256.Create())return Convert.ToBase64String(h.ComputeHash(s));}
 static string Expected(string root,string variant){return Path.Combine(root,variant=="baseline"?".local/combined-libil2cpp/"+Relative:".local/exception-flow/Interpreter_Execute.cpp");}
 public static void Verify(string root,string variant){
  var source=Path.Combine(root,".local/combined-libil2cpp");var installed=Path.Combine(SettingsUtil.LocalIl2CppDir,"libil2cpp");
  foreach(var file in Directory.EnumerateFiles(source,"*",SearchOption.AllDirectories)){
   string rel=file.Substring(source.Length+1).Replace((char)92,'/');if(rel.StartsWith("hybridclr/generated/"))continue;
   var expected=rel==Relative?Expected(root,variant):file;var target=Path.Combine(installed,rel);
   if(!File.Exists(target)||Hash(expected)!=Hash(target))throw new Exception("Isolated runtime mismatch "+rel);
  }
 }
 public static void Prepare(string root,string variant){
  if(variant!="baseline"&&variant!="counterfactual")throw new Exception("Unknown runtime variant");
  if(!new InstallerController().HasInstalledHybridCLR()){
   new InstallerController().InstallFromLocal(Path.Combine(root,".local/combined-libil2cpp"));File.WriteAllText(Marker,"baseline");
  }
  if(!File.Exists(Marker))throw new Exception("Unknown project runtime; preserve it before proceeding");
  string previous=File.ReadAllText(Marker);if(previous!="baseline"&&previous!="counterfactual")throw new Exception("Unknown previous variant");Verify(root,previous);
  if(previous!=variant)File.Copy(Expected(root,variant),Path.Combine(SettingsUtil.LocalIl2CppDir,"libil2cpp",Relative),true);
  Verify(root,variant);File.WriteAllText(Marker,variant);
 }
}
