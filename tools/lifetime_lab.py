"""Isolated lifetime/managed-thread Player build, runs and native capture."""
import argparse,json,os,subprocess,sys
from pathlib import Path
import receipts
from prepare import ROOT,verify_prepared
from lab import assert_log
from lifetime_results import parse_gc,parse_threads,parse_native
ART=ROOT/"artifacts/lifetime"
PROJECT=ROOT/"projects/lifetime-threads"
PLAYER=ART/"Player"
FLAGS=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0

def process(args,timeout=180):
 p=subprocess.Popen([str(x) for x in args],creationflags=FLAGS,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
 try:return p.pid,p.wait(timeout=timeout)
 except subprocess.TimeoutExpired:
  # Stop only this experiment's process tree; never leave a runaway Player/Editor.
  subprocess.run(["taskkill","/PID",str(p.pid),"/T","/F"],creationflags=FLAGS,stdout=subprocess.DEVNULL)
  p.wait();raise RuntimeError("Experiment process timed out")

def sources():
 return sorted(p for p in PROJECT.rglob("*") if p.is_file() and ("Assets" in p.parts and p.suffix in (".cs",".asmdef") or p.parent.name=="Packages" or p.parent.name=="ProjectSettings" and p.name not in ("EditorBuildSettings.asset","HybridCLRSettings.asset")))

def manifest():
 return {p.relative_to(ROOT).as_posix():receipts.sha(p) for p in sources()}

def current_build():
 b=receipts.require_build()
 if manifest()!=b["source_sha256"]:raise RuntimeError("Build source manifest changed")
 return b

def build(args):
 lock=verify_prepared()
 if args.editor is None or not args.editor.is_file():raise ValueError("Pass --editor Unity.exe")
 b=receipts.start_build(lock,receipts.editor_identity(args.editor,lock))
 before=manifest()
 log=ART/"build.log";receipts.fresh_log(log)
 pid,code=process([args.editor,"-batchmode","-nographics","-quit","-projectPath",PROJECT,"-executeMethod","LifetimeBuild.PrepareAndBuild","-logFile",log],1800)
 if code:raise RuntimeError("Unity build exit "+str(code)+"; see artifacts/lifetime/build.log")
 assert_log(log,["LIFE_BUILD_RESULT Succeeded"])
 backup=PLAYER/"LifetimeProbe_BackUpThisFolder_ButDontShipItWithYourGame"
 cpp=PROJECT/"Library/Bee/artifacts/WinPlayerBuildProgram/il2cppOutput/cpp"
 if (backup/"Managed/HotUpdate.dll").exists() or (cpp/"HotUpdate.cpp").exists() or "HotUpdate" in (cpp/"Il2CppCodeRegistration.cpp").read_text(encoding="utf-8-sig"):raise RuntimeError("Hot assembly entered AOT")
 if manifest()!=before:raise RuntimeError("Build inputs changed during compilation; rebuild normalized project")
 b["source_sha256"]=before
 b["hot_update_excluded_from_aot"]=True
 receipts.finish_build(b,[p for p in PLAYER.rglob("*") if p.is_file()])
 print("BUILD PASS",b["build_id"],"pid",pid,flush=True)

def run(args):
 b=current_build();receipts.begin_phase("run",b);logs=[];results=[]
 for mode in ("gc","threads"):
  for n in range(1,4):
   log=ART/f"{mode}-{n}.log";receipts.fresh_log(log)
   pid,code=process([PLAYER/"LifetimeProbe.exe","-batchmode","-nographics","-logFile",log]+(["--threads"] if mode=="threads" else []))
   if code:raise RuntimeError(f"Player exit {code}: {log.name}")
   text=log.read_text(encoding="utf-8-sig")
   data=(parse_gc if mode=="gc" else parse_threads)(text)
   results.append(dict(mode=mode,run=n,pid=pid,exit_code=code,observations=data));logs.append(log)
   print("RUN PASS",mode,n,json.dumps(data),flush=True)
 receipt=ART/"standalone-results.json";receipts.write(receipt,dict(build_id=b["build_id"],runs=results));logs.append(receipt)
 receipts.finish_phase("run",b,logs)

def trace(args):
 b=current_build()
 if args.cdb is None or not args.cdb.is_file():raise ValueError("Pass --cdb x64 cdb.exe")
 receipts.begin_phase("trace",b)
 logs=[ART/"threads-trace.log",ART/"threads-debug-player.log"]
 for log in logs:receipts.fresh_log(log)
 _,code=process([args.cdb,"-G","-y",PLAYER/"LifetimeProbe_BackUpThisFolder_ButDontShipItWithYourGame","-logo",logs[0],"-cf",ROOT/"debugger/lifetime-threads-v9.cdb",PLAYER/"LifetimeProbe.exe","-batchmode","-nographics","--threads","-logFile",logs[1]],300)
 if code:raise RuntimeError("CDB exit "+str(code))
 parse_threads(logs[1].read_text(encoding="utf-8-sig"))
 assert_log(logs[0],["private pdb symbols"])
 receipts.finish_phase("trace",b,logs)
 print("TRACE captured; run native evidence verifier before acceptance",flush=True)

def verify(args):
 b=current_build();receipts.require_evidence()
 runs=json.loads((ART/"standalone-results.json").read_text(encoding="utf-8"))
 if runs["build_id"]!=b["build_id"] or [(r["mode"],r["run"]) for r in runs["runs"]]!=[(m,n) for m in ("gc","threads") for n in range(1,4)]:raise RuntimeError("Run matrix mismatch")
 for r in runs["runs"]:
  text=(ART/f"{r['mode']}-{r['run']}.log").read_text(encoding="utf-8-sig")
  if r["exit_code"]!=0 or r["observations"]!=(parse_gc if r["mode"]=="gc" else parse_threads)(text):raise RuntimeError("Run observation mismatch")
 player=parse_threads((ART/"threads-debug-player.log").read_text(encoding="utf-8-sig"))
 native=parse_native((ART/"threads-trace.log").read_text(encoding="utf-8-sig"),player)
 result=dict(build_id=b["build_id"],environment=b["lock"],standalone=runs["runs"],debug_player=player,native=native)
 receipts.write(ART/"verified-results.json",result)
 print("VERIFY PASS",json.dumps(native),flush=True)

def main():
 receipts.ART=ART # Each CLI process scopes the shared receipt protocol to this experiment.
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument("command",choices=["build","run","trace","verify"])
 parser.add_argument("--editor",type=Path);parser.add_argument("--cdb",type=Path)
 args=parser.parse_args();globals()[args.command](args)
if __name__=="__main__":main()
