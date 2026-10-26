"""Isolated local AssetBundle / hot MonoBehaviour restoration experiment."""
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path
import receipts
from prepare import ROOT,verify_prepared
from lifetime_lab import process
from resource_results import MODES,parse_player
ART=ROOT/"artifacts/resource-mounting";PROJECT=ROOT/"projects/resource-mounting";PLAYER=ART/"Player"
def source_manifest():
 files=[]
 for top in ("Assets","Packages","ProjectSettings"):
  for p in (PROJECT/top).rglob("*"):
   if not p.is_file():continue
   rel=p.relative_to(PROJECT).as_posix()
   if rel.startswith(("Assets/HybridCLR/","Assets/StreamingAssets/")) or rel in ("Assets/HybridCLR.meta","Assets/StreamingAssets.meta","Assets/Probe.unity","Assets/Probe.unity.meta"):continue
   if p.name in ("EditorBuildSettings.asset","HybridCLRSettings.asset"):continue
   files.append(p)
 return {p.relative_to(ROOT).as_posix():receipts.sha(p) for p in sorted(files)}
def check_build_log(log,expected):
 if expected.encode("ascii") not in log.read_bytes():raise RuntimeError("Build marker missing: "+expected)
def run_editor(args,method,log,build_id):
 receipts.fresh_log(log)
 env=dict(os.environ,RESOURCE_BUILD_ID=build_id)
 command=[str(args.editor),"-batchmode","-nographics","-quit","-projectPath",str(PROJECT),"-executeMethod",method,"-logFile",str(log)]
 p=subprocess.Popen(command,env=env,creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
 try:code=p.wait(timeout=1800)
 except subprocess.TimeoutExpired:
  subprocess.run(["taskkill","/PID",str(p.pid),"/T","/F"],stdout=subprocess.DEVNULL);p.wait();raise RuntimeError("Only this experiment's Editor process timed out")
 if code:raise RuntimeError(f"{method} exit {code}; see {log.relative_to(ROOT)}")
 expected="RESOURCE_PREPARE_OK" if method.endswith("Prepare") else "RESOURCE_BUILD_RESULT Succeeded"
 check_build_log(log,expected)
 print(method,"PASS",p.pid,flush=True)
def build(args):
 lock=verify_prepared()
 if not args.editor or not args.editor.is_file():raise ValueError("Pass the locked --editor")
 b=receipts.start_build(lock,receipts.editor_identity(args.editor,lock))
 run_editor(args,"ResourceBuild.Prepare",ART/"prepare.log",b["build_id"])
 before=source_manifest()
 b["source_sha256"]=before;receipts.write(ART/"build-lock.json",b)
 run_editor(args,"ResourceBuild.Build",ART/"build.log",b["build_id"])
 finish_built_player(b)
def finish_built_player(b):
 if source_manifest()!=b["source_sha256"]:raise RuntimeError("Project inputs normalized during build; review and rebuild before acceptance")
 cpp=PROJECT/"Library/Bee/artifacts/WinPlayerBuildProgram/il2cppOutput/cpp"
 backup=PLAYER/"ResourceMountingProbe_BackUpThisFolder_ButDontShipItWithYourGame"
 if (backup/"Managed/HotUpdate.dll").exists() or (cpp/"HotUpdate.cpp").exists() or "HotUpdate" in (cpp/"Il2CppCodeRegistration.cpp").read_text(encoding="utf-8-sig"):raise RuntimeError("HotUpdate entered AOT")
 lists=list(PLAYER.rglob("ScriptingAssemblies.json"))
 if len(lists)!=1:raise RuntimeError("Unexpected assembly list matrix")
 path=lists[0];scripting=json.loads(path.read_text(encoding="utf-8-sig"))
 if scripting['names'].count("HotUpdate.dll")!=1 or len(scripting['names'])!=len(scripting['types']):raise RuntimeError("Startup registration missing or malformed")
 manifests=list((PROJECT/"Library/HybridCLR").rglob("AssemblyManifest.inc"))
 if not any("HotUpdate" in p.read_text(encoding="utf-8-sig") for p in manifests):raise RuntimeError("Generated assembly manifest missing")
 negative=ART/("Player-unregistered-"+b['build_id'])
 shutil.copytree(PLAYER,negative,ignore=shutil.ignore_patterns("*_BackUpThisFolder_ButDontShipItWithYourGame"))
 relative=path.relative_to(PLAYER);negative_json=negative/relative;changed=json.loads(negative_json.read_text(encoding="utf-8-sig"));i=changed['names'].index('HotUpdate.dll');changed['names'].pop(i);changed['types'].pop(i)
 negative_json.write_text(json.dumps(changed,separators=(',',':')),encoding='utf-8')
 differences=[]
 for p in negative.rglob('*'):
  if p.is_file() and receipts.sha(p)!=receipts.sha(PLAYER/p.relative_to(negative)):differences.append(p.relative_to(negative).as_posix())
 if differences!=[relative.as_posix()]:raise RuntimeError("Negative copy changed more than startup list")
 b["generated_assembly_manifest"]={"path":manifests[0].relative_to(ROOT).as_posix(),"sha256":receipts.sha(manifests[0])}
 b.update(hot_update_excluded_from_aot=True,negative_player_dir=negative.relative_to(ART).as_posix(),negative_differences=differences,scripting_assemblies=scripting,fixture=dict(number=42,label='resource-prefab-v1',child='Anchor',payload='resource-payload-v1'),type_tree_enabled=True)
 files=[p for folder in (PLAYER,negative,ART/'Bundles') for p in folder.rglob('*') if p.is_file()]
 receipts.finish_build(b,files)
 print('RESOURCE BUILD PASS',b['build_id'],'artifacts',len(files),flush=True)
def current():
 b=receipts.require_build()
 if source_manifest()!=b['source_sha256']:raise RuntimeError('Source manifest changed after build')
 return b
def run(args):
 b=current();receipts.begin_phase('run',b);rows=[];logs=[]
 for mode in MODES:
  folder=ART/b['negative_player_dir'] if mode=='unregistered' else PLAYER
  for n in range(1,4):
   log=ART/f'{mode}-{n}.log';receipts.fresh_log(log)
   pid,code=process([folder/'ResourceMountingProbe.exe','-batchmode','-nographics','-logFile',log,'--resource-mode',mode],120)
   if code:raise RuntimeError(f'Player exit {code}: {log.name}')
   data=parse_player(log.read_text(encoding='utf-8-sig'),mode,b['build_id'])
   rows.append(dict(mode=mode,run=n,pid=pid,exit_code=code,observations=data));logs.append(log)
   print('RESOURCE RUN',mode,n,'restored',data['restored'],'missing',data['missing'],flush=True)
 results=ART/'run-results.json';receipts.write(results,dict(build_id=b['build_id'],runs=rows));logs.append(results);receipts.finish_phase('run',b,logs)
def verify(args):
 b=current();state=json.loads((ART/'run-status.json').read_text());rows=json.loads((ART/'run-results.json').read_text())
 if state['status']!='complete' or state['build_id']!=b['build_id'] or rows['build_id']!=b['build_id']:raise RuntimeError('Run identity mismatch')
 if [(r['mode'],r['run']) for r in rows['runs']]!=[(mode,n) for mode in MODES for n in range(1,4)]:raise RuntimeError('Incomplete matrix')
 for rel,expected in state['log_sha256'].items():
  if receipts.sha(ART/rel)!=expected:raise RuntimeError('Evidence file changed: '+rel)
 for row in rows['runs']:
  log=ART/f"{row['mode']}-{row['run']}.log"
  if row['exit_code']!=0 or parse_player(log.read_text(encoding='utf-8-sig'),row['mode'],b['build_id'])!=row['observations']:raise RuntimeError('Run result changed')
 tools=['tools/resource_lab.py','tools/resource_results.py','tests/test_resource_results.py','tests/test_resource_tool.py','tools/receipts.py','tools/prepare.py','tools/lifetime_lab.py']
 receipts.write(ART/'verified-results.json',dict(schema=1,build_id=b['build_id'],lock=b['lock'],source_sha256=b['source_sha256'],artifact_sha256=b['artifact_sha256'],tool_sha256={p:receipts.sha(ROOT/p) for p in tools},scripting_assemblies=b['scripting_assemblies'],negative_differences=b['negative_differences'],hot_update_excluded_from_aot=True,type_tree_enabled=True,run=rows['runs'],raw_log_sha256=state['log_sha256']))
 print('RESOURCE RECORDS VERIFIED',b['build_id'],'15 independent Player records; inspect per-case classification',flush=True)
def export(args):
 verify(args);b=current();r=json.loads((ART/'verified-results.json').read_text())
 output=ROOT/'evidence/2026-10-26-resource-mounting';output.mkdir(parents=True,exist_ok=True)
 keys={
 'env':'event mode build unity hot_before registration assembly_name_before',
 'dll':'event name','ping':'event value','stage':'event stage',
 'asset':'event stage value typed missing restored','instantiate':'event value',
 'snapshot':'event instance number label anchor anchor_matches payload payload_name type assembly',
 'life':'event name instance number label anchor payload type assembly',
 'result':'event restored typed missing hot_loaded','done':'event completed'}
 public=[]
 for row in r['run']:
  log=ART/f"{row['mode']}-{row['run']}.log";records=[];diagnostics=[];stage='startup'
  for line in log.read_text(encoding='utf-8-sig').splitlines():
   if line.startswith('RMP '):
    value=json.loads(line[4:]);event=value['event'];records.append({k:value[k] for k in keys[event].split() if k in value})
    if event=='stage':stage=value['stage']
   elif 'The referenced script' in line:diagnostics.append(dict(stage=stage,message=line.strip()))
  rel=f"{row['mode']}-{row['run']}-events.jsonl";path=output/rel
  path.write_text(''.join(json.dumps(v,ensure_ascii=False,separators=(',',':'))+'\n' for v in records),encoding='utf-8')
  reparsed=parse_player(''.join('RMP '+json.dumps(v)+'\n' for v in records),row['mode'],b['build_id'])
  summary={k:v for k,v in row['observations'].items() if k!='events'}
  if {k:v for k,v in reparsed.items() if k!='events'}!=summary:raise RuntimeError('Public export changed observed meaning')
  public.append(dict(mode=row['mode'],run=row['run'],pid=row['pid'],exit_code=row['exit_code'],observations=summary,event_file=rel,event_sha256=receipts.sha(path),diagnostics=diagnostics))
 result={k:r[k] for k in ('schema','build_id','lock','source_sha256','artifact_sha256','tool_sha256','hot_update_excluded_from_aot','type_tree_enabled','negative_differences','raw_log_sha256')}
 result.update(baseline_commit='64938d5c5040fbc2f63274ee4efd8ab6b3c9d07a',publication='Local verified candidate; baseline_commit does not contain this experiment. Publish these sources and records together.',actual_editor_product_version=b['actual_editor_product_version'],generated_assembly_manifest=b['generated_assembly_manifest'],assembly_registration=dict(normal_hot_count=b['scripting_assemblies']['names'].count('HotUpdate.dll'),normal_names_count=len(b['scripting_assemblies']['names']),negative_hot_count=0,negative_names_count=len(b['scripting_assemblies']['names'])-1),fixture=b['fixture'],run=public,limits=['Fixed local-custom Editor, Windows x64 Development IL2CPP Debug, Minimal stripping, TypeTree enabled.','One self-authored MonoBehaviour with two scalar and two Unity reference fields; no serialized schema/version migration, Addressables/network or other-platform validation.','Lifecycle and resource restoration observations are not GC, resource-release capacity, performance or leak-free claims.','No native breakpoint proof of placeholder pointer reuse; that mechanism remains a separate fixed-source explanation.'])
 receipts.write(output/'results.json',result)
 print('RESOURCE EXPORT PASS',b['build_id'],len(public),'filtered event records',flush=True)
def main():
 receipts.ART=ART
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['build','run','verify','export']);p.add_argument('--editor',type=Path);args=p.parse_args();globals()[args.command](args)
if __name__=='__main__':main()
