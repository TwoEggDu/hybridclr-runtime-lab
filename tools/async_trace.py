"""Focused symbol-only native capture for the locked async Player."""
import argparse,json
from pathlib import Path
import receipts,async_lab
from lifetime_lab import process
from async_results import parse_player
ROOT=async_lab.ROOT;ART=async_lab.ART;PLAYER=async_lab.PLAYER

def quote(s):return '"'+s.replace(chr(92),chr(92)*2).replace('"',chr(92)+'"')+'"'
def script():
 ty='((GameAssembly!MethodInfo*)@rcx)';nl=chr(92)+'n'
 cond=' | '.join('(dwo(poi(@rcx+0x18))=='+x+')' for x in ['0x65766f4d','0x72617453','0x69617741','0x6b726f57','0x006e7552'])
 def action(tag,reg='@rcx'):
  obj='((GameAssembly!MethodInfo*)'+reg+')'
  body='.printf "AUTN '+tag+' method=%p name=%ma token=%x class=%ma ns=%ma image=%ma interp=%p'+nl+'", '+reg+', @@c++('+obj+'->name), @@c++('+obj+'->token), @@c++('+obj+'->klass->name), @@c++('+obj+'->klass->namespaze), @@c++('+obj+'->klass->image->name), @@c++('+obj+'->interpData); k 4; '
  return '.if ('+cond.replace('@rcx',reg)+') {'+body+'}; g'
 lines=['.lines -e']
 for tag,name in [('prepare','hybridclr::interpreter::InterpreterModule::GetInterpMethodInfo'),('transform','hybridclr::transform::HiTransform::Transform'),('execute','hybridclr::interpreter::Interpreter::Execute')]:lines.append('bu GameAssembly!'+name+' '+quote(action(tag)))
 lines.append('bu GameAssembly!hybridclr::transform::TransformContext::TransformSubMethodBody '+quote(action('inline','@rdx')))
 obj='((GameAssembly!hybridclr::metadata::SuperSetAOTHomologousImage*)@rcx)'
 body='.printf "AUTN_BODY image=%p token=%x assembly=%ma'+nl+'", @rcx, @rdx, @@c++('+obj+'->_targetAssembly->image->name); k 3; g'
 lines.append('bu GameAssembly!hybridclr::metadata::SuperSetAOTHomologousImage::GetMethodBody '+quote(body))
 native=[]
 for kind,pattern,reg in [('start','AsyncUniTaskMethodBuilder_1_Start*','@r8'),('await','AsyncUniTaskMethodBuilder_1_AwaitUnsafeOnCompleted*','@r9')]:
  obj='((GameAssembly!MethodInfo*)'+reg+')'
  command='.printf "AUTN_NATIVE kind='+kind+' symbol=%y method=%p token=%x name=%ma class=%ma image=%ma full=%d'+nl+'", @rip, '+reg+', @@c++('+obj+'->token), @@c++('+obj+'->name), @@c++('+obj+'->klass->name), @@c++('+obj+'->klass->image->name), @@c++('+obj+'->has_full_generic_sharing_signature); k 5; g'
  native.append('bm GameAssembly!'+pattern+' '+quote(command))
 lines += ['sxe -c '+quote('lmv m GameAssembly; '+('; '.join(native))+'; g')+' ld:GameAssembly.dll','g']
 return chr(10).join(lines)+chr(10)

def trace(args):
 receipts.ART=ART;b=async_lab.current()
 if not args.cdb or not args.cdb.is_file():raise ValueError('Pass x64 --cdb')
 command=ART/'async.cdb';command.write_text(script(),encoding='ascii');receipts.begin_phase('trace',b);logs=[command];rows=[]
 for side,meta,mode in [('hot-dev','off','frame'),('hot-release','off','frame'),('hot-release','on','frame'),('hot-release','on','throw-after')]:
  for n in (1,2,3):
   stem=f'native-{side}-{meta}-{mode}-{n}';log=ART/(stem+'.log');plog=ART/(stem+'-player.log');receipts.fresh_log(log);receipts.fresh_log(plog)
   pid,code=process([args.cdb,'-G','-y',PLAYER/'AsyncUniTaskProbe_BackUpThisFolder_ButDontShipItWithYourGame','-logo',log,'-cf',command,PLAYER/'AsyncUniTaskProbe.exe','-batchmode','-nographics','-logFile',plog,'--async-side',side,'--async-mode',mode,'--async-metadata',meta],180)
   if code:raise RuntimeError('Native process failed')
   obs=parse_player(plog.read_text(encoding='utf-8-sig'),side,mode,meta,b['build_id']);rows.append(dict(side=side,metadata=meta,mode=mode,run=n,pid=pid,exit_code=code,observations=obs));logs += [log,plog];print('ASYNC NATIVE',side,meta,mode,n,obs['classification'],flush=True)
 path=ART/'trace-results.json';receipts.write(path,dict(build_id=b['build_id'],runs=rows));logs.append(path);receipts.finish_phase('trace',b,logs)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cdb',type=Path,required=True);trace(p.parse_args())
