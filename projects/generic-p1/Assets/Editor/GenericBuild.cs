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

public static class GenericBuild
{
    public static void Build()
    {
        var target = BuildTarget.StandaloneWindows64;
        PlayerSettings.SetManagedStrippingLevel(BuildTargetGroup.Standalone, ManagedStrippingLevel.Minimal);
        PlayerSettings.SetIl2CppCodeGeneration(UnityEditor.Build.NamedBuildTarget.Standalone, UnityEditor.Build.Il2CppCodeGeneration.OptimizeSpeed);
        if (!EditorUserBuildSettings.SwitchActiveBuildTarget(BuildTargetGroup.Standalone, target))
            throw new Exception("Switch target failed");
        PlayerSettings.SetScriptingBackend(BuildTargetGroup.Standalone, ScriptingImplementation.IL2CPP);
        PlayerSettings.SetIl2CppCompilerConfiguration(BuildTargetGroup.Standalone, Il2CppCompilerConfiguration.Debug);
        EditorUserBuildSettings.development = true;
        EditorUserBuildSettings.allowDebugging = false;
        UnityEditor.WindowsStandalone.UserBuildSettings.createSolution = false;
        PlayerSettings.productName = "RuntimeGenericProbe";
        PlayerSettings.companyName = "TwoEggExperiment";
        var settings = HybridCLRSettings.instance;
        settings.enable = true;
        settings.useGlobalIl2cpp = false;
        settings.hotUpdateAssemblies = new[] { "HotUpdate" };
        HybridCLRSettings.Save();
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        EditorSceneManager.SaveScene(scene, "Assets/Probe.unity");
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene("Assets/Probe.unity", true) };
        var project = Directory.GetParent(Application.dataPath);
        var root = Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        var caseId = project.Name == "generic-p0" ? "p0" : "p1";
        LabRuntime.CheckLock(root);
        if (!new InstallerController().HasInstalledHybridCLR())
            new InstallerController().InstallFromLocal(Path.Combine(root, ".local/combined-libil2cpp"));
        LabRuntime.SaveLock(root);
        Debug.Log("GENERIC_BUILD_RUNTIME " + SettingsUtil.LocalIl2CppDir);
        PrebuildCommand.GenerateAll();
        Directory.CreateDirectory("Assets/StreamingAssets");
        File.Copy(Path.Combine(SettingsUtil.GetHotUpdateDllsOutputDirByTarget(target), "HotUpdate.dll"), "Assets/StreamingAssets/HotUpdate.dll.bytes", true);
        File.Copy(Path.Combine(SettingsUtil.GetAssembliesPostIl2CppStripDir(target), "Generic.AOT.dll"), "Assets/StreamingAssets/Generic.AOT.dll.bytes", true);
        AssetDatabase.Refresh();
        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions {
            scenes = new[] { "Assets/Probe.unity" }, target = target,
            locationPathName = Path.Combine(root, "artifacts/generics/Player-" + caseId, "RuntimeGenericProbe.exe"),
            options = BuildOptions.Development
        });
        Debug.Log("GENERIC_BUILD_RESULT " + report.summary.result);
        if (report.summary.result != BuildResult.Succeeded) throw new Exception("Build failed");
    }
}
