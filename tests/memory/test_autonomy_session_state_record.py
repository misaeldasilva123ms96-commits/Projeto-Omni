from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.memory.memory_models import (  # noqa: E402
    AUTONOMY_SESSION_LIST_MAX,
    AUTONOMY_SESSION_STRING_MAX,
    AutonomySessionStateRecord,
)


class AutonomySessionStateRecordTest(unittest.TestCase):
    def test_model_accepts_allowed_fields(self) -> None:
        record = AutonomySessionStateRecord(
            session_id="sess-1",
            last_error_type="provider_timeout",
            current_error_count=2,
            stagnant_attempts=1,
            distinct_error_count=2,
            distinct_error_types=["timeout", "rate_limit"],
            progressive_cycles=3,
            last_runtime_mode="provider_failure",
            last_provider_failure_type="timeout",
            last_response_length=42,
            last_response_was_safe_fallback=True,
            last_decision="RETRY",
            last_fingerprint_id="abc123",
            last_progress_score=4,
            last_stagnation_score=2,
            repeated_strategy_count=1,
            strategies_attempted=["retry_short_backoff"],
            updated_at="2026-06-27T00:00:00+00:00",
            expires_at="2026-07-04T00:00:00+00:00",
        )

        payload = record.as_dict()

        self.assertEqual(payload["session_id"], "sess-1")
        self.assertEqual(payload["distinct_error_types"], ["timeout", "rate_limit"])
        self.assertEqual(payload["strategies_attempted"], ["retry_short_backoff"])
        self.assertTrue(payload["last_response_was_safe_fallback"])

    def test_from_dict_ignores_forbidden_fields(self) -> None:
        record = AutonomySessionStateRecord.from_dict(
            {
                "session_id": "sess-1",
                "raw_prompt": "do not persist",
                "raw_response": "do not persist",
                "stack_trace": "Traceback ...",
                "headers": {"authorization": "Bearer secret"},
                "api_key": "sk-test-secret",
                "last_error_type": "timeout",
            }
        )

        self.assertIsNotNone(record)
        payload = record.as_dict() if record is not None else {}
        self.assertEqual(payload["last_error_type"], "timeout")
        self.assertNotIn("raw_prompt", payload)
        self.assertNotIn("raw_response", payload)
        self.assertNotIn("stack_trace", payload)
        self.assertNotIn("headers", payload)
        self.assertNotIn("api_key", payload)

    def test_bounds_string_and_list_values(self) -> None:
        record = AutonomySessionStateRecord(
            session_id="sess-1",
            last_error_type="x" * (AUTONOMY_SESSION_STRING_MAX + 20),
            distinct_error_types=[f"type-{idx}" for idx in range(AUTONOMY_SESSION_LIST_MAX + 5)],
            strategies_attempted=[f"strategy-{idx}" for idx in range(AUTONOMY_SESSION_LIST_MAX + 5)],
        )

        self.assertLessEqual(len(record.last_error_type), AUTONOMY_SESSION_STRING_MAX)
        self.assertEqual(len(record.distinct_error_types), AUTONOMY_SESSION_LIST_MAX)
        self.assertEqual(len(record.strategies_attempted), AUTONOMY_SESSION_LIST_MAX)

    def test_secret_like_values_are_redacted_or_dropped(self) -> None:
        record = AutonomySessionStateRecord(
            session_id="sess-1",
            last_error_type="sk-test-secret-value",
            distinct_error_types=["timeout", "token=secret"],
            strategies_attempted=["retry", "Bearer secret"],
        )

        self.assertEqual(record.last_error_type, "[REDACTED]")
        self.assertEqual(record.distinct_error_types, ["timeout"])
        self.assertEqual(record.strategies_attempted, ["retry"])

    def test_missing_session_id_returns_none(self) -> None:
        self.assertIsNone(AutonomySessionStateRecord.from_dict({"last_error_type": "timeout"}))


if __name__ == "__main__":
    unittest.main()
