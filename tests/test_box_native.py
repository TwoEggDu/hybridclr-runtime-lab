import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from box_native import parse_native
MD=[{"assembly":"Probe.AOT","types":[]},{"assembly":"HotUpdate","types":[{"name":"HotBox.Cases","methods":[{"name":"Run","token":0x600000c}]},{"name":"HotBox.Counter","methods":[{"name":"Increment","token":0x6000004}]}]}]
def fixture():
 lines=['private pdb symbols','CBN_LAYOUT objectSize=16','CBN_METHOD kind=transform method=111 name=Run token=600000c class=Cases ns=HotBox image=HotUpdate.dll interp=0','CBN_BOX name=Counter ns=HotBox data=1000 value=10','CBN_BOX_RETURN object=2000 payload=2010 value=10']
 for ptr,value in [('2010',10),('2010',11),('3000',12)]:
  lines += ['CBN_METHOD kind=frame method=222 name=Increment token=6000004 class=Counter ns=HotBox image=HotUpdate.dll interp=999',f'CBN_RECEIVER kind=frame this={ptr} first={value} header16=0']
 return '\n'.join(lines)
class BoxNativeTests(unittest.TestCase):
 def test_box_receivers_share_payload_then_copy(self):self.assertTrue(parse_native(fixture(),'hot','box','off',MD)['box_alias_and_copy_verified'])
 def test_wrong_payload_offset_rejected(self):
  with self.assertRaises(ValueError):parse_native(fixture().replace('payload=2010','payload=2020'),'hot','box','off',MD)
 def test_second_interface_call_not_same_box_rejected(self):
  with self.assertRaises(ValueError):parse_native(fixture().replace('this=2010 first=11','this=4000 first=11'),'hot','box','off',MD)
 def test_unboxed_copy_alias_rejected(self):
  with self.assertRaises(ValueError):parse_native(fixture().replace('this=3000','this=2010'),'hot','box','off',MD)
 def test_wrong_token_rejected(self):
  with self.assertRaises(ValueError):parse_native(fixture().replace('token=6000004','token=6000009'),'hot','box','off',MD)
 def test_extra_box_rejected(self):
  with self.assertRaises(ValueError):parse_native(fixture()+'\nCBN_BOX name=Counter ns=HotBox data=1000 value=10\nCBN_BOX_RETURN object=5000 payload=5010 value=10','hot','box','off',MD)
class CrossNativeTests(unittest.TestCase):
 def fixture(self):
  meta=[{"assembly":"Probe.AOT","types":[{"name":".GenericCalls","methods":[{"name":"ByRef","token":0x6000009},{"name":"ByValue","token":0x6000008}]}]},MD[1]]
  text='private pdb symbols\nCBN_LAYOUT objectSize=16\nCBN_METHOD kind=execute method=222 name=Increment token=6000004 class=Counter ns=HotBox image=HotUpdate.dll interp=999\nCBN_RECEIVER kind=execute this=3000 first=10 header16=0\nCBN_NATIVE name=ByRef symbol=GameAssembly!GenericCalls_ByRef_TisIl2CppFullySharedGenericAny_gshared (123) method=456 token=6000009'
  return text,meta
 def test_extra_native_helper_rejected(self):
  text,meta=self.fixture();text+='\nCBN_NATIVE name=ByValue symbol=GameAssembly!GenericCalls_ByValue_gshared (789) method=888 token=6000008'
  with self.assertRaises(ValueError):parse_native(text,'cross','ref','off',meta)
 def test_supplementary_body_read_in_off_rejected(self):
  text,meta=self.fixture();text+='\nCBN_BODY image=111 token=6000008 assembly=Probe.AOT.dll'
  with self.assertRaises(ValueError):parse_native(text,'cross','ref','off',meta)
class OverrideReceiverTests(unittest.TestCase):
 def fixture(self):
  md=[{"assembly":"Probe.AOT","types":[]},{"assembly":"HotUpdate","types":[{"name":"HotBox.Cases","methods":[{"name":"TextLocal","token":0x600000b}]},{"name":"HotBox.Counter","methods":[{"name":"ToString","token":0x6000005}]}]}]
  first='CBN_METHOD kind=frame method=111 name=TextLocal token=600000b class=Cases ns=HotBox image=HotUpdate.dll interp=888\nCBN_RECEIVER kind=frame this=1000 first=10 header16=0'
  second='CBN_METHOD kind=frame method=222 name=ToString token=6000005 class=Counter ns=HotBox image=HotUpdate.dll interp=999\nCBN_RECEIVER kind=frame this=1000 first=10 header16=0'
  return 'private pdb symbols\nCBN_LAYOUT objectSize=16\n'+first+'\n'+second,md,first
 def test_override_different_receiver_rejected(self):
  t,md,_=self.fixture();parts=t.rsplit('this=1000',1);t='this=deadbeef'.join(parts)
  with self.assertRaises(ValueError):parse_native(t,'hot','text-override','off',md)
 def test_missing_textlocal_receiver_rejected(self):
  t,md,first=self.fixture()
  with self.assertRaises(ValueError):parse_native(t.replace(first+'\n',''),'hot','text-override','off',md)
if __name__=='__main__':unittest.main()
