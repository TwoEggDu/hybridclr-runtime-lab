using System;
using System.IO;
using HybridCLR;
using HybridCLR.Commands;
using HybridCLR.Installer;
using HybridCLR.Settings;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
public static class BoxBuild {
 static readonly BuildTarget Target=BuildTarget.StandaloneWindows64;
 static string Root {get{return Path.GetFullPath(Path.Combine(Application.dataPath,"../../.."));}}
 public static void Prepare(){
  if(!EditorUserBuildSettings.SwitchActiveBuildTarget(BuildTargetGroup.Standalone,Target))throw new Exception("Switch target failed");
  PlayerSettings.SetScriptingBackend(BuildTargetGroup.Standalone,ScriptingImplementation.IL2CPP);
  PlayerSettings.SetManagedStrippingLevel(BuildTargetGroup.Standalone,ManagedStrippingLevel.Minimal);
  PlayerSettings.SetIl2CppCodeGeneration(UnityEditor.Build.NamedBuildTarget.Standalone,UnityEditor.Build.Il2CppCodeGeneration.OptimizeSpeed);
  PlayerSettings.SetIl2CppCompilerConfiguration(BuildTargetGroup.Standalone,Il2CppCompilerConfiguration.Debug);
  EditorUserBuildSettings.development=true;EditorUserBuildSettings.allowDebugging=false;UnityEditor.WindowsStandalone.UserBuildSettings.createSolution=false;
  PlayerSettings.productName="ConstrainedBoxingProbe";PlayerSettings.companyName="TwoEggExperiment";
  var settings=HybridCLRSettings.instance;settings.enable=true;settings.useGlobalIl2cpp=false;settings.hotUpdateAssemblies=new[]{"HotUpdate"};HybridCLRSettings.Save();
  LabRuntime.CheckLock(Root);if(!new InstallerController().HasInstalledHybridCLR())new InstallerController().InstallFromLocal(Path.Combine(Root,".local/combined-libil2cpp"));LabRuntime.SaveLock(Root);
  var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);EditorSceneManager.SaveScene(scene,"Assets/Probe.unity");EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene("Assets/Probe.unity",true)};
  PrebuildCommand.GenerateAll();Directory.CreateDirectory("Assets/StreamingAssets");
  File.Copy(Path.Combine(SettingsUtil.GetHotUpdateDllsOutputDirByTarget(Target),"HotUpdate.dll"),"Assets/StreamingAssets/HotUpdate.dll.bytes",true);
  File.Copy(Path.Combine(SettingsUtil.GetAssembliesPostIl2CppStripDir(Target),"Probe.AOT.dll"),"Assets/StreamingAssets/Probe.AOT.dll.bytes",true);
  File.WriteAllText("Assets/StreamingAssets/box-build-id.txt",Environment.GetEnvironmentVariable("BOX_BUILD_ID"));
  AssetDatabase.Refresh();AssetDatabase.SaveAssets();Debug.Log("BOX_PREPARE_OK");
 }
 public static void Build(){
  var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{"Assets/Probe.unity"},locationPathName=Path.Combine(Root,"artifacts/constrained-boxing/Player/ConstrainedBoxingProbe.exe"),target=Target,options=BuildOptions.Development});
  Debug.Log("BOX_BUILD_RESULT "+report.summary.result);if(report.summary.result!=BuildResult.Succeeded)throw new Exception("Player build failed");
 }
}
