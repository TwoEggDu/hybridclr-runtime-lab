using GenericProbe;
using UnityEngine;

public static class SeedCalls
{
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
    static void Run()
    {
        var a = GenericTarget.Echo<string>("seed");
        var b = GenericTarget.Echo<int>(1);
        var c = GenericTarget.Echo<Payload>(new Payload { X = 2, Y = 3 });
        Debug.Log("GENERIC_SEEDS " + a + "," + b + "," + c.X + "," + c.Y);
    }
}
