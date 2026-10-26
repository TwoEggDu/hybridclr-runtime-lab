import unittest,subprocess,tempfile,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class BoxMetadataTests(unittest.TestCase):
 def test_actual_constrained_box_unbox_and_ref_signature(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);(p/'Case.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework></PropertyGroup></Project>')
   (p/'Case.cs').write_text('namespace AotBox {public interface I{int Increment();} public struct Counter:I {public int N; public int Increment()=>++N;} public static class Cases {public static int Ref<T>(ref T value)where T:I=>value.Increment();public static Counter Box(Counter value){I boxed=value;boxed.Increment();return (Counter)boxed;}}}')
   subprocess.run(['dotnet','build',str(p/'Case.csproj'),'-c','Release','-v','quiet'],check=True,stdout=subprocess.PIPE)
   run=subprocess.run(['dotnet','run','--project',str(ROOT/'tools/BoxMetadata'),'-c','Release','-v','quiet','--',str(p/'bin/Release/net10.0/Case.dll')],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
   self.assertEqual(run.returncode,0,run.stdout.decode(errors='replace')+run.stderr.decode(errors='replace'))
   row=json.loads(run.stdout.decode('utf-8-sig'))[0];methods=next(t['methods'] for t in row['types'] if t['name']=='AotBox.Cases')
   ref=next(m for m in methods if m['name']=='Ref');box=next(m for m in methods if m['name']=='Box')
   self.assertEqual(ref['signature']['parameters'],['!!0&'])
   self.assertIn('constrained.',[x['opcode'] for x in ref['instructions']]);self.assertIn('box',[x['opcode'] for x in box['instructions']]);self.assertIn('unbox.any',[x['opcode'] for x in box['instructions']])
if __name__=='__main__':unittest.main()
