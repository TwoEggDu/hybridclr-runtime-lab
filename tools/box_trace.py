"""Fixed Windows x64 symbol inspection of own receiver/boxing and generic paths."""
import argparse,json
from pathlib import Path
import receipts,box_lab
from lifetime_lab import process
from box_results import parse_player
ROOT=box_lab.ROOT;ART=box_lab.ART;PLAYER=box_lab.PLAYER
CELLS=(('aot','off','box'),('hot','off','box'),('hot','off','ref'),('hot','off','text-override'),('hot','off','text-fallback'),('cross','on','ref'),('cross','off','ref'),('cross','on','value'),('cross','off','value'))
def quote(s):return '"'+s.replace(chr(92),chr(92)*2).replace('"',chr(92)+'"')+'"'
def script():
 nl=chr(92)+'n';lines=['.lines -e']
 def method(kind,reg='@rcx',args=None):
  obj='((GameAssembly!MethodInfo*)'+reg+')';image=obj+'->klass->image->name[0]'
  cond='(@@c++('+image+')==0x48) | (@@c++('+image+')==0x50)'
  out='.printf "CBN_METHOD kind='+kind+' method=%p name=%ma token=%x class=%ma ns=%ma image=%ma interp=%p'+nl+'", '+reg+', @@c++('+obj+'->name), @@c++('+obj+'->token), @@c++('+obj+'->klass->name), @@c++('+obj+'->klass->namespaze), @@c++('+obj+'->klass->image->name), @@c++('+obj+'->interpData); '
  if args:
   name=obj+'->name[0]';out+='.if ((@@c++('+name+')==0x49) | (@@c++('+name+')==0x54)) {.printf "CBN_RECEIVER kind='+kind+' this=%p first=%d header16=%d'+nl+'", poi('+args+'), dwo(poi('+args+')), dwo(poi('+args+')+0x10)}; '
  out+='k 8; '
  return '.if ('+cond+') {'+out+'}; g'
 for kind,name in [('prepare','hybridclr::interpreter::InterpreterModule::GetInterpMethodInfo'),('transform','hybridclr::transform::HiTransform::Transform'),('execute','hybridclr::interpreter::Interpreter::Execute')]:lines.append('bu GameAssembly!'+name+' '+quote(method(kind,args='@rdx' if kind=='execute' else None)))
 lines.append('bu GameAssembly!hybridclr::interpreter::InterpFrameGroup::EnterFrameFromInterpreter '+quote(method('frame','@rdx','@r8')))
 lines.append('bu GameAssembly!hybridclr::transform::TransformContext::TransformSubMethodBody '+quote(method('inline','@rdx')))
 cls='((GameAssembly!Il2CppClass*)@rcx)';cond='(@@c++('+cls+'->namespaze[0])==0x48) | (@@c++('+cls+'->namespaze[0])==0x41)'
 ret='.printf "CBN_BOX_RETURN object=%p payload=%p value=%d'+nl+'", @rax, @rax+0x10, dwo(@rax+0x10); g'
 enter='.printf "CBN_BOX name=%ma ns=%ma data=%p value=%d'+nl+'", @@c++('+cls+'->name), @@c++('+cls+'->namespaze), @rdx, dwo(@rdx); bp /1 poi(@rsp) '+quote(ret)+'; k 5; '
 lines.append('bu GameAssembly!il2cpp::vm::Object::Box '+quote('.if ('+cond+') {'+enter+'}; g'))
 image='((GameAssembly!hybridclr::metadata::SuperSetAOTHomologousImage*)@rcx)'
 body='.printf "CBN_BODY image=%p token=%x assembly=%ma'+nl+'", @rcx, @rdx, @@c++('+image+'->_targetAssembly->image->name); k 3; g'
 lines.append('bu GameAssembly!hybridclr::metadata::SuperSetAOTHomologousImage::GetMethodBody '+quote(body))
 native=[]
 for name in ('ByRef','ByValue','Text'):
  method='((GameAssembly!MethodInfo*)@rdx)'
  action='.printf "CBN_NATIVE name='+name+' symbol=%y method=%p token=%x'+nl+'", @rip, @rdx, @@c++('+method+'->token); k 5; g'
  native.append('bm GameAssembly!GenericCalls_'+name+'* '+quote(action))
 load=('; '.join(native))+'; lmv m GameAssembly; .printf "CBN_LAYOUT objectSize=%d'+nl+'", @@c++(sizeof(GameAssembly!Il2CppObject)); dt GameAssembly!Il2CppObject; g'
 lines += ['sxe -c '+quote(load)+' ld:GameAssembly.dll','g'];return chr(10).join(lines)+chr(10)

def trace(args):
 receipts.ART=ART;b=box_lab.current()
 if not args.cdb or not args.cdb.is_file():raise ValueError('Pass x64 --cdb')
 command=ART/'boxing.cdb';command.write_text(script(),encoding='ascii');receipts.begin_phase('trace',b);logs=[command];rows=[]
 for route,meta,mode in CELLS:
  for n in (1,2,3):
   stem='native-'+box_lab.stem(route,meta,mode,n);log=ART/(stem+'.log');plog=ART/(stem+'-player.log');receipts.fresh_log(log);receipts.fresh_log(plog)
   pid,code=process([args.cdb,'-G','-y',PLAYER/'ConstrainedBoxingProbe_BackUpThisFolder_ButDontShipItWithYourGame','-logo',log,'-cf',command,PLAYER/'ConstrainedBoxingProbe.exe','-batchmode','-nographics','-logFile',plog,'--box-route',route,'--box-mode',mode,'--box-metadata',meta],180)
   if code:raise RuntimeError('Native driver failed '+stem)
   obs=parse_player(plog.read_text(encoding='utf-8-sig'),route,mode,meta,b['build_id']);rows.append(dict(route=route,metadata=meta,mode=mode,run=n,pid=pid,exit_code=code,observations=obs));logs += [log,plog];print('BOX NATIVE',route,meta,mode,n,obs['classification'],flush=True)
 path=ART/'trace-results.json';receipts.write(path,dict(build_id=b['build_id'],runs=rows));logs.append(path);receipts.finish_phase('trace',b,logs)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cdb',type=Path,required=True);trace(p.parse_args())
