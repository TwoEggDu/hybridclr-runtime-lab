"""Isolated AOT/interpreter EH baseline and one-point runtime counterfactual."""
import argparse,json,os,subprocess,sys,re
from pathlib import Path
import receipts
from prepare import ROOT,verify_prepared
from lifetime_lab import process
from eh_patch import patched_source
from eh_results import ROUTES,FAULTS,VARIANTS,parse_player,parse_context
ART=ROOT/'artifacts/exception-flow';PROJECT=ROOT/'projects/exception-flow';REL='hybridclr/interpreter/Interpreter_Execute.cpp'
def folder(v):return ART/v
def player(v):return folder(v)/'Player'
def source_manifest():
 files=[ROOT/'samples/exception-flow/Scenarios.cs']
 for top in ('Assets','Packages','ProjectSettings'):
  for p in (PROJECT/top).rglob('*'):
   if not p.is_file():continue
   rel=p.relative_to(PROJECT).as_posix()
   if rel.startswith(('Assets/HybridCLR/','Assets/StreamingAssets/')) or rel in ('Assets/HybridCLR.meta','Assets/StreamingAssets.meta','Assets/Probe.unity','Assets/Probe.unity.meta') or p.name in ('EditorBuildSettings.asset','HybridCLRSettings.asset'):continue
   files.append(p)
 return {p.relative_to(ROOT).as_posix():receipts.sha(p) for p in sorted(files)}
def parity():
 template=(ROOT/'samples/exception-flow/Scenarios.cs').read_text(encoding='utf-8')
 for f,ns,side in [('AOT','EHAot','aot'),('HotUpdate','EHHot','hot')]:
  if (PROJECT/'Assets'/f/'Scenarios.cs').read_text(encoding='utf-8')!=template.replace('SAMPLE_NS',ns).replace('SAMPLE_SIDE',side):raise RuntimeError('Own scenario parity changed')
def runtime_manifest(root):
 return {p.relative_to(root).as_posix():receipts.sha(p) for p in root.rglob('*') if p.is_file() and not p.relative_to(root).as_posix().startswith('hybridclr/generated/')}
def expected_runtime(v):
 data=runtime_manifest(ROOT/'.local/combined-libil2cpp')
 if v=='counterfactual':data[REL]=receipts.sha(ROOT/'.local/exception-flow/Interpreter_Execute.cpp')
 return data
def installed():return PROJECT/'Library/HybridCLR/LocalIl2CppData-WindowsEditor/il2cpp/libil2cpp'
def editor(args,method,b):
 log=folder(args.variant)/('prepare.log' if method.endswith('Prepare') else 'build.log');receipts.fresh_log(log)
 env=dict(os.environ,EH_VARIANT=args.variant,EH_BUILD_ID=b['build_id']);cmd=[str(args.editor),'-batchmode','-nographics','-quit','-projectPath',str(PROJECT),'-executeMethod',method,'-logFile',str(log)]
 p=subprocess.Popen(cmd,env=env,creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
 try:code=p.wait(timeout=1800)
 except subprocess.TimeoutExpired:
  subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL);p.wait();raise RuntimeError('Own Editor process timed out')
 marker=b'EH_PREPARE_OK' if method.endswith('Prepare') else b'EH_BUILD_RESULT Succeeded'
 if code or marker not in log.read_bytes():raise RuntimeError('Editor failed; inspect '+str(log.relative_to(ROOT)))
 print(method,args.variant,'PASS',p.pid,flush=True)
def build(args):
 lock=verify_prepared();parity();v=args.variant
 if not args.editor or not args.editor.is_file():raise ValueError('Pass locked --editor')
 pristine=(ROOT/'.local/combined-libil2cpp'/REL).read_bytes();upstream=(ROOT/'.local/src/runtime'/REL).read_bytes()
 if pristine!=upstream:raise RuntimeError('Combined public runtime differs from fixed upstream')
 fix=ROOT/'.local/exception-flow/Interpreter_Execute.cpp';fix.parent.mkdir(parents=True,exist_ok=True);fix.write_bytes(patched_source(pristine.decode('utf-8')).encode('utf-8'))
 if v=='counterfactual':verify_variant('baseline')
 receipts.ART=folder(v);b=receipts.start_build(lock,receipts.editor_identity(args.editor,lock));b['variant']=v
 editor(args,'ExceptionBuild.Prepare',b);b['source_sha256']=source_manifest();b['runtime_sha256']=runtime_manifest(installed())
 if b['runtime_sha256']!=expected_runtime(v):raise RuntimeError('Installed variant differs')
 generated=installed()/'hybridclr/generated';b['generated_sha256']={p.relative_to(generated).as_posix():receipts.sha(p) for p in generated.rglob('*') if p.is_file()};receipts.write(folder(v)/'build-lock.json',b)
 editor(args,'ExceptionBuild.Build',b)
 if b['source_sha256']!=source_manifest() or b['runtime_sha256']!=runtime_manifest(installed()):raise RuntimeError('Build input changed')
 cpp=PROJECT/'Library/Bee/artifacts/WinPlayerBuildProgram/il2cppOutput/cpp';backup=player(v)/'ExceptionFlowProbe_BackUpThisFolder_ButDontShipItWithYourGame/Managed'
 if (backup/'HotUpdate.dll').exists() or (cpp/'HotUpdate.cpp').exists() or 'HotUpdate' in (cpp/'Il2CppCodeRegistration.cpp').read_text(encoding='utf-8-sig'):raise RuntimeError('Hot code entered AOT')
 dlls=[backup/'Probe.AOT.dll',player(v)/'ExceptionFlowProbe_Data/StreamingAssets/HotUpdate.dll.bytes'];output=subprocess.check_output(['dotnet','run','--project',str(ROOT/'tools/EhMetadata'),'--configuration','Release','--verbosity','quiet','--',*map(str,dlls)],text=True,encoding='utf-8-sig');metadata=json.loads(output)
 if [d['sha256'] for d in metadata]!=[receipts.sha(p) for p in dlls]:raise RuntimeError('Metadata identity')
 b.update(metadata=metadata,hot_update_excluded_from_aot=True,own_dll_sha256=[receipts.sha(p) for p in dlls]);receipts.write(folder(v)/'metadata.json',metadata)
 receipts.finish_build(b,[p for p in player(v).rglob('*') if p.is_file()]+[folder(v)/'metadata.json']);print('EH BUILD',v,b['build_id'],'sources',len(b['source_sha256']),'runtime_files',len(b['runtime_sha256']),flush=True)
def current(v):
 receipts.ART=folder(v);parity();b=receipts.require_build()
 if b['variant']!=v or b['source_sha256']!=source_manifest() or b['runtime_sha256']!=expected_runtime(v):raise RuntimeError('Build inputs/variant changed')
 return b
def run(args):
 v=args.variant;b=current(v);receipts.begin_phase('run',b);rows=[];logs=[]
 for route in ROUTES:
  for fault in FAULTS:
   for n in (1,2,3):
    log=folder(v)/f'{route}-{fault}-{n}.log';receipts.fresh_log(log)
    pid,code=process([player(v)/'ExceptionFlowProbe.exe','-batchmode','-nographics','-logFile',log,'--eh-route',route,'--eh-fault',fault],120)
    if code:raise RuntimeError('Driver failed '+log.name)
    obs=parse_player(log.read_text(encoding='utf-8-sig'),route,fault,v,b['build_id']);rows.append(dict(route=route,fault=fault,run=n,pid=pid,exit_code=code,observations=obs));logs.append(log);print('EH RUN',v,route,fault,n,obs['classification'],[a['finally_count'] for a in obs['attempts']],flush=True)
 path=folder(v)/'run-results.json';receipts.write(path,dict(build_id=b['build_id'],runs=rows));logs.append(path);receipts.finish_phase('run',b,logs)
def quote(s):return '"'+s.replace(chr(92),chr(92)*2).replace('"',chr(92)+'"')+'"'
def context_script(catch_line=12757):
 ty='hybridclr::interpreter::InterpMethodInfo';caller=f'(({ty}*)frame->method->interpData)';nl=chr(92)+'n'
 expr='.printf "EHF_VALUES imi=%p callerImi=%p activeEh=%d callerEh=%d offset=%I64d baseMatchesCaller=%d'+nl+'", @@c++(imi), @@c++(frame->method->interpData), @@c++(imi->exClauseCount), @@c++('+caller+'->exClauseCount), @@c++(ip-ipBase), @@c++(ipBase=='+caller+'->codes); '
 expr+='.printf "EHF_METHOD name=%ma token=%x'+nl+'", @@c++(frame->method->name), @@c++(frame->method->token); '
 expr+='.if (@$t0!=0) {.printf "EHF_CALLEE ready=%d activeMatches=%d'+nl+'", (poi(@$t0+0x58)!=0), (@@c++(imi)==poi(@$t0+0x58))} .else {.printf "EHF_CALLEE ready=0 activeMatches=0'+nl+'"}; '
 for n in range(8):
  expr+='.if (@@c++('+caller+'->exClauseCount)>'+str(n)+') {.printf "EHF_REGION begin=%d end=%d'+nl+'", @@c++('+caller+'->exClauses['+str(n)+'].tryBeginOffset), @@c++('+caller+'->exClauses['+str(n)+'].tryEndOffset)}; '
 expr+='k 5; g'
 target='.if (dwo(poi(@rcx+0x18))==0x676e6950) {.if (by(poi(@rcx+0x18)+4)==0x52) {r @$t0=@rcx}}; g'
 lines=['.lines -e','r @$t0=0','bu GameAssembly!hybridclr::transform::HiTransform::Transform '+quote(target),'bu `GameAssembly!Interpreter_Execute.cpp:'+str(catch_line)+'` '+quote(expr),'sxe -c "lmv m GameAssembly; g" ld:GameAssembly.dll','g']
 return chr(10).join(lines)+chr(10)
def trace(args):
 v=args.variant;b=current(v)
 if not args.cdb or not args.cdb.is_file():raise ValueError('Pass x64 --cdb')
 # Source-level breakpoints are collected before switching this project Library to another variant.
 if runtime_manifest(installed())!=b['runtime_sha256']:raise RuntimeError('Current Library source differs from traced PDB variant')
 lines=(installed()/REL).read_text(encoding='utf-8-sig').splitlines();matches=[i+1 for i,x in enumerate(lines) if x.strip()=='PREPARE_EXCEPTION(ex.ex, 0);']
 if len(matches)!=1:raise RuntimeError('Native catch source anchor ambiguous')
 command=folder(v)/'context.cdb';command.write_text(context_script(matches[0]),encoding='ascii');receipts.begin_phase('trace',b);logs=[command];rows=[]
 for n in (1,2,3):
  log=folder(v)/f'context-{n}.log';plog=folder(v)/f'context-{n}-player.log';receipts.fresh_log(log);receipts.fresh_log(plog)
  pid,code=process([args.cdb,'-G','-y',player(v)/'ExceptionFlowProbe_BackUpThisFolder_ButDontShipItWithYourGame','-logo',log,'-cf',command,player(v)/'ExceptionFlowProbe.exe','-batchmode','-nographics','-logFile',plog,'--eh-route','hh','--eh-fault','cctor-ret'],180)
  if code:raise RuntimeError('Trace driver failed')
  obs=parse_player(plog.read_text(encoding='utf-8-sig'),'hh','cctor-ret',v,b['build_id']);ctx=parse_context(log.read_text(encoding='utf-8-sig',errors='replace'))
  if len(ctx)!=2 or not all(x['inside_caller_region'] for x in ctx):raise RuntimeError('Missing attempt context')
  cases=next(x for x in b['metadata'][1]['types'] if x['name']=='Cases');token=next(x['token'] for x in cases['methods'] if x['name']=='RunOwn')
  if any(x['method_token']!=token for x in ctx):raise RuntimeError('Native caller token differs from final DLL')
  rows.append(dict(run=n,pid=pid,exit_code=code,observations=obs,contexts=ctx));logs += [log,plog];print('EH TRACE',v,n,ctx,flush=True)
 path=folder(v)/'trace-results.json';receipts.write(path,dict(build_id=b['build_id'],runs=rows));logs.append(path);receipts.finish_phase('trace',b,logs)
def verify_variant(v):
 b=current(v);all_rows={}
 for kind in ('run','trace'):
  state=json.loads((folder(v)/f'{kind}-status.json').read_text());record=json.loads((folder(v)/f'{kind}-results.json').read_text())
  if state['status']!='complete' or state['build_id']!=b['build_id'] or record['build_id']!=b['build_id']:raise RuntimeError('Phase identity')
  for p,h in state['log_sha256'].items():
   if receipts.sha(folder(v)/p)!=h:raise RuntimeError('Evidence hash changed '+p)
  rows=record['runs'];all_rows[kind]=rows
  if kind=='run' and [(x['route'],x['fault'],x['run']) for x in rows]!=[(r,f,n) for r in ROUTES for f in FAULTS for n in (1,2,3)]:raise RuntimeError('Incomplete run matrix')
  if kind=='trace' and [x['run'] for x in rows]!=[1,2,3]:raise RuntimeError('Incomplete trace matrix')
  for row in rows:
   route,fault=(row['route'],row['fault']) if kind=='run' else ('hh','cctor-ret');name=f'{route}-{fault}-{row["run"]}.log' if kind=='run' else f'context-{row["run"]}-player.log'
   if row['exit_code']!=0 or parse_player((folder(v)/name).read_text(encoding='utf-8-sig'),route,fault,v,b['build_id'])!=row['observations']:raise RuntimeError('Player reparse changed')
   if kind=='trace' and parse_context((folder(v)/f'context-{row["run"]}.log').read_text(encoding='utf-8-sig',errors='replace'))!=row['contexts']:raise RuntimeError('Native reparse changed')
 return dict(build=b,phases=all_rows,raw_sha256={k:json.loads((folder(v)/f'{k}-status.json').read_text())['log_sha256'] for k in ('run','trace')})
def verify(args):
 data={v:verify_variant(v) for v in VARIANTS};a,b=[data[v]['build'] for v in VARIANTS]
 differences=[p for p,h in a['runtime_sha256'].items() if b['runtime_sha256'].get(p)!=h]
 if differences!=[REL] or a['source_sha256']!=b['source_sha256'] or a['own_dll_sha256']!=b['own_dll_sha256'] or a['generated_sha256']!=b['generated_sha256']:raise RuntimeError('Counterfactual changed more inputs')
 from eh_inline import verify_record
 from eh_results import compare_runs
 outcomes=compare_runs(data['baseline']['phases']['run'],data['counterfactual']['phases']['run'])
 for v,d in data.items():
  for row in d['phases']['trace']:
   for x in row['contexts']:
    if x['mismatch']!=(v=='baseline') or x['active_eh']!=(0 if v=='baseline' else 3) or x['caller_eh']!=3 or not x['inside_caller_region'] or not x['callee_cache_ready']:raise RuntimeError('Counterfactual context did not match the hypothesis')
  d['inline_control']=verify_record(v,d['build'])
 result=dict(schema=1,baseline_commit='46ac71c74cd068bc177d653dd143b7bb9dc482bd',lock=a['lock'],variants=data,comparison=dict(runtime_differences=differences,sources_equal=True,own_dlls_equal=True,generated_runtime_equal=True,outcomes=outcomes),publication='Local candidate; publish source and evidence together, not under the preceding commit.')
 tools=['tools/eh_lab.py','tools/eh_results.py','tools/eh_patch.py','tools/eh_inline.py','tools/EhMetadata/Program.cs','tools/EhMetadata/EhMetadata.csproj','tests/test_eh_results.py','tests/test_eh_patch.py','tests/test_eh_tool.py','tests/test_eh_inline.py','tools/receipts.py','tools/prepare.py','tools/lifetime_lab.py'];result['tool_sha256']={p:receipts.sha(ROOT/p) for p in tools};receipts.write(ART/'verified-results.json',result);print('EH VERIFY',differences,'own DLLs/source/generation equal',flush=True);return result
def export(args):
 result=verify(args);out=ROOT/'evidence/2026-10-26-exception-flow';out.mkdir(parents=True,exist_ok=True)
 keys={'env':'seq kind route fault variant build unity hot_before','attempt':'seq kind value','caller':'seq kind origin','throw':'seq kind origin','init':'seq kind origin','caught':'seq kind origin type detail','finally':'seq kind origin','after':'seq kind origin','return':'seq kind','escape':'seq kind type detail','done':'seq kind completed'}
 for v,data in result['variants'].items():
  for phase,rows in data['phases'].items():
   for row in rows:
    obs=row['observations'];events=[{k:x[k] for k in keys[x['kind']].split()} for x in obs['events']];name=f'{v}-{phase}-'+(row['route']+'-'+row['fault']+'-' if phase=='run' else '')+str(row['run'])+'-events.jsonl';path=out/name;path.write_text(''.join(json.dumps(x,separators=(',',':'))+'\n' for x in events),encoding='utf-8')
    parsed=parse_player(''.join('EHF '+json.dumps(x)+'\n' for x in events),obs['route'],obs['fault'],v,data['build']['build_id']);summary={k:x for k,x in obs.items() if k!='events'}
    if {k:x for k,x in parsed.items() if k!='events'}!=summary:raise RuntimeError('Export semantic change')
    row.update(observations=summary,event_file=name,event_sha256=receipts.sha(path))
 for v,data in result['variants'].items():
  row=data['inline_control'];obs=row['observations'];events=[{k:x[k] for k in keys[x['kind']].split()} for x in obs['events']];name=v+'-inline-control-events.jsonl';path=out/name;path.write_text(''.join(json.dumps(x,separators=(',',':'))+chr(10) for x in events),encoding='utf-8')
  row.update(observations={k:x for k,x in obs.items() if k!='events'},event_file=name,event_sha256=receipts.sha(path))
 result['limits']=['Fixed custom Editor/v9, Windows x64 Debug, single-thread exceptions; no performance/concurrency/other-version claim.','AOT-to-hot uses cached delegates; reflection is setup only, not the measured call.','Counterfactual reorders one public runtime macro only in the new project Library; shared prepared runtime and old experiments remain unchanged.'];receipts.write(out/'results.json',result);print('EH EXPORT',sum(len(x['phases']['run'])+len(x['phases']['trace'])+1 for x in result['variants'].values()),'own event records',flush=True)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['build','run','trace','verify','export']);p.add_argument('--variant',choices=VARIANTS,default='baseline');p.add_argument('--editor',type=Path);p.add_argument('--cdb',type=Path);args=p.parse_args();globals()[args.command](args)
if __name__=='__main__':main()
