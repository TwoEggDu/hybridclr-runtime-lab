# Type initialization and first-call Player experiment

2026-10-26. build_id `5b177115-e8ae-4e58-8808-2a0bc54b092a`. Sources and verified evidence are published together in the commit containing this record; use the fixed commit linked by the articles. Baseline74da063 contains only the preceding resource experiment, not this sample.

## Environment and identity

Exact lab-lock.json: local-custom Unity2022.3.62f3_96770f904ca7, package9.0.3 / runtime9.0.1, Windows x64 Development IL2CPP C++ Debug, Minimal stripping. New projects/type-initialization. AOT/hot scenario inputs match samples/type-initialization/Scenarios.cs modulo namespace. Both sides enter Cases through reflection; target calls inside each scenario are direct. AOT assembly loads at Player startup; hot Assembly.Load is explicit, so these are not identical assembly-loading paths.

43 source inputs and227 artifacts are SHA256-bound. HotUpdate is absent from AOT backup/code registration. metadata in results.json is read from final stripped Probe.AOT.dll and shipped HotUpdate.dll.bytes without executing those DLLs. All four target types have .cctor; Strict/Cache`1/Failed have beforefieldinit=false, Relaxed=true. Cases has no .cctor.

## Actual results

Each row has three independent non-debugger processes per side. First three cases plus two failure capture routes =30 processes. 27 complete/exit0; hot failed-inner3 consistently report escaped_first_access/exit2. These three are a captured discrepancy, not a semantic pass.

| Case | AOT | Hot |
|---|---|---|
| strict | one field/cctor initialization after before_call1, before Ping body; Ping7 twice, field41 | same |
| relaxed | one initialization after before_call1, before Ping body; field41 | same allowed schedule; not a universal beforefieldinit ordering |
| generic | `Cache<int>`42 then43, `Cache<string>`82 then83; each field/cctor pair once | same |
| failed inner catch | TypeInitializationException with InvalidOperationException twice; cctor body once | exception escapes to AOT reflection boundary on first access; second access in this route not reached |
| failed-outer | two reflection invocations, TargetInvocationException>TypeInitializationException>InvalidOperationException each; cctor body once | same |

The self-authored final CIL places Failed.Ping at offset30 inside catch-protected try [29,47) on both sides; catch type System.TypeInitializationException. Thus do not explain the observed difference as a source-level call outside try. The exact fault mechanism, ordinary-method throwing controls, other versions and platforms require another experiment; no upstream runtime change was made.

## Separate native evidence

Two additional matching-PDB CDB processes use the same Player: hot strict exits0, hot failed exits2. Each has Ping Transform1 before cctor execution, cctor Transform1/Execute-entry1, an initialization stack through Runtime::ClassInit, and the same Ping MethodInfo with non-null interpData at end. strict has two own Ping method events; failed has none although Ping cache is prepared. Native Execute function entry counts do not count interpreted internal calls.

Only self-authored events, final own-DLL metadata, numeric native summaries and hashes are public. Actual binary/PDB/Unity/native logs remain in ignored artifacts/type-initialization. Original exploratory d70cd30b logs and own inputs remain there under exploration-d70cd30b; they are not the final30-process acceptance data.

## Reproduce

From this repository root, with the previously prepared locked runtime:

```text
python -B tools/init_lab.py build --editor <locked Unity.exe>
python -B tools/init_lab.py run
python -B tools/init_lab.py trace --cdb <x64 cdb.exe>
python -B tools/init_lab.py verify
python -B tools/init_lab.py export
python -B -m unittest discover -s tests
python -B tools/check_repo.py
```

No timing benchmark, initialization-lock contention, cyclic initialization, object-layout, memory-safety or cross-platform claim. The exception discrepancy is reproducible in this custom baseline; it is not attributed to all HybridCLR releases.

## Final validation

144 Python tests and563-file public boundary check pass. Independent review found2 acceptance gaps (relaxed pre-environment initialization, native cctor transform/execution order), both reproduced RED then fixed GREEN. All30 normal and2 native original logs reparse unchanged; runtime/sample inputs and Player binaries did not change during these gate repairs. Implementation-phase validation above preceded publication; the user subsequently authorized commit and push on 2026-10-26.
