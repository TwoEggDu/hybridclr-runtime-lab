# Type Initialization Implementation Plan
> Execute inline using superpowers:executing-plans; one fresh independent final review.
Goal: four-case AOT/hot Player evidence, linked from existing articles.
Architecture: shared scenario + InitEvents sink/InitRunner; InitBuild locked builder; init_results parser, init_lab receipts/export; InitMetadata final-DLL reader.
Spec: ../specs/2026-10-26-type-initialization-design.md
Constraints: unchanged upstream/prior samples; no commit/push; no Unity C++ body publication; preserve unrelated site changes.
Review focus: relaxed early initialization; failed initializer retry; closed-generic state; final-DLL identity; missing/reordered/forged events.
## Task 1 — Acceptance/sample
- [x] tests/test_init_results.py RED then tools/init_results.py GREEN. Reject identity/order/count/value/exception mutations, allow relaxed early init.
- [x] samples/type-initialization/Scenarios.cs mirrored to AOT/hot; sink/runner/asmdefs/metas. Same scenario except namespace.
Interface: parse_player(text,side,mode,build_id); TIP JSON env/stage/meta/init/method/read/caught/done, monotonic seq.
## Task 2 — Build/evidence
- [x] New InitBuild/tools/init_lab.py build/run/verify/export reuse existing locked runtime and receipts. Final-DLL metadata extraction without executing input DLLs.
- [x] 30 normal Players plus2 separately counted native traces; input/artifact/raw-log/tool/event hashes; reparse originals; filtered public evidence.
Interface: build-lock binds inputs/artifacts, run-status binds raw logs; public results bind own events and measurements. Native internals remain separate unless traced.
## Task 3 — Articles
- [x] Three articles, three indexes/plans, one execution record. Scoped Hugo/link checks and full tests/public boundary check.
- [x] Independent review, repair substantive findings. No commit/push.
## Ledger
Ruling: user approved four-case proposal and direct execution; record design without re-requesting approval. Existing codex experiment branch with fresh project; isolate site candidate from shared dirty tree.
Pre-flight: sample/parser/export share TIP schema; builder/runner share build_id; verifier uses final AOT backup and shipped hot DLL, not Editor DLLs.

Task1: seven acceptance tests with identity/order/value mutations RED -> GREEN. Mirrored samples created.
Ruling: add one independent hot/strict CDB process for the existing source-reading stack/cache requirement, separate from24 normal controls. Final metadata includes only self-authored CIL.

Ruling: original hot/failed control exits2: TypeInitializationException escaped the interpreted method's catch. Keep this negative observation; do not patch runtime or mark semantics passing. Add failed-outer with identical AOT reflection boundary on both sides, two direct accesses through Cases.AccessFailed, preserving TargetInvocationException wrapper. Final matrix30 normal processes (27 complete/3 escaped if repeated), plus native traces. Old exploratory build/logs archived in ignored exploration-d70cd30b; new build required because own sample changed.

Task2 complete: final build5b177115,43 inputs/227 artifacts;30 normal processes (27 exit0/3 escaped exit2),2 native traces. Final CIL call offset30 inside try[29,47) for both sides, catch TypeInitializationException. Metadata inspection augmented after build while all Player artifact hashes stayed unchanged; no runtime/sample rebuild for the reader-only enhancement. Full suite142/142; public export reparses to identical observations. Native Ping cache ready before cctor execution, including failed route with no Ping body event. Root cause of catch-boundary discrepancy remains unproven.

Final review: independent reviewer verified original/public hashes and reported2 P2 gate gaps. Both reproduced RED then fixed GREEN: permit relaxed init before unique environment record; reject cctor Execute before Transform. Full suite144/144,563 public files checked. Original30 normal +2 native logs reparse unchanged; no further Player builds/runs. Task3: three articles/three indexes/three canonical plans/one execution record; isolated Hugo1414pages/zeroERROR,428 links/anchors across6pages, browser5-row matrix and index jump verified. No deferred findings; no commit/push.

Publication phase (2026-10-26): user explicitly authorized committing/pushing this reviewed experiment, then fixing the article/index evidence links and publishing the documentation. Earlier no-publication notes describe the implementation phase. Runtime inputs, Player records and validation remain unchanged.
