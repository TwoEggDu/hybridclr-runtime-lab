import unittest,tempfile,subprocess,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class AsyncMetadataTests(unittest.TestCase):
 def test_fields_and_references_materialized_before_reader_disposal(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);(p/"Case.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework></PropertyGroup></Project>')
   (p/"Case.cs").write_text('namespace AotAsync { public static class Cases { public static async System.Threading.Tasks.Task<int> Work() { await System.Threading.Tasks.Task.Yield(); return 42; } } }')
   subprocess.run(["dotnet","build",str(p/"Case.csproj"),"-c","Release","-v","quiet"],check=True,stdout=subprocess.PIPE)
   out=subprocess.run(["dotnet","run","--project",str(ROOT/"tools/AsyncMetadata"),"-c","Release","-v","quiet","--",str(p/"bin/Release/net10.0/Case.dll")],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
   self.assertEqual(out.returncode,0,out.stderr.decode(errors="replace")[:1000])
   data=json.loads(out.stdout.decode("utf-8-sig"))[0]
   state=next(t for t in data["types"] if "<Work>" in t["name"])
   self.assertTrue(state["base_type"].endswith("System.ValueType"));self.assertTrue(state["fields"])
   self.assertTrue(any("YieldAwaitable+YieldAwaiter" in f["type"] for f in state["fields"]))
   self.assertTrue(any("Start<" in c["target"] for t in data["types"] for m in t["methods"] for c in m["calls"]))
if __name__=="__main__":unittest.main()
