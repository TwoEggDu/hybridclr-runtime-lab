import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from resource_lab import check_build_log
class BuildLogTests(unittest.TestCase):
 def test_non_utf8_tool_output_does_not_hide_ascii_success_marker(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"build.log";p.write_bytes(b"compiler: "+bytes.fromhex("b9dcb5c0")+b"\nRESOURCE_BUILD_RESULT Succeeded\n")
   check_build_log(p,"RESOURCE_BUILD_RESULT Succeeded")
 def test_missing_success_marker_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"build.log";p.write_bytes(b"compiler: "+bytes.fromhex("b9dcb5c0"))
   with self.assertRaises(RuntimeError):check_build_log(p,"RESOURCE_BUILD_RESULT Succeeded")
