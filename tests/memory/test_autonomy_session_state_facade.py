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

        self.assertFalse(facade.sqlite_enabled)
        self.assertIsNone(facade.get_autonomy_session_state("sess-1"))
        self.assertEqual(facade.list_autonomy_session_states(), [])
        self.assertEqual(facade.cleanup_expired_autonomy_session_states("2026-06-27T00:00:00+00:00"), 0)
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


if __name__ == "__main__":
    unittest.main()
