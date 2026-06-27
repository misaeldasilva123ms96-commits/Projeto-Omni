from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.memory.memory_models import AutonomySessionStateRecord  # noqa: E402
from brain.memory.sqlite_adapter import SQLiteAdapter  # noqa: E402


class AutonomySessionStateSQLiteTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="omni-autonomy-state-sqlite-"))
        self._db_path = self._tmp / "memory.sqlite"
        self.adapter = SQLiteAdapter(self._db_path)
        self.adapter.connect()

    def tearDown(self) -> None:
        try:
            self.adapter.close()
        except Exception:
            pass
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

    def test_sqlite_table_created(self) -> None:
        self.assertTrue(self.adapter.table_exists("autonomy_session_states"))

    def test_upsert_and_read_by_session_id(self) -> None:
        self.adapter.upsert_autonomy_session_state(self._record())

        loaded = self.adapter.get_autonomy_session_state("sess-1")

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.session_id if loaded else "", "sess-1")
        self.assertEqual(loaded.distinct_error_types if loaded else [], ["timeout"])
        self.assertTrue(loaded.last_response_was_safe_fallback if loaded else False)

    def test_upsert_replaces_existing_row(self) -> None:
        self.adapter.upsert_autonomy_session_state(self._record())
        updated = self._record()
        updated.current_error_count = 5
        updated.last_decision = "REPLAN"

        self.adapter.upsert_autonomy_session_state(updated)
        loaded = self.adapter.get_autonomy_session_state("sess-1")

        self.assertEqual(loaded.current_error_count if loaded else 0, 5)
        self.assertEqual(loaded.last_decision if loaded else "", "REPLAN")
        self.assertEqual(self.adapter.table_count("autonomy_session_states"), 1)

    def test_list_with_limit(self) -> None:
        self.adapter.upsert_autonomy_session_state(self._record("sess-1"))
        self.adapter.upsert_autonomy_session_state(self._record("sess-2"))

        records = self.adapter.list_autonomy_session_states(limit=1)

        self.assertEqual(len(records), 1)

    def test_cleanup_expired_states(self) -> None:
        expired = self._record("old")
        expired.expires_at = "2026-06-01T00:00:00+00:00"
        fresh = self._record("fresh")
        fresh.expires_at = "2999-07-04T00:00:00+00:00"
        self.adapter.upsert_autonomy_session_state(expired)
        self.adapter.upsert_autonomy_session_state(fresh)

        self.assertIsNone(self.adapter.get_autonomy_session_state("old"))

        deleted = self.adapter.cleanup_expired_autonomy_session_states("2026-06-27T00:00:00+00:00")

        self.assertEqual(deleted, 1)
        self.assertIsNone(self.adapter.get_autonomy_session_state("old"))
        self.assertIsNotNone(self.adapter.get_autonomy_session_state("fresh"))

    def test_count_expired_states_without_deleting(self) -> None:
        expired = self._record("old")
        expired.expires_at = "2026-06-01T00:00:00+00:00"
        fresh = self._record("fresh")
        fresh.expires_at = "2999-07-04T00:00:00+00:00"
        self.adapter.upsert_autonomy_session_state(expired)
        self.adapter.upsert_autonomy_session_state(fresh)

        count = self.adapter.count_expired_autonomy_session_states("2026-06-27T00:00:00+00:00")

        self.assertEqual(count, 1)
        self.assertEqual(self.adapter.table_count("autonomy_session_states"), 2)

    def test_corrupt_list_row_degrades_to_none(self) -> None:
        self.adapter._execute(
            "INSERT OR REPLACE INTO autonomy_session_states (session_id, distinct_error_types, strategies_attempted, updated_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?)",
            "corrupt",
            "[not-json",
            "[]",
            "2026-06-27T00:00:00+00:00",
            "2999-07-04T00:00:00+00:00",
        )

        self.assertIsNone(self.adapter.get_autonomy_session_state("corrupt"))


if __name__ == "__main__":
    unittest.main()
