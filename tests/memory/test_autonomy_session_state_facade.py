from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.memory.memory_facade import MemoryFacade  # noqa: E402
from brain.memory.memory_models import AutonomySessionStateRecord  # noqa: E402


class AutonomySessionStateFacadeTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="omni-autonomy-state-facade-"))
        self._audit_path = self._tmp / "audit.jsonl"
        self._sqlite_path = self._tmp / "memory.sqlite"

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _record(self, session_id: str = "sess-1") -> AutonomySessionStateRecord:
        return AutonomySessionStateRecord(
            session_id=session_id,
            last_error_type="timeout",
            current_error_count=2,
            stagnant_attempts=1,
            distinct_error_count=1,
            distinct_error_types=["timeout"],
            progressive_cycles=1,
            last_runtime_mode="provider_failure",
            last_provider_failure_type="timeout",
            last_response_length=10,
            last_response_was_safe_fallback=True,
            last_decision="RETRY",
            last_fingerprint_id="abc123",
            last_progress_score=1,
            last_stagnation_score=3,
            repeated_strategy_count=1,
            strategies_attempted=["retry_short_backoff"],
            updated_at="2026-06-27T00:00:00+00:00",
            expires_at="2999-07-04T00:00:00+00:00",
        )

    def test_jsonl_default_does_not_persist_session_state(self) -> None:
        facade = MemoryFacade(jsonl_path=self._audit_path, sqlite_path=self._sqlite_path)
        facade.initialize()

        facade.record_autonomy_session_state(self._record())
        diagnostics = facade.get_autonomy_session_state_lifecycle_diagnostics("2026-06-27T00:00:00+00:00")

        self.assertFalse(facade.sqlite_enabled)
        self.assertIsNone(facade.get_autonomy_session_state("sess-1"))
        self.assertEqual(facade.list_autonomy_session_states(), [])
        self.assertEqual(facade.cleanup_expired_autonomy_session_states("2026-06-27T00:00:00+00:00"), 0)
        self.assertFalse(diagnostics["expired_state_cleanup_supported"])
        self.assertEqual(diagnostics["expired_state_count"], 0)
        self.assertEqual(facade.audit_records(), [])

    def test_sqlite_opt_in_records_and_reads_session_state(self) -> None:
        facade = MemoryFacade(
            enable_sqlite=True,
            jsonl_path=self._audit_path,
            sqlite_path=self._sqlite_path,
        )
        facade.initialize()

        facade.record_autonomy_session_state(self._record())
        loaded = facade.get_autonomy_session_state("sess-1")

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.session_id if loaded else "", "sess-1")
        self.assertEqual(loaded.last_decision if loaded else "", "RETRY")
        self.assertEqual(facade.audit_records(), [])

    def test_list_and_cleanup_via_facade(self) -> None:
        facade = MemoryFacade(
            enable_sqlite=True,
            jsonl_path=self._audit_path,
            sqlite_path=self._sqlite_path,
        )
        facade.initialize()
        expired = self._record("old")
        expired.expires_at = "2026-06-01T00:00:00+00:00"
        fresh = self._record("fresh")
        facade.record_autonomy_session_state(expired)
        facade.record_autonomy_session_state(fresh)

        self.assertEqual(len(facade.list_autonomy_session_states(limit=10)), 2)
        deleted = facade.cleanup_expired_autonomy_session_states("2026-06-27T00:00:00+00:00")

        self.assertEqual(deleted, 1)
        self.assertIsNone(facade.get_autonomy_session_state("old"))
        self.assertIsNotNone(facade.get_autonomy_session_state("fresh"))
        diagnostics = facade.get_autonomy_session_state_lifecycle_diagnostics("2026-06-27T00:00:00+00:00")
        self.assertTrue(diagnostics["expired_state_cleanup_supported"])
        self.assertEqual(diagnostics["last_cleanup_deleted_count"], 1)
        self.assertFalse(diagnostics["cleanup_degraded"])
        self.assertEqual(diagnostics["expired_state_count"], 0)

    def test_lifecycle_diagnostics_count_expired_without_cleanup(self) -> None:
        facade = MemoryFacade(
            enable_sqlite=True,
            jsonl_path=self._audit_path,
            sqlite_path=self._sqlite_path,
        )
        facade.initialize()
        expired = self._record("old")
        expired.expires_at = "2026-06-01T00:00:00+00:00"
        fresh = self._record("fresh")
        facade.record_autonomy_session_state(expired)
        facade.record_autonomy_session_state(fresh)

        diagnostics = facade.get_autonomy_session_state_lifecycle_diagnostics("2026-06-27T00:00:00+00:00")

        self.assertTrue(diagnostics["expired_state_cleanup_supported"])
        self.assertEqual(diagnostics["expired_state_count"], 1)
        self.assertEqual(diagnostics["last_cleanup_deleted_count"], 0)
        self.assertIsNone(facade.get_autonomy_session_state("old"))
        self.assertIsNotNone(facade.get_autonomy_session_state("fresh"))

    def test_facade_degrades_safely_on_sqlite_init_failure(self) -> None:
        clash_file = self._tmp / "db-container"
        clash_file.write_text("", encoding="utf-8")
        facade = MemoryFacade(
            enable_sqlite=True,
            sqlite_path=clash_file / "nested" / "memory.sqlite",
            jsonl_path=self._audit_path,
        )
        facade.initialize()

        facade.record_autonomy_session_state(self._record())

        self.assertFalse(facade.is_sqlite_connected)
        self.assertIsNone(facade.get_autonomy_session_state("sess-1"))
        self.assertEqual(facade.list_autonomy_session_states(), [])
        self.assertEqual(facade.cleanup_expired_autonomy_session_states("2026-06-27T00:00:00+00:00"), 0)
        diagnostics = facade.get_autonomy_session_state_lifecycle_diagnostics("2026-06-27T00:00:00+00:00")
        self.assertFalse(diagnostics["expired_state_cleanup_supported"])
        self.assertFalse(diagnostics["cleanup_degraded"])

    def test_cleanup_failure_produces_safe_degraded_diagnostics(self) -> None:
        facade = MemoryFacade(
            enable_sqlite=True,
            jsonl_path=self._audit_path,
            sqlite_path=self._sqlite_path,
        )
        facade.initialize()
        self.assertIsNotNone(facade._sqlite)

        def fail_cleanup(_now: str = "") -> int:
            raise RuntimeError("cleanup boom with sk-test-secret")

        def fail_count(_now: str = "") -> int:
            raise RuntimeError("count boom with sk-test-secret")

        facade._sqlite.cleanup_expired_autonomy_session_states = fail_cleanup  # type: ignore[method-assign]
        facade._sqlite.count_expired_autonomy_session_states = fail_count  # type: ignore[method-assign]

        deleted = facade.cleanup_expired_autonomy_session_states("2026-06-27T00:00:00+00:00")
        diagnostics = facade.get_autonomy_session_state_lifecycle_diagnostics("2026-06-27T00:00:00+00:00")

        self.assertEqual(deleted, 0)
        self.assertTrue(diagnostics["expired_state_cleanup_supported"])
        self.assertTrue(diagnostics["cleanup_degraded"])
        self.assertIn(diagnostics["cleanup_last_error_category"], {"cleanup_failed", "count_failed"})
        self.assertNotIn("Traceback", str(diagnostics))
        self.assertNotIn("sqlite", diagnostics["cleanup_last_error_category"].lower())


if __name__ == "__main__":
    unittest.main()
