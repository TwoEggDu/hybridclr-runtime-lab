"""Fetch only the fixed extra UniTask dependency; preserve existing checkouts."""
import json,subprocess
from pathlib import Path
from prepare import ROOT,git

def verify_checkout(path,spec):
 if not (path/".git").exists():raise RuntimeError("Missing UniTask Git checkout")
 if git("-C",path,"rev-parse","HEAD")!=spec["commit"]:raise RuntimeError("Wrong UniTask commit")
 if git("-C",path,"status","--porcelain","--untracked-files=all"):raise RuntimeError("Modified UniTask checkout; preserve and review it")
 package=json.loads((path/spec["package_path"]/"package.json").read_text())
 if package["name"]!="com.cysharp.unitask" or package["version"]!=spec["version"]:raise RuntimeError("UniTask package version mismatch")
 return package["version"]

def main():
 spec=json.loads((ROOT/"async-lock.json").read_text());dst=ROOT/spec["path"]
 if not dst.exists():
  dst.parent.mkdir(parents=True,exist_ok=True)
  subprocess.run(["git","clone","--depth","1","--branch",spec["version"],spec["url"],str(dst)],check=True)
 print("UNI TASK PREPARE",verify_checkout(dst,spec),spec["commit"])
if __name__=="__main__":main()
