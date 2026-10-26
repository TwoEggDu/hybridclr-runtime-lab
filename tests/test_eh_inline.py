import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from eh_inline import parse_inline
S='private pdb symbols\nEHF_INLINE method=RunOwn sameCaller=1 offset=184\nEHF_INLINE method=RunOwn sameCaller=1 offset=184\n'
class InlineTests(unittest.TestCase):
 def test_both_accesses_at_init_opcode(self):self.assertEqual(len(parse_inline(S)),2)
 def test_missing_or_bad_context(self):
  for s in ['',S.replace('sameCaller=1','sameCaller=0'),S.replace('RunOwn','Other'),S.replace('private pdb symbols','exports'),S+S]:
   with self.assertRaises(ValueError):parse_inline(s)
if __name__=='__main__':unittest.main()
