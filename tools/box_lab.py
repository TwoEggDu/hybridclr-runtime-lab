"""Independent locked constrained/boxing Player and audited evidence."""
import argparse,json,os,subprocess
from pathlib import Path
import receipts
from prepare import ROOT,verify_prepared
from lifetime_lab import process
from box_results import ROUTES,MODES,parse_player
ART=ROOT/'artifacts/constrained-boxing';PROJECT=ROOT/'projects/constrained-boxing';PLAYER=ART/'Player'

def render(hot):
 s=(ROOT/'samples/constrained-boxing/Scenarios.cs').read_text(encoding='utf-8').replace('SAMPLE_NS','HotBox' if hot else 'AotBox')
 for key,fun,arg in [('VALUE','ByValue','counter'),('REF','ByRef','ref counter'),('TEXT_COUNTER','Text','ref counter'),('TEXT_PLAIN','Text','ref plain'),('CLASS_VALUE','ByValue','obj'),('CLASS_REF','ByRef','ref obj')]:
  local=fun+'Local('+arg+')';call='(route=="cross"?GenericCalls.'+fun+'('+arg+'):'+local+')' if hot else local;s=s.replace('CALL_'+key,call)
 return s

def parity():
 for f,hot in [('AOT',False),('HotUpdate',True)]:
  if (PROJECT/'Assets'/f/'Scenarios.cs').read_text(encoding='utf-8')!=render(hot):raise RuntimeError('Source template/binding mismatch')

def sources():
 files=[ROOT/'samples/constrained-boxing/Scenarios.cs']
 for top in ('Assets','Packages','ProjectSettings'):
  for p in (PROJECT/top).rglob('*'):
   if not p.is_file():continue
   rel=p.relative_to(PROJECT).as_posix()
   if rel.startswith(('Assets/HybridCLR/','Assets/StreamingAssets/')) or rel in ('Assets/HybridCLR.meta','Assets/StreamingAssets.meta','Assets/Probe.unity','Assets/Probe.unity.meta') or p.name in ('EditorBuildSettings.asset','HybridCLRSettings.asset'):continue
   files.append(p)
 return {p.relative_to(ROOT).as_posix():receipts.sha(p) for p in sorted(files)}

def runtime_manifest(folder):
 return {p.relative_to(folder).as_posix():receipts.sha(p) for p in folder.rglob('*') if p.is_file() and not p.relative_to(folder).as_posix().startswith('hybridclr/generated/')}
def installed():return PROJECT/'Library/HybridCLR/LocalIl2CppData-WindowsEditor/il2cpp/libil2cpp'

def editor(args,method,b):
 log=ART/('prepare.log' if method.endswith('Prepare') else 'build.log');receipts.fresh_log(log)
 env=dict(os.environ,BOX_BUILD_ID=b['build_id']);cmd=[str(args.editor),'-batchmode','-nographics','-quit','-projectPath',str(PROJECT),'-executeMethod',method,'-logFile',str(log)]
 pid=subprocess.Popen(cmd,env=env,creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
 try:code=pid.wait(timeout=1800)
 except subprocess.TimeoutExpired:
  subprocess.run(['taskkill','/PID',str(pid.pid),'/T','/F'],creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL);pid.wait();raise RuntimeError('Own Editor timed out')
 marker=b'BOX_PREPARE_OK' if method.endswith('Prepare') else b'BOX_BUILD_RESULT Succeeded'
 if code or marker not in log.read_bytes():raise RuntimeError('Editor failed: '+str(log.relative_to(ROOT)))
 print(method,'PASS',pid.pid,flush=True)

def metadata():
 backup=PLAYER/'ConstrainedBoxingProbe_BackUpThisFolder_ButDontShipItWithYourGame/Managed';sa=PLAYER/'ConstrainedBoxingProbe_Data/StreamingAssets';paths=[backup/'Probe.AOT.dll',sa/'HotUpdate.dll.bytes']
 out=subprocess.check_output(['dotnet','run','--project',str(ROOT/'tools/BoxMetadata'),'-c','Release','-v','quiet','--',*map(str,paths)],encoding='utf-8-sig');data=json.loads(out)
 if [r['sha256'] for r in data]!=[receipts.sha(p) for p in paths]:raise RuntimeError('Metadata identity')
 if receipts.sha(backup/'Probe.AOT.dll')!=receipts.sha(sa/'Probe.AOT.dll.bytes'):raise RuntimeError('Supplement differs from final AOT DLL')
 for row,ns in zip(data,['AotBox','HotBox']):
  types={t['name']:t for t in row['types']};cases=types[ns+'.Cases'];methods={m['name']:m for m in cases['methods']}
  for name in ['ByValueLocal','ByRefLocal','TextLocal']:
   names=[i['opcode'] for i in methods[name]['instructions']]
   if 'constrained.' not in names or 'callvirt' not in names:raise RuntimeError('Expected constrained callvirt absent '+name)
  if methods['ByRefLocal']['signature']['parameters']!=['!!0&']:raise RuntimeError('Ref generic signature')
  if methods['ByValueLocal']['signature']['parameters']!=['!!0']:raise RuntimeError('Value generic signature')
  ops=[i['opcode'] for i in methods['Run']['instructions']]
  if 'box' not in ops or 'unbox.any' not in ops:raise RuntimeError('Box/unbox.any absent')
  if ns=='AotBox' and any('GenericCalls::' in x['target'] for x in methods['Run']['calls']):raise RuntimeError('AOT baseline instantiated cross target')
 return data

def build(args):
 lock=verify_prepared();parity()
 if not args.editor or not args.editor.is_file():raise ValueError('Pass locked --editor')
 b=receipts.start_build(lock,receipts.editor_identity(args.editor,lock));editor(args,'BoxBuild.Prepare',b)
 b.update(source_sha256=sources(),runtime_sha256=runtime_manifest(installed()));receipts.write(ART/'build-lock.json',b);editor(args,'BoxBuild.Build',b)
 if b['source_sha256']!=sources() or b['runtime_sha256']!=runtime_manifest(installed()):raise RuntimeError('Build input changed')
 cpp=PROJECT/'Library/Bee/artifacts/WinPlayerBuildProgram/il2cppOutput/cpp';backup=PLAYER/'ConstrainedBoxingProbe_BackUpThisFolder_ButDontShipItWithYourGame/Managed'
 if (backup/'HotUpdate.dll').exists() or (cpp/'HotUpdate.cpp').exists() or 'HotUpdate' in (cpp/'Il2CppCodeRegistration.cpp').read_text(encoding='utf-8-sig'):raise RuntimeError('Hot entered AOT')
 data=metadata();b.update(metadata=data,hot_update_excluded_from_aot=True);receipts.write(ART/'metadata.json',data)
 receipts.finish_build(b,[p for p in PLAYER.rglob('*') if p.is_file()]+[ART/'metadata.json']);print('BOX BUILD',b['build_id'],'inputs',len(b['source_sha256']),'artifacts',len(b['artifact_sha256']),flush=True)

def current():
 parity();verify_prepared();b=receipts.require_build()
 if b['source_sha256']!=sources():raise RuntimeError('Source changed')
 expected=runtime_manifest(ROOT/'.local/combined-libil2cpp')
 if b['runtime_sha256']!=expected or runtime_manifest(installed())!=expected:raise RuntimeError('Runtime changed from pristine locked baseline')
 return b

def matrix():return [(r,m,mode,n) for r in ROUTES for m in (('off','on') if r=='cross' else ('off',)) for mode in MODES for n in (1,2,3)]
def stem(r,m,mode,n):return f'{r}-{m}-{mode}-{n}'
def run(args):
 b=current();receipts.begin_phase('run',b);rows=[];logs=[]
 for route,meta,mode,n in matrix():
  log=ART/(stem(route,meta,mode,n)+'.log');receipts.fresh_log(log)
  pid,code=process([PLAYER/'ConstrainedBoxingProbe.exe','-batchmode','-nographics','-logFile',log,'--box-route',route,'--box-mode',mode,'--box-metadata',meta],60)
  if code:raise RuntimeError('Player failed '+log.name)
  obs=parse_player(log.read_text(encoding='utf-8-sig'),route,mode,meta,b['build_id']);rows.append(dict(route=route,metadata=meta,mode=mode,run=n,pid=pid,exit_code=code,observations=obs));logs.append(log);print('BOX RUN',route,meta,mode,n,obs['classification'],flush=True)
 path=ART/'run-results.json';receipts.write(path,dict(build_id=b['build_id'],runs=rows));logs.append(path);receipts.finish_phase('run',b,logs)

def verify(args):
 b=current();status=json.loads((ART/'run-status.json').read_text());record=json.loads((ART/'run-results.json').read_text())
 if status['status']!='complete' or status['build_id']!=b['build_id'] or record['build_id']!=b['build_id']:raise RuntimeError('Run identity')
 for p,h in status['log_sha256'].items():
  if receipts.sha(ART/p)!=h:raise RuntimeError('Raw hash changed '+p)
 rows=record['runs']
 if [(x['route'],x['metadata'],x['mode'],x['run']) for x in rows]!=matrix():raise RuntimeError('Incomplete matrix')
 for row in rows:
  r,m,mode,n=[row[k] for k in ('route','metadata','mode','run')]
  if row['exit_code']!=0 or parse_player((ART/(stem(r,m,mode,n)+'.log')).read_text(encoding='utf-8-sig'),r,mode,m,b['build_id'])!=row['observations']:raise RuntimeError('Raw reparse')
 for row in rows:
  expected='missing_method' if (row['route'],row['metadata'],row['mode'])==('cross','off','value') else 'completed'
  if row['observations']['classification']!=expected:raise RuntimeError('Observed matrix differs from reviewed baseline')
 from box_trace import CELLS
 from box_native import parse_native
 state=json.loads((ART/'trace-status.json').read_text());data=json.loads((ART/'trace-results.json').read_text())
 if state['status']!='complete' or state['build_id']!=b['build_id'] or data['build_id']!=b['build_id']:raise RuntimeError('Native identity')
 for p,h in state['log_sha256'].items():
  if receipts.sha(ART/p)!=h:raise RuntimeError('Native raw hash changed '+p)
 traces=data['runs']
 if [(x['route'],x['metadata'],x['mode'],x['run']) for x in traces]!=[(r,m,mode,n) for r,m,mode in CELLS for n in (1,2,3)]:raise RuntimeError('Incomplete native cells')
 for row in traces:
  r,m,mode,n=[row[k] for k in ('route','metadata','mode','run')];name='native-'+stem(r,m,mode,n)
  if row['exit_code']!=0 or parse_player((ART/(name+'-player.log')).read_text(encoding='utf-8-sig'),r,mode,m,b['build_id'])!=row['observations']:raise RuntimeError('Native player reparse')
  row['native']=parse_native((ART/(name+'.log')).read_text(encoding='utf-8-sig',errors='replace'),r,mode,m,b['metadata'])
 result=dict(schema=1,baseline_commit='b34ac104fa72504d1d2a480ca936ea57a7a0fb22',build=b,runs=rows,traces=traces,raw_sha256=status['log_sha256'],native_raw_sha256=state['log_sha256'])
 result['tool_sha256']={p:receipts.sha(ROOT/p) for p in ['tools/box_lab.py','tools/box_results.py','tools/box_trace.py','tools/box_native.py','tests/test_box_native.py','tools/BoxMetadata/Program.cs','tools/BoxMetadata/BoxMetadata.csproj','tests/test_box_results.py','tests/test_box_metadata.py','tools/receipts.py','tools/prepare.py','tools/lifetime_lab.py']}
 receipts.write(ART/'verified-results.json',result);print('BOX VERIFY',len(rows),'ordinary Players',flush=True);return result

def export(args):
 r=verify(args);out=ROOT/'evidence/2026-10-26-constrained-boxing';out.mkdir(parents=True,exist_ok=True)
 for row in r['runs']+r['traces']:
  obs=row['observations'];events=obs['events'];name=('native-' if 'native' in row else '')+stem(row['route'],row['metadata'],row['mode'],row['run'])+'-events.jsonl';p=out/name;p.write_text(''.join(json.dumps(e,separators=(',',':'))+'\n' for e in events),encoding='utf-8')
  if parse_player(''.join('CBX '+json.dumps(e)+'\n' for e in events),row['route'],row['mode'],row['metadata'],r['build']['build_id'])!=obs:raise RuntimeError('Export reparse')
  row.update(observations={k:v for k,v in obs.items() if k!='events'},event_file=name,event_sha256=receipts.sha(p))
 r['limits']=['Fixed custom Unity/v9 Windows x64; no performance/other-platform conclusion.','Box is a same-semantics control that does not invoke GenericCalls; cross generic claim applies to other modes.','AOT baseline does not instantiate GenericCalls; actual native/metadata availability must be observed, not presumed.','No previous exception counterfactual patch or changes to older experiments.']
 receipts.write(out/'results.json',r);print('BOX EXPORT',len(r['runs'])+len(r['traces']),'own events',flush=True)

def main():
 receipts.ART=ART;p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['build','run','verify','export']);p.add_argument('--editor',type=Path);args=p.parse_args();globals()[args.command](args)
if __name__=='__main__':main()
