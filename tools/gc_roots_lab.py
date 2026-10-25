"""Pinned roots/snapshots experiment; preserves gc-callbacks baseline receipts."""
import argparse,json,re,subprocess
from pathlib import Path
import gc_callback_lab as baseline
import receipts,lifetime_lab as shared
from prepare import ROOT
from lab import assert_log
from gc_callback_results import parse_player
from gc_roots_results import parse_trace,validate_snapshot_matrix
from unity_snapshot import Snapshot
ART=ROOT/'artifacts/gc-roots';PROJECT=ROOT/'projects/gc-roots';PLAYER=ART/'Player'
baseline.ART=ART;baseline.PROJECT=PROJECT;baseline.PLAYER=PLAYER

def current():return baseline.current()
def build(args):return baseline.build(args)
def validate_player(text,mode):
 if mode=='idle':
  assert_log_text=['GCR_IDLE_READY','GCR_IDLE_OBSERVED','full=3','GCR_IDLE_DONE']
  if not all(t in text for t in assert_log_text) or 'Exception:' in text:raise ValueError('Idle control failed')
  return {'idle_alive':re.search(r'GCR_IDLE_OBSERVED alive=(True|False)',text)[1]=='True','released_alive':re.search(r'GCR_IDLE_DONE alive=(True|False)',text)[1]=='True'}
 return parse_player(text,mode)
def run(args):
 b=current();receipts.begin_phase('run',b);logs=[];rows=[]
 for mode in ('handle','stack','idle'):
  for n in range(1,4):
   log=ART/f'{mode}-{n}.log';receipts.fresh_log(log)
   pid,code=shared.process([PLAYER/'GcCallbackProbe.exe','-batchmode','-nographics','-logFile',log]+([] if mode=='handle' else ['--'+mode]),240)
   if code:raise RuntimeError(f'Control exit {code}: {log}')
   row=validate_player(log.read_text(encoding='utf-8-sig'),mode);rows.append(dict(mode=mode,run=n,pid=pid,exit_code=code,observations=row));logs.append(log)
   print('CONTROL PASS',mode,n,flush=True)
 for mode in ('handle','stack'):
  for n in range(1,4):
   folder=ART/'snapshots'/f'{mode}-{n}';folder.mkdir(parents=True,exist_ok=True)
   if list(folder.glob('*.snap')):raise RuntimeError('Existing snapshots; preserve before rerun')
   log=ART/f'{mode}-snapshot-{n}.log';receipts.fresh_log(log)
   pid,code=shared.process([PLAYER/'GcCallbackProbe.exe','-batchmode','-nographics','-logFile',log,'--snapshot-dir',folder]+([] if mode=='handle' else ['--stack']),300)
   if code:raise RuntimeError(f'Snapshot exit {code}: {log}')
   text=log.read_text(encoding='utf-8-sig');row=validate_player(text,mode)
   stages=['before-native','active','joined-held','released'] if mode=='handle' else ['before-native','active','released']
   if {p.stem for p in folder.glob('*.snap')}!=set(stages):raise ValueError('Incomplete snapshot matrix')
   snapshots={}
   for stage in stages:
    if text.count('GCR_SNAPSHOT_END stage='+stage+' ')!=1:raise ValueError('Missing snapshot callback')
    file=folder/(stage+'.snap');snapshots[stage]=dict(sha256=receipts.sha(file),bytes=file.stat().st_size,summary=Snapshot(file).summary());logs.append(file)
   validate_snapshot_matrix(mode,snapshots)
   rows.append(dict(mode=mode,run=n,pid=pid,exit_code=code,observations=row,snapshots=snapshots));logs.append(log)
   print('SNAPSHOT PASS',mode,n,json.dumps({s:v['summary']['hot_handle_targets'] for s,v in snapshots.items()}),flush=True)
 target=ART/'run-results.json';receipts.write(target,dict(build_id=b['build_id'],runs=rows));logs.append(target);receipts.finish_phase('run',b,logs)
def inspect(args):
 b=current();native=ART/'abi-validation.log';player=ART/'abi-player.log'
 script=ART/'abi-validation.cdb'
 script.write_text('sxe -c "x GameAssembly!*GetGCRootData*; lmv m GameAssembly; dt GameAssembly!hybridclr::interpreter::MachineState; uf GameAssembly!hybridclr::interpreter::MachineState::GetGCRootData; .printf \\"GR_LAYOUT slot=%d\\\\n\\", @@c++(sizeof(hybridclr::interpreter::StackObject)); q" ld:GameAssembly.dll\ng\n')
 symbols=PLAYER/'GcCallbackProbe_BackUpThisFolder_ButDontShipItWithYourGame'
 pid,code=shared.process([args.cdb,'-G','-y',symbols,'-logo',native,'-cf',script,PLAYER/'GcCallbackProbe.exe','-batchmode','-nographics','-logFile',player],120)
 raw=native.read_text(encoding='utf-8-sig')
 start=re.search(r'^([0-9a-f`]+) GameAssembly!.*::GetGCRootData \(void \*\)',raw,re.M)
 returns=re.findall(r'^([0-9a-f`]+)\s+c3\s+ret\s*$',raw,re.M)
 layout=re.search(r'^GR_LAYOUT slot=(\d+)',raw,re.M)
 number=lambda x:int(x.replace('`',''),16)
 if not start or len(returns)!=1 or not layout:raise ValueError('Could not validate callback ABI')
 offset=number(returns[0])-number(start[1])
 expected={'_stackBase':'000','_stackSize':'008','_stackTopIdx':'00c','_frameTopIdx':'020'}
 for name,field in expected.items():
  if not re.search(r'\+0x'+field+r'\s+'+name+r'\s+:',raw):raise ValueError('PDB layout changed')
 if offset!=0xa9 or int(layout[1])!=8 or 'private pdb symbols' not in raw:raise ValueError('Debugger script ABI no longer valid')
 receipts.write(ART/'abi-status.json',dict(status='complete',build_id=b['build_id'],pid=pid,debugger_exit_code=code,return_offset=offset,slot_bytes=8,field_offsets={k:int(v,16) for k,v in expected.items()},log_sha256={'abi-validation.log':receipts.sha(native)}))
 print('ABI VALIDATED return_offset='+hex(offset)+' slot=8',flush=True)

def trace(args):
 b=current();abi=json.loads((ART/'abi-status.json').read_text())
 if abi['build_id']!=b['build_id'] or abi['return_offset']!=0xa9:raise ValueError('Inspect current build ABI first')
 receipts.begin_phase('trace',b);logs=[];rows=[]
 for mode in ('handle','stack','idle'):
  for n in range(1,4):
   native=ART/f'{mode}-trace-{n}.log';player=ART/f'{mode}-debug-player-{n}.log'
   for log in (native,player):receipts.fresh_log(log)
   symbols=str(PLAYER/'GcCallbackProbe_BackUpThisFolder_ButDontShipItWithYourGame')+';'+str(ART/'plugin')
   command=[args.cdb,'-G','-y',symbols,'-logo',native,'-cf',ROOT/'debugger/gc-roots-v9.cdb',PLAYER/'GcCallbackProbe.exe','-batchmode','-nographics','-logFile',player]+([] if mode=='handle' else ['--'+mode])
   pid,code=shared.process(command,300)
   if code:raise RuntimeError('CDB exit '+str(code))
   observed=validate_player(player.read_text(encoding='utf-8-sig'),mode)
   raw=native.read_text(encoding='utf-8-sig');assert_log(native,['private pdb symbols'])
   if any(x in raw for x in ('Syntax error','Unable to resolve','Command file execution failed')):raise ValueError('Debugger command failed')
   data=parse_trace(raw)
   active=[s for s in data['samples'] if s['top']>0];empty=[s for s in data['samples'] if s['top']==0]
   if mode=='idle':
    if len(empty)<3 or active:raise ValueError('Idle roots not empty')
   elif len(active)<3 or not all(s['target_offsets'] for s in active):raise ValueError('Active target missing from reported range')
   if 'GC_push' not in raw:raise ValueError('Collector caller stack missing')
   rows.append(dict(mode=mode,run=n,pid=pid,exit_code=code,player=observed,native=data));logs.extend([native,player])
   print('ROOT TRACE PASS',mode,n,'samples',len(data['samples']),'bytes',sorted({s['bytes'] for s in data['samples']}),'offsets',sorted({off for s in data['samples'] for off in s['target_offsets']}),flush=True)
 target=ART/'trace-results.json';receipts.write(target,dict(build_id=b['build_id'],runs=rows));logs.append(target);receipts.finish_phase('trace',b,logs)
def verify(args):
 b=current();receipts.require_evidence()
 import check_snapshots_unity
 check_snapshots_unity.verify()
 abi=json.loads((ART/'abi-status.json').read_text())
 if abi.get('status')!='complete' or abi.get('build_id')!=b['build_id'] or abi.get('return_offset')!=0xa9 or abi.get('slot_bytes')!=8:raise ValueError('ABI receipt mismatch')
 for rel,sha in abi['log_sha256'].items():
  if receipts.sha(ART/rel)!=sha:raise ValueError('ABI log changed')
 official=json.loads((ART/'official-reader-status.json').read_text())
 if official.get('status')!='complete' or official.get('build_id')!=b['build_id'] or official.get('exit_code')!=0:raise ValueError('Official reader status mismatch')
 for rel,sha in official['log_sha256'].items():
  if receipts.sha(ART/rel)!=sha:raise ValueError('Official reader log changed')
 for rel,sha in official['source_sha256'].items():
  if receipts.sha(ROOT/rel)!=sha:raise ValueError('Official reader source changed')
 runs=json.loads((ART/'run-results.json').read_text());traces=json.loads((ART/'trace-results.json').read_text())
 if runs['build_id']!=b['build_id'] or traces['build_id']!=b['build_id']:raise ValueError('Build mismatch')
 expected_controls=[(m,n) for m in ('handle','stack','idle') for n in range(1,4)]
 expected_snapshots=[(m,n) for m in ('handle','stack') for n in range(1,4)]
 if [(r['mode'],r['run']) for r in runs['runs'] if 'snapshots' not in r]!=expected_controls or [(r['mode'],r['run']) for r in runs['runs'] if 'snapshots' in r]!=expected_snapshots or [(r['mode'],r['run']) for r in traces['runs']]!=expected_controls:raise ValueError('Incomplete run matrix')
 for row in runs['runs']:
  suffix=f"{row['mode']}-snapshot-{row['run']}" if 'snapshots' in row else f"{row['mode']}-{row['run']}"
  if row['exit_code']!=0 or validate_player((ART/(suffix+'.log')).read_text(encoding='utf-8-sig'),row['mode'])!=row['observations']:raise ValueError('Run mismatch')
  if 'snapshots' in row:validate_snapshot_matrix(row['mode'],row['snapshots'])
  for stage,snapshot in row.get('snapshots',{}).items():
   p=ART/'snapshots'/f"{row['mode']}-{row['run']}"/(stage+'.snap')
   if Snapshot(p).summary()!=snapshot['summary']:raise ValueError('Snapshot summary mismatch')
 for row in traces['runs']:
  if row['native']!=parse_trace((ART/f"{row['mode']}-trace-{row['run']}.log").read_text(encoding='utf-8-sig')):raise ValueError('Trace mismatch')
 verifier={p.relative_to(ROOT).as_posix():receipts.sha(p) for p in [ROOT/'tools/gc_roots_lab.py',ROOT/'tools/gc_roots_results.py',ROOT/'tools/unity_snapshot.py',ROOT/'debugger/gc-roots-v9.cdb',ROOT/'tests/test_gc_roots_results.py',ROOT/'tests/test_unity_snapshot.py',ROOT/'tools/UnitySnapshotCheck.cs',ROOT/'tools/check_snapshots_unity.py',ROOT/'tools/gc_callback_lab.py',ROOT/'tools/gc_callback_results.py',ROOT/'tools/receipts.py',ROOT/'tools/lifetime_lab.py',ROOT/'tools/prepare.py',ROOT/'tools/lab.py']}
 receipts.write(ART/'verified-results.json',dict(build_id=b['build_id'],lock=b['lock'],source_sha256=b['source_sha256'],artifact_sha256=b['artifact_sha256'],official_reader=official,abi=abi,verifier_sha256=verifier,run=runs,trace=traces))
 print('ROOTS VERIFY PASS',b['build_id'],flush=True)
def main():
 receipts.ART=ART
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['build','run','inspect','trace','verify']);parser.add_argument('--editor',type=Path);parser.add_argument('--cdb',type=Path)
 args=parser.parse_args();globals()[args.command](args)
if __name__=='__main__':main()
