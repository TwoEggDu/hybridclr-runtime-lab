import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from eh_lab import context_script
class CommandTests(unittest.TestCase):
 def test_debugger_commands_have_no_literal_newline_inside_breakpoint(self):
  s=context_script();self.assertEqual(len(s.splitlines()),6);self.assertIn('EHF_VALUES',s.splitlines()[3]);self.assertIn('EHF_REGION',s.splitlines()[3])
if __name__=='__main__':unittest.main()
