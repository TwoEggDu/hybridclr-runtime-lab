"""Build and run the isolated Windows x64 lab. All paths derive from this checkout."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from prepare import ROOT, verify_prepared
from receipts import editor_identity, start_build, finish_build, require_build, begin_phase, finish_phase, fresh_log

ART = ROOT / "artifacts"
FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

def run_process(args):
    process = subprocess.Popen([str(x) for x in args], creationflags=FLAGS)
    return process.pid, process.wait()

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def assert_log(path, required):
    data = path.read_text(encoding="utf-8-sig", errors="replace")
    for line in required:
        if line not in data:
            raise RuntimeError(f"Missing result {line!r} in {path.name}")
    return data

def check_generic_log(path, fail, metadata):
    expected = [f"GENERIC_MODE metadata={metadata}", f"GENERIC_DONE failures={4 if fail else 0}"]
    if metadata:
        expected.append("GENERIC_METADATA code=OK")
    for name, value in [("RunString", "echo-string"), ("RunInt", "42"), ("RunPayload", "7000011")]:
        for call in (1, 2):
            if fail and name != "RunString":
                expected.append(f"GENERIC_EXCEPTION case={name} call={call} type=System.MissingMethodException")
            else:
                expected.append(f"GENERIC_RESULT case={name} call={call} value={value} ok=True")
    assert_log(path, expected)

def build(args):
    lock = verify_prepared()
    if args.editor is None or not args.editor.is_file():
        raise RuntimeError("Pass --editor with an existing Unity.exe path")
    receipt = start_build(lock, editor_identity(args.editor, lock))
    for project, method, log in [
        ("call-chain", "ProbeBuild.PrepareAndBuild", ART / "call-chain/build.log"),
        ("generic-p0", "GenericBuild.Build", ART / "generics/logs/build-p0.log"),
        ("generic-p1", "GenericBuild.Build", ART / "generics/logs/build-p1.log"),
    ]:
        fresh_log(log)
        pid, code = run_process([args.editor, "-batchmode", "-nographics", "-quit", "-projectPath", ROOT / "projects" / project, "-executeMethod", method, "-logFile", log])
        if code != 0:
            raise RuntimeError(f"Unity build failed: {project}, exit={code}; inspect {log}")
        assert_log(log, ["PROBE_BUILD_RESULT Succeeded" if project == "call-chain" else "GENERIC_BUILD_RESULT Succeeded"])
        print(f"BUILD {project}: pid={pid}, exit={code}", flush=True)
    # Freeze a common hot-update input after both builds have finished.
    relative = "RuntimeGenericProbe_Data/StreamingAssets/HotUpdate.dll.bytes"
    shutil.copy2(ART / "generics/Player-p0" / relative, ART / "generics/Player-p1" / relative)
    for case in ("p0", "p1"):
        player = ART / "generics" / ("Player-" + case)
        supplementary = player / "RuntimeGenericProbe_Data/StreamingAssets/Generic.AOT.dll.bytes"
        stripped = player / "RuntimeGenericProbe_BackUpThisFolder_ButDontShipItWithYourGame/Managed/Generic.AOT.dll"
        if sha(supplementary) != sha(stripped):
            raise RuntimeError(f"Supplementary metadata does not match final stripped assembly: {case}")
    players = [ART / "call-chain/Player", ART / "generics/Player-p0", ART / "generics/Player-p1"]
    finish_build(receipt, [f for player in players for f in player.rglob("*") if f.is_file()])
    print("BUILD PASS: three Players; identical hot DLL and build-specific metadata")

def run(args):
    build = require_build()
    begin_phase("run", build)
    logs = []
    exe = ART / "call-chain/Player/HybridCLRReadingProbe.exe"
    log = ART / "call-chain/player.log"
    fresh_log(log)
    logs.append(log)
    pid, code = run_process([exe, "-batchmode", "-nographics", "-logFile", log])
    if code != 0:
        raise RuntimeError(f"Call-chain exit {code}")
    assert_log(log, ["PROBE_FIRST=5", "PROBE_SECOND=15", "PROBE_PASS"])
    (ART / "call-chain/receipt.json").write_text(json.dumps({"pid": pid, "exitCode": code}) + "\n")
    receipts = []
    for case in ("p0", "p1"):
        for metadata in (False, True):
            name = f"{case}-m{int(metadata)}"
            log = ART / f"generics/logs/{name}-standalone.log"
            exe = ART / f"generics/Player-{case}/RuntimeGenericProbe.exe"
            fresh_log(log)
            logs.append(log)
            pid, code = run_process([exe, "-batchmode", "-nographics", "-logFile", log] + (["--metadata"] if metadata else []))
            fail = case == "p0" and not metadata
            if code != (2 if fail else 0):
                raise RuntimeError(f"Unexpected exit {code}: {name}")
            check_generic_log(log, fail, metadata)
            receipts.append({"build": case, "metadata": metadata, "pid": pid, "exitCode": code})
            print(f"RUN {name}: exit={code} (expected)", flush=True)
    (ART / "generics/logs/standalone-receipts.json").write_text(json.dumps(receipts, indent=2) + "\n")
    logs.extend([ART / "call-chain/receipt.json", ART / "generics/logs/standalone-receipts.json"])
    finish_phase("run", build, logs)
    print("RUN PASS: Add and all four generic controls")

def trace(args):
    build = require_build()
    if args.cdb is None or not args.cdb.is_file():
        raise RuntimeError("Pass --cdb with an existing x64 cdb.exe path")
    begin_phase("trace", build)
    logs = []
    cases = [("call-chain", False)] + [(case, meta) for case in ("p0", "p1") for meta in (False, True)]
    for case, meta in cases:
        add = case == "call-chain"
        player = ART / ("call-chain/Player" if add else f"generics/Player-{case}")
        product = "HybridCLRReadingProbe" if add else "RuntimeGenericProbe"
        logbase = ART / ("call-chain/final" if add else f"generics/logs/{case}-m{int(meta)}-final")
        command = ROOT / "debugger" / ("call-chain-v9.cdb" if add else "generics-v9.cdb")
        cmd = [args.cdb, "-G", "-y", player / (product + "_BackUpThisFolder_ButDontShipItWithYourGame"), "-logo", str(logbase) + "-trace.log", "-cf", command, player / (product + ".exe"), "-batchmode", "-nographics", "-logFile", str(logbase) + "-player.log"]
        if meta:
            cmd.append("--metadata")
        for suffix in ("-trace.log", "-player.log"):
            log = Path(str(logbase) + suffix)
            fresh_log(log)
            logs.append(log)
        _, code = run_process(cmd)
        # CDB forwards the debuggee exit code; p0/m0 deliberately exits 2.
        if code != (2 if case == "p0" and not meta else 0):
            raise RuntimeError(f"CDB failed: {case}, exit={code}")
        if add:
            assert_log(Path(str(logbase) + "-player.log"), ["PROBE_FIRST=5", "PROBE_SECOND=15", "PROBE_PASS"])
        else:
            check_generic_log(Path(str(logbase) + "-player.log"), case == "p0" and not meta, meta)
        print(f"TRACE {case} metadata={meta}: captured", flush=True)
    finish_phase("trace", build, logs)
    subprocess.run([sys.executable, str(ROOT / "tools/verify_generics.py"), str(ROOT), str(ART / "generics/verified-results.json")], check=True)
    subprocess.run([sys.executable, str(ROOT / "tools/verify_call_chain.py")], check=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "run", "trace"])
    parser.add_argument("--editor", type=Path)
    parser.add_argument("--cdb", type=Path)
    args = parser.parse_args()
    globals()[args.command](args)

if __name__ == "__main__":
    main()
