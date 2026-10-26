import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from concurrent_trace import parse_trace

def fixture():
 s=['private pdb symbols','CIN_METHOD kind=before method=100 name=Read class=Cold ns=HotConcurrent image=HotUpdate.dll interp=0 tid=a']
 s+=['CIN_METHOD kind=prepare method=100 name=Read class=Cold ns=HotConcurrent image=HotUpdate.dll interp=0 tid=a','CIN_METHOD kind=transform method=100 name=Read class=Cold ns=HotConcurrent image=HotUpdate.dll interp=0 tid=a']
 s+=['CIN_METHOD kind=execute method=100 name=Read class=Cold ns=HotConcurrent image=HotUpdate.dll interp=200 tid='+str(t) for t in ('a','b','c','d')]
 s+=['CIN_METHOD kind=after method=100 name=Read class=Cold ns=HotConcurrent image=HotUpdate.dll interp=200 tid=a']
 return '\n'.join(s)
class NativeTests(unittest.TestCase):
 def test_cold(self):self.assertEqual(parse_trace(fixture(),'hot','cold',4)['targets'][0]['observed_transform_hits'],1)
 def test_reject_warm_missing_duplicate_and_different_cache(self):
  s=fixture()
  bad=[s.replace('kind=before method=100 name=Read class=Cold ns=HotConcurrent image=HotUpdate.dll interp=0 tid=a','kind=before method=100 name=Read class=Cold ns=HotConcurrent image=HotUpdate.dll interp=200 tid=a'),s.replace('kind=transform','kind=unexpected'),s.replace('kind=after method=100 name=Read class=Cold ns=HotConcurrent image=HotUpdate.dll interp=200 tid=a','kind=after method=100 name=Read class=Cold ns=HotConcurrent image=HotUpdate.dll interp=300'),s.replace('private pdb symbols','export symbols'),s.replace('class=Cold ns=HotConcurrent','class=Wrong ns=HotConcurrent')]
  for b in bad:
   with self.subTest(b=b[-80:]),self.assertRaises(ValueError):parse_trace(b,'hot','cold',4)
 def test_repeated_transform_hit_is_not_conversion_count(self):
  r=parse_trace(fixture()+"\n"+fixture().splitlines()[3],"hot","cold",4)["targets"][0]
  self.assertEqual(r["observed_transform_hits"],2);self.assertFalse(r["conversion_count_conclusive"])
 def test_partial_native_entry_count_is_explicit(self):
  s=fixture();s=s.replace(s.splitlines()[4]+"\n", "",1)
  r=parse_trace(s,"hot","cold",4)["targets"][0]
  self.assertEqual(r["observed_execute_hits"],3);self.assertEqual(r["expected_interpreter_entries"],4);self.assertFalse(r["all_expected_interpreter_threads_observed"])
 def test_repeated_hit_retained_and_unknown_worker_rejected(self):
  from concurrent_trace import check_worker_ids
  x=parse_trace(fixture()+"\n"+fixture().splitlines()[4],"hot","cold",4)
  self.assertEqual(x["targets"][0]["observed_execute_hits"],5)
  self.assertEqual(x["targets"][0]["observed_worker_threads"],4)
  with self.assertRaises(ValueError):check_worker_ids(x,{"events":[dict(kind="ready",native=10)]})
 def test_aot_wait_evidence_required(self):
  rows=[x.replace('class=Cold ns=HotConcurrent image=HotUpdate.dll','class=Strict ns=AotConcurrent image=Probe.AOT.dll').replace('interp=200','interp=0') for x in fixture().splitlines() if x.startswith('private') or 'kind=before' in x or 'kind=after' in x]
  text='\n'.join(rows)
  with self.assertRaises(ValueError):parse_trace(text,'aot','strict',4)
  text+='\nCIN_CLASS kind=classinit classptr=100 name=Strict ns=AotConcurrent started=1 finished=0 owner=a error=0 tid=b\nCIN_SLEEP tid=b\nGameAssembly!il2cpp::vm::Runtime::ClassInit\n'
  x=parse_trace(text,'aot','strict',4);self.assertEqual(x['classinit_sleep_stacks'],1)
 def test_aot_entry_coverage_is_not_applicable(self):
  rows=[x.replace('class=Cold ns=HotConcurrent image=HotUpdate.dll','class=Strict ns=AotConcurrent image=Probe.AOT.dll').replace('interp=200','interp=0') for x in fixture().splitlines() if x.startswith('private') or 'kind=before' in x or 'kind=after' in x]
  text='\n'.join(rows)+'\nCIN_CLASS kind=classinit classptr=100 name=Strict ns=AotConcurrent started=1 finished=0 owner=a error=0 tid=b\nCIN_SLEEP tid=b\nGameAssembly!il2cpp::vm::Runtime::ClassInit\n'
  t=parse_trace(text,'aot','strict',4)['targets'][0]
  self.assertNotIn('expected_body_events',t);self.assertEqual(t['expected_interpreter_entries'],0)
  self.assertEqual(t['interpreter_entry_coverage'],'not_applicable');self.assertIsNone(t['all_expected_interpreter_threads_observed'])
 def test_reject_debugger_errors(self):
  for error in ('Syntax error','Unable to resolve','Symbol not found'):
   with self.assertRaises(ValueError):parse_trace(fixture()+'\n'+error,'hot','cold',4)
if __name__=='__main__':unittest.main()
