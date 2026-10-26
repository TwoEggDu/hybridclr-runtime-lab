"""Separate native symbol samples; never counted as ordinary concurrency runs."""
import argparse,json,re
from pathlib import Path
import receipts,concurrent_lab as lab
from lifetime_lab import process
from concurrent_results import parse_player
ART=lab.ART;PLAYER=lab.PLAYER;NAME=lab.NAME
CELLS=[('hot',m,4) for m in ('cold','strict','failed','generic')]+[('aot',m,4) for m in ('strict','failed','generic')]+[('mixed','strict',4)]
def quote(s):return '"'+s.replace(chr(92),chr(92)*2).replace('"',chr(92)+'"')+'"'
def script(capture_wait=False,class_state=False):
 nl=chr(92)+'n';lines=['.lines -e'];hardware=[]
 def method(kind,reg='@rcx'):
  m='((GameAssembly!MethodInfo*)'+reg+')';cond='(@@c++('+m+'->klass->namespaze[0])==0x48) | (@@c++('+m+'->klass->namespaze[0])==0x41)'
  out='.printf "CIN_METHOD kind='+kind+' method=%p name=%ma class=%ma ns=%ma image=%ma interp=%p tid=%x'+nl+'", '+reg+', @@c++('+m+'->name), @@c++('+m+'->klass->name), @@c++('+m+'->klass->namespaze), @@c++('+m+'->klass->image->name), @@c++('+m+'->interpData), @$tid; '
  return '.if ('+cond+') {'+out+'}; g'
 for kind,symbol in ([] if class_state else [('transform','hybridclr::transform::HiTransform::Transform'),('execute','hybridclr::interpreter::Interpreter::Execute')]):hardware.append('ba e1 GameAssembly!'+symbol+' '+quote(method(kind)))
 c='((GameAssembly!Il2CppClass*)@rcx)';cond='(@@c++('+c+'->namespaze[0])==0x48) | (@@c++('+c+'->namespaze[0])==0x41)'
 out='.printf "CIN_CLASS kind=classinit classptr=%p name=%ma ns=%ma started=%d finished=%d owner=%p error=%d tid=%x'+nl+'", @rcx, @@c++('+c+'->name), @@c++('+c+'->namespaze), @@c++('+c+'->cctor_started), @@c++('+c+'->cctor_finished_or_no_cctor), @@c++('+c+'->cctor_thread), @@c++('+c+'->initializationExceptionGCHandle), @$tid; k 5; '
 if class_state:lines.append('bu GameAssembly!il2cpp::vm::Runtime::ClassInit '+quote('.if ('+cond+') {'+out+'}; g'))
 # Sleep(1) stacks can expose ClassInit polling; other Sleep(1) callers are ignored by parser.
 if capture_wait:lines.append('bu GameAssembly!il2cpp::os::Thread::Sleep '+quote('.if (@rcx==1) {.printf "CIN_SLEEP tid=%x'+nl+'", @$tid; k 5;}; g'))
 load='; '.join(hardware)+'; bm GameAssembly!ConcurrentHub_BeforeRelease* '+quote(method('before'))+'; bm GameAssembly!ConcurrentHub_AfterJoin* '+quote(method('after'))+'; lmv m GameAssembly; g'
 lines+=['sxe -c '+quote(load)+' ld:GameAssembly.dll','g'];return '\n'.join(lines)+'\n'
def rows(text,prefix):
 return [dict(re.findall(r'(\w+)=([^\s]+)',line[len(prefix):])) for line in text.splitlines() if line.startswith(prefix)]
def pointer(x):return int(x.replace('`',''),16)
def parse_trace(text,side,mode,n):
 def need(x,msg):
  if not x:raise ValueError(msg)
 need('private pdb symbols' in text,'private PDB absent')
 need(not any(x.lower() in text.lower() for x in ('syntax error','unable to resolve','symbol not found')),'debugger error')
 methods=[r for r in rows(text,'CIN_METHOD ') if r.get('ns') in ('AotConcurrent','HotConcurrent')]
 need(all(set(r)=={'kind','method','name','class','ns','image','interp','tid'} and r['kind'] in ('before','after','prepare','transform','execute') for r in methods),'native event')
 before=[r for r in methods if r['kind']=='before'];after=[r for r in methods if r['kind']=='after'];need(len(before)==(2 if mode=='generic' or side=='mixed' else 1),'before count')
 need(len(after)==len(before) and len({r['method'] for r in before})==len(before),'target method identities')
 expected_class={'cold':'Cold','strict':'Strict','failed':'Failed','generic':'Cache`1'}[mode]
 want=[('HotConcurrent' if side=='hot' else 'AotConcurrent',expected_class)]*(2 if mode=='generic' else 1)
 if side=='mixed':want.append(('HotConcurrent','Bridge'))
 need(sorted((r['ns'],r['class']) for r in before)==sorted(want) and all(r['name']=='Read' for r in before),'target class/method')
 targets=[]
 for b in before:
  same=[r for r in methods if r['method']==b['method']];a=[r for r in after if r['method']==b['method']]
  need(len(a)==1 and all((x['name'],x['class'],x['ns'],x['image'])==(b['name'],b['class'],b['ns'],b['image']) for x in same),'method identity changed')
  need(b['image']==('HotUpdate.dll' if b['ns']=='HotConcurrent' else 'Probe.AOT.dll'),'assembly identity')
  need(pointer(b['interp'])==0,'target already warm')
  hot=b['ns']=='HotConcurrent';failure=mode=='failed';expected_exec=0 if not hot or failure else n//2 if side=='mixed' else n
  transforms=[r for r in same if r['kind']=='transform'];execs=[r for r in same if r['kind']=='execute']
  need((len(transforms)>=1 if expected_exec else len(transforms)==0) and (1<=len({x['tid'] for x in execs})<=expected_exec if expected_exec else len(execs)==0),'target transform/execute count')
  cache=pointer(a[0]['interp']);need((cache!=0)==(expected_exec>0),'final target cache')
  need(all(pointer(x['interp'])==cache and cache!=0 for x in execs),'cache identity changed')
  need(all(pointer(x['interp'])==0 for x in transforms),'transform on populated cache')
  targets.append(dict(namespace=b['ns'],type=b['class'],method='Read',initial_cache_null=True,final_cache_present=cache!=0,observed_transform_hits=len(transforms),conversion_count_conclusive=False,observed_execute_hits=len(execs),observed_worker_threads=len({x['tid'] for x in execs}),execute_thread_ids=sorted(set(int(x['tid'],16) for x in execs)),expected_interpreter_entries=expected_exec,all_expected_interpreter_threads_observed=(len({x['tid'] for x in execs})==expected_exec if expected_exec else None),interpreter_entry_coverage=('not_applicable' if not expected_exec else 'all_expected_threads' if len({x['tid'] for x in execs})==expected_exec else 'partial'),prepare_probe='not instrumented'))
 cctors=[r for r in methods if r['name']=='.cctor' and r['kind']=='execute']
 need(len(cctors)==(0 if side!='hot' or mode=='cold' else 2 if mode=='generic' else 1),'cctor execute count')
 allowed=set(x['method'] for x in before)
 need(all(x['name'] in ('.cctor','Subject') for x in methods if x['method'] not in allowed),'unexpected own interpreter method')
 classes=[r for r in rows(text,'CIN_CLASS ') if r.get('ns') in ('AotConcurrent','HotConcurrent') and r.get('name') in ('Strict','Failed','Cache`1')]
 contenders=[r for r in classes if r.get('started')=='1' and r.get('finished')=='0' and pointer(r.get('owner','0'))!=0 and pointer(r['owner'])!=int(r['tid'],16)]
 waits=sum('il2cpp::vm::Runtime::ClassInit' in block.split('CIN_',1)[0] for block in text.split('CIN_SLEEP ')[1:])
 if side=='aot':need(len(contenders)>0,'ClassInit contender evidence missing')
 if side=='aot' and mode=='strict':need(waits>0,'ClassInit waiting stack missing')
 return dict(method_entry_breakpoints='separate configurations: hardware Execute/Transform OR software ClassInit/Sleep; software main-thread markers',targets=targets,interpreted_cctors=len(cctors),classinit_entries=len(classes),contender_entries=len(contenders),classinit_sleep_stacks=waits)
def trace(args):
 receipts.ART=ART;b=lab.current()
 if not args.cdb or not args.cdb.is_file():raise ValueError('Pass x64 --cdb')
 receipts.begin_phase('trace',b);logs=[];runs=[]
 for side,mode,n in CELLS:
  stem=f'native-{side}-{mode}-{n}';command=ART/(stem+'.cdb');command.write_text(script(side=='aot' and mode=='strict',side=='aot'),encoding='ascii');logs.append(command);log=ART/(stem+'.log');plog=ART/(stem+'-player.log');receipts.fresh_log(log);receipts.fresh_log(plog)
  pid,code=process([args.cdb,'-G','-y',PLAYER/(NAME+'_BackUpThisFolder_ButDontShipItWithYourGame'),'-logo',log,'-cf',command,*lab.player_args(side,mode,n,plog)],240)
  obs=parse_player(plog.read_text(encoding='utf-8-sig',errors='replace'),side,mode,n,b['build_id']);native=parse_trace(log.read_text(encoding='utf-8-sig',errors='replace'),side,mode,n)
  check_worker_ids(native,obs)
  if code:raise RuntimeError('Native driver exit '+str(code))
  runs.append(dict(prefix='native',side=side,mode=mode,workers=n,pid=pid,exit_code=code,observations=obs,native=native));logs += [log,plog];receipts.write(ART/'trace-progress.json',dict(build_id=b['build_id'],runs=runs));print('CONCURRENT NATIVE',side,mode,n,json.dumps(native),flush=True)
 result=ART/'trace-results.json';receipts.write(result,dict(build_id=b['build_id'],runs=runs));logs.append(result);receipts.finish_phase('trace',b,logs)
def check_worker_ids(native,obs):
 ids={x['native'] for x in obs['events'] if x['kind']=='ready'}
 if any(not set(x['execute_thread_ids'])<=ids for x in native['targets']):raise ValueError('Native target entered on unexpected thread')
def verify_traces(b):
 s=json.loads((ART/'trace-status.json').read_text());d=json.loads((ART/'trace-results.json').read_text())
 if s['status']!='complete' or s['build_id']!=b['build_id'] or d['build_id']!=b['build_id'] or [(x['side'],x['mode'],x['workers']) for x in d['runs']]!=CELLS:raise RuntimeError('Native identity/matrix')
 for rel,h in s['log_sha256'].items():
  if receipts.sha(ART/rel)!=h:raise RuntimeError('Native log changed '+rel)
 for x in d['runs']:
  stem=f"native-{x['side']}-{x['mode']}-{x['workers']}"
  if x['exit_code'] or parse_player((ART/(stem+'-player.log')).read_text(encoding='utf-8-sig',errors='replace'),x['side'],x['mode'],x['workers'],b['build_id'])!=x['observations'] or parse_trace((ART/(stem+'.log')).read_text(encoding='utf-8-sig',errors='replace'),x['side'],x['mode'],x['workers'])!=x['native']:raise RuntimeError('Native reparse changed')
  check_worker_ids(x['native'],x['observations'])
 return dict(runs=d['runs'],raw_log_sha256=s['log_sha256'])
def reparse():
 receipts.ART=ART;b=lab.current()
 status=json.loads((ART/'trace-status.json').read_text());data=json.loads((ART/'trace-results.json').read_text())
 if status['status']!='complete' or status['build_id']!=b['build_id'] or data['build_id']!=b['build_id'] or [(x['side'],x['mode'],x['workers']) for x in data['runs']]!=CELLS:raise RuntimeError('Cannot reparse incomplete evidence')
 for rel,h in status['log_sha256'].items():
  if receipts.sha(ART/rel)!=h:raise RuntimeError('Refuse to refresh altered evidence '+rel)
 for x in data['runs']:
  stem=f"native-{x['side']}-{x['mode']}-{x['workers']}"
  obs=parse_player((ART/(stem+'-player.log')).read_text(encoding='utf-8-sig',errors='replace'),x['side'],x['mode'],x['workers'],b['build_id'])
  if x['exit_code'] or obs!=x['observations']:raise RuntimeError('Player observation changed')
  x['native']=parse_trace((ART/(stem+'.log')).read_text(encoding='utf-8-sig',errors='replace'),x['side'],x['mode'],x['workers']);check_worker_ids(x['native'],obs)
 receipts.write(ART/'trace-results.json',data);receipts.finish_phase('trace',b,[ART/rel for rel in status['log_sha256']]);print('CONCURRENT NATIVE REPARSE',len(data['runs']))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cdb',type=Path);p.add_argument('--reparse',action='store_true');a=p.parse_args();reparse() if a.reparse else trace(a)
