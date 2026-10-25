"""Validate Add identity, cache, arguments and real Player results from local traces."""
import json
import re
from pathlib import Path
from receipts import require_evidence

build_receipt = require_evidence()
from prepare import ROOT
from lab import assert_log, sha

base = ROOT / "artifacts/call-chain"
trace = assert_log(base / "final-trace.log", ["private pdb symbols"])
assert "Syntax error" not in trace and "Couldn't resolve" not in trace
for tag, expected in [("LOAD", 1), ("INVOKE", 2), ("PREPARE", 1), ("TRANSFORM", 1), ("EXECUTE", 2)]:
    assert len(re.findall(rf"^PROBE_NATIVE_{tag} ", trace, re.M)) == expected, tag
methods = re.findall(r"^PROBE_NATIVE_(?:INVOKE|PREPARE|TRANSFORM|EXECUTE) method=([0-9a-f]+)", trace, re.M)
assert len(set(methods)) == 1
assert re.findall(r"^PROBE_NATIVE_EXECUTE .*?args=(-?\d+,-?\d+)(?=\s|$)", trace, re.M) == ["2,3", "7,8"]
blocks = re.split(r"^PROBE_NATIVE_", trace, flags=re.M)[1:]
invokers = [b for b in blocks if b.startswith("INVOKE ")]
assert "interpData : (null)" in invokers[0]
cache = re.search(r"interpData\s*:\s*(0x[0-9a-f`]+)", invokers[1]).group(1)
for block in blocks:
    if block.startswith("EXECUTE "):
        assert cache in block
for file in ("player.log", "final-player.log"):
    assert_log(base / file, ["PROBE_FIRST=5", "PROBE_SECOND=15", "PROBE_PASS"])
receipt = json.loads((base / "receipt.json").read_text())
assert receipt["exitCode"] == 0
player = base / "Player"
summary = {"build_id": build_receipt["build_id"], "actual_editor_product_version": build_receipt["actual_editor_product_version"], "results": [5, 15], "load_count": 1, "invoke_count": 2, "transform_count": 1, "execute_count": 2, "same_method_and_cache": True, "standalone_exit_code": 0,
           "game_assembly_sha256": sha(player / "GameAssembly.dll"), "hot_update_sha256": sha(player / "HybridCLRReadingProbe_Data/StreamingAssets/HotUpdate.dll.bytes")}
(base / "verified-results.json").write_text(json.dumps(summary, indent=2) + "\n")
print("PASS: Add load/invoke/transform/execute, identity, cache and results")
