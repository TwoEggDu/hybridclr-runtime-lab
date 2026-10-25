using System.Runtime.CompilerServices;
using UnityEngine.Scripting;

namespace GenericProbe
{
    [Preserve]
    public struct Payload
    {
        public int X;
        public long Y;
    }

    [Preserve]
    public static class GenericTarget
    {
        [Preserve, MethodImpl(MethodImplOptions.NoInlining)]
        public static T Echo<T>(T value) => value;
    }
}
