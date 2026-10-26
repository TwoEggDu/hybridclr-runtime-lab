# Exception Flow Implementation Plan
> Execute inline with executing-plans/TDD; one independent whole-scope final review.
Goal: causal evidence for hot initializer exception escape.
Spec: ../specs/2026-10-26-exception-flow-design.md
Architecture: read-only original-PDB probe, new shared AOT/hot sample + ExceptionBuild; eh_results/eh_lab evidence gates; isolated public-runtime macro counterfactual; own metadata reader. Record exact sources and outputs per variant.
Review focus: frame/imi mismatch, init-vs-body throw, bridge/reflection wrappers, repeated failed initialization, finally/handler execution, unchanged input DLLs, publication privacy.
## Task1 — Locate and acceptance
- [x] Read-only original failure probe; capture frame/current imi/caller interpData/code offset/EH count at native catch.
- [x] Unit tests RED then parser GREEN: identity/matrix/event order/count/exception/catch/finally/escaping. Do not force unexpected failure into success.
## Task2 — New Player and counterfactual
- [x] New projects/exception-flow, mirrored source, fixed Editor/runtime verification. Per-side ordinary/manual-typeinit/failed-initializer and AOT-to-hot cached delegate; three independent processes per route.
- [x] Native baseline context, public one-point patch only after proof; build counterfactual with unchanged sample/DLLs; repeat full matrix + context traces. Bind hashes; export own data only.
## Task3 — Documentation and review
- [x] Core exception/type-init articles, related contradictory status links, three indexes/plans and execution record.
- [x] Full Python/public checks; isolated Hugo/link/browser check. Fresh final review; fix substantive issues. No commit/push.
## Ledger
Ruling: user approved the proposal and existing environment, so record design/plan and proceed without redundant approval. Lab branch codex/gc-managed-thread-lab; isolated project/runtime outputs inside this lab. Site dirty edits will use scoped candidate.
Preflight: build variant and build_id identify every event; context parser consumes actual native PDB outputs; old receipts untouched. Public counterfactual applies only to the named public HybridCLR macro, not Unity implementation bodies.

Original probe: RunFailed frame->method->interpData differs from active imi; activeEh0/callerEh1; throw offset88 in caller transformed try[88,136), ipBase matches caller. This supports testing state-switch ordering, not a source try-placement explanation. No runtime source changed yet.

Build setup: generated C# path separator literal failed compilation before Player creation; replaced with explicit char92, preserved compiler log. No runtime/Player evidence accepted from this attempt. Parser/patch tests10 methods RED -> GREEN.

Ruling: first new baseline (9d11ae2f)36 cases all handled; native simple-void cctor contexts matched caller (3 clauses), unlike original int-return sample. Public MethodBodyCache/TransformContext shows short method inlining inserts InitClassStaticCtor before frame switch and does not rely solely on MethodImpl NoInlining. Preserve this useful control. Add cctor-ret using same Failed type with explicit branch to guarantee non-inlining; archive exploration logs/own input, rebuild final baseline48 cases. Do not attribute difference to return type alone. CDB newline generation bug reproduced RED and fixed GREEN before accepting native logs.

Task2: final baseline0628a07c and counterfactualc811dcee. Each48 normal processes; baseline45handled/3hh-cctor-ret escaped (finally0), counterfactual48handled (finally1 per access). Source43, own final AOT/hot DLLs and generated files byte-equal;919 runtime inputs differ only selected public macro file. Stronger counterfactual preserves method preparation before cctor in a nextImi temporary and delays only active imi assignment. Three PDB processes per variant capture6 caller contexts: baselineactiveEH0/callerEH3/imi=PingRet versus counterfactual3/3/imi=caller, sameoffset304 inside[48,328). Short-void control each variant1 additionalnative process actually hits InitClassStaticCtor atoffset248, active caller retained. No shared upstream/runtime/old project modified.

Task3 complete: twelve scoped site files (five related articles,three indexes,three canonical plans,one execution record); isolatedHugo1414pages/zeroERROR,500 internal links/anchors across8pages; actual browser matrix and index anchor verified. Full161 Python tests and725-file public boundary pass. Independent fresh review found no P1/P2; original hashes/reparses104 records and causal scope confirmed. No deferred issues, Git commit/push or upstream source edits.

Publication phase2026-10-26: user explicitly authorized committing/pushing this reviewed experiment, then fixing the article/index evidence links and publishing the documentation. Earlier no-publication notes describe the implementation phase. Runtime/sample inputs and accepted evidence remain unchanged.
