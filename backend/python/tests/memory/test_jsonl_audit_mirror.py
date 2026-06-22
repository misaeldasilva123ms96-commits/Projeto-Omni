from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.memory.jsonl_audit_mirror import JSONLAuditMirror
from brain.memory.memory_models import redact_payload


class JSONLAuditMirrorTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="omni-jsonl-test-"))
        self._path = self._tmp / "audit.jsonl"
        self.mirror = JSONLAuditMirror(self._path)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_append_creates_file(self) -> None:
        self.assertFalse(self._path.exists())
        self.mirror.append("test", {"key": "value"})
        self.assertTrue(self._path.exists())

    def test_read_all_returns_appended_records(self) -> None:
        self.mirror.append("type_a", {"id": 1})
        self.mirror.append("type_b", {"id": 2})
        records = self.mirror.read_all()
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["type"], "type_a")
        self.assertEqual(records[1]["type"], "type_b")

    def test_read_all_with_limit(self) -> None:
        for i in range(10):
            self.mirror.append("t", {"i": i})
        records = self.mirror.read_all(limit=3)
        self.assertEqual(len(records), 3)

    def test_count_lines(self) -> None:
        for _ in range(5):
            self.mirror.append("t", {"x": 1})
        self.assertEqual(self.mirror.count_lines(), 5)

    def test_truncate_empties_file(self) -> None:
        self.mirror.append("t", {"x": 1})
        self.mirror.truncate()
        self.assertEqual(self.mirror.count_lines(), 0)
        self.assertEqual(self.mirror.read_all(), [])

    def test_read_all_empty_file(self) -> None:
        self.assertEqual(self.mirror.read_all(), [])

    def test_count_lines_nonexistent_file(self) -> None:
        mirror = JSONLAuditMirror(self._tmp / "nonexistent.jsonl")
        self.assertEqual(mirror.count_lines(), 0)

    def test_append_is_append_only(self) -> None:
        self.mirror.append("t", {"i": 1})
        self.mirror.append("t", {"i": 2})
        records = self.mirror.read_all()
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["payload"]["i"], 1)
        self.assertEqual(records[1]["payload"]["i"], 2)

    def test_redaction_applied_before_write(self) -> None:
        self.mirror.append("test", {"api_key": "sk-secret"})
        records = self.mirror.read_all()
        self.assertEqual(records[0]["payload"]["api_key"], "[REDACTED]")

    def test_path_property(self) -> None:
        self.assertEqual(self.mirror.path, self._path)


if __name__ == "__main__":
    unittest.main()
