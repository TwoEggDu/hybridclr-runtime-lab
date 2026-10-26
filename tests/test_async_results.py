import sys,unittest,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from async_results import parse_player

def fixture(mode="frame",side="hot-dev",meta="on"):
 rows=[]
 def add(kind,frame=1,**kw): rows.append(dict(seq=len(rows)+1,kind=kind,frame=frame,thread=1,**kw))
 add("env",side=side,mode=mode,metadata=meta,build="build",unity="2022.3.62f3",hot_before=False)
 if meta=="on":add("metadata",value=0,label="UniTask",detail="Superset")
 add("enter",label=side)
 if mode!="throw-before":add("before_await")
 if mode in ("frame","throw-after"):
  add("register");add("entry_return",label="Pending");add("consumer_begin");add("waiting",label="Pending")
  for k in ["complete","dispatch_begin","gate_result","gate_resume","nextframe_wait","dispatch_end"]:add(k,3)
  add("resumed",4)
 else:
  if mode=="sync":add("resumed")
 if mode in ("sync","throw-before"):
  add("work_finally");add("entry_return",label="Faulted" if mode=="throw-before" else "Succeeded");add("consumer_begin")
 else:add("work_finally",4)
 add("consumer_caught" if mode.startswith("throw-") else "consumer_result",4 if mode in ("frame","throw-after") else 1,value=42 if not mode.startswith("throw-") else 0,type="System.InvalidOperationException" if mode.startswith("throw-") else "")
 add("consumer_finally",4 if mode in ("frame","throw-after") else 1)
 if mode in ("sync","throw-before"):add("waiting",label="Succeeded")
 add("done",5,value=0)
 return rows

def text(rows):return "\n".join("AUT "+json.dumps(x) for x in rows)
class AsyncResultTests(unittest.TestCase):
 def parse(self,r,mode="frame",meta="on"):return parse_player(text(r),"hot-dev",mode,meta,"build")
 def test_sync_no_registration(self):self.assertEqual(self.parse(fixture("sync"),"sync")["classification"],"result")
 def test_cross_frame(self):self.assertTrue(self.parse(fixture())["suspended"])
 def test_before_exception_no_suspension(self):self.assertEqual(self.parse(fixture("throw-before"),"throw-before")["classification"],"caught")
 def test_after_exception(self):self.assertEqual(self.parse(fixture("throw-after"),"throw-after")["classification"],"caught")
 def test_wrong_build_rejected(self):
  r=fixture();r[0]["build"]="old"
  with self.assertRaises(ValueError):self.parse(r)
 def test_missing_finally_rejected(self):
  r=[x for x in fixture() if x["kind"]!="work_finally"]
  for i,x in enumerate(r):x["seq"]=i+1
  with self.assertRaises(ValueError):self.parse(r)
 def test_same_frame_resume_rejected(self):
  r=fixture();next(x for x in r if x["kind"]=="resumed")["frame"]=3
  with self.assertRaises(ValueError):self.parse(r)
 def test_duplicate_resume_rejected(self):
  r=fixture();r.insert(-2,dict(next(x for x in r if x["kind"]=="resumed")))
  for i,x in enumerate(r):x["seq"]=i+1
  with self.assertRaises(ValueError):self.parse(r)
 def test_metadata_failure_rejected(self):
  r=fixture();next(x for x in r if x["kind"]=="metadata")["value"]=1
  with self.assertRaises(ValueError):self.parse(r)
 def test_thread_change_rejected(self):
  r=fixture();r[-3]["thread"]=2
  with self.assertRaises(ValueError):self.parse(r)
 def test_entry_failure_only_off(self):
  r=fixture();r=[r[0],dict(seq=2,kind="entry_error",frame=1,thread=1,type="System.MissingMethodException"),dict(seq=3,kind="done",frame=2,thread=1,value=0)]
  r[0]["metadata"]="off"
  self.assertEqual(self.parse(r,meta="off")["classification"],"entry_missing_method")
  r[0]["metadata"]="on"
  with self.assertRaises(ValueError):self.parse(r)
if __name__=="__main__":unittest.main()
