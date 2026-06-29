from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.memory.memory_models import (
    DRY_RUN_RETRY_EVIDENCE_LIST_MAX,
    DRY_RUN_RETRY_EVIDENCE_SUMMARY_MAX,
    DRY_RUN_RETRY_PLAN_EVIDENCE_EVENT_TYPE,
    DryRunRetryPlanEvidenceRecord,
)


class DryRunRetryPlanEvidenceRecordTest(unittest.TestCase):
    def test_record_serializes_only_allowed_fields(self) -> None:
        record = DryRunRetryPlanEvidenceRecord.from_dict({
            "plan_id": "plan-1",
            "plan_type": "dry_run_retry",
            "advisory": False,
            "would_retry": True,
            "retry_reason": "transient_provider_timeout",
            "blocked": False,
            "block_reasons": ["retry_budget_available"],
            "retry_eligibility_score": 0.75,
            "risk_level": "low",
            "source_decision": "RETRY",
            "fingerprint_id": "fp-1",
            "stagnation_score": 8,
            "progress_score": 2,
            "suggested_retry_strategy": "same_provider_safe_retry",
            "evidence_summary": "safe bounded summary",
            "created_at": "2026-06-29T00:00:00+00:00",
            "recorded_at": "2026-06-29T00:00:01+00:00",
            "session_id": "session-1",
            "request_id": "request-1",
            "trace_id": "trace-1",
            "raw_prompt": "must not persist",
            "rewritten_prompt": "must not persist",
            "raw_response": "must not persist",
            "provider_payload": {"raw": "must not persist"},
            "provider_credentials": "must not persist",
            "api_key": "sk-test-secret",
            "headers": {"authorization": "bearer token"},
            "cookies": "must not persist",
            "stack_trace": "must not persist",
            "stdout": "must not persist",
            "stderr": "must not persist",
            "command_args": "--unsafe",
            "file_contents": "must not persist",
            ".env": "SECRET=1",
            "tool_output": "must not persist",
            "raw_receipt": "must not persist",
            "raw_exception": "must not persist",
            "repr": "must not persist",
            "extra_field": "must not persist",
        })

        self.assertIsNotNone(record)
        payload = record.as_dict() if record else {}
        self.assertEqual(payload["event_type"], DRY_RUN_RETRY_PLAN_EVIDENCE_EVENT_TYPE)
        self.assertTrue(payload["advisory"])
        self.assertNotIn("raw_prompt", payload)
        self.assertNotIn("rewritten_prompt", payload)
        self.assertNotIn("raw_response", payload)
        self.assertNotIn("provider_payload", payload)
        self.assertNotIn("provider_credentials", payload)
        self.assertNotIn("api_key", payload)
        self.assertNotIn("headers", payload)
        self.assertNotIn("cookies", payload)
        self.assertNotIn("stack_trace", payload)
        self.assertNotIn("stdout", payload)
        self.assertNotIn("stderr", payload)
        self.assertNotIn("command_args", payload)
        self.assertNotIn("file_contents", payload)
        self.assertNotIn(".env", payload)
        self.assertNotIn("tool_output", payload)
        self.assertNotIn("raw_receipt", payload)
        self.assertNotIn("raw_exception", payload)
        self.assertNotIn("repr", payload)
        self.assertNotIn("extra_field", payload)

    def test_event_type_is_forced(self) -> None:
        record = DryRunRetryPlanEvidenceRecord(
            plan_id="plan-1",
            event_type="unsafe_event",
        )

        self.assertEqual(record.event_type, DRY_RUN_RETRY_PLAN_EVIDENCE_EVENT_TYPE)
        self.assertEqual(record.as_dict()["event_type"], DRY_RUN_RETRY_PLAN_EVIDENCE_EVENT_TYPE)

    def test_forbidden_values_are_redacted_or_stripped(self) -> None:
        record = DryRunRetryPlanEvidenceRecord.from_dict({
            "plan_id": "plan-1",
            "evidence_summary": "raw prompt contains secret=abc",
            "suggested_retry_strategy": "provider payload should not appear",
            "session_id": "session-token=abc",
            "request_id": "request-1",
            "trace_id": "trace-1",
        })

        self.assertIsNotNone(record)
        payload = record.as_dict() if record else {}
        self.assertEqual(payload["evidence_summary"], "[REDACTED]")
        self.assertEqual(payload["suggested_retry_strategy"], "[REDACTED]")
        self.assertEqual(payload["session_id"], "[REDACTED]")
        self.assertNotIn("secret=abc", str(payload))
        self.assertNotIn("provider payload", str(payload))

    def test_strings_and_block_reasons_are_bounded(self) -> None:
        long_summary = "safe " * 100
        reasons = [f"reason-{idx}" for idx in range(DRY_RUN_RETRY_EVIDENCE_LIST_MAX + 5)]
        record = DryRunRetryPlanEvidenceRecord(
            plan_id="plan-1",
            evidence_summary=long_summary,
            block_reasons=reasons,
        )

        payload = record.as_dict()
        self.assertLessEqual(len(payload["evidence_summary"]), DRY_RUN_RETRY_EVIDENCE_SUMMARY_MAX)
        self.assertEqual(len(payload["block_reasons"]), DRY_RUN_RETRY_EVIDENCE_LIST_MAX)

    def test_malformed_missing_values_degrade_safely(self) -> None:
        self.assertIsNone(DryRunRetryPlanEvidenceRecord.from_dict({}))
        self.assertIsNone(DryRunRetryPlanEvidenceRecord.from_dict({"plan_id": ""}))

        record = DryRunRetryPlanEvidenceRecord.from_dict({
            "plan_id": "plan-1",
            "retry_eligibility_score": "not-a-score",
            "stagnation_score": "not-a-count",
            "block_reasons": "not-a-list",
        })

        self.assertIsNotNone(record)
        payload = record.as_dict() if record else {}
        self.assertEqual(payload["retry_eligibility_score"], 0.0)
        self.assertEqual(payload["stagnation_score"], 0)
        self.assertEqual(payload["block_reasons"], [])


if __name__ == "__main__":
    unittest.main()
