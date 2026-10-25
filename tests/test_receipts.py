import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import receipts

class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.art = self.root / "artifacts"
        self.art.mkdir()
        self.lock = {"editor": {"product_version": "test-editor"}}
        (self.root / "lab-lock.json").write_text(json.dumps(self.lock))
        self.p1 = patch.object(receipts, "ROOT", self.root); self.p1.start()
        self.p2 = patch.object(receipts, "ART", self.art); self.p2.start()
        self.binary = self.art / "Player.bin"; self.binary.write_bytes(b"generation-one")
    def tearDown(self):
        self.p2.stop(); self.p1.stop(); self.tmp.cleanup()
    def completed(self):
        build = receipts.start_build(self.lock, "test-editor")
        receipts.finish_build(build, [self.binary])
        return build
    def evidence(self, build):
        for kind in ("run", "trace"):
            log = self.art / (kind + ".txt"); log.write_text("result")
            receipts.begin_phase(kind, build)
            receipts.finish_phase(kind, build, [log])
    def test_valid_build_and_evidence(self):
        build = self.completed(); self.evidence(build)
        self.assertEqual(receipts.require_evidence()["build_id"], build["build_id"])
    def test_partial_rebuild_invalidates_previous_success(self):
        self.completed(); receipts.start_build(self.lock, "test-editor")
        with self.assertRaisesRegex(RuntimeError, "No completed build"):
            receipts.require_build()
    def test_new_build_rejects_old_run_and_trace(self):
        old = self.completed(); self.evidence(old); self.completed()
        with self.assertRaisesRegex(RuntimeError, "another build"):
            receipts.require_evidence()
    def test_changed_player_is_rejected(self):
        self.completed(); self.binary.write_bytes(b"replaced")
        with self.assertRaisesRegex(RuntimeError, "artifact changed"):
            receipts.require_build()
    def test_changed_log_is_rejected(self):
        build = self.completed(); self.evidence(build); (self.art / "trace.txt").write_text("replaced")
        with self.assertRaisesRegex(RuntimeError, "log changed"):
            receipts.require_evidence()
    def test_interrupted_trace_is_rejected(self):
        build = self.completed(); self.evidence(build); receipts.begin_phase("trace", build)
        with self.assertRaisesRegex(RuntimeError, "incomplete"):
            receipts.require_evidence()

if __name__ == "__main__": unittest.main()
