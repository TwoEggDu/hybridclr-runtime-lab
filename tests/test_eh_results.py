import sys,json,unittest,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from eh_results import parse_player,parse_context
def fixture(route='hh',fault='cctor',escape=False):
 rows=[];caller='hot' if route[0]=='h' else 'aot';target='hot' if route[1]=='h' else 'aot'
 def e(kind,**kw):rows.append(dict(kind=kind,**kw))
 e('env',route=route,fault=fault,variant='baseline',build='id',unity='2022.3.62f3',hot_before=False)
 for n in (1,2):
  e('attempt',value=n);e('caller',origin=caller)
  if fault.startswith('cctor'):
   if n==1:e('init',origin=target)
  else:e('throw',origin=target)
  etype='System.InvalidOperationException' if fault=='body' else 'System.TypeInitializationException';detail=etype+('>System.InvalidOperationException' if fault!='body' else '')
  if escape:e('escape',type=etype,detail=detail)
  else:e('caught',origin=caller,type=etype,detail=detail);e('finally',origin=caller);e('after',origin=caller);e('return')
 e('done',completed=True)
 return [dict(seq=i+1,**v) for i,v in enumerate(rows)]
def encode(r):return '\n'.join('EHF '+json.dumps(v) for v in r)
class EHTests(unittest.TestCase):
 def test_all_routes_faults(self):
  for r in ('aa','hh','ha','ah'):
   for f in ('body','manual','cctor'):
    self.assertEqual(parse_player(encode(fixture(r,f)),r,f,'baseline','id')['classification'],'handled')
 def test_escape_record_not_pass(self):
  o=parse_player(encode(fixture(escape=True)),'hh','cctor','baseline','id');self.assertEqual(o['classification'],'escaped');self.assertFalse(o['semantic_match'])
 def test_corruptions(self):
  for kind in ['env','attempt','caller','init','caught','finally','after','return','done']:
   r=fixture();r.pop(next(i for i,x in enumerate(r) if x['kind']==kind))
   for i,x in enumerate(r):x['seq']=i+1
   with self.subTest(kind=kind),self.assertRaises(ValueError):parse_player(encode(r),'hh','cctor','baseline','id')
  for k,v in [('build','wrong'),('route','aa'),('fault','body'),('variant','counterfactual'),('hot_before',True)]:
   r=fixture();r[0][k]=v
   with self.subTest(k=k),self.assertRaises(ValueError):parse_player(encode(r),'hh','cctor','baseline','id')
 def test_duplicate_cctor_or_fake_exception(self):
  for mutation in ('init','exception','target','sequence','done'):
   r=fixture()
   if mutation=='init':r.insert(3,dict(kind='init',origin='hot'))
   elif mutation=='exception':next(x for x in r if x['kind']=='caught')['type']='System.Exception'
   elif mutation=='target':next(x for x in r if x['kind']=='init')['origin']='aot'
   elif mutation=='sequence':r[2],r[3]=r[3],r[2]
   else:r[-1]['completed']=False
   if mutation!='sequence':
    for i,x in enumerate(r):x['seq']=i+1
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):parse_player(encode(r),'hh','cctor','baseline','id')
 def test_mixed_observation_preserved(self):
  a=fixture(escape=True);b=fixture();start=next(i for i,x in enumerate(a) if x['kind']=='attempt' and x['value']==2);start_b=next(i for i,x in enumerate(b) if x['kind']=='attempt' and x['value']==2);a=a[:start]+b[start_b:]
  for i,x in enumerate(a):x['seq']=i+1
  self.assertEqual(parse_player(encode(a),'hh','cctor','baseline','id')['classification'],'mixed')
class NonInlineCaseTests(unittest.TestCase):
 def test_noninlined_initializer_case_is_distinct(self):
  r=fixture(fault='cctor-ret',escape=True)
  o=parse_player(encode(r),'hh','cctor-ret','baseline','id');self.assertEqual(o['cctor_count'],1);self.assertEqual(o['classification'],'escaped')
def context_fixture(mismatch=True):
 return ('private pdb symbols\nEHF_VALUES imi='+('222' if mismatch else '111')+' callerImi=111 activeEh='+('0' if mismatch else '1')+' callerEh=1 offset=88 baseMatchesCaller=1\nEHF_METHOD name=RunOwn token=6000004\nEHF_CALLEE ready=1 activeMatches='+('1' if mismatch else '0')+'\nEHF_REGION begin=88 end=136\n')
class ContextTests(unittest.TestCase):
 def test_mismatch_inside_caller_region(self):
  r=parse_context(context_fixture());self.assertTrue(r[0]['mismatch']);self.assertTrue(r[0]['inside_caller_region'])
 def test_matching_after_patch(self):self.assertFalse(parse_context(context_fixture(False))[0]['mismatch'])
 def test_identity_and_consistency(self):
  for a,b in [('name=RunOwn','name=Other'),('ready=1','ready=0'),('activeMatches=1','activeMatches=0'),('token=6000004','token=2000004')]:
   with self.subTest(a=a),self.assertRaises(ValueError):parse_context(context_fixture().replace(a,b))
  with self.assertRaises(ValueError):parse_context(context_fixture(False).replace('activeEh=1','activeEh=0'))
 def test_bad_context_rejected(self):
  for s in ['','EHF_VALUES imi=222','private pdb symbols\nSyntax error']:
   with self.assertRaises(ValueError):parse_context(s)
class ComparisonTests(unittest.TestCase):
 def rows(self,variant):
  rows=[]
  for route in ['aa','hh','ha','ah']:
   for fault in ['body','manual','cctor','cctor-ret']:
    for n in [1,2,3]:
     escape=variant=='baseline' and route=='hh' and fault=='cctor-ret';r=fixture(route,fault,escape);r[0]['variant']=variant
     rows.append(dict(route=route,fault=fault,run=n,observations=parse_player(encode(r),route,fault,variant,'id')))
  return rows
 def test_controlled_outcome_change(self):
  from eh_results import compare_runs
  self.assertEqual(compare_runs(self.rows('baseline'),self.rows('counterfactual'))['baseline_escaped'],3)
 def test_unaffected_or_unfixed_rejected(self):
  from eh_results import compare_runs
  a,b=self.rows('baseline'),self.rows('counterfactual');b[0]['observations']['classification']='escaped'
  with self.assertRaises(ValueError):compare_runs(a,b)
  a,b=self.rows('baseline'),self.rows('counterfactual');a[0]['observations']['classification']='escaped'
  with self.assertRaises(ValueError):compare_runs(a,b)
if __name__=='__main__':unittest.main()
