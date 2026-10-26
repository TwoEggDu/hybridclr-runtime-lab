"""Locked concurrent first-call/type-init build, run and evidence export."""
import argparse,json,os,subprocess
from pathlib import Path
import receipts
from prepare import ROOT,verify_prepared
from lifetime_lab import process
from concurrent_results import CELLS,parse_player
ART=ROOT/'artifacts/concurrent-initialization';PROJECT=ROOT/'projects/concurrent-initialization';PLAYER=ART/'Player'
NAME='ConcurrentInitializationProbe'
def sources():
 files=[ROOT/'samples/concurrent-initialization/Scenarios.cs']
 for top in ('Assets','Packages','ProjectSettings'):
  for p in (PROJECT/top).rglob('*'):
   if not p.is_file():continue
   rel=p.relative_to(PROJECT).as_posix()
   if rel.startswith(('Assets/HybridCLR/','Assets/StreamingAssets/')) or rel in ('Assets/HybridCLR.meta','Assets/StreamingAssets.meta','Assets/Probe.unity','Assets/Probe.unity.meta') or p.name in ('EditorBuildSettings.asset','HybridCLRSettings.asset'):continue
   files.append(p)
 return {p.relative_to(ROOT).as_posix():receipts.sha(p) for p in sorted(files)}
def parity():
 template=(ROOT/'samples/concurrent-initialization/Scenarios.cs').read_text(encoding='utf-8')
 for folder,ns in [('AOT','AotConcurrent'),('HotUpdate','HotConcurrent')]:
  if (PROJECT/'Assets'/folder/'Scenarios.cs').read_text(encoding='utf-8')!=template.replace('SAMPLE_NAMESPACE',ns):raise RuntimeError('Scenario parity')
def installed():return PROJECT/'Library/HybridCLR/LocalIl2CppData-WindowsEditor/il2cpp/libil2cpp'
def runtime_manifest(folder):return {p.relative_to(folder).as_posix():receipts.sha(p) for p in folder.rglob('*') if p.is_file() and not p.relative_to(folder).as_posix().startswith('hybridclr/generated/')}
def editor(args,method,b):
 log=ART/('prepare.log' if method.endswith('Prepare') else 'build.log');receipts.fresh_log(log)
 env=dict(os.environ,CONCURRENT_BUILD_ID=b['build_id'])
 child=subprocess.Popen([str(args.editor),'-batchmode','-nographics','-quit','-projectPath',str(PROJECT),'-executeMethod',method,'-logFile',str(log)],env=env,creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
 try:code=child.wait(timeout=1800)
 except subprocess.TimeoutExpired:
  subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL);child.wait();raise RuntimeError('Own Editor timeout')
 marker=b'CONCURRENT_PREPARE_OK' if method.endswith('Prepare') else b'CONCURRENT_BUILD_RESULT Succeeded'
 if code or marker not in log.read_bytes():raise RuntimeError('Editor failed: '+str(log.relative_to(ROOT)))
 print(method,'PASS',child.pid,flush=True)
def metadata():
 paths=[PLAYER/(NAME+'_BackUpThisFolder_ButDontShipItWithYourGame/Managed/Probe.AOT.dll'),PLAYER/(NAME+'_Data/StreamingAssets/HotUpdate.dll.bytes')]
 data=json.loads(subprocess.check_output(['dotnet','run','--project',str(ROOT/'tools/ConcurrentMetadata'),'-c','Release','-v','quiet','--',*map(str,paths)],encoding='utf-8-sig'))
 if [x['sha256'] for x in data]!=[receipts.sha(p) for p in paths]:raise RuntimeError('Wrong final DLL')
 for row,ns in zip(data,['AotConcurrent','HotConcurrent']):
  types={x['name']:x for x in row['types']}
  if set(types)!=set(['Cold','Strict','Failed','Cache`1']+(['Bridge'] if ns=='HotConcurrent' else [])):raise RuntimeError('Type matrix')
  for name,t in types.items():
   if t['ns']!=ns or t['beforefieldinit']!=(name in ('Cold','Bridge')):raise RuntimeError('Type flags')
   if len([m for m in t['methods'] if m['name']=='.cctor'])!=(0 if name in ('Cold','Bridge') else 1):raise RuntimeError('Cctor metadata')
 return data
def build(args):
 lock=verify_prepared();parity()
 if not args.editor or not args.editor.is_file():raise ValueError('Pass locked --editor')
 b=receipts.start_build(lock,receipts.editor_identity(args.editor,lock));editor(args,'ConcurrentBuild.Prepare',b)
 b.update(source_sha256=sources(),runtime_sha256=runtime_manifest(installed()));receipts.write(ART/'build-lock.json',b);editor(args,'ConcurrentBuild.Build',b)
 if sources()!=b['source_sha256'] or runtime_manifest(installed())!=b['runtime_sha256']:raise RuntimeError('Build input changed')
 cpp=PROJECT/'Library/Bee/artifacts/WinPlayerBuildProgram/il2cppOutput/cpp';backup=PLAYER/(NAME+'_BackUpThisFolder_ButDontShipItWithYourGame/Managed')
 if (backup/'HotUpdate.dll').exists() or (cpp/'HotUpdate.cpp').exists() or 'HotUpdate' in (cpp/'Il2CppCodeRegistration.cpp').read_text(encoding='utf-8-sig'):raise RuntimeError('Hot entered AOT')
 b.update(metadata=metadata(),hot_update_excluded_from_aot=True)
 original=runtime_manifest(ROOT/'.local/combined-libil2cpp')
 if original!=b['runtime_sha256']:raise RuntimeError('Installed runtime is not pristine prepared runtime')
 receipts.write(ART/'metadata.json',b['metadata']);receipts.finish_build(b,[p for p in PLAYER.rglob('*') if p.is_file()]+[ART/'metadata.json']);print('CONCURRENT BUILD PASS',b['build_id'],len(b['runtime_sha256']),flush=True)
def current():
 parity();verify_prepared();b=receipts.require_build()
 if sources()!=b['source_sha256'] or runtime_manifest(installed())!=b['runtime_sha256']:raise RuntimeError('Inputs changed')
 if json.loads((ART/'metadata.json').read_text())!=b['metadata']:raise RuntimeError('Metadata changed')
 return b
def player_args(side,mode,n,log):return [PLAYER/(NAME+'.exe'),'-batchmode','-nographics','-logFile',log,'--side',side,'--mode',mode,'--workers',str(n)]
def run(args):
 b=current();receipts.begin_phase('run',b);rows=[];logs=[]
 for side,mode,n in CELLS:
  for rep in (1,2,3):
   log=ART/f'{side}-{mode}-{n}-{rep}.log';receipts.fresh_log(log);pid,code=process(player_args(side,mode,n,log),120)
   obs=parse_player(log.read_text(encoding='utf-8-sig',errors='replace'),side,mode,n,b['build_id'])
   if code:raise RuntimeError('Player exit '+str(code))
   rows.append(dict(side=side,mode=mode,workers=n,run=rep,pid=pid,exit_code=code,observations=obs));logs.append(log);print('CONCURRENT RUN',side,mode,n,rep,'overlap',[x['attempts_during_initializer'] for x in obs['subjects']],flush=True)
 result=ART/'run-results.json';receipts.write(result,dict(build_id=b['build_id'],runs=rows));logs.append(result);receipts.finish_phase('run',b,logs)
def verify(args):
 b=current();s=json.loads((ART/'run-status.json').read_text());d=json.loads((ART/'run-results.json').read_text())
 if s['status']!='complete' or s['build_id']!=b['build_id'] or d['build_id']!=b['build_id']:raise RuntimeError('Incomplete run')
 if [(x['side'],x['mode'],x['workers'],x['run']) for x in d['runs']]!=[(s,m,n,r) for s,m,n in CELLS for r in (1,2,3)]:raise RuntimeError('Matrix incomplete')
 for rel,h in s['log_sha256'].items():
  if receipts.sha(ART/rel)!=h:raise RuntimeError('Evidence changed '+rel)
 for x in d['runs']:
  log=ART/f"{x['side']}-{x['mode']}-{x['workers']}-{x['run']}.log"
  if x['exit_code'] or parse_player(log.read_text(encoding='utf-8-sig',errors='replace'),x['side'],x['mode'],x['workers'],b['build_id'])!=x['observations']:raise RuntimeError('Reparse changed')
 from concurrent_trace import verify_traces
 traces=verify_traces(b)
 tools=['tools/concurrent_lab.py','tools/concurrent_results.py','tools/concurrent_trace.py','tests/test_concurrent_results.py','tests/test_concurrent_trace.py','tools/ConcurrentMetadata/Program.cs','tools/ConcurrentMetadata/ConcurrentMetadata.csproj','tools/receipts.py','tools/prepare.py','tools/lifetime_lab.py']
 record=dict(schema=1,build_id=b['build_id'],lock=b['lock'],source_sha256=b['source_sha256'],runtime_sha256=b['runtime_sha256'],artifact_sha256=b['artifact_sha256'],metadata=b['metadata'],hot_update_excluded_from_aot=True,tool_sha256={p:receipts.sha(ROOT/p) for p in tools},raw_log_sha256=s['log_sha256'],native=traces,runs=d['runs'])
 receipts.write(ART/'verified-results.json',record);print('CONCURRENT VERIFY',len(d['runs']),len(traces['runs']),flush=True);return record
def export(args):
 r=verify(args);out=ROOT/'evidence/2026-10-26-concurrent-initialization';out.mkdir(parents=True,exist_ok=True)
 for group in [r['runs'],r['native']['runs']]:
  for x in group:
   obs=x['observations'];name=f"{x.get('prefix','run')}-{x['side']}-{x['mode']}-{x['workers']}-{x.get('run',1)}-events.jsonl";path=out/name
   events=obs['events'];path.write_text(''.join(json.dumps(e,separators=(',',':'))+'\n' for e in events),encoding='utf-8')
   if parse_player(''.join('CIP '+json.dumps(e)+'\n' for e in events),x['side'],x['mode'],x['workers'],r['build_id'])!=obs:raise RuntimeError('Export changed semantics')
   x['observations']={k:v for k,v in obs.items() if k!='events'};x.update(event_file=name,event_sha256=receipts.sha(path))
 r.update(baseline_commit='563813195813cc2d618bdf301e12ab1af0556d79',publication='Source and evidence are versioned together in the commit containing this record. baseline_commit is the preceding constrained/boxing experiment, not this experiment.',limits=['Fixed local-custom Unity/Windows x64 Development IL2CPP Debug; no performance or other-platform claim.','Ordinary run attempts overlap initializer event interval, not a native proof of simultaneous execution or universal thread safety.','Debugger breakpoints perturb scheduling and may miss or repeat fast concurrent entries; raw hit counts and unique worker threads are retained separately. Player body events are the execution-count authority.','Original pinned runtime; no previous exception-flow counterfactual patch installed. Failure is caught at AOT reflection boundary.'])
 receipts.write(out/'results.json',r);print('CONCURRENT EXPORT',r['build_id'],flush=True)
def main():
 receipts.ART=ART;p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['build','run','verify','export']);p.add_argument('--editor',type=Path);args=p.parse_args();globals()[args.command](args)
if __name__=='__main__':main()
