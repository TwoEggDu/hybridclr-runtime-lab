"""Verify the four local runs and emit a source-free evidence summary.

Usage: python tools/verify_generics.py <repository-root> <summary.json>
Requires the log names and directory layout documented in README.md.
"""
import hashlib
import json
import re
import sys
from pathlib import Path
from receipts import require_evidence
from prepare import ROOT

repo, output = map(Path, sys.argv[1:])
if repo.resolve() != ROOT.resolve():
    raise ValueError("Repository argument must match this checkout")
build_receipt = require_evidence()
root = repo / "artifacts/generics"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest().upper()
read = lambda p: p.read_text(encoding="utf-8-sig", errors="replace")
receipts = json.loads(read(root / "logs/standalone-receipts.json"))
summary = {"schema": 1, "build_id": build_receipt["build_id"], "actual_editor_product_version": build_receipt["actual_editor_product_version"], "builds": {}, "runs": {}}
hot_hashes = []
for build in ("p0", "p1"):
    project, player = repo / "projects" / ("generic-" + build), root / ("Player-" + build)
    backup = player / "RuntimeGenericProbe_BackUpThisFolder_ButDontShipItWithYourGame"
    assets = player / "RuntimeGenericProbe_Data/StreamingAssets"
    hot_hashes.append(sha(assets / "HotUpdate.dll.bytes"))
    metadata_hash = sha(assets / "Generic.AOT.dll.bytes")
    assert metadata_hash == sha(backup / "Managed/Generic.AOT.dll")
    assert metadata_hash == sha(project / "Library/HybridCLR/AssembliesPostIl2CppStrip/StandaloneWindows64/Generic.AOT.dll")
    # The package adds hot DLL names to ScriptingAssemblies.json; that list is not AOT proof.
    cpp = project / "Library/Bee/artifacts/WinPlayerBuildProgram/il2cppOutput/cpp"
    assert not (backup / "Managed/HotUpdate.dll").exists()
    assert not (cpp / "HotUpdate.cpp").exists()
    assert "HotUpdate" not in read(cpp / "Il2CppCodeRegistration.cpp")
    configs = [json.loads(read(p)) for p in (project / "Library/Bee").glob("Player*-inputdata.json")]
    config = next(c for c in configs if "Player-" + build in c["PlayerBuildProgramLibrary.Data.PlayerBuildConfig"]["DestinationPath"])
    il2cpp = config["PlayerBuildProgramLibrary.Data.Il2CppConfig"]
    linker = config["PlayerBuildProgramLibrary.Data.LinkerConfig"]
    assert il2cpp["ConfigurationName"] == "Debug"
    assert il2cpp["EnableFullGenericSharing"] is False
    assert linker["Ruleset"] == "Minimal"
    assert "GENERIC_BUILD_RESULT Succeeded" in read(root / f"logs/build-{build}.log")
    summary["builds"][build] = {
        "hot_update_sha256": hot_hashes[-1], "supplementary_aot_sha256": metadata_hash,
        "game_assembly_sha256": sha(player / "GameAssembly.dll"),
        "pdb_sha256": sha(backup / "GameAssembly.pdb"),
        "cpp_configuration": il2cpp["ConfigurationName"],
        "bee_enable_full_generic_sharing": il2cpp["EnableFullGenericSharing"],
        "linker_ruleset": linker["Ruleset"], "hot_update_excluded_from_aot": True,
    }
    for metadata in (False, True):
        case = f"{build}-m{int(metadata)}"
        trace = read(root / f"logs/{case}-final-trace.log")
        player_log = read(root / f"logs/{case}-final-player.log")
        standalone = read(root / f"logs/{case}-standalone.log")
        fail = build == "p0" and not metadata
        expected_failure_count = 4 if fail else 0
        for log in (player_log, standalone):
            assert f"GENERIC_MODE metadata={metadata}" in log
            assert f"GENERIC_DONE failures={expected_failure_count}" in log
            assert ("GENERIC_METADATA code=OK" in log) == metadata
            for name, value in (("RunString", "echo-string"), ("RunInt", "42"), ("RunPayload", "7000011")):
                for call in (1, 2):
                    if fail and name != "RunString":
                        assert f"GENERIC_EXCEPTION case={name} call={call} type=System.MissingMethodException" in log
                    else:
                        assert f"GENERIC_RESULT case={name} call={call} value={value} ok=True" in log
        assert "private pdb symbols" in trace
        assert "Syntax error" not in trace and "Couldn't resolve" not in trace
        def events(tag):
            pattern = rf"^GENERIC_{tag} method=([0-9a-f]+)\n\s+.*?name\s*:\s*.*?\"([^\"]+)\"(?:\n\s+.*?interpData\s*:\s*(.*))?"
            return re.findall(pattern, trace, re.M)
        transforms = events("NATIVE_TRANSFORM")
        executes = events("EXECUTE")
        inlines = events("INLINE")
        assert [v[1] for v in transforms] == ["RunString", "RunInt", "RunPayload"]
        # Execute can be entered even when the target call subsequently throws.
        assert [v[1] for v in executes] == [n for n in ("RunString", "RunInt", "RunPayload") for _ in range(2)]
        for i in range(0, len(executes), 2):
            assert executes[i] == executes[i + 1]  # same method and cached interpData
            assert executes[i][2] and "(null)" not in executes[i][2]
        assert len(inlines) == (2 if build == "p0" and metadata else 0)
        assert all(v[1] == "Echo" for v in inlines)
        if inlines:
            assert "ConsistentAOTHomologousImage" in trace
            assert "TransformContext::TransformSubMethodBody+" in trace
        assert not re.search(r"^GENERIC_INTERP_FRAME", trace, re.M)
        native = re.findall(r"^GENERIC_NATIVE_ECHO (.+)$", trace, re.M)
        shared = [s for s in native if "_gshared " in s]
        assert len(shared) == (2 if build == "p0" else 9)
        if build == "p1":
            # One AOT seed plus two interpreted-wrapper calls per native implementation.
            for arg in ("RuntimeObject", "Int32", "Payload"):
                assert sum(f"Echo_Tis{arg}" in s for s in shared) == 3
        receipt = next(r for r in receipts if r["build"] == build and r["metadata"] == metadata)
        assert receipt["exitCode"] == (2 if fail else 0)
        summary["runs"][case] = {
            "standalone_pid": receipt["pid"], "standalone_exit_code": receipt["exitCode"],
            "result_lines": [s for s in player_log.splitlines() if s.startswith(("GENERIC_MODE", "GENERIC_METADATA", "GENERIC_RESULT", "GENERIC_EXCEPTION", "GENERIC_DONE"))],
            "wrapper_transform_count": len(transforms), "wrapper_execute_count": len(executes),
            "echo_inline_count": len(inlines), "native_shared_echo_hits_including_seeds": len(shared),
            "same_wrapper_method_and_cache_on_second_call": True,
        }
assert len(set(hot_hashes)) == 1
output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("PASS: 2 builds, 4 debugger runs, 4 standalone runs; hashes, results, paths and caches verified")
