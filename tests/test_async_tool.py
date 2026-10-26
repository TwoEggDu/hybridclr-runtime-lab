import sys,unittest, tempfile, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from prepare_async import verify_checkout
from async_lab import matrix
class AsyncToolTests(unittest.TestCase):
 def test_matrix_exact_cells(self):
  cells=matrix();self.assertEqual(len(cells),60);self.assertEqual(len(set(cells)),60)
  self.assertEqual([x for x in cells if x[0]=="aot" and x[1]!="off"],[])
 def test_missing_dependency_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   with self.assertRaises(RuntimeError):verify_checkout(Path(t)/"missing",{"commit":"a"*40,"package_path":"pkg","version":"2.5.10"})
if __name__=="__main__":unittest.main()
