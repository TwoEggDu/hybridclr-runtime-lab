# Resource mounting implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline. User explicitly approved the design and requested implementation. No Git publication in this request.

**Goal:** Establish the code and resource restoration paths and controlled failures for one hot-update MonoBehaviour.
**Architecture:** Isolated project and artifact tree, structured self-authored event records, frozen original Player and a separate startup-list-negative copy. Reuse receipts/prepare contracts.
**Tech Stack:** Locked custom Unity 2022.3.62f3_96770f904ca7, package9.0.3/runtime9.0.1, Windows x64 IL2CPP Development Debug; Python acceptance gates.
**Spec:** ../specs/2026-10-26-resource-mounting-design.md

## Constraints and review focus
- No edits to Editor/runtime or earlier experiment sources; no whole-repository staging or publication.
- HotUpdate must be excluded from AOT; correct assembly registration, DLL, bundle and asset identities are checked separately.
- Each route uses a fresh process. Positives need fields/references and full lifecycle, not only a GameObject result.
- Reject wrong build/mode, duplicate completion, missing type or fields, lifecycle reordering and unexpected runtime exceptions.
- Negative copy differs only in ScriptingAssemblies.json; originals and their hash-bound receipt stay unchanged. Unexpected negative success must be reported honestly.
- Raw/binary data remain ignored; unit tests verify acceptance gates and do not replace Player results.

## Task 1: Sample and acceptance contract
Files: tests/test_resource_results.py; tools/resource_results.py; projects/resource-mounting/Assets/AOT/{ResourceEvents,ResourceRunner}.cs, Assets/HotUpdate/MountProbe.cs and assembly definitions/metas.
Interface: parse_player(text, mode, build_id) returns one validated observation; RMP JSON events have env, dll, ping, snapshot, lifecycle, result, done stages.
- [x] Write parser tests for successful code/bundle, late DLL and missing registration, wrong build/mode, wrong field/reference, bad lifecycle, missing/duplicate completion and exception logs.
- [x] Observe RED (missing module), implement acceptance contract, observe GREEN (16 tests).
- [x] Implement one inactive object lifecycle, using an AOT event sink and reflection rather than a compiled HotUpdate reference.

## Task 2: Build and independent Player matrix
Files: Assets/Editor/ResourceBuild.cs, reused self-authored LabRuntime.cs; tools/resource_lab.py; project settings/fixtures; scoped check_repo.py entry.
- [x] Prepare exact dependencies and verify Editor identity; generate deterministic fixtures and ABI/link inputs.
- [x] Build local AssetBundle with TypeTree; build IL2CPP Player and assert hot DLL exclusion and startup-list inclusion.
- [x] Freeze source/tool/asset/DLL/bundle/Player hashes. Create copied Player with only the HotUpdate name/type-list entry removed.
- [x] Run code/bundle/late/unregistered/resources modes three times each in fresh processes. Inspect actual outcomes and reject false positives.
- [x] Reparse original logs, check matrix and hashes, publish only filtered own events and numeric/identity results.

## Task 3: Article and navigation closure
Files: experiment README/evidence; TechStackShow HCLR-4, three indexes, canonical plans and one resource execution record.
- [x] Explain observed route, lifecycle and failure evidence with limits; preserve prior URLs and unrelated edits.
- [x] Add a resource-identity flow diagram only where it aids the measured chain.
- [x] Hugo/link checks on scoped candidate, source/publication boundary checks and complete test suite.
- [x] Independent final review and fix any substantive findings; no automatic commit/push.

## Ledger
Pre-flight: shared contracts are ResourceEvents event schema, parse_player interface and resource_lab build_id/receipt. Existing receipt helpers are reused without changes.
Ruling: the user approved the proposal and asked to implement inline; this recorded design/plan needs no repeated approval. Commit steps are deferred until explicit publication request.

Task 1: acceptance contract RED→GREEN, 16 tests. Sample/build sources created; actual Player matrix pending.

Task 2 Ruling: initial Player compilation succeeded but mixed compiler-log encoding broke UTF-8 decoding. Preserve rejected logs; check the ASCII build marker on original bytes. Added resource-stage and anchor-identity gates before accepting Player evidence; regression tests observed RED.

Task 2 Ruling: fixed v9 writes Library/HybridCLR/.../generated/AssemblyManifest.inc, not the old article name AssemblyManifest.cpp. Startup list already contains one HotUpdate.dll. Resume acceptance of the completed Player only after the persisted prebuild source hash matches; no runtime source changed.

Task 2 Ruling: SaveAsPrefabAsset uses BundleProbe/MainPackageProbe as asset root names. First code controls and bundle restore succeeded; the parser incorrectly expected the temporary construction name ResourcePrefab. Keep the measured resource names, add RED→GREEN regression, preserve exploratory logs and run the complete matrix. Runtime/source inputs unchanged.

Task 2 complete: build7adc9fed, 46 source and256 artifact hashes bound. Fifteen accepted independent Players exit0; code/bundle restore and all negative controls report missing components. Raw bytes preserved; exported self-authored events reparse identically. Full Python suite118/118.

Final review: independent reviewer found two P2 acceptance gaps (stage order, phase counts), no contradiction in original Player evidence. Both reproduced RED in13 regressions;35 resource tests and131 total tests GREEN. Negative unexpected success is retained, while zero missing slots/phase transitions are needs_investigation. Unchanged15 original logs reparse as6 restored and9 missing_at_asset_and_instance; no newPlayer needed.

Task3 complete: HCLR-4 plus three indexes and canonical plans updated. Scoped Hugo1414pages/0ERROR,263 internal links/anchors, actual478x632 Mermaid render and index navigation verified. Final P2 gate fixes covered by13 RED→GREEN regressions;131/131 tests. No deferred minors or remaining review findings; no Git commit/push requested.
