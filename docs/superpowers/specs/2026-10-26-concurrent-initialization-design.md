# Concurrent first calls and type initialization

Question: distinguish cold interpreted-method preparation, successful/failed static initialization, and closed generic static state under registered managed-thread contention.

Fixed baseline: lab-lock.json local-custom Unity 2022.3.62f3, package9.0.3/runtime9.0.1, Windows x64 Development IL2CPP C++ Debug/Minimal/OptimizeSpeed. Original prepared runtime; the previous exception-flow patch is NOT installed.

Independent projects/concurrent-initialization; AOT/hot scenario sources differ only by namespace. 2/4 workers wait behind an external gate. Each of 18 cells uses three fresh Players: AOT/hot cold(no cctor), Strict, Failed, Cache<int>/Cache<string>, plus mixed Strict reached by direct AOT and hot Bridge->AOT. Reflection dispatch is intentional, not a direct-call benchmark.

Explicit cctors set a, sleep150ms, then set b (failure throws after delay). No cctor waits for another worker or a test barrier. AOT catches each reflection wrapper, preserving exact TypeInitializationException/InvalidOperationException chain and message. Failed types receive two later main-thread accesses after joins. No hot-internal-catch claim.

Acceptance: complete ready/attempt/body/outcome/join events, distinct OS and managed IDs, one initializer per closed type, full field state only, exact failure cause, no initializer retry, no silent worker error. Final DLL flags/IL and hot AOT exclusion, source/artifact/runtime/raw-log hashes must match.

Separate native processes inspect MethodHandle-backed target MethodInfo at external pre-release and post-join markers. interpData must initially be null; methods that execute acquire stable cache identities. Hardware entry breakpoints for Transform/Execute avoid observed software-breakpoint counting ambiguity. ClassInit entry states and an AOT strict Sleep(1) stack sample establish selected contender/wait paths; no universal lock or concurrency proof.

Non-goals: performance, all schedules/platforms, native callback contention, cyclic/reentrant cctors, readonly/Nullable, metadata absence, global fixes. Public output contains own source, event JSONL, symbol summaries and hashes; no Unity C++ source, binaries, PDBs, generated C++ or raw logs.
