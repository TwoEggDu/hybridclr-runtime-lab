using System;
using System.IO;
using System.Reflection;
using HybridCLR;
using UnityEngine;

public static class GenericLauncher
{
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void Run()
    {
        int failures = 0;
        try
        {
            bool metadata = Array.IndexOf(Environment.GetCommandLineArgs(), "--metadata") >= 0;
            Debug.Log("GENERIC_MODE metadata=" + metadata);
            if (metadata)
            {
                var aot = File.ReadAllBytes(Path.Combine(Application.streamingAssetsPath, "Generic.AOT.dll.bytes"));
                var code = RuntimeApi.LoadMetadataForAOTAssembly(aot, HomologousImageMode.Consistent);
                Debug.Log("GENERIC_METADATA code=" + code + " bytes=" + aot.Length);
                if (code != LoadImageErrorCode.OK) throw new Exception("Metadata failed: " + code);
            }
            var bytes = File.ReadAllBytes(Path.Combine(Application.streamingAssetsPath, "HotUpdate.dll.bytes"));
            var assembly = Assembly.Load(bytes);
            var type = assembly.GetType("HotUpdate.GenericCalls", true);
            string[] names = { "RunString", "RunInt", "RunPayload" };
            object[] expected = { "echo-string", 42, 7000011L };
            for (int i = 0; i < names.Length; ++i)
            {
                var method = type.GetMethod(names[i], BindingFlags.Public | BindingFlags.Static);
                for (int call = 1; call <= 2; ++call)
                {
                    Debug.Log("GENERIC_BEGIN case=" + names[i] + " call=" + call);
                    try
                    {
                        var actual = method.Invoke(null, null);
                        bool ok = Equals(expected[i], actual);
                        Debug.Log("GENERIC_RESULT case=" + names[i] + " call=" + call + " value=" + actual + " ok=" + ok);
                        if (!ok) ++failures;
                    }
                    catch (Exception e)
                    {
                        var cause = e is TargetInvocationException && e.InnerException != null ? e.InnerException : e;
                        Debug.Log("GENERIC_EXCEPTION case=" + names[i] + " call=" + call + " type=" + cause.GetType().FullName + " message=" + cause.Message);
                        ++failures;
                    }
                }
            }
        }
        catch (Exception e) { Debug.LogException(e); ++failures; }
        Debug.Log("GENERIC_DONE failures=" + failures);
        Application.Quit(failures == 0 ? 0 : 2);
    }
}
