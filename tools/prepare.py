"""Fetch exact upstream revisions into ignored storage; never reset existing checkouts."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def git(*args):
    return subprocess.check_output(["git", *map(str, args)], text=True).strip()

def tree_digest(path):
    digest = hashlib.sha256()
    for file in sorted(p for p in path.rglob("*") if p.is_file()):
        digest.update(file.relative_to(path).as_posix().encode())
        digest.update(file.read_bytes())
    return digest.hexdigest()

def verify_sources(lock):
    for name, spec in lock["dependencies"].items():
        path = ROOT / ".local/src" / name
        if git("-C", path, "rev-parse", "HEAD") != spec["commit"]:
            raise RuntimeError(f"Wrong revision: {name}")
        if git("-C", path, "status", "--porcelain", "--untracked-files=all"):
            raise RuntimeError(f"Modified dependency: {name}; preserve/review it before continuing")

def verify_prepared():
    lock = json.loads((ROOT / "lab-lock.json").read_text())
    verify_sources(lock)
    receipt = json.loads((ROOT / ".local/prepared.json").read_text())
    if receipt["lock"] != lock or receipt["combined_sha256"] != tree_digest(ROOT / ".local/combined-libil2cpp"):
        raise RuntimeError("Prepared runtime does not match the lock or has changed")
    return lock

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-cache", type=Path, help="Optional existing clones: pkg, runtime, il2cpp-plus")
    args = parser.parse_args()
    lock = json.loads((ROOT / "lab-lock.json").read_text())
    for name, spec in lock["dependencies"].items():
        dst = ROOT / ".local/src" / name
        if dst.exists():
            if not (dst / ".git").exists():
                raise RuntimeError(f"Existing non-repository directory: {dst}")
            continue
        source = args.source_cache / ("pkg" if name == "package" else name) if args.source_cache else spec["url"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--no-hardlinks", "--no-checkout", str(source), str(dst)], check=True)
        subprocess.run(["git", "-C", str(dst), "checkout", "--detach", spec["commit"]], check=True)
    verify_sources(lock)
    versions = json.loads((ROOT / ".local/src/package/Data~/hybridclr_version.json").read_text())
    mapping = next(v for v in versions["versions"] if v["unity_version"] == "2022.3.x")
    if mapping["hybridclr"]["tag"] != lock["dependencies"]["runtime"]["tag"] or mapping["il2cpp_plus"]["tag"] != lock["dependencies"]["il2cpp-plus"]["tag"]:
        raise RuntimeError("Package version mapping disagrees with lock")
    combined = ROOT / ".local/combined-libil2cpp"
    if combined.exists():
        verify_prepared()
        print("Already prepared; exact revisions and combined source verified")
        return
    shutil.copytree(ROOT / ".local/src/il2cpp-plus/libil2cpp", combined)
    shutil.copytree(ROOT / ".local/src/runtime/hybridclr", combined / "hybridclr")
    receipt = {"lock": lock, "combined_sha256": tree_digest(combined)}
    (ROOT / ".local/prepared.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("Prepared pinned dependencies; no Editor installation was modified")

if __name__ == "__main__":
    main()
