from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.memory.autonomy_session_cleanup import (  # noqa: E402
    cleanup_expired_autonomy_session_states_manual,
)
from brain.memory.memory_facade import MemoryFacade  # noqa: E402
from brain.memory.memory_models import AutonomySessionStateRecord  # noqa: E402
from brain.runtime.autonomy import AutonomyController, AutonomySessionTracker, DecisionType  # noqa: E402
from brain.runtime.autonomy.error_progress_tracker import SmartErrorProgressTracker  # noqa: E402
from brain.runtime.autonomy.runtime_wiring import evaluate_autonomy  # noqa: E402

_CLEANUP_RESULT_FIELDS = {
    "operation_id",
    "operation_type",
    "attempted",
    "supported",
    "dry_run",
    "sqlite_path_fingerprint",
    "sqlite_path_present",
    "would_delete_count",
    "deleted_count",
    "degraded",
    "error_category",
    "attempted_at",
    "sqlite_enabled",
    "sqlite_connected",
    "cutoff_time",
}


class _FailingCleanupFacade:
    sqlite_enabled = True
    is_sqlite_connected = True

    def cleanup_expired_autonomy_session_states(self, now: str | None = None) -> int:
        raise RuntimeError("cleanup failed with sk-test-secret")

    def get_autonomy_session_state_lifecycle_diagnostics(self, now: str | None = None) -> dict[str, Any]:
        return {
            "cleanup_degraded": True,
            "cleanup_last_error_category": "Bearer sk-test-secret",
            "last_cleanup_attempted_at": "2026-06-27T00:00:00+00:00",
            "expired_state_count": 0,
        }


class AutonomySessionStateManualCleanupTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="omni-autonomy-manual-cleanup-"))
        self._audit_path = self._tmp / "audit.jsonl"
        self._sqlite_path = self._tmp / "memory.sqlite"

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _record(self, session_id: str, expires_at: str) -> AutonomySessionStateRecord:
        return AutonomySessionStateRecord(
            session_id=session_id,
            last_error_type="timeout",
            current_error_count=1,
            distinct_error_count=1,
            distinct_error_types=["timeout"],
            updated_at="2026-06-27T00:00:00+00:00",
            expires_at=expires_at,
        )

    def _sqlite_facade(self) -> MemoryFacade:
        facade = MemoryFacade(
            enable_sqlite=True,
            sqlite_path=self._sqlite_path,
            jsonl_path=self._audit_path,
        )
        facade.initialize()
        self.assertTrue(facade.is_sqlite_connected)
        return facade

    def test_manual_cleanup_noops_safely_when_sqlite_disabled(self) -> None:
        facade = MemoryFacade(jsonl_path=self._audit_path, sqlite_path=self._sqlite_path)
        facade.initialize()

        result = cleanup_expired_autonomy_session_states_manual(
            facade=facade,
            now="2026-06-27T00:00:00+00:00",
        )

        self.assertTrue(result.attempted)
        self.assertFalse(result.supported)
        self.assertFalse(result.dry_run)
        self.assertEqual(result.would_delete_count, 0)
        self.assertEqual(result.deleted_count, 0)
        self.assertFalse(result.degraded)
        self.assertEqual(result.error_category, "")
        self.assertFalse(result.sqlite_enabled)
        self.assertFalse(result.sqlite_connected)
        self.assertFalse(result.sqlite_path_present)
        self.assertEqual(result.sqlite_path_fingerprint, "")
        self.assertEqual(result.operation_type, "cleanup_autonomy_session_states")
        self.assertTrue(result.operation_id.startswith("cleanup-"))
        self.assertEqual(facade.audit_records(), [])

    def test_manual_cleanup_dry_run_noops_safely_when_sqlite_disabled(self) -> None:
        facade = MemoryFacade(jsonl_path=self._audit_path, sqlite_path=self._sqlite_path)
        facade.initialize()

        result = cleanup_expired_autonomy_session_states_manual(
            facade=facade,
            now="2026-06-27T00:00:00+00:00",
            dry_run=True,
        )

        self.assertTrue(result.attempted)
        self.assertFalse(result.supported)
        self.assertTrue(result.dry_run)
        self.assertEqual(result.would_delete_count, 0)
        self.assertEqual(result.deleted_count, 0)
        self.assertFalse(result.degraded)
        self.assertEqual(result.error_category, "")
        self.assertFalse(result.sqlite_enabled)
        self.assertFalse(result.sqlite_connected)
        self.assertFalse(result.sqlite_path_present)
        self.assertEqual(result.sqlite_path_fingerprint, "")
        self.assertEqual(result.cutoff_time, "2026-06-27T00:00:00+00:00")

    def test_manual_cleanup_deletes_only_expired_rows_when_sqlite_enabled(self) -> None:
        facade = self._sqlite_facade()
        facade.record_autonomy_session_state(self._record("old", "2026-06-01T00:00:00+00:00"))
        facade.record_autonomy_session_state(self._record("fresh", "2999-01-01T00:00:00+00:00"))

        result = cleanup_expired_autonomy_session_states_manual(
            facade=facade,
            now="2026-06-27T00:00:00+00:00",
        )

        self.assertTrue(result.attempted)
        self.assertTrue(result.supported)
        self.assertFalse(result.dry_run)
        self.assertEqual(result.would_delete_count, 0)
        self.assertEqual(result.deleted_count, 1)
        self.assertFalse(result.degraded)
        self.assertEqual(result.error_category, "")
        self.assertTrue(result.sqlite_enabled)
        self.assertTrue(result.sqlite_connected)
        self.assertFalse(result.sqlite_path_present)
        self.assertEqual(result.sqlite_path_fingerprint, "")
        self.assertIsNone(facade.get_autonomy_session_state("old"))
        self.assertIsNotNone(facade.get_autonomy_session_state("fresh"))

    def test_manual_cleanup_dry_run_counts_without_deleting(self) -> None:
        facade = self._sqlite_facade()
        self.assertIsNotNone(facade._sqlite)
        facade.record_autonomy_session_state(self._record("old", "2026-06-01T00:00:00+00:00"))
        facade.record_autonomy_session_state(self._record("fresh", "2999-01-01T00:00:00+00:00"))

        result = cleanup_expired_autonomy_session_states_manual(
            facade=facade,
            now="2026-06-27T00:00:00+00:00",
            dry_run=True,
        )

        self.assertTrue(result.attempted)
        self.assertTrue(result.supported)
        self.assertTrue(result.dry_run)
        self.assertEqual(result.would_delete_count, 1)
        self.assertEqual(result.deleted_count, 0)
        self.assertFalse(result.degraded)
        self.assertEqual(result.error_category, "")
        self.assertTrue(result.sqlite_enabled)
        self.assertTrue(result.sqlite_connected)
        self.assertFalse(result.sqlite_path_present)
        self.assertEqual(result.sqlite_path_fingerprint, "")
        self.assertEqual(result.cutoff_time, "2026-06-27T00:00:00+00:00")
        self.assertEqual(facade._sqlite.table_count("autonomy_session_states"), 2)
        self.assertIsNotNone(facade.get_autonomy_session_state("fresh"))

        destructive = cleanup_expired_autonomy_session_states_manual(
            facade=facade,
            now="2026-06-27T00:00:00+00:00",
        )

        self.assertEqual(destructive.deleted_count, 1)
        self.assertEqual(facade._sqlite.table_count("autonomy_session_states"), 1)

    def test_manual_cleanup_returns_safe_metadata_only(self) -> None:
        facade = self._sqlite_facade()

        result = cleanup_expired_autonomy_session_states_manual(
            facade=facade,
            now="2026-06-27T00:00:00+00:00",
        ).as_dict()

        self.assertEqual(set(result), _CLEANUP_RESULT_FIELDS)
        self.assertNotIn("session_id", result)
        self.assertNotIn("raw_prompt", str(result))
        self.assertNotIn("raw_response", str(result))
        self.assertNotIn("traceback", str(result).lower())

    def test_manual_cleanup_path_fingerprint_is_stable_and_safe(self) -> None:
        facade = self._sqlite_facade()
        raw_path = self._sqlite_path

        first = cleanup_expired_autonomy_session_states_manual(
            facade=facade,
            now="2026-06-27T00:00:00+00:00",
            dry_run=True,
            sqlite_path=raw_path,
        ).as_dict()
        second = cleanup_expired_autonomy_session_states_manual(
            facade=facade,
            now="2026-06-27T00:00:00+00:00",
            dry_run=True,
            sqlite_path=raw_path,
        ).as_dict()

        self.assertTrue(first["sqlite_path_present"])
        self.assertEqual(first["sqlite_path_fingerprint"], second["sqlite_path_fingerprint"])
        self.assertTrue(str(first["sqlite_path_fingerprint"]).startswith("sha256:"))
        self.assertNotIn(str(raw_path), str(first))
        self.assertNotIn(raw_path.name, str(first))

    def test_manual_cleanup_failure_degrades_safely(self) -> None:
        result = cleanup_expired_autonomy_session_states_manual(
            facade=_FailingCleanupFacade(),  # type: ignore[arg-type]
            now="2026-06-27T00:00:00+00:00",
        )

        self.assertTrue(result.attempted)
        self.assertTrue(result.supported)
        self.assertFalse(result.dry_run)
        self.assertEqual(result.would_delete_count, 0)
        self.assertEqual(result.deleted_count, 0)
        self.assertTrue(result.degraded)
        self.assertEqual(result.error_category, "cleanup_failed")
        self.assertNotIn("sk-test-secret", str(result.as_dict()))
        self.assertNotIn("Traceback", str(result.as_dict()))

    def test_manual_cleanup_dry_run_failure_degrades_safely(self) -> None:
        result = cleanup_expired_autonomy_session_states_manual(
            facade=_FailingCleanupFacade(),  # type: ignore[arg-type]
            now="2026-06-27T00:00:00+00:00",
            dry_run=True,
        )

        self.assertTrue(result.attempted)
        self.assertTrue(result.supported)
        self.assertTrue(result.dry_run)
        self.assertEqual(result.would_delete_count, 0)
        self.assertEqual(result.deleted_count, 0)
        self.assertTrue(result.degraded)
        self.assertEqual(result.error_category, "cleanup_degraded")
        self.assertNotIn("sk-test-secret", str(result.as_dict()))
        self.assertNotIn("Traceback", str(result.as_dict()))

    def test_manual_cleanup_does_not_alter_advisory_decisions_or_output(self) -> None:
        facade = self._sqlite_facade()
        tracker = AutonomySessionTracker(memory_facade=facade)
        inspection = {"signals": {"failure_class": "timeout", "runtime_mode": "standard"}}
        controller = AutonomyController(emit_governance_events=False)

        before = evaluate_autonomy(
            inspection,
            "sess-1",
            "ok",
            controller=controller,
            tracker=tracker,
            smart_tracker=SmartErrorProgressTracker(),
        )
        cleanup_expired_autonomy_session_states_manual(
            facade=facade,
            now="2026-06-27T00:00:00+00:00",
        )
        after = evaluate_autonomy(
            inspection,
            "sess-2",
            "ok",
            controller=controller,
            tracker=AutonomySessionTracker(memory_facade=facade),
            smart_tracker=SmartErrorProgressTracker(),
        )

        self.assertTrue(before["advisory"])
        self.assertTrue(after["advisory"])
        self.assertEqual(before["decision"], DecisionType.RETRY.value)
        self.assertEqual(after["decision"], DecisionType.RETRY.value)
        self.assertNotEqual(after["decision"], DecisionType.SELF_REPAIR.value)
        self.assertNotEqual(after["decision"], DecisionType.SWITCH_PROVIDER.value)


if __name__ == "__main__":
    unittest.main()
