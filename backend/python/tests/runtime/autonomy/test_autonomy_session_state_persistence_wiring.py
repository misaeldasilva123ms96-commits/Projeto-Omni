from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any

from brain.memory.memory_facade import MemoryFacade
from brain.memory.memory_models import AutonomySessionStateRecord
from brain.runtime.autonomy import AutonomyController, AutonomySessionTracker, DecisionType
from brain.runtime.autonomy.error_progress_tracker import SmartErrorProgressTracker
from brain.runtime.autonomy.runtime_wiring import evaluate_autonomy


class _SpyFacade:
    def __init__(self, *, sqlite_enabled: bool, connected: bool, fail_read: bool = False, fail_write: bool = False) -> None:
        self.sqlite_enabled = sqlite_enabled
        self.is_sqlite_connected = connected
        self.fail_read = fail_read
        self.fail_write = fail_write
        self.reads: list[str] = []
        self.writes: list[AutonomySessionStateRecord] = []
        self.record: AutonomySessionStateRecord | None = None

    def get_autonomy_session_state(self, session_id: str) -> AutonomySessionStateRecord | None:
        self.reads.append(session_id)
        if self.fail_read:
            raise RuntimeError("read failed")
        return self.record

    def record_autonomy_session_state(self, record: AutonomySessionStateRecord) -> None:
        self.writes.append(record)
        if self.fail_write:
            raise RuntimeError("write failed")
        self.record = record


class AutonomySessionStatePersistenceWiringTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="omni-autonomy-runtime-state-"))
        self._sqlite_path = self._tmp / "memory.sqlite"
        self._audit_path = self._tmp / "audit.jsonl"

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _controller(self) -> AutonomyController:
        return AutonomyController(emit_governance_events=False)

    def _evaluate(
        self,
        inspection: dict[str, Any],
        tracker: AutonomySessionTracker,
        response: str = "ok",
    ) -> dict[str, Any]:
        return evaluate_autonomy(
            inspection,
            "sess-1",
            response,
            controller=self._controller(),
            tracker=tracker,
            smart_tracker=SmartErrorProgressTracker(),
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

    def test_sqlite_disabled_keeps_process_local_behavior(self) -> None:
        facade = _SpyFacade(sqlite_enabled=False, connected=False)
        tracker = AutonomySessionTracker(memory_facade=facade)  # type: ignore[arg-type]
        inspection = {"signals": {"failure_class": "timeout", "runtime_mode": "standard"}}

        result = self._evaluate(inspection, tracker)

        self.assertTrue(result["advisory"])
        self.assertEqual(facade.reads, [])
        self.assertEqual(facade.writes, [])
        self.assertEqual(tracker.get_state("sess-1").current_error_count, 1)  # type: ignore[union-attr]

    def test_jsonl_default_does_not_attempt_session_state_persistence(self) -> None:
        facade = MemoryFacade(sqlite_path=self._sqlite_path, jsonl_path=self._audit_path)
        facade.initialize()
        tracker = AutonomySessionTracker(memory_facade=facade)
        inspection = {"signals": {"failure_class": "timeout", "runtime_mode": "standard"}}

        self._evaluate(inspection, tracker)

        self.assertFalse(facade.sqlite_enabled)
        self.assertIsNone(facade.get_autonomy_session_state("sess-1"))
        self.assertEqual(facade.audit_records(), [])

    def test_sqlite_enabled_hydrates_tracker_from_persisted_state(self) -> None:
        facade = self._sqlite_facade()
        facade.record_autonomy_session_state(
            AutonomySessionStateRecord(
                session_id="sess-1",
                last_error_type="timeout",
                current_error_count=4,
                distinct_error_count=1,
                distinct_error_types=["timeout"],
                updated_at="2026-06-27T00:00:00+00:00",
                expires_at="2999-01-01T00:00:00+00:00",
            )
        )
        tracker = AutonomySessionTracker(memory_facade=facade)
        inspection = {"signals": {"failure_class": "timeout", "runtime_mode": "standard"}}

        self._evaluate(inspection, tracker)

        state = tracker.get_state("sess-1")
        self.assertIsNotNone(state)
        self.assertEqual(state.current_error_count if state else 0, 5)

    def test_sqlite_enabled_upserts_after_evaluation(self) -> None:
        facade = self._sqlite_facade()
        tracker = AutonomySessionTracker(memory_facade=facade)
        inspection = {"signals": {"failure_class": "timeout", "runtime_mode": "standard"}}

        self._evaluate(inspection, tracker)
        persisted = facade.get_autonomy_session_state("sess-1")

        self.assertIsNotNone(persisted)
        self.assertEqual(persisted.current_error_count if persisted else 0, 1)
        self.assertEqual(persisted.last_error_type if persisted else "", "timeout")
        self.assertEqual(persisted.last_decision if persisted else "", DecisionType.RETRY.value)

    def test_missing_persisted_state_falls_back_to_new_process_local_state(self) -> None:
        facade = self._sqlite_facade()
        tracker = AutonomySessionTracker(memory_facade=facade)

        self._evaluate({"signals": {"failure_class": "timeout", "runtime_mode": "standard"}}, tracker)

        state = tracker.get_state("sess-1")
        self.assertEqual(state.current_error_count if state else 0, 1)

    def test_corrupt_persisted_state_falls_back_safely(self) -> None:
        facade = self._sqlite_facade()
        self.assertIsNotNone(facade._sqlite)
        facade._sqlite._execute(
            "INSERT OR REPLACE INTO autonomy_session_states (session_id, distinct_error_types, strategies_attempted, updated_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?)",
            "sess-1",
            "[not-json",
            "[]",
            "2026-06-27T00:00:00+00:00",
            "2999-01-01T00:00:00+00:00",
        )
        tracker = AutonomySessionTracker(memory_facade=facade)

        self._evaluate({"signals": {"failure_class": "timeout", "runtime_mode": "standard"}}, tracker)

        state = tracker.get_state("sess-1")
        self.assertEqual(state.current_error_count if state else 0, 1)

    def test_memory_facade_read_failure_does_not_break_runtime(self) -> None:
        facade = _SpyFacade(sqlite_enabled=True, connected=True, fail_read=True)
        tracker = AutonomySessionTracker(memory_facade=facade)  # type: ignore[arg-type]

        result = self._evaluate({"signals": {"failure_class": "timeout", "runtime_mode": "standard"}}, tracker)

        self.assertTrue(result["advisory"])
        self.assertEqual(tracker.get_state("sess-1").current_error_count, 1)  # type: ignore[union-attr]

    def test_memory_facade_write_failure_does_not_break_runtime(self) -> None:
        facade = _SpyFacade(sqlite_enabled=True, connected=True, fail_write=True)
        tracker = AutonomySessionTracker(memory_facade=facade)  # type: ignore[arg-type]

        result = self._evaluate({"signals": {"failure_class": "timeout", "runtime_mode": "standard"}}, tracker)

        self.assertTrue(result["advisory"])
        self.assertEqual(tracker.get_state("sess-1").current_error_count, 1)  # type: ignore[union-attr]

    def test_raw_prompt_response_and_secret_are_not_persisted(self) -> None:
        facade = self._sqlite_facade()
        tracker = AutonomySessionTracker(memory_facade=facade)
        inspection = {
            "signals": {
                "failure_class": "timeout",
                "runtime_mode": "standard",
                "raw_prompt": "secret prompt",
                "api_key": "sk-test-secret",
            },
            "raw_response": "secret response",
        }

        self._evaluate(inspection, tracker, response="secret response")
        persisted = facade.get_autonomy_session_state("sess-1")
        payload = persisted.as_dict() if persisted is not None else {}
        as_text = str(payload)

        self.assertNotIn("raw_prompt", as_text)
        self.assertNotIn("raw_response", as_text)
        self.assertNotIn("secret prompt", as_text)
        self.assertNotIn("secret response", as_text)
        self.assertNotIn("sk-test-secret", as_text)

    def test_response_string_result_is_unchanged_with_sqlite_disabled(self) -> None:
        inspection = {"signals": {"failure_class": "timeout", "runtime_mode": "standard"}}
        baseline = self._evaluate(inspection, AutonomySessionTracker())
        sqlite_disabled = self._evaluate(
            inspection,
            AutonomySessionTracker(memory_facade=_SpyFacade(sqlite_enabled=False, connected=False)),  # type: ignore[arg-type]
        )

        self.assertEqual(sqlite_disabled, baseline)

    def test_advisory_only_decisions_remain_advisory(self) -> None:
        result = self._evaluate(
            {"signals": {"failure_class": "timeout", "runtime_mode": "standard"}},
            AutonomySessionTracker(memory_facade=_SpyFacade(sqlite_enabled=False, connected=False)),  # type: ignore[arg-type]
        )

        self.assertTrue(result["advisory"])
        self.assertNotEqual(result["decision"], DecisionType.SELF_REPAIR.value)
        self.assertNotEqual(result["decision"], DecisionType.SWITCH_PROVIDER.value)


if __name__ == "__main__":
    unittest.main()
