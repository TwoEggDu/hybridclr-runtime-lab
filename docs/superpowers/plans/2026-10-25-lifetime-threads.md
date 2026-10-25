# Object lifetime and managed threads experiment

Goal: Extend the approved runtime lab with real Player evidence for object retention/release and managed worker calls, then update existing articles.
Architecture: one independent projects/lifetime-threads Unity project, separate gc and threads processes, scoped artifacts/lifetime receipts. Reuse pinned dependencies and Editor identity guards.
Spec: user approved static-container/event retention and managed worker experiment; native callbacks and performance are deferred.

## Constraints and observation contract
- Same lab-lock.json and custom Editor 2022.3.62f3_96770f904ca7; Windows x64 IL2CPP Development, C++ Debug, Minimal stripping.
- No changes to Editor/runtime implementation. GC enabled, incremental setting explicitly recorded; forced collections are observation aids, not performance measurements.
- GC: create 16 hot objects per group (unrooted/static/event) on a short-lived managed worker, then join it to exclude its active stack. AOT owns static references/event delegates and weak observers. Observe retained, static-cleared, all-cleared stages. Live controls must survive; released counts are observations with bounded collection attempts, never a universal immediate-reclamation guarantee.
- Threads: two simultaneously alive managed workers call the same hot Add twice each; synchronize worker execution to observe one conversion and shared method cache. Record managed and OS thread IDs, Execute, MachineState create/destroy and root deregistration. No Unity API on workers.
- Only own sample code and sanitized evidence are public. Source pointers only for Unity implementation. No native callback or GC root-snapshot claims without evidence.
- Do not commit/push this round unless separately requested; use dedicated branch in the clean lab, exact article files in shared dirty article workspace.

## Tasks
- [x] Parser tests RED then GREEN: reject missing/duplicate stages, lost held targets, bad worker identities/results. Existing receipt tests remain applicable.
- [x] Implement isolated project/build/run and bounded process timeouts. Build current sources and verify hot DLL excluded from AOT.
- [x] Run GC and threads in three fresh processes each. Capture native worker lifecycle with matching PDB; verify identity, cache, roots and cleanup from actual trace.
- [x] Save source/build/log hashes and source-free evidence; independent review before completion.
- [x] Update existing GC and thread articles and their plans/index validation status; Hugo and links.

## Ledger
- Context/design fixed by user's approval. Routine implementation choices above are agent decisions. Existing call-chain/generic evidence is preserved in its separate artifact directory.

- Completed build: 70021d1d-8d18-4bdf-8066-446dd9898b80. First post-build decode failed under the Windows default encoding; switched generated registration read to UTF-8 and rebuilt. Only the subsequent complete receipt was accepted.
- Three standalone GC and three standalone threads processes passed; one separate CDB process recorded matching PDB, four Execute / one Transform, two overlapping MachineState lifetimes and matching root cleanup entries.
- Independent review found and fixed missing pre-build manifest freeze/key comparison and missing environment/load acceptance. Native verifier and article evidence review passed. Fifteen unit tests passed; these validate parsers/receipts, not runtime behavior.
- Article changes: three existing bodies, three indexes, three canonical plans and two execution outlines. Hugo 0.157.0 built 1379 pages with zero errors (shared worktree count); 328 local links/anchors on six target pages passed. No GC root snapshot, native callback, concurrent first conversion or performance claims.
- Implementation ended without commit/push; the user subsequently authorized publishing both repositories and adding fixed experiment links. The new evidence retains the original source base and captured source hashes; the extension does not exist in e0220099.
