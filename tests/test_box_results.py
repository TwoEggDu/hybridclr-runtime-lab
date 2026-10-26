import sys,json,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from box_results import parse_player

def fixture(mode="box",route="hot",metadata="off"):
 rows=[]
 def add(kind,**kw):rows.append(dict(seq=len(rows)+1,kind=kind,**kw))
 add("env",route=route,mode=mode,metadata=metadata,build="b",unity="2022.3.62f3",hot_before=False)
 if metadata=="on":add("metadata",label="Probe.AOT",value=0,detail="Superset")
 add("begin",value=10)
 if mode=="box":
  for n in [11,12,13]:add("target",label="Counter.Increment",value=n)
  add("result",a=10,b=12,c=13,flag=True,text="")
 elif mode=="ref":add("target",label="Counter.Increment",value=11);add("result",a=11,b=11,c=0,flag=False,text="")
 elif mode=="text-fallback":add("result",a=10,b=0,c=0,flag=False,text="HotBox.PlainCounter")
 add("done",value=0)
 return rows

def parse(r,mode="box",route="hot",metadata="off"):return parse_player("\n".join("CBX "+json.dumps(x) for x in r),route,mode,metadata,"b")
class BoxResultTests(unittest.TestCase):
 def test_box_copy_and_identity(self):self.assertEqual(parse(fixture())["classification"],"completed")
 def test_ref_original_changed(self):self.assertEqual(parse(fixture("ref"),"ref")["result"]["a"],11)
 def test_fallback_type_name(self):self.assertEqual(parse(fixture("text-fallback"),"text-fallback")["classification"],"completed")
 def test_modified_original_after_box_rejected(self):
  r=fixture();r[-2]["a"]=12
  with self.assertRaises(ValueError):parse(r)
 def test_box_changed_by_unboxed_copy_rejected(self):
  r=fixture();r[-2]["b"]=13
  with self.assertRaises(ValueError):parse(r)
 def test_wrong_identity_rejected(self):
  r=fixture();r[-2]["flag"]=False
  with self.assertRaises(ValueError):parse(r)
 def test_wrong_build_rejected(self):
  r=fixture();r[0]["build"]="old"
  with self.assertRaises(ValueError):parse(r)
 def test_missing_result_rejected(self):
  r=fixture();r.pop(-2)
  for i,x in enumerate(r):x["seq"]=i+1
  with self.assertRaises(ValueError):parse(r)
 def test_missing_implementation_classified_only_cross_off(self):
  r=fixture("value",route="cross");r=r[:2]+[dict(seq=3,kind="error",type="System.MissingMethodException",detail="AOT generic method not instantiated in aot. assembly:Probe.AOT.dll, method:System.Int32 GenericCalls::ByValue<HotBox.Counter>(HotBox.Counter)"),dict(seq=4,kind="done",value=0)]
  self.assertEqual(parse(r,"value","cross")["classification"],"missing_method")
  r[0]["route"]="hot"
  with self.assertRaises(ValueError):parse(r,"value")
 def test_failed_metadata_rejected(self):
  r=fixture(metadata="on");r[1]["value"]=1
  with self.assertRaises(ValueError):parse(r,metadata="on")
class MissingIdentityTests(unittest.TestCase):
 def rows(self,detail):
  r=fixture("value",route="cross")[:2]
  return r+[dict(seq=3,kind="error",type="System.MissingMethodException",detail=detail),dict(seq=4,kind="done",value=0)]
 def test_wrong_assembly_rejected(self):
  detail="AOT generic method not instantiated in aot. assembly:Other.dll, method:System.Int32 GenericCalls::ByValue<HotBox.Counter>(HotBox.Counter)"
  with self.assertRaises(ValueError):parse(self.rows(detail),"value","cross")
 def test_wrong_method_rejected(self):
  detail="AOT generic method not instantiated in aot. assembly:Probe.AOT.dll, method:System.Int32 Dictionary::get_Item(HotBox.Counter)"
  with self.assertRaises(ValueError):parse(self.rows(detail),"value","cross")
 def test_wrong_type_argument_rejected(self):
  detail="AOT generic method not instantiated in aot. assembly:Probe.AOT.dll, method:System.Int32 GenericCalls::ByValue<Other.Counter>(Other.Counter)"
  with self.assertRaises(ValueError):parse(self.rows(detail),"value","cross")
if __name__=="__main__":unittest.main()
