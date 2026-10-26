"""Read-only repository contract checks; no Unity/runtime acceptance implied."""
import ast
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
lock = json.loads((ROOT / "lab-lock.json").read_text())
assert lock["editor"]["distribution"] == "local-custom"
for spec in lock["dependencies"].values():
    assert re.fullmatch(r"[0-9a-f]{40}", spec["commit"])
    assert spec["url"].startswith("https://github.com/focus-creative-games/")
for name in ("call-chain", "generic-p0", "generic-p1", "lifetime-threads", "native-callbacks", "gc-callbacks", "gc-roots", "incremental-barriers", "resource-mounting", "type-initialization", "exception-flow", "async-unitask", "constrained-boxing", "concurrent-initialization"):
    project = ROOT / "projects" / name
    manifest = json.loads((project / "Packages/manifest.json").read_text())
    dependency = manifest["dependencies"]["com.code-philosophy.hybridclr"]
    assert dependency == "file:../../../.local/src/package"
    assert (project / "Packages" / dependency[5:]).resolve() == ROOT / ".local/src/package"
    assert lock["editor"]["version"] in (project / "ProjectSettings/ProjectVersion.txt").read_text()
    for f in (project / "Assets").rglob("*.asmdef"):
        json.loads(f.read_text())
async_lock = json.loads((ROOT / "async-lock.json").read_text())
assert async_lock["commit"] == "7c0f199fe0d3fc528024488ccd671e6c7b27745b"
async_manifest = json.loads((ROOT / "projects/async-unitask/Packages/manifest.json").read_text())
assert async_manifest["dependencies"]["com.cysharp.unitask"] == "file:../../../.local/async-unitask/UniTask/src/UniTask/Assets/Plugins/UniTask"
assert not (ROOT / "projects/generic-p0/Assets/AOT/SeedCalls.cs").exists()
assert (ROOT / "projects/generic-p1/Assets/AOT/SeedCalls.cs").is_file()
for folder in ("GenericAOT", "HotUpdate"):
    a = ROOT / "projects/generic-p0/Assets" / folder
    b = ROOT / "projects/generic-p1/Assets" / folder
    for f in a.iterdir():
        if f.suffix in (".cs", ".asmdef"):
            assert f.read_bytes() == (b / f.name).read_bytes()
paths = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")
paths = sorted(set(p for p in paths if p))
for rel in paths:
    path = ROOT / rel
    assert not rel.startswith((".local/", "artifacts/")), rel
    assert rel in {"native/native-callbacks/plugin.cpp", "native/gc-callbacks/plugin.cpp", "native/incremental-barriers/plugin.cpp"} or path.suffix.lower() not in {".dll", ".exe", ".pdb", ".cpp", ".h", ".bytes", ".log"}, rel
    if path.suffix == ".py":
        ast.parse(path.read_text(encoding="utf-8"))
    if path.suffix == ".json":
        json.loads(path.read_text(encoding="utf-8-sig"))
    if rel.startswith("projects/") and "/Assets/" in rel and path.suffix in (".cs", ".asmdef"):
        assert Path(str(path) + ".meta").is_file(), rel
    if path.is_file():
        text = path.read_text(encoding="utf-8-sig")
        assert not re.search(r"[A-Z]:[/\\](?:Users|workspace|UnityEngine)[/\\]", text, re.I), rel
        assert ("-----BEGIN " + "OPENSSH PRIVATE KEY-----") not in text, rel
print(f"PASS: {len(paths)} public files; manifests, project boundaries, source parity and publication scope")
