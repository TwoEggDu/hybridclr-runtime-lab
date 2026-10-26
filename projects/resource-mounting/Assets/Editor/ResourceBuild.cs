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
public static class ResourceBuild {
 static readonly BuildTarget Target=BuildTarget.StandaloneWindows64;
 static string Root {get{return Path.GetFullPath(Path.Combine(Application.dataPath,"../../.."));}}
 static string Output {get{return Path.Combine(Root,"artifacts/resource-mounting");}}
 public static void Prepare(){
  if(!EditorUserBuildSettings.SwitchActiveBuildTarget(BuildTargetGroup.Standalone,Target))throw new Exception("Switch target failed");
  PlayerSettings.SetScriptingBackend(BuildTargetGroup.Standalone,ScriptingImplementation.IL2CPP);
  PlayerSettings.SetManagedStrippingLevel(BuildTargetGroup.Standalone,ManagedStrippingLevel.Minimal);
  PlayerSettings.SetIl2CppCodeGeneration(UnityEditor.Build.NamedBuildTarget.Standalone,UnityEditor.Build.Il2CppCodeGeneration.OptimizeSpeed);
  PlayerSettings.SetIl2CppCompilerConfiguration(BuildTargetGroup.Standalone,Il2CppCompilerConfiguration.Debug);
  EditorUserBuildSettings.development=true;EditorUserBuildSettings.allowDebugging=false;UnityEditor.WindowsStandalone.UserBuildSettings.createSolution=false;
  PlayerSettings.productName="ResourceMountingProbe";PlayerSettings.companyName="TwoEggExperiment";
  var settings=HybridCLRSettings.instance;settings.enable=true;settings.useGlobalIl2cpp=false;settings.hotUpdateAssemblies=new[]{"HotUpdate"};HybridCLRSettings.Save();
  LabRuntime.CheckLock(Root);if(!new InstallerController().HasInstalledHybridCLR())new InstallerController().InstallFromLocal(Path.Combine(Root,".local/combined-libil2cpp"));LabRuntime.SaveLock(Root);
  Directory.CreateDirectory("Assets/Fixtures");Directory.CreateDirectory("Assets/Resources");
  File.WriteAllText("Assets/Fixtures/Payload.txt","resource-payload-v1");AssetDatabase.Refresh();
  var type=Type.GetType("ResourceHot.MountProbe, HotUpdate",true);
  MakePrefab(type,"Assets/Fixtures/BundleProbe.prefab");MakePrefab(type,"Assets/Resources/MainPackageProbe.prefab");
  var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);EditorSceneManager.SaveScene(scene,"Assets/Probe.unity");EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene("Assets/Probe.unity",true)};
  PrebuildCommand.GenerateAll();
  Directory.CreateDirectory(Path.Combine(Output,"Bundles"));
  var manifest=BuildPipeline.BuildAssetBundles(Path.Combine(Output,"Bundles"),new[]{new AssetBundleBuild{assetBundleName="resource-probe.bundle",assetNames=new[]{"Assets/Fixtures/BundleProbe.prefab"}}},BuildAssetBundleOptions.UncompressedAssetBundle|BuildAssetBundleOptions.ForceRebuildAssetBundle,Target);
  if(!manifest)throw new Exception("AssetBundle build failed");
  Directory.CreateDirectory("Assets/StreamingAssets");
  File.Copy(Path.Combine(SettingsUtil.GetHotUpdateDllsOutputDirByTarget(Target),"HotUpdate.dll"),"Assets/StreamingAssets/HotUpdate.dll.bytes",true);
  File.Copy(Path.Combine(Output,"Bundles/resource-probe.bundle"),"Assets/StreamingAssets/resource-probe.bundle",true);
  File.WriteAllText("Assets/StreamingAssets/resource-build-id.txt",Environment.GetEnvironmentVariable("RESOURCE_BUILD_ID"));
  AssetDatabase.Refresh();AssetDatabase.SaveAssets();Debug.Log("RESOURCE_PREPARE_OK");
 }
 static void MakePrefab(Type type,string path){
  var go=new GameObject("ResourcePrefab");go.SetActive(false);var child=new GameObject("Anchor");child.transform.SetParent(go.transform,false);
  var c=go.AddComponent(type);type.GetField("Number").SetValue(c,42);type.GetField("Label").SetValue(c,"resource-prefab-v1");type.GetField("Anchor").SetValue(c,child.transform);type.GetField("Payload").SetValue(c,AssetDatabase.LoadAssetAtPath<TextAsset>("Assets/Fixtures/Payload.txt"));
  if(!PrefabUtility.SaveAsPrefabAsset(go,path))throw new Exception("Prefab save failed");UnityEngine.Object.DestroyImmediate(go);
 }
 public static void Build(){
  var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{"Assets/Probe.unity"},locationPathName=Path.Combine(Output,"Player/ResourceMountingProbe.exe"),target=Target,options=BuildOptions.Development});
  Debug.Log("RESOURCE_BUILD_RESULT "+report.summary.result);if(report.summary.result!=BuildResult.Succeeded)throw new Exception("Player build failed");
 }
}
