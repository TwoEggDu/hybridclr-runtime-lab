import struct,tempfile,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from unity_snapshot import Snapshot

def fixture(kind=2):
 data=bytearray(struct.pack('<I',0xAEABCDCD));offset=len(data);data+=b'abcdEFGH'
 block=len(data);data+=struct.pack('<QQQ',8,8,offset)
 blocks=len(data);data+=struct.pack('<IIQ',0x20170724,1,block)
 entry=len(data)
 if kind==2:data+=struct.pack('<HIIQ',2,0,4,2)
 elif kind==3:data+=struct.pack('<HIIQ',3,0,2,0)+struct.pack('<QQ',4,8)
 elif kind==1:data+=struct.pack('<HIIQ',1,0,4,4)
 directory=len(data);data+=struct.pack('<IIQIQ',0xCDCDAEAB,0x20170724,blocks,1,entry)
 data+=struct.pack('<QI',directory,0xABCDCDAE)
 return data
class SnapshotChecks(unittest.TestCase):
 def load(self,data):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'test.snap';path.write_bytes(data);return Snapshot(path)
 def test_constant(self):self.assertEqual(self.load(fixture()).entry(0),[b'abcd',b'EFGH'])
 def test_constant_count_ignores_next_header(self):
  data=fixture();data[66:70]=b'xxxx'
  self.assertEqual(self.load(data).entry(0),[b'abcd',b'EFGH'])
 def test_dynamic(self):self.assertEqual(self.load(fixture(3)).entry(0),[b'abcd',b'EFGH'])
 def test_single(self):self.assertEqual(self.load(fixture(1)).entry(0),[b'EFGH'])
 def test_bad_signature(self):
  data=fixture();data[0]=0
  with self.assertRaises(ValueError):self.load(data)
 def test_truncated(self):
  with self.assertRaises(ValueError):self.load(fixture()[:-5])
 def test_directory_bounds(self):
  data=fixture();data[-12:-4]=struct.pack('<Q',999999)
  with self.assertRaises(ValueError):self.load(data)
 def test_chunk_bounds(self):
  data=fixture();data[28:36]=struct.pack('<Q',999999)
  with self.assertRaises(ValueError):self.load(data)
 def test_dynamic_outside_block(self):
  data=fixture(3);data[78:86]=struct.pack('<Q',999999)
  with self.assertRaises(ValueError):self.load(data).entry(0)
if __name__=='__main__':unittest.main()
