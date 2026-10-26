import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from concurrent_results import parse_player

def fixture(mode='strict',side='hot',n=2):
 rows=[]
 def add(kind,**kw):rows.append(dict(kind=kind,**kw))
 subjects=['AotConcurrent.Strict'] if side=='mixed' else [('HotConcurrent' if side=='hot' else 'AotConcurrent')+'.'+x for x in ({'cold':['Cold'],'strict':['Strict'],'failed':['Failed'],'generic':['Cache<System.Int32>','Cache<System.String>']}[mode])]
 add('env',side=side,mode=mode,nworkers=n,build='build',unity='2022.3.62f3',hot_before=False,managed=1,native=1)
 for s in subjects:add('meta',subject=s,bfi=mode=='cold',cctor=mode!='cold')
 for w in range(n):add('ready',worker=w,managed=w+10,native=w+100)
 add('gate',phase='open')
 for w in range(n):add('attempt',worker=w,managed=w+10,native=w+100)
 for s in subjects:
  if mode!='cold':add('init_begin',subject=s,managed=10,native=100)
  if mode not in ('cold','failed'):add('init_end',subject=s,managed=10,native=100)
  for w in range(n):
   if mode!='failed':add('body',subject=s,managed=w+10,native=w+100,value=7 if mode=='cold' else 81123 if 'String' in s else 41083)
   add('caught' if mode=='failed' else 'result',subject=s,worker=w,managed=w+10,native=w+100,value=0 if mode=='failed' else 7 if mode=='cold' else 81123 if 'String' in s else 41083,detail=('System.Reflection.TargetInvocationException>System.TypeInitializationException>System.InvalidOperationException' if mode=='failed' else ''),message='concurrent-init-failed:'+s if mode=='failed' else '')
 for w in range(n):add('join',worker=w,joined=True)
 if mode=='failed':
  for w in (n,n+1):add('caught',subject=subjects[0],worker=w,managed=1,native=1,detail='System.Reflection.TargetInvocationException>System.TypeInitializationException>System.InvalidOperationException',message='concurrent-init-failed:'+subjects[0])
 add('done',completed=True)
 return [dict(seq=i+1,**x) for i,x in enumerate(rows)]
def encode(r):return '\n'.join('CIP '+json.dumps(x) for x in r)
class ConcurrentTests(unittest.TestCase):
 def check(self,r,mode='strict',side='hot',n=2):return parse_player(encode(r),side,mode,n,'build')
 def test_matrix(self):
  for s in ('aot','hot'):
   for m in ('cold','strict','failed','generic'):
    for n in (2,4):self.check(fixture(m,s,n),m,s,n)
  self.check(fixture('strict','mixed'),side='mixed')
 def test_missing_or_duplicate_events(self):
  for kind in ('env','meta','ready','gate','attempt','init_begin','init_end','body','result','join','done'):
   for duplicate in (False,True):
    r=fixture();i=next(i for i,x in enumerate(r) if x['kind']==kind)
    if duplicate:r.insert(i,copy.deepcopy(r[i]))
    else:r.pop(i)
    for j,x in enumerate(r):x['seq']=j+1
    with self.subTest(kind=kind,dup=duplicate),self.assertRaises(ValueError):self.check(r)
 def test_bad_identity(self):
  for kind,key,value in [('env','build','stale'),('env','hot_before',True),('meta','cctor',False),('ready','managed',11),('attempt','native',101),('body','value',0),('result','subject','Wrong.Strict'),('join','joined',False),('done','completed',False)]:
   r=fixture();next(x for x in r if x['kind']==kind)[key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):self.check(r)
 def test_partial_publication(self):
  r=fixture();next(x for x in r if x['kind']=='result')['value']=41000
  with self.assertRaises(ValueError):self.check(r)
 def test_body_before_end(self):
  r=fixture();a=next(i for i,x in enumerate(r) if x['kind']=='init_end');b=next(i for i,x in enumerate(r) if x['kind']=='body');r[a],r[b]=r[b],r[a]
  for i,x in enumerate(r):x['seq']=i+1
  with self.assertRaises(ValueError):self.check(r)
 def test_early_attempt(self):
  r=fixture();a=next(i for i,x in enumerate(r) if x['kind']=='gate');b=a+1;r[a],r[b]=r[b],r[a]
  for i,x in enumerate(r):x['seq']=i+1
  with self.assertRaises(ValueError):self.check(r)
 def test_failed_exact_cause_and_count(self):
  for key,val in [('detail','System.Reflection.TargetInvocationException>System.InvalidOperationException'),('message','concurrent-init-failed:Wrong')]:
   r=fixture('failed');next(x for x in r if x['kind']=='caught')[key]=val
   with self.assertRaises(ValueError):self.check(r,'failed')
  r=fixture('failed');r.insert(-1,dict(seq=len(r),kind='init_begin',subject='HotConcurrent.Failed',managed=10,native=100));r[-1]['seq']+=1
  with self.assertRaises(ValueError):self.check(r,'failed')
 def test_generic_isolation(self):
  r=fixture('generic');next(x for x in r if x['kind']=='result' and 'String' in x['subject'])['value']=41083
  with self.assertRaises(ValueError):self.check(r,'generic')
 def test_retry_requires_all_joins_and_main_thread_in_order(self):
  cases=[]
  r=fixture('failed');i=next(i for i,x in enumerate(r) if x['kind']=='caught' and x['worker']==2);r.insert(next(i for i,x in enumerate(r) if x['kind']=='join'),r.pop(i));cases.append(r)
  r=fixture('failed')
  for x in r:
   if x['kind']=='caught' and x['worker']>=2:x['managed']=1000+x['worker'];x['native']=10000+x['worker']
  cases.append(r)
  r=fixture('failed');a=next(i for i,x in enumerate(r) if x['kind']=='caught' and x['worker']==2);r[a],r[a+1]=r[a+1],r[a];cases.append(r)
  for r in cases:
   for i,x in enumerate(r):x['seq']=i+1
   with self.assertRaises(ValueError):self.check(r,'failed')
 def test_workers_cannot_be_the_main_thread(self):
  r=fixture();r[0]['managed']=10;r[0]['native']=100
  with self.assertRaises(ValueError):self.check(r)
 def test_fatal_unknown(self):
  with self.assertRaises(ValueError):parse_player(encode(fixture())+'\nCIP_FATAL fail','hot','strict',2,'build')
  r=fixture();r[-1]['kind']='invented'
  with self.assertRaises(ValueError):self.check(r)
if __name__=='__main__':unittest.main()
