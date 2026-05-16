from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.learning.runtime_learning_store import RuntimeLearningStore  # noqa: E402


def test_runtime_learning_store_reads_latest_record_from_bounded_tail() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = RuntimeLearningStore(Path(tmp))
        store.path.parent.mkdir(parents=True, exist_ok=True)
        with store.path.open("w", encoding="utf-8") as handle:
            for index in range(600):
                handle.write(json.dumps({"record_id": f"old-{index}", "padding": "x" * 1024}))
                handle.write("\n")
            handle.write(json.dumps({"record_id": "latest", "session_id": "sess-a"}))
            handle.write("\n")

        with patch.object(Path, "read_text", side_effect=AssertionError("read_text should not be used")):
            latest = store.read_latest_record()

        assert latest is not None
        assert latest["record_id"] == "latest"


def test_runtime_learning_store_reads_session_records_from_bounded_tail() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = RuntimeLearningStore(Path(tmp))
        store.path.parent.mkdir(parents=True, exist_ok=True)
        with store.path.open("w", encoding="utf-8") as handle:
            for index in range(600):
                handle.write(json.dumps({"record_id": f"old-{index}", "session_id": "other", "padding": "x" * 1024}))
                handle.write("\n")
            for index in range(4):
                handle.write(json.dumps({"record_id": f"target-{index}", "session_id": "sess-a"}))
                handle.write("\n")

        with patch.object(Path, "read_text", side_effect=AssertionError("read_text should not be used")):
            records = store.read_recent_for_session("sess-a", limit=3)

        assert [record["record_id"] for record in records] == ["target-3", "target-2", "target-1"]
