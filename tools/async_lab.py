"""Locked independent async/UniTask build, fresh Player matrix and evidence."""
import argparse,json,os,subprocess,sys
from pathlib import Path
import receipts
from prepare import ROOT,verify_prepared,git,tree_digest
from lifetime_lab import process
from async_results import SIDES,MODES,parse_player
ART=ROOT/'artifacts/async-unitask';PROJECT=ROOT/'projects/async-unitask';PLAYER=ART/'Player'

def dependency():
 spec=json.loads((ROOT/'async-lock.json').read_text());src=ROOT/spec['path']
 if git('-C',src,'rev-parse','HEAD')!=spec['commit'] or git('-C',src,'status','--porcelain','--untracked-files=all'):raise RuntimeError('UniTask source identity changed')
 return dict(lock=spec,package_sha256=tree_digest(src/spec['package_path']))

def sources():
 files=[ROOT/'samples/async-unitask/Scenarios.cs',ROOT/'async-lock.json']
 for top in ('Assets','Packages','ProjectSettings'):
  for p in (PROJECT/top).rglob('*'):
   if not p.is_file():continue
   rel=p.relative_to(PROJECT).as_posix()
   if rel.startswith(('Assets/HybridCLR/','Assets/StreamingAssets/')) or rel in ('Assets/HybridCLR.meta','Assets/StreamingAssets.meta','Assets/Probe.unity','Assets/Probe.unity.meta') or p.name in ('EditorBuildSettings.asset','HybridCLRSettings.asset'):continue
   files.append(p)
 return {p.relative_to(ROOT).as_posix():receipts.sha(p) for p in sorted(files)}

def parity():
 t=(ROOT/'samples/async-unitask/Scenarios.cs').read_text(encoding='utf-8')
 for folder,ns,side in [('AOT','AotAsync','aot'),('HotUpdate','HotAsync','hot')]:
  if (PROJECT/'Assets'/folder/'Scenarios.cs').read_text(encoding='utf-8')!=t.replace('SAMPLE_NS',ns).replace('SAMPLE_SIDE',side):raise RuntimeError('Scenario parity')

def runtime_manifest():
 d=PROJECT/'Library/HybridCLR/LocalIl2CppData-WindowsEditor/il2cpp/libil2cpp'
 return {p.relative_to(d).as_posix():receipts.sha(p) for p in d.rglob('*') if p.is_file() and not p.relative_to(d).as_posix().startswith('hybridclr/generated/')}

def editor(args,method,b):
 log=ART/('prepare.log' if method.endswith('Prepare') else 'build.log');receipts.fresh_log(log)
 env=dict(os.environ,ASYNC_BUILD_ID=b['build_id']);cmd=[str(args.editor),'-batchmode','-nographics','-quit','-projectPath',str(PROJECT),'-executeMethod',method,'-logFile',str(log)]
 p=subprocess.Popen(cmd,env=env,creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
 try:code=p.wait(timeout=1800)
 except subprocess.TimeoutExpired:
  subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL);p.wait();raise RuntimeError('Own Editor timeout')
 marker='ASYNC_PREPARE_OK' if method.endswith('Prepare') else 'ASYNC_BUILD_RESULT Succeeded'
 if code or marker.encode('ascii') not in log.read_bytes():raise RuntimeError('Editor failed: '+str(log.relative_to(ROOT)))
 print(method,'PASS',p.pid,flush=True)

def metadata():
 backup=PLAYER/'AsyncUniTaskProbe_BackUpThisFolder_ButDontShipItWithYourGame/Managed';sa=PLAYER/'AsyncUniTaskProbe_Data/StreamingAssets'
 paths=[backup/'Probe.AOT.dll',sa/'hot-dev.dll.bytes',sa/'hot-release.dll.bytes']
 out=subprocess.check_output(['dotnet','run','--project',str(ROOT/'tools/AsyncMetadata'),'--configuration','Release','--verbosity','quiet','--',*map(str,paths)],encoding='utf-8-sig')
 data=json.loads(out)
 if [x['sha256'] for x in data]!=[receipts.sha(p) for p in paths]:raise RuntimeError('Metadata wrong DLL')
 for row in data:
  states=[t for t in row['types'] if '<Work>' in t['name']]
  if len(states)!=1 or not any(x['name']=='MoveNext' for x in states[0]['methods']):raise RuntimeError('Missing state machine')
 if receipts.sha(backup/'UniTask.dll')!=receipts.sha(sa/'UniTask.dll.bytes'):raise RuntimeError('Supplementary UniTask differs from final Player stripped assembly')
 return data

def build(args):
 lock=verify_prepared();parity();dep=dependency()
 if not args.editor or not args.editor.is_file():raise ValueError('Pass locked --editor')
 b=receipts.start_build(lock,receipts.editor_identity(args.editor,lock));b['unitask']=dep
 editor(args,'AsyncBuild.Prepare',b);b['source_sha256']=sources();b['runtime_sha256']=runtime_manifest();receipts.write(ART/'build-lock.json',b)
 editor(args,'AsyncBuild.Build',b)
 if b['source_sha256']!=sources() or b['runtime_sha256']!=runtime_manifest() or dep!=dependency():raise RuntimeError('Build inputs changed')
 cpp=PROJECT/'Library/Bee/artifacts/WinPlayerBuildProgram/il2cppOutput/cpp';backup=PLAYER/'AsyncUniTaskProbe_BackUpThisFolder_ButDontShipItWithYourGame/Managed'
 if (backup/'HotUpdate.dll').exists() or (cpp/'HotUpdate.cpp').exists() or 'HotUpdate' in (cpp/'Il2CppCodeRegistration.cpp').read_text(encoding='utf-8-sig'):raise RuntimeError('Hot code entered AOT')
 data=metadata();receipts.write(ART/'metadata.json',data);b.update(metadata=data,hot_update_excluded_from_aot=True)
 receipts.finish_build(b,[p for p in PLAYER.rglob('*') if p.is_file()]+[ART/'metadata.json']);print('ASYNC BUILD',b['build_id'],'sources',len(b['source_sha256']),'artifacts',len(b['artifact_sha256']),flush=True)

def current():
 parity();b=receipts.require_build()
 if b['source_sha256']!=sources() or b['unitask']!=dependency():raise RuntimeError('Source/dependency changed')
 verify_prepared()
 pristine=ROOT/'.local/combined-libil2cpp'
 expected={p.relative_to(pristine).as_posix():receipts.sha(p) for p in pristine.rglob('*') if p.is_file() and not p.relative_to(pristine).as_posix().startswith('hybridclr/generated/')}
 if b['runtime_sha256']!=expected or runtime_manifest()!=expected:raise RuntimeError('Runtime differs from original locked preparation')
 return b

def matrix():return [(side,meta,mode,n) for side in SIDES for meta in (('off',) if side=='aot' else ('off','on')) for mode in MODES for n in (1,2,3)]
def filename(s,m,mode,n):return f'{s}-{m}-{mode}-{n}.log'
def run(args):
 b=current();receipts.begin_phase('run',b);rows=[];logs=[]
 for side,meta,mode,n in matrix():
  log=ART/filename(side,meta,mode,n);receipts.fresh_log(log)
  pid,code=process([PLAYER/'AsyncUniTaskProbe.exe','-batchmode','-nographics','-logFile',log,'--async-side',side,'--async-mode',mode,'--async-metadata',meta],60)
  if code:raise RuntimeError('Player failed '+log.name)
  obs=parse_player(log.read_text(encoding='utf-8-sig'),side,mode,meta,b['build_id'])
  rows.append(dict(side=side,metadata=meta,mode=mode,run=n,pid=pid,exit_code=code,observations=obs));logs.append(log);print('ASYNC RUN',side,meta,mode,n,obs['classification'],flush=True)
 path=ART/'run-results.json';receipts.write(path,dict(build_id=b['build_id'],runs=rows));logs.append(path);receipts.finish_phase('run',b,logs)

def verify(args):
 b=current();status=json.loads((ART/'run-status.json').read_text());record=json.loads((ART/'run-results.json').read_text())
 if status['status']!='complete' or status['build_id']!=b['build_id'] or record['build_id']!=b['build_id']:raise RuntimeError('Run identity')
 for p,h in status['log_sha256'].items():
  if receipts.sha(ART/p)!=h:raise RuntimeError('Raw hash changed '+p)
 rows=record['runs']
 if [(x['side'],x['metadata'],x['mode'],x['run']) for x in rows]!=matrix():raise RuntimeError('Incomplete matrix')
 for row in rows:
  s,m,mode,n=[row[k] for k in ('side','metadata','mode','run')]
  if row['exit_code']!=0 or parse_player((ART/filename(s,m,mode,n)).read_text(encoding='utf-8-sig'),s,mode,m,b['build_id'])!=row['observations']:raise RuntimeError('Raw reparse mismatch')
 from async_native import parse_native
 trace_state=json.loads((ART/'trace-status.json').read_text());trace_record=json.loads((ART/'trace-results.json').read_text())
 if trace_state['status']!='complete' or trace_state['build_id']!=b['build_id'] or trace_record['build_id']!=b['build_id']:raise RuntimeError('Trace identity')
 for p,h in trace_state['log_sha256'].items():
  if receipts.sha(ART/p)!=h:raise RuntimeError('Native raw hash changed '+p)
 traces=trace_record['runs'];expected=[(s,m,mode,n) for s,m,mode in [('hot-dev','off','frame'),('hot-release','off','frame'),('hot-release','on','frame'),('hot-release','on','throw-after')] for n in (1,2,3)]
 if [(x['side'],x['metadata'],x['mode'],x['run']) for x in traces]!=expected:raise RuntimeError('Incomplete trace matrix')
 for row in traces:
  s,m,mode,n=[row[k] for k in ('side','metadata','mode','run')];stem=f'native-{s}-{m}-{mode}-{n}'
  if row['exit_code']!=0 or parse_player((ART/(stem+'-player.log')).read_text(encoding='utf-8-sig'),s,mode,m,b['build_id'])!=row['observations']:raise RuntimeError('Native player reparse')
  data=parse_native((ART/(stem+'.log')).read_text(encoding='utf-8-sig',errors='replace'),b['metadata'][1 if s=='hot-dev' else 2]);row['native']=data
  if data['builder_route']!=('native-reference' if s=='hot-dev' else 'native-any'):raise RuntimeError('Native route differs')
 result=dict(schema=1,baseline_commit='f5ba510382e170ac06d2fd7033db363e6c58f62e',build=b,runs=rows,traces=traces,raw_sha256=status['log_sha256'],native_raw_sha256=trace_state['log_sha256'])
 result['tool_sha256']={p:receipts.sha(ROOT/p) for p in ['tools/async_lab.py','tools/async_results.py','tools/async_trace.py','tools/async_native.py','tools/prepare_async.py','tests/test_async_tool.py','tests/test_async_metadata.py','tests/test_async_native.py','tools/AsyncMetadata/Program.cs','tools/AsyncMetadata/AsyncMetadata.csproj','tests/test_async_results.py','tools/receipts.py','tools/prepare.py','tools/lifetime_lab.py']}
 receipts.write(ART/'verified-results.json',result);print('ASYNC VERIFY',len(rows),'ordinary Players',flush=True);return result

def export(args):
 r=verify(args);out=ROOT/'evidence/2026-10-26-async-unitask';out.mkdir(parents=True,exist_ok=True)
 keys='seq kind frame thread side mode metadata build unity label type detail value hot_before'.split()
 for row in r['runs']+r['traces']:
  obs=row['observations'];events=[{k:e[k] for k in keys if k in e} for e in obs['events']]
  name=('native-' if 'native' in row else '')+filename(row['side'],row['metadata'],row['mode'],row['run']).replace('.log','-events.jsonl');p=out/name;p.write_text(''.join(json.dumps(e,separators=(',',':'))+'\n' for e in events),encoding='utf-8')
  reparsed=parse_player(''.join('AUT '+json.dumps(e)+'\n' for e in events),row['side'],row['mode'],row['metadata'],r['build']['build_id'])
  if reparsed!=obs:raise RuntimeError('Export changed events')
  row.update(observations={k:v for k,v in obs.items() if k!='events'},event_file=name,event_sha256=receipts.sha(p))
 r['limits']=['UniTask is preserved in full in link.xml for this focused sample; off does not mean native implementations are absent.','Both metadata groups use existing native builder implementations in the captured paths; loading metadata does not force interpretation.','Fixed custom Editor/v9 Windows x64; no performance, concurrency or other-platform conclusion.','UniTask2.5.10 fixed independently of unchanged runtime lock; debug/release hot compilation are separate shape dimensions.','No claim of reproducing or resolving the historical Android Release native crash.','Counterfactual exception-flow runtime patch is not installed.']
 receipts.write(out/'results.json',r);print('ASYNC EXPORT',len(r['runs'])+len(r['traces']),'own events',flush=True)

def main():
 receipts.ART=ART;p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['build','run','verify','export']);p.add_argument('--editor',type=Path);args=p.parse_args();globals()[args.command](args)
if __name__=='__main__':main()
