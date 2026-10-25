import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from callback_results import parse_player,parse_native
HEADER="CB_ENV mode={mode} unity=2022.3.62f3 incremental=True gcMode=Enabled\nCB_LOAD bytes=4096 assembly=HotUpdate pointer=12345\nCB_MAIN managed=1 native=100\n"
REGISTERED=HEADER.format(mode="registered")+"CB_OWNER before=5 after=5 native=101 result=50015 joined=True\nCB_CALL index=0 managed=5 native=101 a=2 b=3 result=5\nCB_CALL index=1 managed=5 native=101 a=7 b=8 result=15\nCB_RELEASE afterJoin=True\nCB_DONE mode=registered failures=0\n"
RAW=HEADER.format(mode="raw")+"CB_STOP entered=True joinedBefore=False requested=1\nCB_RAW native=102 count=3 first=5 second=15 third=23 joined=True\nCB_CALL index=0 managed=5 native=102 a=2 b=3 result=5\nCB_CALL index=1 managed=6 native=102 a=7 b=8 result=15\nCB_CALL index=2 managed=7 native=102 a=11 b=12 result=23\nCB_RELEASE afterJoin=True\nCB_DONE mode=raw failures=0\n"
class PlayerResults(unittest.TestCase):
 def test_normal_results(self):
  self.assertEqual(len(parse_player(RAW,"raw")["calls"]),3)
  self.assertEqual(len(parse_player(REGISTERED,"registered")["calls"]),2)
 def test_incomplete_or_wrong_results(self):
  for text in [RAW.replace("joinedBefore=False","joinedBefore=True"),RAW.replace("third=23","third=24"),RAW.replace("count=3","count=4"),RAW.replace("afterJoin=True","afterJoin=False"),RAW.replace("native=102 a=7","native=103 a=7"),RAW.replace("incremental=True","incremental=False"),RAW.replace("CB_CALL index=1", "MISSING index=1")]:
   with self.assertRaises(ValueError):parse_player(text,"raw")
 def test_release_before_join_rejected(self):
  text=RAW.replace("CB_RELEASE afterJoin=True\n","")
  text=text.replace("CB_STOP", "CB_RELEASE afterJoin=True\nCB_STOP",1)
  with self.assertRaises(ValueError):parse_player(text,"raw")
 def test_registered_identity_preserved(self):
  with self.assertRaises(ValueError):parse_player(REGISTERED.replace("after=5","after=6"),"registered")



# Synthetic trace fixture; never used as runtime evidence.
def native_fixture(mode):
 tid='66' if mode=='raw' else '65';rows=['GameAssembly C (private pdb symbols)','NativeProbe C (private pdb symbols)']
 def e(kind,fields='',thread=None):rows.append(f'CB_NATIVE_{kind} tid={thread or tid}'+(' '+fields if fields else ''))
 def cleanup(state):
  e('FREE');e('DESTROY','state='+state);e('ROOT_REMOVE','root='+state)
 if mode=='raw':e('PLUGIN','phase=5 a=0 b=0 value=0')
 for i,(a,b,result) in enumerate([(2,3,5),(7,8,15)]+([(11,12,23)] if mode=='raw' else [])):
  state=f'{100+i:x}'
  e('PLUGIN',f'phase=1 a={a} b={b} value=0');e('WRAPPER',f'wrapper=3039 a={a} b={b}');e('SCOPE_ENTER','helper=abc')
  if mode=='raw':e('ATTACH')
  e('EXECUTE','method=123');rows+=[' name : 0x456 "Call"',(' interpData : (null)' if i==0 else ' interpData : 0x00000000`00000789 Void'),'GameAssembly!__ReversePInvokeMethod_0+0x1']
  if i==0:e('TRANSFORM','method=123')
  if mode=='raw' or i==0:e('CREATE','state='+state);e('ROOT_ADD','root='+state)
  if mode=='raw' and i==2:e('PLUGIN','phase=3 a=0 b=0 value=0','64')
  e('SCOPE_LEAVE','helper=abc owned='+('1234' if mode=='raw' else '0'))
  if mode=='raw':e('DETACH','function=eee thread=1234');cleanup(state)
  e('PLUGIN',f'phase=2 a={a} b={b} value={result}')
 if mode=='raw':e('PLUGIN','phase=6 a=0 b=0 value=0');e('PLUGIN','phase=4 a=0 b=0 value=0','64')
 else:cleanup('64')
 return '\n'.join(rows)
class NativeResults(unittest.TestCase):
 def test_owned_vs_existing_registration(self):
  for mode,text in [('raw',RAW),('registered',REGISTERED)]:self.assertEqual(parse_native(native_fixture(mode),parse_player(text,mode))['callback_count'],3 if mode=='raw' else 2)
 def test_missing_cache_field_rejected(self):
  text=native_fixture('raw').replace(' interpData : (null)\n','',1)
  with self.assertRaises(ValueError):parse_native(text,parse_player(RAW,'raw'))
 def test_missing_roots_or_wrong_ownership(self):
  for text in [native_fixture('raw').replace('ROOT_REMOVE','MISSING'),native_fixture('raw').replace('owned=1234','owned=0',1),native_fixture('raw').replace('00000789','00000999',1),native_fixture('raw').replace('wrapper=3039','wrapper=3038',1)]:
   with self.assertRaises(ValueError):parse_native(text,parse_player(RAW,'raw'))

if __name__=="__main__":unittest.main()
