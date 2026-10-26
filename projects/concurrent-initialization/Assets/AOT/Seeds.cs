public static class ConcurrentSeeds {public static int NeverRun(){return AotConcurrent.Cache<int>.Read()+AotConcurrent.Cache<string>.Read();}}
