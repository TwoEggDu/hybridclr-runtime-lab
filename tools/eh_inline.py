"""Read-only PDB observation of the short static-call inlining path."""
import re,json,argparse
from pathlib import Path
def parse_inline(text):
 if 'private pdb symbols' not in text or any(x in text for x in ('Syntax error',"Couldn\'t resolve",'Unable to resolve')):raise ValueError('Native inline symbols/error')
 rows=re.findall(r'^EHF_INLINE method=(\w+) sameCaller=([01]) offset=(-?\d+)',text,re.M)
 if len(rows)!=2 or any(n!='RunOwn' or same!='1' or int(off)<0 for n,same,off in rows):raise ValueError('Inline observation identity/count')
 return [dict(method=n,active_matches_caller=True,offset=int(off),opcode='InitClassStaticCtor') for n,_,off in rows]
def verify_record(v,b):
 import eh_lab as lab
 from eh_results import parse_player
 import receipts
 f=lab.folder(v);r=json.loads((f/'inline-control.json').read_text())
 if r['build_id']!=b['build_id'] or r['runtime_source_sha256']!=b['runtime_sha256'][lab.REL] or r['exit_code']!=0:raise RuntimeError('Inline identity')
 for p,h in r['raw_sha256'].items():
  if receipts.sha(f/p)!=h:raise RuntimeError('Inline raw log changed')
 obs=parse_player((f/'inline-player.log').read_text(encoding='utf-8-sig'),'hh','cctor',v,b['build_id']);native=parse_inline((f/'inline-native.log').read_text(encoding='utf-8-sig',errors='replace'))
 if obs!=r['observations'] or native!=r['native']:raise RuntimeError('Inline reparse changed')
 return r
def main():
 import eh_lab as lab
 import receipts
 from eh_results import parse_player
 from eh_patch import patched_source
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cdb',type=Path,required=True);args=p.parse_args()
 for v in ('baseline','counterfactual'):
  b=lab.current(v);f=lab.folder(v);source=(lab.ROOT/'.local/combined-libil2cpp'/lab.REL).read_bytes().decode('utf-8')
  if v=='counterfactual':source=patched_source(source)
  import hashlib
  if hashlib.sha256(source.encode('utf-8')).hexdigest()!=b['runtime_sha256'][lab.REL]:raise RuntimeError('Variant source identity')
  lines=source.splitlines();start=next(i for i,x in enumerate(lines) if 'case HiOpcodeEnum::InitClassStaticCtor:' in x);line=next(i+1 for i in range(start+1,start+8) if 'RuntimeInitClassCCtorWithoutInitClass' in lines[i])
  expr='.printf "EHF_INLINE method=%ma sameCaller=%d offset=%I64d'+chr(92)+'n'+chr(34)+', @@c++(frame->method->name), @@c++(imi==(hybridclr::interpreter::InterpMethodInfo*)frame->method->interpData), @@c++(ip-ipBase); g'
  command=f/'inline.cdb';command.write_text('.lines -e'+chr(10)+'bu `GameAssembly!Interpreter_Execute.cpp:'+str(line)+'` '+lab.quote(expr)+chr(10)+'sxe -c "lmv m GameAssembly; g" ld:GameAssembly.dll'+chr(10)+'g'+chr(10),encoding='ascii')
  log=f/'inline-native.log';plog=f/'inline-player.log';receipts.fresh_log(log);receipts.fresh_log(plog)
  pid,code=lab.process([args.cdb,'-G','-y',lab.player(v)/'ExceptionFlowProbe_BackUpThisFolder_ButDontShipItWithYourGame','-logo',log,'-cf',command,lab.player(v)/'ExceptionFlowProbe.exe','-batchmode','-nographics','-logFile',plog,'--eh-route','hh','--eh-fault','cctor'],180)
  obs=parse_player(plog.read_text(encoding='utf-8-sig'),'hh','cctor',v,b['build_id']);native=parse_inline(log.read_text(encoding='utf-8-sig',errors='replace'))
  if code or obs['classification']!='handled':raise RuntimeError('Inline control failed')
  record=dict(build_id=b['build_id'],runtime_source_sha256=b['runtime_sha256'][lab.REL],source_line=line,pid=pid,exit_code=code,observations=obs,native=native,raw_sha256={p.name:receipts.sha(p) for p in (command,log,plog)});receipts.write(f/'inline-control.json',record);verify_record(v,b);print('INLINE_CONTROL',v,native,flush=True)
if __name__=='__main__':main()
