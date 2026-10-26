# Incremental-slice reference mutations and barrier paths implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline. User approved the design and execution. Current request does not include commit/push.

**Goal:** Establish an observed single GC cycle spanning slices, compare AOT and interpreted reference writes, and capture actual barrier/dirty paths without claiming all barriers or unique roots.
**Architecture:** Independent projects/incremental-barriers and artifacts/incremental-barriers; own NativeProbe observer subscribes through existing IL2CPP profiler exports using a fixed allocation-free event buffer. Keep locked runtime/Editor untouched. A pre-warmed persistent managed worker and main-thread serial handshakes isolate incremental ordering from native-thread races.
**Tech Stack:** Custom Unity2022.3.62f3_96770f904ca7, package9.0.3/runtime9.0.1/il2cpp_plus2022.3.x-9.0.1, Windowsx64 Development IL2CPP Debug, CDB and Python.
**Spec:** User-approved preceding design: stable cross-slice cycle, same object graph AOT/hot writers covering fields/reference arrays/reference-containing structs, identify actual write/barrier paths and graph results. Preserve unproven marking/extra-root caveats.

## Constraints
- Baseline4861bed remains unchanged. No Editor installation or runtime source patches.
- Manual GC mode is an experiment variable to suppress automatic collection; explicitly start a collection, advance via public CollectIncremental, record native profiler cycle events. Heap/budget bounded; unsupported or never-overlapping runs are rejected, not relabeled as passing.
- Capture GC start/end and mark phase separately; true is not cycle identity. Require unchanged cycle and no End across accepted mutation steps.
- Candidate targets weakly held before cycle, writers return before next slice. Native inspection should assess owner/target marks and dirty effects where possible. Any inability to exclude incidental roots is documented; path hit and liveness alone do not establish barrier necessity.
- Raw PDB/disassembly/logs stay ignored; publish only self-authored sources/events/numeric receipts. No memory snapshots during incremental timing run.
- Articles: three existingGC/thread bodies, three indexes, canonical plans and existing execution records. Other TechStackShow changes preserved.

## Task1: Controlled cycle and evidence gate
- [x] Write negative tests first: no remaining work, cycle changed, End before write, missing/out-of-order mutation, wrong graph count.
- [x] Implement profiler observer and same-graph AOT/hot sample in isolated project. Build pinned environment and verify excluded HotUpdate/AOT parity.
- [x] Probe workload/budget and establish stable cross-slice cycle with native events. Preserve rejected explorations separately.

## Task2: Covered write paths
- [x] Run AOT/hot three independent processes each; record explicit cycle and write sequence, final graph identities and payload.
- [x] Verify actual CIL, matchingPDB writer stores/barriers/dirty path and collector state; examine owner/target marks and extra roots rather than infer necessity from survival.
- [x] Keep failures/negative controls meaningful; prove parser rejects changed-cycle and graph corruption.

## Task3: Publication-ready record
- [x] Bind logs and summaries to final source/build/tool hashes; preserve earlier receipts.
- [x] Add sanitized evidence README/results and update existing articles/indexes/plans with measured limits.
- [x] Hugo and link validation; final independent review and fixes. No Git publication.

## Progress
Initial lab clean at4861bed. Source confirms Manual mode disables automatic collection while explicit APIs exist; public profiler GC events are available conditionally and will be verified in actual Player. Plan execution authorized; no repeated approval needed.

Ruling: each writer runs on a short-lived managed worker, serialized by main-thread Join before the next slice. This removes writer native/interpreter stacks from subsequent roots and reduces incidental retention; it is not concurrent-GC or external-native-callback testing. First build succeeded but source fingerprint rejected generated AOTGenericReferences/settings normalization; preserve as initial observation and rebuild fixed inputs.

Initial probe b0c720b2 crashed during heap growth; actual stack points to profiler heap-resize dispatch with null resize callback. Provide a self-authored non-null, allocation-free OnHeap observer; do not modify runtime. Preserve rejected probe and rebuild. Probe runner now propagates nonzero child exits rather than only printing them.

Probe89e9cfa9 completed each collection before first accepted slice. Actual source/events show START/END wrap full-collection entry, whereas MARK_END accompanies completed mark/GC number increment. Ruling: use unchanged MARK_END count and native GC_gc_no for cycle identity, distinguish repeated MARK_START attempts, set budget BEFORE explicit start and allocate retained workload after the initial full collection. Preserve rejected false-only probe.

Probe0599bce9 established12 true slices with unchanged MARK_END, but creating/registering a new writer thread completed the cycle before the first write; gate correctly rejected bothwriters. Ruling: create/warm one persistent managed worker before initialFull, serialize mutations with events, scrub64KiB native stack after each writer returns and wait; Join only after cycle. This reduces stale native stack roots while avoiding registration mid-cycle; no claim of all auxiliary roots absent. Initial root/thread model updated based on observed behavior. Drain through existing il2cpp_gc_collect_a_little to stop at first completion without repeatedly requesting new cycles. Log BASE completion count before start; do not label void start as more=True.

Final sample70a8a176: owner/arrays prepared before baselineFull, large retained workload allocated after it. Twelve true public incremental requests on consecutive frames; drain uses native collect-a-little in a tight loop, avoiding per-frame allocation starting another cycle before observed termination. Graph/mark checks occur before worker Join (thread unregistration can complete an additional cycle). Native marker7 separates post-completion events. Six ordinary and six CDB Players accepted; nativeGC4->5, owner1/target0 beforewrites, alltargets1 beforeJoin, graph12078, three destination pages rescanned. AOT16/hot24 overload-entry hits, not store counts; dirty0->1 twice per process, remaining writes may hit already-dirty pages. Three hot traces each6 idle-root queries, owner registration/removal matched.89Python tests pass. Review/docs/build pending.

Final independent review: corrected wording from writer-return to marker4 writer-tail before KeepAlive/return; root queries classified baseline1/cycle2/postcycle3, not all waiting. Added raw event order validation, post-last-write/pre-END rescan gates and legal dirty-bit gates with seven negative tests.96 tests pass; six original trace logs reparse and hash-boundverify pass. Runtime/sample source unchanged, no newPlayer run required.

Completed: independent review passed after fixes. Isolated Hugo candidate1408pages/0ERROR; six article/index pages382 internal links/anchors valid. No commit/push.
