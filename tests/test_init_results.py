import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from init_results import parse_player
def fixture(mode='strict',side='hot'):
 r=[]
 def add(kind,**kw):r.append(dict(kind=kind,**kw))
 add('env',side=side,mode=mode,build='build',unity='2022.3.62f3',hot_before=False)
 for p in ['before_load','after_load','after_resolve']:add('stage',phase=p)
 add('meta',subject={'strict':'Strict','relaxed':'Relaxed','generic':'Cache`1','failed':'Failed'}[mode],bfi=mode=='relaxed',cctor=True)
 if mode in ('strict','relaxed'):
  add('stage',phase='before_call1')
  if mode=='strict':add('init',subject='Strict.field',value=41);add('init',subject='Strict.cctor',value=41)
  add('method',subject='Ping',value=7);add('read',subject='call1',value=7);add('stage',phase='before_field')
  if mode=='relaxed':add('init',subject='Relaxed.field',value=41)
  add('read',subject='field',value=41);add('stage',phase='before_call2');add('method',subject='Ping',value=7);add('read',subject='call2',value=7)
 elif mode=='generic':
  for name,value in [('int1',42),('string1',82),('int2',43),('string2',83)]:
   add('stage',phase='before_'+name)
   if name.endswith('1'):
    t='System.Int32' if name=='int1' else 'System.String';v=value-1
    add('init',subject='Cache<'+t+'>.field',value=v);add('init',subject='Cache<'+t+'>.cctor',value=v)
   add('method',subject='Next',value=value);add('read',subject=name,value=value)
 else:
  for n in [1,2]:
   add('stage',phase='before_call'+str(n))
   if n==1:add('init',subject='Failed.cctor',value=1)
   add('caught',subject='call'+str(n),type='System.TypeInitializationException',detail='System.TypeInitializationException>System.InvalidOperationException',value=0)
 add('done',completed=True)
 return [dict(seq=i+1,**v) for i,v in enumerate(r)]
def encode(r):return '\n'.join('TIP '+json.dumps(v) for v in r)
class ParserTests(unittest.TestCase):
 def check(self,r,mode='strict',side='hot'):return parse_player(encode(r),side,mode,'build')
 def test_all_cases_both_sides(self):
  for s in ['aot','hot']:
   for m in ['strict','relaxed','generic','failed']:
    with self.subTest(side=s,mode=m):self.assertEqual(self.check(fixture(m,s),m,s)['mode'],m)
 def test_relaxed_early_init_allowed(self):
  r=fixture('relaxed');r.insert(1,r.pop(next(i for i,x in enumerate(r) if x['kind']=='init')))
  for i,x in enumerate(r):x['seq']=i+1
  self.assertEqual(self.check(r,'relaxed')['initializers'][0]['subject'],'Relaxed.field')
 def test_mutations_rejected(self):
  bad=[]
  for k in ['env','meta','stage','done','init','read','method']:
   r=fixture();r.pop(next(i for i,x in enumerate(r) if x['kind']==k));bad.append(r)
  for k,v in [('build','wrong'),('side','aot'),('mode','failed'),('hot_before',True)]:
   r=fixture();r[0][k]=v;bad.append(r)
  r=fixture();r[-1]['completed']=False;bad.append(r)
  r=fixture();r.append(r[-1]);bad.append(r)
  r=fixture();next(x for x in r if x['kind']=='read')['value']=99;bad.append(r)
  r=fixture();next(x for x in r if x['kind']=='meta')['bfi']=True;bad.append(r)
  r=fixture();r[1],r[2]=r[2],r[1];bad.append(r)
  r=fixture();r.insert(-1,dict(kind='init',subject='Strict.cctor',value=41));bad.append(r)
  for i,r in enumerate(bad):
   with self.subTest(n=i),self.assertRaises(ValueError):self.check(r)
 def test_semantic_order(self):
  r=fixture();r.insert(1,r.pop(next(i for i,x in enumerate(r) if x.get('subject')=='Strict.cctor')))
  for i,x in enumerate(r):x['seq']=i+1
  with self.assertRaises(ValueError):self.check(r)
 def test_generic_values(self):
  for sub in ['int1','string1','int2','string2']:
   r=fixture('generic');next(x for x in r if x.get('subject')==sub)['value']=0
   with self.assertRaises(ValueError):self.check(r,'generic')
 def test_failed_no_retry_or_body(self):
  for k in ['init','method']:
   r=fixture('failed');r.insert(-1,dict(kind=k,subject='Failed.cctor' if k=='init' else 'Ping',value=1))
   for i,x in enumerate(r):x['seq']=i+1
   with self.assertRaises(ValueError):self.check(r,'failed')
  r=fixture('failed');next(x for x in r if x['kind']=='caught')['type']='System.Exception'
  with self.assertRaises(ValueError):self.check(r,'failed')
 def test_fatal_or_unknown(self):
  with self.assertRaises(ValueError):parse_player(encode(fixture())+'\nTIP_FATAL failed','hot','strict','build')
  r=fixture();r.insert(-1,dict(seq=123,kind='invented'))
  with self.assertRaises(ValueError):self.check(r)
class FailureBoundaryTests(unittest.TestCase):
 def test_outer_boundary_captures_both_reflection_failures(self):
  r=fixture('failed');r[0]['mode']='failed-outer'
  for x in r:
   if x['kind']=='caught':x['type']='System.Reflection.TargetInvocationException';x['detail']='System.Reflection.TargetInvocationException>System.TypeInitializationException>System.InvalidOperationException'
  o=parse_player(encode(r),'hot','failed-outer','build');self.assertEqual(len(o['exceptions']),2)
 def test_escaped_inner_boundary_is_observation_not_success(self):
  r=fixture('failed');r=r[:7]+[dict(seq=8,kind='escaped',subject='outer_entry',type='System.Reflection.TargetInvocationException',detail='System.Reflection.TargetInvocationException>System.TypeInitializationException>System.InvalidOperationException'),dict(seq=9,kind='done',completed=False)]
  o=parse_player(encode(r),'hot','failed','build');self.assertEqual(o['classification'],'escaped_first_access');self.assertFalse(o['semantic_match'])
  for mutation in ['missing_init','bad_exception','fake_success','second_attempt']:
   import copy
   v=copy.deepcopy(r)
   if mutation=='missing_init':v.pop(6)
   elif mutation=='bad_exception':v[-2]['detail']='System.Exception'
   elif mutation=='fake_success':v[-1]['completed']=True
   else:v.insert(-2,dict(kind='stage',phase='before_call2'))
   for i,x in enumerate(v):x['seq']=i+1
   with self.assertRaises(ValueError):parse_player(encode(v),'hot','failed','build')
class ReviewTimingTests(unittest.TestCase):
 def test_relaxed_initialization_before_environment_is_allowed(self):
  for side in ['aot','hot']:
   r=fixture('relaxed',side);r.insert(0,r.pop(next(i for i,x in enumerate(r) if x['kind']=='init')))
   for i,x in enumerate(r):x['seq']=i+1
   self.assertEqual(parse_player(encode(r),side,'relaxed','build')['initializers'][0]['after_stage'],'startup')
if __name__=='__main__':unittest.main()
