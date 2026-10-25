using GenericProbe;

namespace HotUpdate
{
    public static class GenericCalls
    {
        public static string RunString() => GenericTarget.Echo<string>("echo-string");
        public static int RunInt() => GenericTarget.Echo<int>(42);
        public static long RunPayload()
        {
            var result = GenericTarget.Echo<Payload>(new Payload { X = 7, Y = 11 });
            return result.X * 1000000L + result.Y;
        }
    }
}
