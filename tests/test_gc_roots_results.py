import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from gc_roots_results import parse_trace,validate_snapshot_matrix
VALID="""GR_ADD tid=12 state=1000
GR_TARGET tid=12 object=9000
GR_ENTRY tid=20 state=1000 out=5000 expected=8000 top=2
GR_RETURN tid=20 state=1000 pair=5000 base=8000 bytes=16 top=2 target=9000
GR_SLOT state=1000 offset=0 value=9000
GR_SLOT state=1000 offset=8 value=0
GR_REMOVE tid=12 state=1000
"""
class RootChecks(unittest.TestCase):
 def test_range_and_target(self):
  x=parse_trace(VALID);self.assertEqual(x['samples'][0]['target_offsets'],[0]);self.assertEqual(x['removed'],['1000'])
 def test_missing_return(self):
  with self.assertRaises(ValueError):parse_trace(VALID.replace('GR_RETURN tid=20 state=1000 pair=5000 base=8000 bytes=16 top=2 target=9000\n',''))
 def test_wrong_range(self):
  with self.assertRaises(ValueError):parse_trace(VALID.replace('bytes=16','bytes=24'))
 def test_wrong_base(self):
  with self.assertRaises(ValueError):parse_trace(VALID.replace('base=8000','base=7000'))
 def test_wrong_pair(self):
  with self.assertRaises(ValueError):parse_trace(VALID.replace('pair=5000','pair=6000'))
 def test_missing_slot(self):
  with self.assertRaises(ValueError):parse_trace(VALID.replace('GR_SLOT state=1000 offset=8 value=0\n',''))
 def test_out_of_range(self):
  with self.assertRaises(ValueError):parse_trace(VALID.replace('offset=8','offset=16'))
 def test_remove_wrong_owner(self):
  with self.assertRaises(ValueError):parse_trace(VALID.replace('GR_REMOVE tid=12','GR_REMOVE tid=ff'))
 def test_after_removal(self):
  with self.assertRaises(ValueError):parse_trace(VALID.replace('GR_REMOVE tid=12 state=1000\n','').replace('GR_TARGET','GR_REMOVE tid=12 state=1000\nGR_TARGET'))
 def test_empty_interval(self):
  text=VALID.replace('top=2','top=0').replace('base=8000 bytes=16','base=0 bytes=0')
  text='\n'.join(l for l in text.splitlines() if not l.startswith('GR_SLOT'))
  self.assertEqual(parse_trace(text)['samples'][0]['bytes'],0)
class MatrixChecks(unittest.TestCase):
 def matrix(self):
  import copy
  summary=dict(format_version=[16],capture_flags=[1],vm_info=[[8,16,32,16,24,16]],unknown_handle_targets=0,hot_handle_targets=[dict(type='GcHot.Context',address=9000,context=dict(tag=73,head=0,slots_type='GcHot.Node[]',slots_length=64,nonnull_slots=0))])
  result={s:dict(summary=copy.deepcopy(summary)) for s in ('before-native','active','joined-held','released')}
  result['released']['summary']['hot_handle_targets']=[]
  return result
 def test_valid(self):self.assertEqual(validate_snapshot_matrix('handle',self.matrix()),9000)
 def test_missing_stage(self):
  x=self.matrix();del x['active']
  with self.assertRaises(ValueError):validate_snapshot_matrix('handle',x)
 def test_wrong_identity(self):
  x=self.matrix();x['active']['summary']['hot_handle_targets'][0]['address']=9001
  with self.assertRaises(ValueError):validate_snapshot_matrix('handle',x)
 def test_wrong_graph(self):
  x=self.matrix();x['active']['summary']['hot_handle_targets'][0]['context']['slots_length']=63
  with self.assertRaises(ValueError):validate_snapshot_matrix('handle',x)
 def test_unresolved_target(self):
  x=self.matrix();x['active']['summary']['unknown_handle_targets']=1
  with self.assertRaises(ValueError):validate_snapshot_matrix('handle',x)
 def test_handle_survived_release(self):
  x=self.matrix();x['released']=x['active']
  with self.assertRaises(ValueError):validate_snapshot_matrix('handle',x)
 def test_stack_has_no_strong_target(self):
  x=self.matrix();del x['joined-held']
  with self.assertRaises(ValueError):validate_snapshot_matrix('stack',x)
if __name__=='__main__':unittest.main()
