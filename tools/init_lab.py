"""Build/run/reparse/export the isolated locked type-initialization Player."""
import argparse,json,os,subprocess,sys
from pathlib import Path
import receipts
from prepare import ROOT,verify_prepared
from lifetime_lab import process
from init_results import SIDES,MODES,parse_player
ART=ROOT/'artifacts/type-initialization';PROJECT=ROOT/'projects/type-initialization';PLAYER=ART/'Player'
def sources():
 files=[ROOT/'samples/type-initialization/Scenarios.cs']
 for top in ('Assets','Packages','ProjectSettings'):
  for p in (PROJECT/top).rglob('*'):
   if not p.is_file():continue
   rel=p.relative_to(PROJECT).as_posix()
   if rel.startswith(('Assets/HybridCLR/','Assets/StreamingAssets/')) or rel in ('Assets/HybridCLR.meta','Assets/StreamingAssets.meta','Assets/Probe.unity','Assets/Probe.unity.meta'):continue
   if p.name in ('EditorBuildSettings.asset','HybridCLRSettings.asset'):continue
   files.append(p)
 return {p.relative_to(ROOT).as_posix():receipts.sha(p) for p in sorted(files)}
def parity():
 template=(ROOT/'samples/type-initialization/Scenarios.cs').read_text()
 for folder,ns in [('AOT','AotInit'),('HotUpdate','HotInit')]:
  if (PROJECT/'Assets'/folder/'Scenarios.cs').read_text()!=template.replace('SAMPLE_NAMESPACE',ns):raise RuntimeError('Scenario source parity changed')
def editor(args,method,log,bid):
 receipts.fresh_log(log);env=dict(os.environ,INIT_BUILD_ID=bid)
 cmd=[str(args.editor),'-batchmode','-nographics','-quit','-projectPath',str(PROJECT),'-executeMethod',method,'-logFile',str(log)]
 p=subprocess.Popen(cmd,env=env,creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
 try:code=p.wait(timeout=1800)
 except subprocess.TimeoutExpired:
  subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL);p.wait();raise RuntimeError('This experiment Editor timed out')
 if code:raise RuntimeError(f'{method} exit {code}; inspect {log.relative_to(ROOT)}')
 marker=b'INIT_PREPARE_OK' if method.endswith('Prepare') else b'INIT_BUILD_RESULT Succeeded'
 if marker not in log.read_bytes():raise RuntimeError('Build marker missing')
 print(method,'PASS',p.pid,flush=True)
def metadata_check(data,b):
 if len(data)!=2:raise RuntimeError('Final DLL metadata matrix')
 for row,ns,path in zip(data,['AotInit','HotInit'],[PLAYER/'TypeInitializationProbe_BackUpThisFolder_ButDontShipItWithYourGame/Managed/Probe.AOT.dll',PLAYER/'TypeInitializationProbe_Data/StreamingAssets/HotUpdate.dll.bytes']):
  if row['sha256']!=receipts.sha(path):raise RuntimeError('Metadata read wrong final DLL')
  types={t['name']:t for t in row['types']}
  if set(types)!={'Cases','Strict','Relaxed','Cache`1','Failed'}:raise RuntimeError('Final type set changed')
  for name,t in types.items():
   if t['ns']!=ns or t['beforefieldinit']!=(name in ('Cases','Relaxed')):raise RuntimeError('Final type flags changed')
   ctors=[m for m in t['methods'] if m['name']=='.cctor']
   if len(ctors)!=(0 if name=='Cases' else 1) or any(m['il_bytes']==0 for m in ctors):raise RuntimeError('Final .cctor absent')
 return data
def build(args):
 lock=verify_prepared();parity()
 if not args.editor or not args.editor.is_file():raise ValueError('Pass locked --editor')
 b=receipts.start_build(lock,receipts.editor_identity(args.editor,lock))
 editor(args,'InitBuild.Prepare',ART/'prepare.log',b['build_id'])
 b['source_sha256']=sources();receipts.write(ART/'build-lock.json',b)
 editor(args,'InitBuild.Build',ART/'build.log',b['build_id'])
 finish(b)
def finish(b):
 if sources()!=b['source_sha256']:raise RuntimeError('Inputs normalized during build; review before acceptance')
 backup=PLAYER/'TypeInitializationProbe_BackUpThisFolder_ButDontShipItWithYourGame/Managed'
 cpp=PROJECT/'Library/Bee/artifacts/WinPlayerBuildProgram/il2cppOutput/cpp'
 if (backup/'HotUpdate.dll').exists() or (cpp/'HotUpdate.cpp').exists() or 'HotUpdate' in (cpp/'Il2CppCodeRegistration.cpp').read_text(encoding='utf-8-sig'):raise RuntimeError('HotUpdate entered AOT')
 cmd=['dotnet','run','--project',str(ROOT/'tools/InitMetadata'),'--configuration','Release','--verbosity','quiet','--',str(backup/'Probe.AOT.dll'),str(PLAYER/'TypeInitializationProbe_Data/StreamingAssets/HotUpdate.dll.bytes')]
 output=subprocess.check_output(cmd,text=True,encoding='utf-8-sig');data=json.loads(output);metadata_check(data,b);receipts.write(ART/'metadata.json',data)
 b.update(hot_update_excluded_from_aot=True,metadata=data)
 receipts.finish_build(b,[p for p in PLAYER.rglob('*') if p.is_file()]+[ART/'metadata.json'])
 print('INIT BUILD PASS',b['build_id'],'inputs',len(b['source_sha256']),'artifacts',len(b['artifact_sha256']),flush=True)
def current():
 parity();b=receipts.require_build()
 if sources()!=b['source_sha256']:raise RuntimeError('Source changed after build')
 metadata_check(json.loads((ART/'metadata.json').read_text()),b)
 return b
def run(args):
 b=current();receipts.begin_phase('run',b);rows=[];logs=[]
 for side in SIDES:
  for mode in MODES:
   for n in range(1,4):
    log=ART/f'{side}-{mode}-{n}.log';receipts.fresh_log(log)
    pid,code=process([PLAYER/'TypeInitializationProbe.exe','-batchmode','-nographics','-logFile',log,'--init-side',side,'--init-mode',mode],120)
    data=parse_player(log.read_text(encoding='utf-8-sig'),side,mode,b['build_id'])
    if code!=(2 if data['classification']=='escaped_first_access' else 0):raise RuntimeError('Unexpected Player exit')
    rows.append(dict(side=side,mode=mode,run=n,pid=pid,exit_code=code,observations=data));logs.append(log)
    print('INIT RUN',side,mode,n,json.dumps(data['initializers']),flush=True)
 result=ART/'run-results.json';receipts.write(result,dict(build_id=b['build_id'],runs=rows));logs.append(result);receipts.finish_phase('run',b,logs)
def verify(args):
 b=current();state=json.loads((ART/'run-status.json').read_text());data=json.loads((ART/'run-results.json').read_text())
 if state['status']!='complete' or state['build_id']!=b['build_id'] or data['build_id']!=b['build_id']:raise RuntimeError('Evidence identity mismatch')
 rows=data['runs']
 if [(x['side'],x['mode'],x['run']) for x in rows]!=[(s,m,n) for s in SIDES for m in MODES for n in (1,2,3)]:raise RuntimeError('Incomplete matrix')
 for rel,h in state['log_sha256'].items():
  if receipts.sha(ART/rel)!=h:raise RuntimeError('Raw evidence changed: '+rel)
 for row in rows:
  path=ART/f"{row['side']}-{row['mode']}-{row['run']}.log"
  if row['exit_code']!=(2 if row['observations']['classification']=='escaped_first_access' else 0) or parse_player(path.read_text(encoding='utf-8-sig'),row['side'],row['mode'],b['build_id'])!=row['observations']:raise RuntimeError('Reparse changed')
 from init_trace import parse_trace
 ts=json.loads((ART/'trace-status.json').read_text());tr=json.loads((ART/'trace-results.json').read_text())
 if ts['status']!='complete' or ts['build_id']!=b['build_id'] or tr['build_id']!=b['build_id'] or [x['mode'] for x in tr['runs']]!=['strict','failed']:raise RuntimeError('Trace identity/matrix')
 for rel,h in ts['log_sha256'].items():
  if receipts.sha(ART/rel)!=h:raise RuntimeError('Native evidence changed: '+rel)
 for row in tr['runs']:
  mode=row['mode'];obs=parse_player((ART/f'trace-{mode}-player.log').read_text(encoding='utf-8-sig'),'hot',mode,b['build_id'])
  if {k:v for k,v in obs.items() if k!='events'}!=row['observations'] or parse_trace((ART/f'trace-{mode}.log').read_text(encoding='utf-8-sig',errors='replace'))!=row['native']:raise RuntimeError('Native reparse changed')
  if row['exit_code']!=(2 if obs['classification']=='escaped_first_access' else 0):raise RuntimeError('Native exit mismatch')
 tools=['tools/init_lab.py','tools/init_results.py','tools/init_trace.py','tests/test_init_results.py','tests/test_init_trace.py','tools/InitMetadata/Program.cs','tools/InitMetadata/InitMetadata.csproj','tools/receipts.py','tools/prepare.py','tools/lifetime_lab.py']
 record=dict(schema=1,build_id=b['build_id'],lock=b['lock'],source_sha256=b['source_sha256'],artifact_sha256=b['artifact_sha256'],tool_sha256={p:receipts.sha(ROOT/p) for p in tools},metadata=b['metadata'],hot_update_excluded_from_aot=True,raw_log_sha256=state['log_sha256'],trace_log_sha256=ts['log_sha256'],native_trace=tr['runs'],runs=rows)
 receipts.write(ART/'verified-results.json',record);print('INIT VERIFY PASS',b['build_id'],len(rows),flush=True);return record
def export(args):
 r=verify(args);out=ROOT/'evidence/2026-10-26-type-initialization';out.mkdir(parents=True,exist_ok=True);rows=[]
 keys={'env':'seq kind side mode build unity hot_before','stage':'seq kind phase','meta':'seq kind subject bfi cctor','init':'seq kind subject value','method':'seq kind subject value','read':'seq kind subject value','caught':'seq kind subject type detail','escaped':'seq kind subject type detail','done':'seq kind completed'}
 for row in r['runs']:
  obs=row['observations'];events=[{k:x[k] for k in keys[x['kind']].split()} for x in obs['events']]
  text=''.join(json.dumps(x,separators=(',',':'))+'\n' for x in events);name=f"{row['side']}-{row['mode']}-{row['run']}-events.jsonl";path=out/name;path.write_text(text,encoding='utf-8')
  check=parse_player(''.join('TIP '+json.dumps(x)+'\n' for x in events),row['side'],row['mode'],r['build_id'])
  summary={k:v for k,v in obs.items() if k!='events'}
  if {k:v for k,v in check.items() if k!='events'}!=summary:raise RuntimeError('Export changed meaning')
  rows.append(dict(side=row['side'],mode=row['mode'],run=row['run'],pid=row['pid'],exit_code=row['exit_code'],observations=summary,event_file=name,event_sha256=receipts.sha(path)))
 r['runs']=rows
 for row in r['native_trace']:
  log=ART/f"trace-{row['mode']}-player.log"
  obs=parse_player(log.read_text(encoding='utf-8-sig'),'hot',row['mode'],r['build_id'])
  events=[{k:x[k] for k in keys[x['kind']].split()} for x in obs['events']];name=f"trace-{row['mode']}-events.jsonl";path=out/name
  path.write_text(''.join(json.dumps(x,separators=(',',':'))+'\n' for x in events),encoding='utf-8');row.update(event_file=name,event_sha256=receipts.sha(path))
 r.update(baseline_commit='74da063e0fe2a4cbac894acfa77d3b0df4074356',publication='Local verified candidate; baseline_commit is the preceding resource experiment, not this sample.',limits=['Single-thread, fixed local-custom Editor and Windows x64 Development IL2CPP Debug; no timing/performance or other-platform claim.','Both sides enter Cases.Run via reflection; target scenario calls are direct. AOT assembly is part of Player startup; hot Assembly.Load is explicit.','beforefieldinit observation is one allowed schedule, not a required schedule for other runtimes. Native strict/failed traces are separate observations, not proof of all initializer or exception paths.'])
 receipts.write(out/'results.json',r);print('INIT EXPORT PASS',r['build_id'],len(rows),flush=True)
def trace(args):
 from init_trace import parse_trace
 import re
 b=current()
 if not args.cdb or not args.cdb.is_file():raise ValueError('Pass x64 --cdb')
 cpp=PROJECT/'Library/Bee/artifacts/WinPlayerBuildProgram/il2cppOutput/cpp/Probe.AOT.cpp'
 quit_symbols=set(re.findall(r'Application_Quit_m[A-Za-z0-9_]+',cpp.read_text(encoding='utf-8-sig')))
 if len(quit_symbols)!=1:raise RuntimeError('Quit marker identity ambiguous')
 template=(ROOT/'debugger/call-chain-v9.cdb').read_text(encoding='utf-8');lines=['r @$t0=0']
 for line in template.splitlines():
  if any(tag in line for tag in ('PROBE_NATIVE_PREPARE','PROBE_NATIVE_TRANSFORM','PROBE_NATIVE_EXECUTE')):
   line=line.replace('PROBE_NATIVE_','TIP_NATIVE_').replace(' args=%d,%d','').replace(', dwo(@rdx), dwo(@rdx+8)','').replace('k 5','k 12')
   if 'TIP_NATIVE_TRANSFORM' in line:line=line.replace('; dt GameAssembly!', '; .if (dwo(poi(@rcx+0x18))==0x676e6950) { r @$t0=@rcx; }; dt GameAssembly!')
   lines.append(line)
 # 0x18/name and 0x58/interpData are verified by dt in every fixed-PDB block.
 quote=chr(92)+chr(34)
 lines.append('bu GameAssembly!'+next(iter(quit_symbols))+' ".printf '+quote+'TIP_NATIVE_END method=%p'+chr(92)+'n'+quote+', @$t0; dt GameAssembly!MethodInfo @$t0 name klass interpData; g"')
 lines += ['sxe -c "lmv m GameAssembly; g" ld:GameAssembly.dll','g']
 command=ART/'type-init.cdb';command.write_text('\n'.join(lines)+'\n',encoding='ascii')
 receipts.begin_phase('trace',b);logs=[command];rows=[]
 for mode in ('strict','failed'):
  trace_log=ART/f'trace-{mode}.log';player_log=ART/f'trace-{mode}-player.log'
  receipts.fresh_log(trace_log);receipts.fresh_log(player_log)
  pid,code=process([args.cdb,'-G','-y',PLAYER/'TypeInitializationProbe_BackUpThisFolder_ButDontShipItWithYourGame','-logo',trace_log,'-cf',command,PLAYER/'TypeInitializationProbe.exe','-batchmode','-nographics','-logFile',player_log,'--init-side','hot','--init-mode',mode],180)
  obs=parse_player(player_log.read_text(encoding='utf-8-sig'),'hot',mode,b['build_id'])
  if code!=(2 if obs['classification']=='escaped_first_access' else 0):raise RuntimeError('Trace exit mismatch')
  native=parse_trace(trace_log.read_text(encoding='utf-8-sig',errors='replace'))
  rows.append(dict(mode=mode,pid=pid,exit_code=code,observations={k:v for k,v in obs.items() if k!='events'},native=native));logs += [trace_log,player_log]
  print('INIT TRACE',mode,json.dumps(native),flush=True)
 path=ART/'trace-results.json';receipts.write(path,dict(build_id=b['build_id'],runs=rows));logs.append(path);receipts.finish_phase('trace',b,logs)

def main():
 receipts.ART=ART
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['build','run','verify','export','trace']);p.add_argument('--editor',type=Path);p.add_argument('--cdb',type=Path);args=p.parse_args();globals()[args.command](args)
if __name__=='__main__':main()
