# Native callback experiment implementation plan

Goal: Extend the approved lab on the pinned custom Editor and v9 runtime with real native callback and shutdown evidence, then update the existing thread article and three indexes.
Architecture: independent projects/native-callbacks plus self-authored native/native-callbacks/plugin.cpp. Separate registered/raw Player processes, scoped artifacts/callbacks. Windows x64 C ABI with cdecl int(int,int), generated Reverse P/Invoke wrapper and standard runtime attachment. No Editor/runtime modifications.
Spec: user's approved four-case approach in the conversation. Native callback lifetime and thread registration are the problem; return values alone are insufficient.

## Decisions and boundaries
- Reuse lab-lock.json and custom Editor 2022.3.62f3_96770f904ca7. Preserve previous Player/evidence directories.
- Use Win32 CreateThread for externally owned thread. Compare managed Thread invoking native inline with native-owned thread callbacks. One static hot callback with MonoPInvokeCallback; keep delegate rooted until native join returns.
- Raw thread invokes Add twice (5,15), then third callback (23) blocked on managed gate. Main coroutine observes entry, requests stop, confirms nonblocking join times out while in-flight, releases gate, joins, then drops delegate. Count must remain 3: no fourth callback.
- Callback work is pure framework/data; catch exceptions at ABI boundary. All waits bounded. No Unity API in callback.
- Trace actual wrapper, ScopedThreadAttacher, Attach/Detach, Execute, TLS create/free and root cleanup. Per-call state reuse/cleanup and addresses are observations, not predetermined assertions.
- Public source includes only our native plugin. Third-party C++ implementations, binary/PDB and full debugger logs stay local. Implementation phase stayed local; publication requires a subsequent explicit user request.

## Tasks
- [x] Parser negative tests RED then GREEN; retain old receipt tests.
- [x] Implement plugin, isolated AOT/hot project, compiler/build identity and scoped receipts.
- [x] Build, run registered/raw in three fresh Player processes each; trace matching PDB and verify identities, results and stop ordering.
- [x] Independent whole-change review; sanitized evidence/hashes.
- [x] Thread article, three indexes, canonical plans/execution evidence; Hugo and links.

## Ledger
- User approved the approach; routine ABI/plugin choices above are agent decisions. Proceed without repeating approval.

- Accepted build: 65d3ddb9-3bb0-4ce9-99b9-59f4ff1cc82b. Initial source normalization was rejected, then rebuilt with stable inputs and failure shutdown handling.
- Six standalone processes passed; separate registered/raw debugger captures have both matching private PDBs. Raw: three owned attachments/three cleanup cycles, Detach overload entries six; registered: zero wrapper-owned attachment and one retained TLS state cleaned at managed worker exit.
- Native verifier passed actual logs. First Execute explicitly null cache; one conversion and later method-cache reuse per process. Stop in third callback, callback return, worker end, join, delegate release all verified.
- Independent review found two verifier gaps (shutdown record ordering; absent cache field treated as null); negative tests observed failing and fixed. Twenty-two tests passed. No blocker in final code/evidence/article review.
- Public evidence is source-free except the self-authored native plugin. check_repo checks 241 public files. Third-party sources and original debug logs/binaries remain ignored.
- Article: thread body plus three indexes and five planning/execution documents. Hugo 0.157.0 built 1397 pages, zero errors (shared workspace count); 245 local links/anchors on four target pages passed.
- Implementation completed without commit/push. The user subsequently authorized publishing this experiment and the related article/index updates with fixed links. Previous a387d28 remains the prior experiment baseline.
