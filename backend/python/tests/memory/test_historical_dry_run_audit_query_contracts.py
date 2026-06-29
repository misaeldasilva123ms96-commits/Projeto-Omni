from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.memory.historical_audit_query_models import (  # noqa: E402
    DRY_RUN_AUDIT_MAX_LIMIT,
    DryRunAuditQueryRequest,
)
from brain.memory.memory_facade import MemoryFacade  # noqa: E402
from brain.memory.memory_models import (  # noqa: E402
    DRY_RUN_REPLAN_PLAN_EVIDENCE_EVENT_TYPE,
    DRY_RUN_RETRY_PLAN_EVIDENCE_EVENT_TYPE,
    DryRunReplanPlanEvidenceRecord,
    DryRunRetryPlanEvidenceRecord,
)


FORBIDDEN_TEXT = (
    "raw_prompt",
    "rewritten_prompt",
    "raw_response",
    "provider_payload",
    "api_key",
    "token=",
    "stack trace",
    "stdout",
    "stderr",
    "command args",
    "file contents",
    "raw jsonl",
    "raw sql",
    "database row",
)


class HistoricalDryRunAuditQueryContractsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="omni-audit-query-test-"))
        self._audit_path = self._tmp / "audit.jsonl"
        self._sqlite_path = self._tmp / "memory.sqlite"

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _sqlite_facade(self) -> MemoryFacade:
        facade = MemoryFacade(
            enable_sqlite=True,
            jsonl_path=self._audit_path,
            sqlite_path=self._sqlite_path,
        )
        facade.initialize()
        return facade

    def _record_retry(self, facade: MemoryFacade, plan_id: str = "retry-plan") -> None:
        facade.record_dry_run_retry_plan_evidence(
            DryRunRetryPlanEvidenceRecord(
                plan_id=plan_id,
                would_retry=True,
                retry_reason="transient_error",
                blocked=False,
                block_reasons=[],
                retry_eligibility_score=0.75,
                risk_level="low",
                source_decision="RETRY",
                fingerprint_id="fp-retry",
                stagnation_score=2,
                progress_score=8,
                suggested_retry_strategy="same_provider_retry",
                evidence_summary="safe retry summary",
                created_at="2026-06-29T10:00:00Z",
                recorded_at="2026-06-29T10:00:01Z",
                session_id="session-a",
                request_id="request-a",
                trace_id="trace-a",
            )
        )

    def _record_replan(self, facade: MemoryFacade, plan_id: str = "replan-plan") -> None:
        facade.record_dry_run_replan_plan_evidence(
            DryRunReplanPlanEvidenceRecord(
                plan_id=plan_id,
                would_replan=True,
                replan_reason="stagnation",
                blocked=True,
                block_reasons=["user_approval_required"],
                replan_eligibility_score=0.4,
                risk_level="medium",
                source_decision="REPLAN",
                fingerprint_id="fp-replan",
                stagnation_score=9,
                progress_score=1,
                repeated_strategy_count=3,
                suggested_strategy="alternate_safe_strategy",
                evidence_summary="safe replan summary",
                created_at="2026-06-29T11:00:00Z",
                session_id="session-b",
                request_id="request-b",
                trace_id="trace-b",
            )
        )

    def test_list_query_returns_only_safe_allowlisted_fields(self) -> None:
        facade = self._sqlite_facade()
        self._record_retry(facade)
        self._record_replan(facade)

        response = facade.query_historical_dry_run_audit_evidence({"limit": 10})
        payload = response.as_dict()

        self.assertFalse(payload["degraded"])
        self.assertEqual(payload["page_info"]["returned_count"], 2)
        required_keys = {
            "event_type",
            "plan_id",
            "plan_type",
            "advisory",
            "would_retry",
            "would_replan",
            "blocked",
            "block_reasons",
            "risk_level",
            "source_decision",
            "fingerprint_id",
            "progress_score",
            "stagnation_score",
            "retry_eligibility_score",
            "replan_eligibility_score",
            "repeated_strategy_count",
            "suggested_retry_strategy",
            "suggested_strategy",
            "evidence_summary",
            "created_at",
            "recorded_at",
            "request_id",
            "session_id",
            "trace_id",
            "recorded",
            "degraded",
            "storage_mode",
            "sqlite_enabled",
            "persistence",
        }
        for item in payload["items"]:
            self.assertEqual(set(item), required_keys)
            self.assertTrue(item["advisory"])
            self.assertEqual(item["storage_mode"], "sqlite")
            self.assertTrue(item["sqlite_enabled"])

    def test_detail_query_returns_safe_detail_shape(self) -> None:
        facade = self._sqlite_facade()
        self._record_retry(facade, plan_id="detail-plan")

        detail = facade.get_historical_dry_run_audit_evidence_detail("detail-plan")

        self.assertIsNotNone(detail)
        payload = detail.as_dict() if detail is not None else {}
        self.assertEqual(payload["plan_id"], "detail-plan")
        self.assertEqual(payload["event_type"], DRY_RUN_RETRY_PLAN_EVIDENCE_EVENT_TYPE)
        self.assertEqual(payload["storage_metadata"], {
            "storage_mode": "sqlite",
            "sqlite_enabled": True,
        })
        self.assertIn("diagnostic_details", payload)
        self.assertNotIn("raw_sql", str(payload).lower())
        self.assertNotIn("raw_jsonl", str(payload).lower())

    def test_forbidden_fields_never_appear(self) -> None:
        facade = self._sqlite_facade()
        facade.record_dry_run_retry_plan_evidence(
            DryRunRetryPlanEvidenceRecord.from_dict({
                "plan_id": "unsafe-plan",
                "would_retry": True,
                "risk_level": "low",
                "source_decision": "RETRY",
                "evidence_summary": "raw_prompt sk-test provider_payload stdout",
                "raw_prompt": "do not persist",
                "provider_payload": {"token": "secret"},
                "raw_sql": "select * from dry_run_retry_plan_evidence",
            })
        )

        payload = facade.query_historical_dry_run_audit_evidence({"limit": 10}).as_dict()
        serialized = str(payload).lower()

        for forbidden in FORBIDDEN_TEXT:
            self.assertNotIn(forbidden, serialized)
        self.assertIn("redacted", serialized)

    def test_invalid_enum_filter_degrades_safely(self) -> None:
        facade = self._sqlite_facade()
        self._record_retry(facade)

        response = facade.query_historical_dry_run_audit_evidence({
            "filters": {"risk_level": "critical"},
        }).as_dict()

        self.assertTrue(response["degraded"])
        self.assertEqual(response["error_category"], "invalid_filter")
        self.assertEqual(response["items"], [])

    def test_unsupported_filter_is_ignored_with_warning(self) -> None:
        facade = self._sqlite_facade()
        self._record_retry(facade)

        response = facade.query_historical_dry_run_audit_evidence({
            "filters": {"raw_prompt": "secret", "plan_type": "dry_run_retry"},
        }).as_dict()

        self.assertFalse(response["degraded"])
        self.assertIn("unsupported_filter", response["warnings"])
        self.assertEqual(response["applied_filters"], {"plan_type": "dry_run_retry"})
        self.assertEqual(len(response["items"]), 1)

    def test_filtering_by_event_type_and_session_id(self) -> None:
        facade = self._sqlite_facade()
        self._record_retry(facade)
        self._record_replan(facade)

        response = facade.query_historical_dry_run_audit_evidence({
            "filters": {
                "event_type": DRY_RUN_REPLAN_PLAN_EVIDENCE_EVENT_TYPE,
                "session_id": "session-b",
            },
            "limit": 10,
        }).as_dict()

        self.assertEqual(len(response["items"]), 1)
        self.assertEqual(response["items"][0]["plan_type"], "dry_run_replan")

    def test_limit_is_bounded_and_max_page_size_enforced(self) -> None:
        request = DryRunAuditQueryRequest.from_dict({"limit": 1000})

        self.assertEqual(request.limit, DRY_RUN_AUDIT_MAX_LIMIT)

    def test_sort_field_and_direction_are_allowlisted(self) -> None:
        bad_field = DryRunAuditQueryRequest.from_dict({"sort_field": "raw_sql"})
        bad_direction = DryRunAuditQueryRequest.from_dict({"sort_direction": "drop table"})

        self.assertFalse(bad_field.valid)
        self.assertEqual(bad_field.error_category, "invalid_sort")
        self.assertFalse(bad_direction.valid)
        self.assertEqual(bad_direction.error_category, "invalid_sort")

    def test_ordering_is_deterministic(self) -> None:
        facade = self._sqlite_facade()
        self._record_retry(facade, plan_id="b-plan")
        self._record_retry(facade, plan_id="a-plan")

        response = facade.query_historical_dry_run_audit_evidence({
            "limit": 10,
            "sort_field": "created_at",
            "sort_direction": "asc",
        }).as_dict()

        plan_ids = [item["plan_id"] for item in response["items"]]
        self.assertEqual(plan_ids, sorted(plan_ids))

    def test_jsonl_default_mode_degrades_without_raw_line_exposure(self) -> None:
        facade = MemoryFacade(jsonl_path=self._audit_path, sqlite_path=self._sqlite_path)
        facade.initialize()
        self._record_retry(facade)

        response = facade.query_historical_dry_run_audit_evidence({"limit": 10}).as_dict()
        serialized = str(response).lower()

        self.assertTrue(response["degraded"])
        self.assertEqual(response["error_category"], "storage_unavailable")
        self.assertEqual(response["items"], [])
        self.assertIn("historical_audit_query_requires_sqlite", response["warnings"])
        self.assertNotIn("raw jsonl", serialized)
        self.assertNotIn("safe retry summary", serialized)

    def test_storage_failure_degrades_safely(self) -> None:
        facade = self._sqlite_facade()
        facade._sqlite = _FailingSQLite()  # type: ignore[attr-defined]

        response = facade.query_historical_dry_run_audit_evidence({"limit": 10}).as_dict()

        self.assertTrue(response["degraded"])
        self.assertEqual(response["error_category"], "query_failed")
        self.assertEqual(response["items"], [])
        self.assertNotIn("RuntimeError", str(response))
        self.assertNotIn("boom", str(response))

    def test_query_results_are_not_execution_input(self) -> None:
        facade = self._sqlite_facade()
        self._record_retry(facade)

        payload = facade.query_historical_dry_run_audit_evidence({"limit": 1}).as_dict()
        item = payload["items"][0]

        self.assertNotIn("execute", item)
        self.assertNotIn("action", item)
        self.assertNotIn("provider_route", item)
        self.assertTrue(item["advisory"])


class _FailingSQLite:
    def list_dry_run_retry_plan_evidence(self, *args: Any, **kwargs: Any) -> list[Any]:
        raise RuntimeError("boom raw sql select * from secret")

    def list_dry_run_replan_plan_evidence(self, *args: Any, **kwargs: Any) -> list[Any]:
        raise RuntimeError("boom raw sql select * from secret")


if __name__ == "__main__":
    unittest.main()
