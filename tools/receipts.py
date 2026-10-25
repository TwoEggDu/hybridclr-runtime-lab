"""Bind local acceptance to one completed build and unchanged artifacts/logs."""
import hashlib
import json
import os
import subprocess
import uuid
from pathlib import Path
from prepare import ROOT
ART = ROOT / "artifacts"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")

def editor_identity(editor, lock):
    if os.name != "nt":
        raise RuntimeError("This baseline requires Windows x64")
    env = dict(os.environ, RUNTIME_LAB_EDITOR=str(editor.resolve()))
    actual = subprocess.check_output(["powershell.exe", "-NoProfile", "-Command", "(Get-Item -LiteralPath $env:RUNTIME_LAB_EDITOR).VersionInfo.ProductVersion"], env=env, text=True).strip()
    if actual != lock["editor"]["product_version"]:
        raise RuntimeError(f"Editor identity mismatch: expected {lock['editor']['product_version']}, actual {actual!r}. Record and validate a separate baseline instead.")
    return actual

def start_build(lock, actual_editor):
    receipt = {"schema": 1, "build_id": str(uuid.uuid4()), "status": "building", "lock": lock, "actual_editor_product_version": actual_editor}
    write(ART / "build-lock.json", receipt)
    return receipt

def finish_build(receipt, files):
    receipt["artifact_sha256"] = {p.relative_to(ART).as_posix(): sha(p) for p in sorted(files)}
    receipt["status"] = "complete"
    write(ART / "build-lock.json", receipt)

def require_build():
    expected = json.loads((ROOT / "lab-lock.json").read_text())
    actual = json.loads((ART / "build-lock.json").read_text())
    if actual.get("status") != "complete" or actual.get("lock") != expected or actual.get("actual_editor_product_version") != expected["editor"]["product_version"]:
        raise RuntimeError("No completed build matches the current environment lock")
    for rel, expected_hash in actual["artifact_sha256"].items():
        if sha(ART / rel) != expected_hash:
            raise RuntimeError(f"Built artifact changed: {rel}")
    return actual

def begin_phase(kind, build):
    write(ART / f"{kind}-status.json", {"status": "running", "build_id": build["build_id"]})

def finish_phase(kind, build, logs):
    write(ART / f"{kind}-status.json", {"status": "complete", "build_id": build["build_id"], "log_sha256": {p.relative_to(ART).as_posix(): sha(p) for p in logs}})

def require_evidence():
    build = require_build()
    for kind in ("run", "trace"):
        data = json.loads((ART / f"{kind}-status.json").read_text())
        if data.get("status") != "complete" or data.get("build_id") != build["build_id"]:
            raise RuntimeError(f"{kind} evidence is missing, incomplete, or from another build")
        for rel, expected_hash in data["log_sha256"].items():
            if sha(ART / rel) != expected_hash:
                raise RuntimeError(f"Recorded log changed: {rel}")
    return build

def fresh_log(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("")
