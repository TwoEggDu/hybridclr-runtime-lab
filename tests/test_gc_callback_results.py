import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from gc_callback_results import parse_player,parse_native

def fixture(mode):
 n={'handle':2,'stack':1,'stress':1024}[mode]
 checksum={'handle':149,'stack':257,'stress':786944}[mode]
 rows=[f'GCP_ENV mode={mode} unity=2022.3.62f3 incremental=True gcMode=Enabled',f'GCP_LOAD bytes=6144 assembly=HotUpdate pointer=12345 context={0 if mode=="stack" else 32}', 'GCP_MAIN managed=1 native=100']
 if mode!='stack':rows+=['GCP_HELD stage=before alive=True full=3']
 for seq in (range(32,1025,32) if mode=='stress' else [n]):rows+=[f'GCP_CHECK seq={seq} alive=True full={0 if mode=="stress" else 3} slices={4 if mode=="stress" else 0} more=0']
 rows += ['GCP_STOP joinedBefore=False requested=1','GCP_GC before=10 after=13 delta=3',f'GCP_JOIN count={n} checksum={checksum} errors=0 native=101 joined=True']
 if mode!='stack':rows+=['GCP_HELD stage=after alive=True full=3','GCP_HANDLE_FREE afterJoin=True']
 rows += ['GCP_RELEASED alive=False full=3','GCP_DELEGATE_RELEASE afterJoin=True',f'GCP_DONE mode={mode} failures=0']
 return '\n'.join(rows)
class PlayerResults(unittest.TestCase):
 def test_all_modes(self):
  for mode in ['handle','stack','stress']:self.assertEqual(parse_player(fixture(mode),mode)['count'],{'handle':2,'stack':1,'stress':1024}[mode])
 def test_survivor_observation_not_erased(self):
  self.assertTrue(parse_player(fixture('stack').replace('GCP_RELEASED alive=False','GCP_RELEASED alive=True'),'stack')['released_alive'])
 def test_invalid_record_rejected(self):
  text=fixture('stress')
  for wrong in [text.replace('seq=64 ','seq=65 '),text.replace('checksum=786944','checksum=0'),text.replace('errors=0','errors=1'),text.replace('joinedBefore=False','joinedBefore=True'),text.replace('stage=before alive=True','stage=before alive=False'),text.replace('full=0 slices=4','full=3 slices=4',1),text.replace('GCP_HANDLE_FREE afterJoin=True','GCP_HANDLE_FREE afterJoin=False')]:
   with self.assertRaises(ValueError):parse_player(wrong,'stress')
 def test_checkpoint_outside_lifetime_rejected(self):
  text=fixture('stress');first=next(line for line in text.splitlines() if line.startswith('GCP_CHECK'))
  text=first+'\n'+text.replace(first+'\n','',1)
  with self.assertRaises(ValueError):parse_player(text,'stress')
 def test_gc_counter_mismatch_rejected(self):
  with self.assertRaises(ValueError):parse_player(fixture('stress').replace('after=13 delta=3','after=13 delta=4'),'stress')
 def test_explicit_collection_count_floor(self):
  for mode in ['handle','stack']:
   for delta in range(3):
    with self.assertRaises(ValueError):parse_player(fixture(mode).replace('after=13 delta=3',f'after={10+delta} delta={delta}'),mode)
 def test_early_handle_free_rejected(self):
  text=fixture('handle').replace('GCP_HANDLE_FREE afterJoin=True\n','')
  text='GCP_HANDLE_FREE afterJoin=True\n'+text
  with self.assertRaises(ValueError):parse_player(text,'handle')

# Synthetic events only; real Player traces are accepted separately.
def native_fixture(mode):
 rows=['GameAssembly C (private pdb symbols)','NativeProbe C (private pdb symbols)'];tid='65';n=2 if mode=='handle' else 1
 def e(kind,fields='',thread=tid):rows.append(f'GCP_NATIVE_{kind} tid={thread}'+(' '+fields if fields else ''))
 e('PLUGIN','phase=5 seq=0 value=0')
 for seq in range(1,n+1):
  e('PLUGIN',f'phase=1 seq={seq} value=0');e('WRAPPER',f'wrapper=3039 context={"20" if mode=="handle" else "0"} seq={seq} mode={0 if mode=="handle" else 1}')
  e('SCOPE_ENTER','helper=abc');e('ATTACH');e('EXECUTE','method=123')
  rows += [' name : 0x456 "Call"',(' interpData : (null)' if seq==1 else ' interpData : 0x00000000`00000789 Void'),'GameAssembly!__ReversePInvokeMethod_0+0x1']
  if seq==1:e('TRANSFORM','method=123');rows+=[' name : 0x456 "Call"']
  e('CREATE','state=def');e('ROOT_ADD','root=def')
  if seq==n:
   for i in range(3):e('COLLECT',thread='64')
   e('PLUGIN','phase=3 seq=0 value=0',thread='64')
  e('SCOPE_LEAVE','helper=abc owned=1234');e('DETACH','function=eee thread=1234');e('FREE');e('DESTROY','state=def');e('ROOT_REMOVE','root=def')
  result=seq+73 if mode=='handle' else 257;e('PLUGIN',f'phase=2 seq={seq} value={result}')
 e('PLUGIN','phase=6 seq=0 value=0');e('PLUGIN','phase=4 seq=0 value=0',thread='64')
 if mode=='handle':e('CONTEXT_FREE',thread='66')
 return '\n'.join(rows)
class NativeResults(unittest.TestCase):
 def test_retention_trace(self):
  for mode in ['handle','stack']:self.assertEqual(parse_native(native_fixture(mode),parse_player(fixture(mode),mode))['active_full_collects'],3)
 def test_missing_or_misplaced_collection_rejected(self):
  text=native_fixture('stack')
  for wrong in [text.replace('GCP_NATIVE_COLLECT','MISSING',1),text.replace('GCP_NATIVE_COLLECT tid=64','GCP_NATIVE_COLLECT tid=66',1),text.replace('root=def','root=bad',1),text.replace('context=0 seq=1','context=20 seq=1')]:
   with self.assertRaises(ValueError):parse_native(wrong,parse_player(fixture('stack'),'stack'))
if __name__=='__main__':unittest.main()
