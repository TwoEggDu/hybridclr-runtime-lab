import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from lifetime_results import parse_gc, parse_threads, parse_native
GC = """LIFE_GC stage=held none=0 static=16 event=16 rounds=3
LIFE_GC stage=static-cleared none=0 static=0 event=16 rounds=3
LIFE_GC stage=all-cleared none=0 static=0 event=0 rounds=3
LIFE_DONE mode=gc failures=0"""
THREADS = """LIFE_MAIN managed=1 native=100
LIFE_WORKER index=0 managed=2 native=101 first=5 second=15 joined=True
LIFE_WORKER index=1 managed=3 native=102 first=5 second=15 joined=True
LIFE_DONE mode=threads failures=0"""
GC="LIFE_ENV mode=gc unity=2022.3.62f3 incremental=True gcMode=Enabled\nLIFE_LOAD bytes=4096 assembly=HotUpdate\n"+GC
THREADS="LIFE_ENV mode=threads unity=2022.3.62f3 incremental=True gcMode=Enabled\nLIFE_LOAD bytes=4096 assembly=HotUpdate\n"+THREADS
class Results(unittest.TestCase):
 def test_environment_required(self):
  for log in (GC.replace("incremental=True","incremental=False"),GC.replace("assembly=HotUpdate","assembly=Other"),GC.split("\n",1)[1]):
   with self.assertRaises(ValueError):parse_gc(log)
 def test_gc_controls_and_observation(self):
  self.assertEqual(parse_gc(GC)["all-cleared"]["static"], 0)
  self.assertEqual(parse_gc(GC.replace("static=0 event=0", "static=1 event=0"))["all-cleared"]["static"], 1)
 def test_missing_or_duplicate_stage(self):
  for log in (GC.replace("stage=held", "stage=other"), GC+"\n"+GC.splitlines()[0]):
   with self.assertRaises(ValueError): parse_gc(log)
 def test_lost_control_rejected(self):
  with self.assertRaises(ValueError): parse_gc(GC.replace("static=16", "static=15"))
 def test_thread_results(self):
  self.assertEqual(len(parse_threads(THREADS)["workers"]), 2)
 def test_bad_thread_identity_and_result(self):
  for log in (THREADS.replace("native=102", "native=101"), THREADS.replace("first=5", "first=6"), THREADS.replace("joined=True", "joined=False")):
   with self.assertRaises(ValueError): parse_threads(log)
def native_fixture():
 lines=["GameAssembly C (private pdb symbols)","LIFE_NATIVE_TRANSFORM tid=65 method=123",' name : 0x456 "Add"']
 for tid,state in [("65","abc"),("66","def")]:
  for args in ["2,3","7,8"]:
   lines += [f"LIFE_NATIVE_EXECUTE tid={tid} method=123 args={args}",' name : 0x456 "Add"'," interpData : 0x00000000`00000789 Void","GameAssembly!hybridclr::interpreter::InterpreterInvoke+0x1bd"]
   if args=="2,3":lines += [f"LIFE_NATIVE_CREATE tid={tid} state={state}",f"LIFE_NATIVE_ROOT_ADD tid={tid} root={state}"]
 for tid,state in [("65","abc"),("66","def")]:lines += [f"LIFE_NATIVE_FREE tid={tid}",f"LIFE_NATIVE_DESTROY tid={tid} state={state}",f"LIFE_NATIVE_ROOT_REMOVE tid={tid} root={state}"]
 return "\n".join(lines)
class NativeResults(unittest.TestCase):
 def test_lifecycle_and_cache(self):
  self.assertEqual(parse_native(native_fixture(),parse_threads(THREADS))["execute_count"],4)
 def test_missing_cleanup_or_cache_drift(self):
  for text in [native_fixture().replace("LIFE_NATIVE_ROOT_REMOVE tid=65", "MISSING tid=65"),native_fixture().replace("00000789", "00000999",1),native_fixture().replace("state=def","state=abc")]:
   with self.assertRaises(ValueError):parse_native(text,parse_threads(THREADS))
 def test_false_command_echo_not_accepted(self):
  with self.assertRaises(ValueError):parse_native('0:000> .printf "'+native_fixture().replace("\n","\\n")+'"',parse_threads(THREADS))
if __name__ == "__main__": unittest.main()
