using System;
using System.IO;
using System.Security.Cryptography;
using HybridCLR.Installer;
using HybridCLR;
public static class LabRuntime
{
    const string Marker = "Library/lab-runtime-lock.json";
    static string Hash(string path)
    {
        using (var stream = File.OpenRead(path))
        using (var sha = SHA256.Create()) return Convert.ToBase64String(sha.ComputeHash(stream));
    }
    static void VerifyImplementation(string root)
    {
        var source = Path.Combine(root, ".local/combined-libil2cpp");
        var installed = Path.Combine(SettingsUtil.LocalIl2CppDir, "libil2cpp");
        foreach (var file in Directory.EnumerateFiles(source, "*", SearchOption.AllDirectories))
        {
            var relative = file.Substring(source.Length + 1);
            // GenerateAll owns this directory; compare all other implementation files.
            if (relative.Replace('\\', '/').StartsWith("hybridclr/generated/")) continue;
            var target = Path.Combine(installed, relative);
            if (!File.Exists(target) || Hash(file) != Hash(target))
                throw new Exception("Installed runtime differs from prepared source: " + relative + ". Preserve/review local changes before using a fresh Library.");
        }
    }
    public static void CheckLock(string root)
    {
        if (!new InstallerController().HasInstalledHybridCLR()) return;
        var expected = File.ReadAllText(Path.Combine(root, "lab-lock.json"));
        if (!File.Exists(Marker) || File.ReadAllText(Marker) != expected)
            throw new Exception("Installed runtime has an unknown/different lab lock. Use a fresh project Library after checking your local changes.");
        VerifyImplementation(root);
    }
    public static void SaveLock(string root)
    {
        VerifyImplementation(root);
        File.Copy(Path.Combine(root, "lab-lock.json"), Marker, true);
    }
}
