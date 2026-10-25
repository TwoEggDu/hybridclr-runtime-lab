"""Pinned Windows x64 native callback experiment; output is scoped to artifacts/callbacks."""
import argparse,json,os,subprocess,shutil
from pathlib import Path
import receipts,lifetime_lab as shared
from prepare import ROOT,verify_prepared
from lab import assert_log
from callback_results import parse_player,parse_native
ART=ROOT/'artifacts/callbacks';PROJECT=ROOT/'projects/native-callbacks';PLAYER=ART/'Player'

def inputs():
 files=[p for top in ('Assets','Packages','ProjectSettings') for p in (PROJECT/top).rglob('*') if p.is_file() and ((top=='Assets' and p.suffix in ('.cs','.asmdef')) or (top!='Assets' and p.name not in ('EditorBuildSettings.asset','HybridCLRSettings.asset')))]
 files.append(ROOT/'native/native-callbacks/plugin.cpp')
 return {p.relative_to(ROOT).as_posix():receipts.sha(p) for p in sorted(files)}

def current():
 b=receipts.require_build()
 if inputs()!=b['source_sha256']:raise RuntimeError('Source manifest changed')
 return b

def build(args):
 lock=verify_prepared()
 b=receipts.start_build(lock,receipts.editor_identity(args.editor,lock));before=inputs()
 b['source_sha256']=before;receipts.write(ART/'build-lock.json',b)
 out=ART/'plugin';out.mkdir(parents=True,exist_ok=True)
 vswhere=Path(os.environ['ProgramFiles(x86)'])/'Microsoft Visual Studio/Installer/vswhere.exe'
 install=subprocess.check_output([vswhere,'-latest','-products','*','-property','installationPath'],text=True).strip()
 vcvars=Path(install)/'VC/Auxiliary/Build/vcvars64.bat'
 if not vcvars.is_file():raise RuntimeError('MSVC x64 environment missing')
 cmd=out/'build-native.cmd'
 cmd.write_text('@echo off\ncall "'+str(vcvars)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\ncl /nologo /LD /Od /Zi /EHsc /MD /Brepro "'+str(ROOT/'native/native-callbacks/plugin.cpp')+'" /Fo"'+str(out/'NativeProbe.obj')+'" /Fd"'+str(out/'compiler.pdb')+'" /link /OUT:"'+str(out/'NativeProbe.dll')+'" /DEBUG /PDB:"'+str(out/'NativeProbe.pdb')+'" /IMPLIB:"'+str(out/'NativeProbe.lib')+'" >"'+str(out/'compiler.txt')+'" 2>&1\nexit /b %errorlevel%\n',encoding='utf-8')
 _,code=shared.process(['cmd.exe','/d','/c',cmd],180)
 if code:raise RuntimeError('Native compilation failed; see compiler.txt')
 plugin=PROJECT/'Assets/Plugins/x86_64';plugin.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(out/'NativeProbe.dll',plugin/'NativeProbe.dll')
 log=ART/'build.log';receipts.fresh_log(log)
 _,code=shared.process([args.editor,'-batchmode','-nographics','-quit','-projectPath',PROJECT,'-executeMethod','CallbackBuild.PrepareAndBuild','-logFile',log],1800)
 if code:raise RuntimeError('Unity build failed; see callbacks/build.log')
 assert_log(log,['CALLBACK_BUILD_RESULT Succeeded'])
 cpp=PROJECT/'Library/Bee/artifacts/WinPlayerBuildProgram/il2cppOutput/cpp'
 backup=PLAYER/'CallbackProbe_BackUpThisFolder_ButDontShipItWithYourGame'
 if (backup/'Managed/HotUpdate.dll').exists() or (cpp/'HotUpdate.cpp').exists() or 'HotUpdate' in (cpp/'Il2CppCodeRegistration.cpp').read_text(encoding='utf-8-sig'):raise RuntimeError('Hot assembly entered AOT')
 if inputs()!=before:raise RuntimeError('Unity normalized build inputs; review then rebuild')
 b['source_sha256']=before;b['hot_update_excluded_from_aot']=True
 b['compiler_log_sha256']=receipts.sha(out/'compiler.txt')
 compiler=sorted((Path(install)/'VC/Tools/MSVC').glob('*/bin/Hostx64/x64/cl.exe'))[-1]
 b['compiler']=dict(toolset=compiler.parents[3].name,sha256=receipts.sha(compiler))
 receipts.finish_build(b,[p for folder in (PLAYER,out) for p in folder.rglob('*') if p.is_file()])
 print('BUILD PASS',b['build_id'],flush=True)

def run(args):
 b=current();receipts.begin_phase('run',b);logs=[];rows=[]
 for mode in ('registered','raw'):
  for n in range(1,4):
   log=ART/f'{mode}-{n}.log';receipts.fresh_log(log)
   pid,code=shared.process([PLAYER/'CallbackProbe.exe','-batchmode','-nographics','-logFile',log]+(['--raw'] if mode=='raw' else []))
   if code:raise RuntimeError(f'Player exit {code}: {log.name}')
   data=parse_player(log.read_text(encoding='utf-8-sig'),mode)
   rows.append(dict(mode=mode,run=n,pid=pid,exit_code=code,observations=data));logs.append(log)
   print('RUN PASS',mode,n,json.dumps(data),flush=True)
 target=ART/'standalone-results.json';receipts.write(target,dict(build_id=b['build_id'],runs=rows));logs.append(target)
 receipts.finish_phase('run',b,logs)

def trace(args):
 b=current();receipts.begin_phase('trace',b);logs=[]
 for mode in ('registered','raw'):
  native=ART/f'{mode}-trace.log';player=ART/f'{mode}-debug-player.log'
  for log in (native,player):receipts.fresh_log(log)
  symbols=str(PLAYER/'CallbackProbe_BackUpThisFolder_ButDontShipItWithYourGame')+';'+str(ART/'plugin')
  _,code=shared.process([args.cdb,'-G','-y',symbols,'-logo',native,'-cf',ROOT/'debugger/native-callbacks-v9.cdb',PLAYER/'CallbackProbe.exe','-batchmode','-nographics','-logFile',player]+(['--raw'] if mode=='raw' else []),300)
  if code:raise RuntimeError('CDB process failed')
  parse_player(player.read_text(encoding='utf-8-sig'),mode);assert_log(native,['private pdb symbols'])
  logs.extend([native,player])
 receipts.finish_phase('trace',b,logs);print('TRACE CAPTURED: native evidence acceptance pending',flush=True)

def verify(args):
 b=current();receipts.require_evidence()
 runs=json.loads((ART/'standalone-results.json').read_text(encoding='utf-8'))
 if runs['build_id']!=b['build_id'] or [(r['mode'],r['run']) for r in runs['runs']]!=[(mode,n) for mode in ('registered','raw') for n in range(1,4)]:raise RuntimeError('Run matrix mismatch')
 for r in runs['runs']:
  observed=parse_player((ART/f"{r['mode']}-{r['run']}.log").read_text(encoding='utf-8-sig'),r['mode'])
  if r['exit_code']!=0 or observed!=r['observations']:raise RuntimeError('Standalone receipt mismatch')
 debug=[]
 for mode in ('registered','raw'):
  player=parse_player((ART/f'{mode}-debug-player.log').read_text(encoding='utf-8-sig'),mode)
  native=parse_native((ART/f'{mode}-trace.log').read_text(encoding='utf-8-sig'),player)
  debug.append(dict(mode=mode,player=player,native=native))
 result=dict(build_id=b['build_id'],lock=b['lock'],compiler=b['compiler'],source_sha256=b['source_sha256'],standalone=runs['runs'],debug=debug)
 receipts.write(ART/'verified-results.json',result)
 print('VERIFY PASS',json.dumps(debug),flush=True)

def main():
 receipts.ART=ART
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['build','run','trace','verify'])
 parser.add_argument('--editor',type=Path);parser.add_argument('--cdb',type=Path)
 args=parser.parse_args();globals()[args.command](args)
if __name__=='__main__':main()
