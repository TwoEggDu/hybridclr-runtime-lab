# Cross AOT/interpreter exception propagation and initializer escape

2026-10-26. Sources, the public counterfactual patch and verified evidence are published together in the commit containing this record; use the fixed commit linked by the articles. Baseline46ac71c is the preceding type-initialization experiment, not this sample.

## Fixed environment and exact intervention

Existing lab-lock.json: local-custom Unity2022.3.62f3_96770f904ca7, package9.0.3/runtime9.0.1, Windows x64 Development IL2CPP C++ Debug, Minimal stripping. New projects/exception-flow. Both variants share43 input hashes, identical final stripped Probe.AOT.dll and shipped HotUpdate.dll.bytes, and identical4 generated runtime files. HotUpdate is excluded from AOT registration.

Baseline build_id0628a07c-8e75-40ed-bb91-c295c40414c7; counterfactual build_idc811dcee-5771-4a89-86f9-ed53d862be1d. Each Player has227 artifact hashes. Of919 runtime input files, only public hybridclr/interpreter/Interpreter_Execute.cpp differs. patches/exception-flow-delay-active-imi.patch changes only PREPARE_NEW_FRAME_FROM_INTERPRETER: prepare nextImi as a temporary, run class initialization, assign active imi only after success. This preserves method preparation before initialization; it does not alter catch types, call-site source, DLLs or runtime configuration.

The intervention lives only in this new project's Library. Shared .local/combined-libil2cpp, upstream Git sources and all earlier project Libraries/Players/receipts remain unchanged. Counterfactual is an experimental variant, not an upstream release or production acceptance.

## Matrix and actual outcomes

Four directions: aa=AOT->AOT, hh=hot->hot, ha=hot->AOT, ah=AOT->hot using a cached delegate. Entry into hot uses cached delegates; reflection creates them during setup and is not a measured Invoke/DynamicInvoke. Every process makes two attempts, with typed catches and finally in the caller.

Four target shapes: ordinary InvalidOperationException body; manually thrown TypeInitializationException with inner InvalidOperationException; failed .cctor through short void Ping; same failed type through branched int PingRet (guaranteed non-inlining by this version's branch rule, not by return type alone).

Each direction/shape has3 independent non-debugger processes,48 per variant,96 total. All drivers exit0 to complete observation; classification is separate.

| Case | Baseline | Counterfactual |
|---|---|---|
| hh/cctor-ret |3 processes, both accesses escape; inner catch0/finally0; .cctor body once|3 processes, both accesses caught; finally1 per access; .cctor body once|
| Other15 direction/shape combinations |45 processes handled, finally1 per access|45 processes handled, finally1 per access|

A manually thrown TypeInitializationException is caught on the original runtime, so exception type alone does not explain the escape. Void/int here also differ in method body control flow and actual lowering; no causal claim that return type alone causes the bug.

## Causal native evidence

3 matching-PDB hh/cctor-ret processes per variant (two contexts each): baseline frame/current IP still belong to RunOwn while active imi equals prepared PingRet interpData. ActiveEH0, callerEH3. Throw offset304 lies inside caller typed-catch [48,328) and finally [48,448); ipBase matches caller. Handler search therefore uses the wrong method's empty EH table and unwinds the caller, skipping its handlers.

Counterfactual contexts retain caller imi: ActiveEH3/callerEH3, same throw offset304 and ranges. PingRet cache remains prepared in both versions, isolating the early active-context switch. Both accesses then execute catch/finally. The caller MethodDef token0x0600000A is bound to the final HotUpdate metadata.

Final own CIL places Failed.PingRet call at87 in try[17,96), two typed catches, and finally[17,144). CIL87 and transformed304 are different coordinate systems and are not compared directly.

2 additional matching-PDB short-void controls (one per variant) actually stop at InitClassStaticCtor, offset248, with active imi matching caller on both attempts. This is the inlining path; it does not execute the premature frame-transition assignment. Public MethodBodyCache/TransformContext source and observed opcode explain why merely adding C# NoInlining is insufficient to prove the internal path in this fixed version.

96 normal +8 native processes are final accepted evidence,104 own event files. Initial9d11ae2f short-only controls, C# setup compile error and rejected CDB quoting logs are preserved under ignored exploration paths, not counted in this matrix. Read-only original5b177115 RunFailed probes also showed ActiveEH0/callerEH1, offset88 inside[88,136), consistent with the same mismatch; those exploratory raw probes remain local.

## Reproduce

```text
python -B tools/eh_lab.py build --variant baseline --editor <locked Unity.exe>
python -B tools/eh_lab.py run --variant baseline
python -B tools/eh_lab.py trace --variant baseline --cdb <x64 cdb.exe>
python -B tools/eh_lab.py build --variant counterfactual --editor <locked Unity.exe>
python -B tools/eh_lab.py run --variant counterfactual
python -B tools/eh_lab.py trace --variant counterfactual --cdb <x64 cdb.exe>
python -B tools/eh_inline.py --cdb <x64 cdb.exe>
python -B tools/eh_lab.py verify
python -B tools/eh_lab.py export
python -B -m unittest discover -s tests
python -B tools/check_repo.py
```

The normal/native raw logs, PDBs, generated Unity C++ and binaries remain ignored. Public results contain own CIL/metadata/events and hash-bound numeric native summaries. No filter/rethrow/nested-finally completeness, other-platform/version, concurrency or performance claim. Findings apply to this fixed source/custom Editor and exercised non-inlined frame-transition path.

## Final validation

161 Python tests and725-file public boundary checks passed. Independent read-only final review confirmed the raw hashes/reparses,104 own event files, exact same-input comparison and narrow causal claims; no P1/P2 findings. All prior experiments and shared runtime sources remain unchanged. Article publication is a separate later step.
