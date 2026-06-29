from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.memory.memory_models import (
    DRY_RUN_REPLAN_PLAN_EVIDENCE_EVENT_TYPE,
    DRY_RUN_REPLAN_EVIDENCE_LIST_MAX,
    DRY_RUN_REPLAN_EVIDENCE_SUMMARY_MAX,
    DryRunReplanPlanEvidenceRecord,
)


class DryRunReplanPlanEvidenceRecordTest(unittest.TestCase):
    def test_record_serializes_only_allowed_fields(self) -> None:
        record = DryRunReplanPlanEvidenceRecord.from_dict({
            "plan_id": "plan-1",
            "plan_type": "dry_run_replan",
            "advisory": False,
            "would_replan": True,
            "replan_reason": "replan_eligible",
            "blocked": False,
            "block_reasons": ["strategy_stuck"],
            "replan_eligibility_score": 0.75,
            "risk_level": "low",
            "source_decision": "REPLAN",
            "fingerprint_id": "fp-1",
            "stagnation_score": 8,
            "progress_score": 2,
            "repeated_strategy_count": 3,
            "suggested_strategy": "change_safe_strategy_category",
            "evidence_summary": "safe bounded summary",
            "created_at": "2026-06-29T00:00:00+00:00",
            "session_id": "session-1",
            "request_id": "request-1",
            "trace_id": "trace-1",
            "raw_prompt": "must not persist",
            "rewritten_prompt": "must not persist",
            "raw_response": "must not persist",
            "provider_payload": {"raw": "must not persist"},
            "api_key": "sk-test-secret",
            "extra_field": "must not persist",
        })

        self.assertIsNotNone(record)
        payload = record.as_dict() if record else {}
        self.assertEqual(payload["event_type"], DRY_RUN_REPLAN_PLAN_EVIDENCE_EVENT_TYPE)
        self.assertTrue(payload["advisory"])
        self.assertNotIn("raw_prompt", payload)
        self.assertNotIn("rewritten_prompt", payload)
        self.assertNotIn("raw_response", payload)
        self.assertNotIn("provider_payload", payload)
        self.assertNotIn("api_key", payload)
        self.assertNotIn("extra_field", payload)

    def test_event_type_is_forced(self) -> None:
        record = DryRunReplanPlanEvidenceRecord(
            plan_id="plan-1",
            event_type="unsafe_event",
        )

        self.assertEqual(record.event_type, DRY_RUN_REPLAN_PLAN_EVIDENCE_EVENT_TYPE)
        self.assertEqual(record.as_dict()["event_type"], DRY_RUN_REPLAN_PLAN_EVIDENCE_EVENT_TYPE)

    def test_forbidden_values_are_redacted_or_stripped(self) -> None:
        record = DryRunReplanPlanEvidenceRecord.from_dict({
            "plan_id": "plan-1",
            "evidence_summary": "raw_prompt contains secret=abc",
            "suggested_strategy": "provider_payload should not appear",
            "session_id": "session-token=abc",
            "request_id": "request-1",
            "trace_id": "trace-1",
        })

        self.assertIsNotNone(record)
        payload = record.as_dict() if record else {}
        self.assertEqual(payload["evidence_summary"], "[REDACTED]")
        self.assertEqual(payload["suggested_strategy"], "[REDACTED]")
        self.assertEqual(payload["session_id"], "[REDACTED]")
        self.assertNotIn("secret=abc", str(payload))
        self.assertNotIn("provider_payload", str(payload))

    def test_strings_and_block_reasons_are_bounded(self) -> None:
        long_summary = "safe " * 100
        reasons = [f"reason-{idx}" for idx in range(DRY_RUN_REPLAN_EVIDENCE_LIST_MAX + 5)]
        record = DryRunReplanPlanEvidenceRecord(
            plan_id="plan-1",
            evidence_summary=long_summary,
            block_reasons=reasons,
        )

        payload = record.as_dict()
        self.assertLessEqual(len(payload["evidence_summary"]), DRY_RUN_REPLAN_EVIDENCE_SUMMARY_MAX)
        self.assertEqual(len(payload["block_reasons"]), DRY_RUN_REPLAN_EVIDENCE_LIST_MAX)

    def test_malformed_missing_values_degrade_safely(self) -> None:
        self.assertIsNone(DryRunReplanPlanEvidenceRecord.from_dict({}))
        self.assertIsNone(DryRunReplanPlanEvidenceRecord.from_dict({"plan_id": ""}))

        record = DryRunReplanPlanEvidenceRecord.from_dict({
            "plan_id": "plan-1",
            "replan_eligibility_score": "not-a-score",
            "stagnation_score": "not-a-count",
            "block_reasons": "not-a-list",
        })

        self.assertIsNotNone(record)
        payload = record.as_dict() if record else {}
        self.assertEqual(payload["replan_eligibility_score"], 0.0)
        self.assertEqual(payload["stagnation_score"], 0)
        self.assertEqual(payload["block_reasons"], [])


if __name__ == "__main__":
    unittest.main()
