import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from async_native import parse_native
META={"types":[{"name":"HotAsync.Cases","methods":[{"name":"Work","token":0x06000003}]},{"name":"HotAsync.Cases+<Work>d__0","methods":[{"name":"MoveNext","token":0x06000004}]}]}
def fixture():
 a=["private pdb symbols"]
 for tag,name,token,cl,ptr,cache in [("execute","Work","6000003","Cases","111","0"),("prepare","Work","6000003","Cases","111","0"),("transform","Work","6000003","Cases","111","0"),("prepare","MoveNext","6000004","<Work>d__0","222","0"),("transform","MoveNext","6000004","<Work>d__0","222","0")]+[("execute","MoveNext","6000004","<Work>d__0","222","333")]*3:
  a.append(f"AUTN {tag} method={ptr} name={name} token={token} class={cl} ns=HotAsync image=HotUpdate.dll interp={cache}")
 for k in ["start","await","await"]:
  name="Start" if k=="start" else "AwaitUnsafeOnCompleted"
  a.append(f"AUTN_NATIVE kind={k} symbol=GameAssembly!AsyncUniTaskMethodBuilder_1_{name}_TisIl2CppFullySharedGenericAny_gshared (123) method=456 token=6000be6 name={name} class=AsyncUniTaskMethodBuilder`1 image=UniTask.dll full=0")
 return "\n".join(a)
class AsyncNativeTests(unittest.TestCase):
 def test_shared_native_and_interpreter_resume(self):
  r=parse_native(fixture(),META);self.assertEqual(r["move_next_execute_count"],3);self.assertEqual(r["builder_route"],"native-any")
 def test_missing_resume_rejected(self):
  t=fixture();line=next(l for l in t.splitlines() if l.startswith("AUTN execute") and "MoveNext" in l)
  with self.assertRaises(ValueError):parse_native(t.replace(line+"\n","",1),META)
 def test_wrong_token_rejected(self):
  with self.assertRaises(ValueError):parse_native(fixture().replace("token=6000004","token=6000009"),META)
 def test_no_builder_hit_rejected(self):
  with self.assertRaises(ValueError):parse_native("\n".join(x for x in fixture().splitlines() if not x.startswith("AUTN_NATIVE")),META)
 def test_unexpected_unitask_interpretation_rejected(self):
  extra="\nAUTN transform method=111 name=Start token=6000be6 class=AsyncUniTaskMethodBuilder`1 ns=Cysharp.Threading.Tasks.CompilerServices image=UniTask.dll interp=0"
  with self.assertRaises(ValueError):parse_native(fixture()+extra,META)
 def test_unexpected_supplementary_body_read_rejected(self):
  with self.assertRaises(ValueError):parse_native(fixture()+"\nAUTN_BODY image=111 token=6000be6 assembly=UniTask.dll",META)
 def test_debugger_error_rejected(self):
  with self.assertRaises(ValueError):parse_native(fixture()+"\nSyntax error",META)
if __name__=="__main__":unittest.main()
