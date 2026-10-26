import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from init_trace import parse_trace
S="""private pdb symbols
TIP_NATIVE_TRANSFORM method=222 +0x018 name : 0x234 \"Ping\"
+0x058 interpData : (null)
TIP_NATIVE_TRANSFORM method=111 +0x018 name : 0x123 \".cctor\"
+0x058 interpData : (null)
TIP_NATIVE_EXECUTE method=111 +0x018 name : 0x123 \".cctor\"
+0x058 interpData : 0xaaa Void
GameAssembly!il2cpp::vm::Runtime::ClassInit
TIP_NATIVE_END method=222 +0x018 name : 0x234 \"Ping\"
+0x058 interpData : 0xbbb Void
"""
class TraceTests(unittest.TestCase):
 def test_identity_stack_and_final_cache(self):
  r=parse_trace(S);self.assertTrue(r['ping_cache_ready_at_end']);self.assertEqual(r['cctor_transforms'],1)
 def test_corruptions_rejected(self):
  for a,b in [('private pdb symbols','export symbols'),('Runtime::ClassInit','Other'),('TIP_NATIVE_END method=222','TIP_NATIVE_END method=333'),('0xbbb Void','(null)'),('TIP_NATIVE_EXECUTE','NO_EXECUTE')]:
   with self.subTest(a=a),self.assertRaises(ValueError):parse_trace(S.replace(a,b))
class ReviewNativeOrderTests(unittest.TestCase):
 def test_execution_before_cctor_transform_rejected(self):
  start=S.index('TIP_NATIVE_TRANSFORM method=111');mid=S.index('TIP_NATIVE_EXECUTE method=111');end=S.index('TIP_NATIVE_END')
  bad=S[:start]+S[mid:end]+S[start:mid]+S[end:]
  with self.assertRaises(ValueError):parse_trace(bad)
if __name__=='__main__':unittest.main()
