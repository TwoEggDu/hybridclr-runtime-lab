"""Pinned Windows x64 native callback experiment; output is scoped to artifacts/incremental-barriers."""
import argparse,json,os,subprocess,shutil,re
from pathlib import Path
import receipts,lifetime_lab as shared
from prepare import ROOT,verify_prepared
from lab import assert_log
from incremental_results import parse_player
import incremental_debugger
ART=ROOT/'artifacts/incremental-barriers';PROJECT=ROOT/'projects/incremental-barriers';PLAYER=ART/'Player'

def inputs():
 files=[p for top in ('Assets','Packages','ProjectSettings') for p in (PROJECT/top).rglob('*') if p.is_file() and ((top=='Assets' and p.suffix in ('.cs','.asmdef')) or (top!='Assets' and p.name not in ('EditorBuildSettings.asset','HybridCLRSettings.asset')))]
 files.append(ROOT/'native/incremental-barriers/plugin.cpp')
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
 cmd.write_text('@echo off\ncall "'+str(vcvars)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\ncl /nologo /LD /Od /Zi /EHsc /MD /Brepro "'+str(ROOT/'native/incremental-barriers/plugin.cpp')+'" /Fo"'+str(out/'NativeProbe.obj')+'" /Fd"'+str(out/'compiler.pdb')+'" /link /OUT:"'+str(out/'NativeProbe.dll')+'" /DEBUG /PDB:"'+str(out/'NativeProbe.pdb')+'" /IMPLIB:"'+str(out/'NativeProbe.lib')+'" >"'+str(out/'compiler.txt')+'" 2>&1\nexit /b %errorlevel%\n',encoding='utf-8')
 _,code=shared.process(['cmd.exe','/d','/c',cmd],180)
 if code:raise RuntimeError('Native compilation failed; see compiler.txt')
 plugin=PROJECT/'Assets/Plugins/x86_64';plugin.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(out/'NativeProbe.dll',plugin/'NativeProbe.dll')
 log=ART/'build.log';receipts.fresh_log(log)
 _,code=shared.process([args.editor,'-batchmode','-nographics','-quit','-projectPath',PROJECT,'-executeMethod','GcCallbackBuild.PrepareAndBuild','-logFile',log],1800)
 if code:raise RuntimeError('Unity build failed; see callbacks/build.log')
 assert_log(log,['GCP_BUILD_RESULT Succeeded'])
 cpp=PROJECT/'Library/Bee/artifacts/WinPlayerBuildProgram/il2cppOutput/cpp'
 backup=PLAYER/'GcCallbackProbe_BackUpThisFolder_ButDontShipItWithYourGame'
 if (backup/'Managed/HotUpdate.dll').exists() or (cpp/'HotUpdate.cpp').exists() or 'HotUpdate' in (cpp/'Il2CppCodeRegistration.cpp').read_text(encoding='utf-8-sig'):raise RuntimeError('Hot assembly entered AOT')
 if inputs()!=before:raise RuntimeError('Unity normalized build inputs; review then rebuild')
 b['source_sha256']=before;b['hot_update_excluded_from_aot']=True
 b['compiler_log_sha256']=receipts.sha(out/'compiler.txt')
 compiler=sorted((Path(install)/'VC/Tools/MSVC').glob('*/bin/Hostx64/x64/cl.exe'))[-1]
 b['compiler']=dict(toolset=compiler.parents[3].name,sha256=receipts.sha(compiler))
 receipts.finish_build(b,[p for folder in (PLAYER,out) for p in folder.rglob('*') if p.is_file()])
 print('BUILD PASS',b['build_id'],flush=True)


def probe(args):
 b=current();log=ART/'probe.log';receipts.fresh_log(log)
 pid,code=shared.process([PLAYER/'GcCallbackProbe.exe','-batchmode','-nographics','-logFile',log,'--probe','--heap',str(args.heap),'--budget',str(args.budget)],240)
 print('PROBE EXIT',pid,code,flush=True)
 for line in log.read_text(encoding='utf-8-sig').splitlines():
  if line.startswith(('WBI_ENV','WBI_BEGIN','WBI_SLICE','WBI_END','WBI_GRAPH','WBI_DONE')):print(line,flush=True)
 if code:raise RuntimeError('Probe process failed; preserve log and diagnose')
def run(args):
 b=current();receipts.begin_phase('run',b);rows=[];logs=[]
 for mode in ('aot','hot'):
  for n in range(1,4):
   log=ART/f'{mode}-{n}.log';receipts.fresh_log(log)
   pid,code=shared.process([PLAYER/'GcCallbackProbe.exe','-batchmode','-nographics','-logFile',log]+(['--hot'] if mode=='hot' else []),240)
   if code:raise RuntimeError(f'Player exit {code}: {log}')
   data=parse_player(log.read_text(encoding='utf-8-sig'),mode)
   rows.append(dict(mode=mode,run=n,pid=pid,exit_code=code,observations=data));logs.append(log)
   print('RUN PASS',mode,n,'drain',data['drain_calls'],flush=True)
 target=ART/'run-results.json';receipts.write(target,dict(build_id=b['build_id'],runs=rows));logs.append(target);receipts.finish_phase('run',b,logs)

def trace(args):
 b=current();receipts.begin_phase('trace',b);rows=[];logs=[]
 script=ROOT/'debugger/incremental-barriers-v9.cdb'
 if script.read_text()!=incremental_debugger.script():raise ValueError('Debugger generation mismatch')
 for mode in ('aot','hot'):
  for n in range(1,4):
   native=ART/f'{mode}-trace-{n}.log';player=ART/f'{mode}-debug-player-{n}.log'
   for log in (native,player):receipts.fresh_log(log)
   symbols=str(PLAYER/'GcCallbackProbe_BackUpThisFolder_ButDontShipItWithYourGame')+';'+str(ART/'plugin')
   pid,code=shared.process([args.cdb,'-G','-y',symbols,'-logo',native,'-cf',script,PLAYER/'GcCallbackProbe.exe','-batchmode','-nographics','-logFile',player]+(['--hot'] if mode=='hot' else []),300)
   if code:raise RuntimeError(f'CDB exit {code}: {native}')
   observed=parse_player(player.read_text(encoding='utf-8-sig'),mode)
   from incremental_results import parse_trace
   data=parse_trace(native.read_text(encoding='utf-8-sig'),mode)
   rows.append(dict(mode=mode,run=n,pid=pid,exit_code=code,player=observed,native=data));logs.extend([native,player])
   print('TRACE PASS',mode,n,flush=True)
 target=ART/'trace-results.json';receipts.write(target,dict(build_id=b['build_id'],runs=rows));logs.append(target);receipts.finish_phase('trace',b,logs)

def metadata(b):
 files=[PLAYER/'GcCallbackProbe_Data/StreamingAssets/HotUpdate.dll.bytes',PLAYER/'GcCallbackProbe_BackUpThisFolder_ButDontShipItWithYourGame/Managed/Probe.AOT.dll']
 result=subprocess.run(['dotnet','build',ROOT/'tools/BarrierMetadata/BarrierMetadata.csproj','-v','quiet'],capture_output=True,encoding='utf-8',check=True)
 result=subprocess.run(['dotnet',ROOT/'tools/BarrierMetadata/bin/Debug/net10.0/BarrierMetadata.dll']+files,capture_output=True,encoding='utf-8',check=True)
 text=result.stdout
 for file in files:
  if receipts.sha(file).upper() not in text:raise ValueError('Metadata DLL mismatch')
 methods=text.split('METHOD ')[1:]
 if len(methods)!=2:raise ValueError('Write method matrix')
 instructions=[]
 for method in methods:
  instructions.append([re.sub(r'0x[0-9A-F]{8} ','',line.split(': ',1)[1]) for line in method.splitlines() if line.startswith(' IL_')])
 normalized=[[line.replace('ldstr string:Candidate lost before hot write','ldstr string:Candidate lost before write') for line in method] for method in instructions]
 if normalized[0]!=normalized[1]:raise ValueError('AOT/hot CIL parity changed')
 for opcode in ('stfld Field','stelem.ref','stfld Pair','stelem WbPair'):
  if not any(opcode in line for line in instructions[0]):raise ValueError('Missing CIL path '+opcode)
 path=ART/'cil.txt';path.write_text(text)
 return dict(log_sha256=receipts.sha(path),input_sha256={p.relative_to(ART).as_posix():receipts.sha(p) for p in files},identical_write_instructions_except_diagnostic_literal=True,diagnostic_literal_difference=['Candidate lost before hot write','Candidate lost before write'])

def verify(args):
 b=current();receipts.require_evidence()
 from incremental_results import parse_trace
 runs=json.loads((ART/'run-results.json').read_text());traces=json.loads((ART/'trace-results.json').read_text());expected=[(m,n) for m in ('aot','hot') for n in range(1,4)]
 for rows in (runs,traces):
  if rows['build_id']!=b['build_id'] or [(r['mode'],r['run']) for r in rows['runs']]!=expected:raise ValueError('Run matrix/build mismatch')
 for row in runs['runs']:
  if row['exit_code']!=0 or row['observations']!=parse_player((ART/f"{row['mode']}-{row['run']}.log").read_text(encoding='utf-8-sig'),row['mode']):raise ValueError('Run result changed')
 for row in traces['runs']:
  if row['exit_code']!=0 or row['player']!=parse_player((ART/f"{row['mode']}-debug-player-{row['run']}.log").read_text(encoding='utf-8-sig'),row['mode']) or row['native']!=parse_trace((ART/f"{row['mode']}-trace-{row['run']}.log").read_text(encoding='utf-8-sig'),row['mode']):raise ValueError('Trace result changed')
 cil=metadata(b)
 files=['tools/incremental_lab.py','tools/incremental_results.py','tools/incremental_debugger.py','debugger/incremental-barriers-v9.cdb','tools/BarrierMetadata/Program.cs','tools/BarrierMetadata/BarrierMetadata.csproj','tests/test_incremental_results.py','tools/receipts.py','tools/lifetime_lab.py','tools/prepare.py','tools/lab.py']
 verifier={rel:receipts.sha(ROOT/rel) for rel in files}
 receipts.write(ART/'verified-results.json',dict(build_id=b['build_id'],lock=b['lock'],source_sha256=b['source_sha256'],artifact_sha256=b['artifact_sha256'],verifier_sha256=verifier,cil=cil,run=runs,trace=traces))
 print('INCREMENTAL VERIFY PASS',b['build_id'],flush=True)

def main():
 receipts.ART=ART
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['build','probe','run','trace','verify']);p.add_argument('--editor',type=Path);p.add_argument('--cdb',type=Path);p.add_argument('--heap',type=int,default=250000);p.add_argument('--budget',type=int,default=1000)
 args=p.parse_args();globals()[args.command](args)
if __name__=='__main__':main()
