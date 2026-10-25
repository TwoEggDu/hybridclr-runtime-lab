# GC retention and bounded pressure in native callbacks

Goal: execute the user's approved follow-up on the locked custom Unity/v9 Windows x64 environment, then update existing GC/thread articles, experiment evidence and all three indexes.
Architecture: independent projects/gc-callbacks + self-authored native/gc-callbacks/plugin.cpp; artifacts/gc-callbacks receipts and a strict result parser. Old experiments remain unchanged.
Spec: three groups from the approved conversation: Normal GCHandle context; hot local references surviving a collection during a native callback; bounded single-native-thread allocations/reference writes with orderly stop.

## Fixed choices and acceptance boundaries
- lab-lock.json unchanged: custom 2022.3.62f3_96770f904ca7, package v9.0.3/runtime v9.0.1/paired il2cpp_plus, x64 Development C++ Debug Minimal.
- handle: create hot context on a short-lived managed creator; use Normal GCHandle, pass only its opaque IntPtr token to native. Before native start and after join, explicit collections must preserve held control. Stop/join before freeing handle; released survivor count is an observation, not an immediate-zero guarantee.
- stack: no context handle. Static hot callback creates a target only in its active invocation, exposes a short WeakReference, blocks at an AOT synchronization gate, survives explicit GC, verifies content after resume, then returns. Weak reference is observed again after native join. This is retention evidence, not a GC root snapshot.
- stress: 1024 callbacks on one raw OS thread; each creates 32 nodes with 256-byte payloads, changes references in a handle-retained hot context, checks payload/link invariants. Payload allocation total 8,388,608 bytes excludes object/header/interop overhead. Gate every 32 calls (32 checkpoints); main requests incremental collection slices (1,000,000 ns each) and records true/false returns. No forced full collection during stress; post-join cleanup collections are separate.
- all modes stop during the final held callback; Join(0) must be incomplete before release. Join completes before freeing handle and dropping callback delegate. Bounded waits, failure releases gate and tries join while preserving roots on failure. No Unity APIs on callbacks.
- Run three fresh processes per mode. Trace handle/stack separately with matching PDB, pointer/ABI/target validation, collection while callback active, scoped cleanup and post-join handle release. Stress has standalone workload evidence; do not imply its entire execution was single-stepped.
- No throughput/GC latency/wbarrier-completeness/heap-return/other-platform claims. Public files include only our native plugin, own C# and sanitized observations. Implementation phase stayed local; publication requires subsequent user authorization.

## Tasks
- [x] Parser negative tests RED then GREEN, with correct-but-nonzero released survivors preserved.
- [x] New isolated project/plugin and build/source/receipt identity checks; build locked runtime.
- [x] Nine standalone runs and focused retention traces; strict verification.
- [x] Independent review, hashed source-free evidence, fix acceptance gaps.
- [x] Update existing GC/thread bodies, three indexes/plans, Hugo and link checks.

## Ledger
- User approved implementation; the bounded counts and layout above are agent choices. No repeated approval required.

- Accepted final build: 148235df-910b-441f-94b2-b7348eb02d8c. Initial compile normalized ProjectSettings and generated AOTGenericReferences and was rejected. Reference invariants were strengthened after review; then collection counter instrumentation was added and rebuilt. Only the final build's evidence is accepted.
- Nine standalone Player runs pass. handle/stack active callback windows record GC delta3; stress each records count1024/checksum786944/errors0, payload8,388,608 bytes, 32 checkpoints, 128 incremental requests all false, process-window GC delta256. This does not show an ongoing multi-slice mark cycle or prove barriers complete.
- Focused handle/stack CDB evidence passes matching PDB, pointer/context/seq/mode, callback identity, active Full after root registration and before scope leave, cleanup and join-before-FreeContext. Stress has no per-call native trace.
- Review fixes: verify all64 slot IDs/occupancy/Head/Next; order all checkpoints within lifetime; enforce GCdelta>=3 for explicit collection groups. Each acceptance gap has a failing-then-passing negative test. Python31 tests and actual hot-source desktop data-corruption4/4 pass. Desktop tests are not GC/Player evidence.
- Article and canonical plans updated: three existing GC/thread bodies, three indexes and five plan/execution records. Hugo0.157.0 builds1401 pages/zero errors (shared workspace count); 349 local links/anchors across six target pages pass.
- Implementation ended without commit/push. The user subsequently authorized publishing the experiment and related article/index updates with fixed links. b915632 remains the prior experiment baseline.
