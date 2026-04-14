from __future__ import annotations

import json
import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.engine_adoption_store import EngineAdoptionStore  # noqa: E402
from brain.runtime.observability.engine_adoption_reader import read_engine_adoption  # noqa: E402


class EngineAdoptionReaderTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-observability"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"engine-adoption-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_store_increments_packaged_and_fallback_counters(self) -> None:
        with self.temp_workspace() as workspace_root:
            store = EngineAdoptionStore(workspace_root)
            store.record_selection(
                engine_mode="packaged_upstream",
                engine_reason="dist_candidate_selected",
                session_id="sess-26",
            )
            store.record_selection(
                engine_mode="authority_fallback",
                engine_reason="heavy_execution_request",
                session_id="sess-26",
            )
            snapshot = store.snapshot()
            counters = snapshot["engine_counters"]
            self.assertEqual(counters["packaged_upstream"], 1)
            self.assertEqual(counters["authority_fallback"], 1)
            self.assertEqual(counters["fallback_by_reason"]["heavy_execution_request"], 1)

    def test_store_tracks_known_fallback_reasons(self) -> None:
        with self.temp_workspace() as workspace_root:
            store = EngineAdoptionStore(workspace_root)
            store.record_selection(
                engine_mode="authority_fallback",
                engine_reason="packaged_import_failed",
                session_id="sess-26",
            )
            store.record_selection(
                engine_mode="authority_fallback",
                engine_reason="fallback_policy_triggered",
                session_id="sess-26",
            )
            payload = json.loads(
                (workspace_root / ".logs" / "fusion-runtime" / "engine_adoption.json").read_text(encoding="utf-8")
            )
            breakdown = payload["engine_counters"]["fallback_by_reason"]
            self.assertEqual(breakdown["packaged_import_failed"], 1)
            self.assertEqual(breakdown["fallback_policy_triggered"], 1)

    def test_store_resets_when_session_changes(self) -> None:
        with self.temp_workspace() as workspace_root:
            store = EngineAdoptionStore(workspace_root)
            store.record_selection(
                engine_mode="packaged_upstream",
                engine_reason="dist_candidate_selected",
                session_id="sess-a",
            )
            store.record_selection(
                engine_mode="authority_fallback",
                engine_reason="heavy_execution_request",
                session_id="sess-b",
            )
            snapshot = store.snapshot()
            self.assertEqual(snapshot["session_id"], "sess-b")
            self.assertEqual(snapshot["engine_counters"]["packaged_upstream"], 0)
            self.assertEqual(snapshot["engine_counters"]["authority_fallback"], 1)

    def test_reader_returns_safe_payload_when_file_missing_or_invalid(self) -> None:
        with self.temp_workspace() as workspace_root:
            self.assertEqual(
                read_engine_adoption(workspace_root),
                {
                    "scope": "session",
                    "session_id": "",
                    "packaged_upstream_count": 0,
                    "authority_fallback_count": 0,
                    "fallback_breakdown": {
                        "heavy_execution_request": 0,
                        "packaged_import_failed": 0,
                        "fallback_policy_triggered": 0,
                    },
                    "adoption_rate": 0.0,
                    "promotion_ready": False,
                },
            )

            path = workspace_root / ".logs" / "fusion-runtime"
            path.mkdir(parents=True, exist_ok=True)
            (path / "engine_adoption.json").write_text('{"scope": ', encoding="utf-8")
            self.assertEqual(read_engine_adoption(workspace_root)["promotion_ready"], False)

    def test_reader_computes_adoption_rate_and_promotion_readiness(self) -> None:
        with self.temp_workspace() as workspace_root:
            store = EngineAdoptionStore(workspace_root)
            for _ in range(8):
                store.record_selection(
                    engine_mode="packaged_upstream",
                    engine_reason="dist_candidate_selected",
                    session_id="sess-26",
                )
            for _ in range(2):
                store.record_selection(
                    engine_mode="authority_fallback",
                    engine_reason="heavy_execution_request",
                    session_id="sess-26",
                )
            adoption = read_engine_adoption(workspace_root)
            self.assertEqual(adoption["packaged_upstream_count"], 8)
            self.assertEqual(adoption["authority_fallback_count"], 2)
            self.assertAlmostEqual(adoption["adoption_rate"], 0.8)
            self.assertTrue(adoption["promotion_ready"])

    def test_promotion_ready_false_when_packaged_import_failed_exists(self) -> None:
        with self.temp_workspace() as workspace_root:
            store = EngineAdoptionStore(workspace_root)
            for _ in range(9):
                store.record_selection(
                    engine_mode="packaged_upstream",
                    engine_reason="dist_candidate_selected",
                    session_id="sess-26",
                )
            store.record_selection(
                engine_mode="authority_fallback",
                engine_reason="packaged_import_failed",
                session_id="sess-26",
            )
            self.assertFalse(read_engine_adoption(workspace_root)["promotion_ready"])

    def test_promotion_ready_false_when_total_requests_is_low(self) -> None:
        with self.temp_workspace() as workspace_root:
            store = EngineAdoptionStore(workspace_root)
            for _ in range(4):
                store.record_selection(
                    engine_mode="packaged_upstream",
                    engine_reason="dist_candidate_selected",
                    session_id="sess-26",
                )
            self.assertFalse(read_engine_adoption(workspace_root)["promotion_ready"])


if __name__ == "__main__":
    unittest.main()
