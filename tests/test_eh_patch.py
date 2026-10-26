import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from eh_patch import patched_source
class PatchTests(unittest.TestCase):
 def test_only_interpreter_macro_order_changes(self):
  path=Path(__file__).resolve().parents[1]/'.local/src/runtime/hybridclr/interpreter/Interpreter_Execute.cpp';source=path.read_text(encoding='utf-8-sig');changed=patched_source(source)
  self.assertNotEqual(source,changed);self.assertEqual(len(source.splitlines())+1,len(changed.splitlines()))
  a=source.index('#define PREPARE_NEW_FRAME_FROM_INTERPRETER');b=source.index('#define LEAVE_FRAME',a)
  self.assertEqual(source[:a],changed[:a]);self.assertEqual(source[b:],changed[changed.index('#define LEAVE_FRAME',a):]);part=changed[a:changed.index('#define LEAVE_FRAME',a)];self.assertLess(part.index('auto nextImi ='),part.index('RuntimeInitClassCCtorWithoutInitClass'));self.assertLess(part.index('RuntimeInitClassCCtorWithoutInitClass'),part.index('imi = nextImi;'))
 def test_wrong_or_already_patched_rejected(self):
  with self.assertRaises(ValueError):patched_source('unrelated')
  path=Path(__file__).resolve().parents[1]/'.local/src/runtime/hybridclr/interpreter/Interpreter_Execute.cpp'
  with self.assertRaises(ValueError):patched_source(patched_source(path.read_text(encoding='utf-8-sig')))
if __name__=='__main__':unittest.main()
