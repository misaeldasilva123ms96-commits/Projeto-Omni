from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.memory.historical_audit_query_models import (  # noqa: E402
    DryRunAuditEvidenceDetail,
    DryRunAuditEvidenceItem,
    DryRunAuditPageInfo,
    DryRunAuditQueryRequest,
    DryRunAuditQueryResponse,
    REQUIRED_AUDIT_QUERY_WARNINGS,
)
from brain.memory.historical_audit_query_service import (  # noqa: E402
    HistoricalDryRunAuditQueryService,
    get_historical_dry_run_audit_detail,
    query_historical_dry_run_audit,
)
from brain.memory.memory_models import (  # noqa: E402
    DRY_RUN_RETRY_PLAN_EVIDENCE_EVENT_TYPE,
)


FORBIDDEN_TEXT = (
    "raw_prompt",
    "rewritten_prompt",
    "raw_response",
    "provider_payload",
    "api_key",
    "token=",
    "traceback",
    "stack trace",
    "stdout",
    "stderr",
    "command args",
    "file contents",
    "raw jsonl",
    "raw sql",
    "database row",
    "select *",
)


def _safe_item(plan_id: str = "plan-safe") -> DryRunAuditEvidenceItem:
    return DryRunAuditEvidenceItem(
        event_type=DRY_RUN_RETRY_PLAN_EVIDENCE_EVENT_TYPE,
        plan_id=plan_id,
        plan_type="dry_run_retry",
        advisory=True,
        would_retry=True,
        blocked=False,
        block_reasons=[],
        risk_level="low",
        source_decision="RETRY",
        fingerprint_id="fp-safe",
        progress_score=8,
        stagnation_score=2,
        retry_eligibility_score=0.75,
        evidence_summary="safe metadata summary",
        created_at="2026-06-29T10:00:00Z",
        recorded_at="2026-06-29T10:00:01Z",
        request_id="request-safe",
        session_id="session-safe",
        trace_id="trace-safe",
        storage_mode="unknown",
        sqlite_enabled=False,
    )


def _safe_response(item: DryRunAuditEvidenceItem | None = None) -> DryRunAuditQueryResponse:
    items = [item or _safe_item()]
    return DryRunAuditQueryResponse(
        items=items,
        page_info=DryRunAuditPageInfo(limit=25, offset=0, returned_count=len(items)),
        applied_filters={},
        warnings=[],
        degraded=False,
    )


class _MemoryFacadeSpy:
    def __init__(
        self,
        *,
        response: DryRunAuditQueryResponse | Any | None = None,
        detail: DryRunAuditEvidenceDetail | Any | None = None,
        raise_on_query: bool = False,
        raise_on_detail: bool = False,
    ) -> None:
        self.response = response if response is not None else _safe_response()
        self.detail = detail if detail is not None else DryRunAuditEvidenceDetail(_safe_item())
        self.raise_on_query = raise_on_query
        self.raise_on_detail = raise_on_detail
        self.query_calls: list[DryRunAuditQueryRequest] = []
        self.detail_calls: list[str] = []

    def query_historical_dry_run_audit_evidence(
        self,
        request: DryRunAuditQueryRequest,
    ) -> DryRunAuditQueryResponse:
        self.query_calls.append(request)
        if self.raise_on_query:
            raise RuntimeError("raw_prompt token=secret traceback select * from database row")
        return self.response

    def get_historical_dry_run_audit_evidence_detail(
        self,
        plan_id: str,
    ) -> DryRunAuditEvidenceDetail | None:
        self.detail_calls.append(plan_id)
        if self.raise_on_detail:
            raise RuntimeError("raw_response provider_payload stack trace")
        return self.detail

    def __getattr__(self, name: str) -> Any:
        if any(marker in name.lower() for marker in ("sqlite", "jsonl", "sql", "runtime", "provider")):
            raise AssertionError(f"unsafe access attempted: {name}")
        raise AttributeError(name)


class HistoricalDryRunAuditQueryServiceTest(unittest.TestCase):
    def test_list_query_delegates_to_memory_facade_safe_method_only(self) -> None:
        facade = _MemoryFacadeSpy()
        service = HistoricalDryRunAuditQueryService(facade)
        request = DryRunAuditQueryRequest.from_dict({"limit": 10})

        response = service.query_historical_dry_run_audit(request)

        self.assertIs(response, facade.response)
        self.assertEqual(facade.query_calls, [request])
        self.assertEqual(facade.detail_calls, [])

    def test_detail_read_delegates_to_memory_facade_safe_method_only(self) -> None:
        facade = _MemoryFacadeSpy()
        service = HistoricalDryRunAuditQueryService(facade)

        detail = service.get_historical_dry_run_audit_detail("plan-safe")

        self.assertIs(detail, facade.detail)
        self.assertEqual(facade.detail_calls, ["plan-safe"])
        self.assertEqual(facade.query_calls, [])

    def test_module_helpers_delegate_through_service(self) -> None:
        facade = _MemoryFacadeSpy()
        request = DryRunAuditQueryRequest.from_dict({"limit": 5})

        response = query_historical_dry_run_audit(facade, request)
        detail = get_historical_dry_run_audit_detail(facade, "plan-safe")

        self.assertIs(response, facade.response)
        self.assertIs(detail, facade.detail)

    def test_invalid_input_degrades_without_memory_facade_call(self) -> None:
        facade = _MemoryFacadeSpy()
        service = HistoricalDryRunAuditQueryService(facade)

        response = service.query_historical_dry_run_audit({"filters": {}})  # type: ignore[arg-type]
        payload = response.as_dict()

        self.assertTrue(payload["degraded"])
        self.assertEqual(payload["error_category"], "invalid_request")
        self.assertEqual(facade.query_calls, [])

    def test_invalid_request_degrades_before_memory_facade_call(self) -> None:
        facade = _MemoryFacadeSpy()
        service = HistoricalDryRunAuditQueryService(facade)
        request = DryRunAuditQueryRequest.from_dict({"filters": {"risk_level": "critical"}})

        response = service.query_historical_dry_run_audit(request).as_dict()

        self.assertTrue(response["degraded"])
        self.assertEqual(response["error_category"], "invalid_filter")
        self.assertEqual(facade.query_calls, [])

    def test_filter_sort_enum_limit_timestamp_and_id_validation_are_enforced(self) -> None:
        good = DryRunAuditQueryRequest.from_dict({
            "filters": {
                "plan_type": "dry_run_retry",
                "event_type": DRY_RUN_RETRY_PLAN_EVIDENCE_EVENT_TYPE,
                "source_decision": "RETRY",
                "risk_level": "low",
                "blocked": "false",
                "request_id": "request-safe",
                "created_at_from": "2026-06-29T00:00:00Z",
                "created_at_to": "2026-06-30T00:00:00Z",
            },
            "limit": 1000,
            "sort_field": "risk_level",
            "sort_direction": "asc",
        })
        bad_timestamp = DryRunAuditQueryRequest.from_dict({
            "filters": {
                "created_at_from": "2026-06-30T00:00:00Z",
                "created_at_to": "2026-06-29T00:00:00Z",
            },
        })
        bad_id = DryRunAuditQueryRequest.from_dict({"filters": {"request_id": "../secret"}})
        bad_sort = DryRunAuditQueryRequest.from_dict({"sort_field": "raw_sql"})

        self.assertTrue(good.valid)
        self.assertEqual(good.limit, 100)
        self.assertEqual(good.applied_filters["blocked"], False)
        self.assertFalse(bad_timestamp.valid)
        self.assertEqual(bad_timestamp.error_category, "invalid_filter")
        self.assertFalse(bad_id.valid)
        self.assertEqual(bad_id.error_category, "invalid_filter")
        self.assertFalse(bad_sort.valid)
        self.assertEqual(bad_sort.error_category, "invalid_sort")

    def test_service_preserves_max_page_size_and_required_warnings(self) -> None:
        facade = _MemoryFacadeSpy()
        request = DryRunAuditQueryRequest.from_dict({"limit": 1000})

        response = HistoricalDryRunAuditQueryService(facade).query_historical_dry_run_audit(
            request
        ).as_dict()

        self.assertEqual(facade.query_calls[0].limit, 100)
        for warning in REQUIRED_AUDIT_QUERY_WARNINGS:
            self.assertIn(warning, response["warnings"])

    def test_service_output_contains_only_safe_response_fields(self) -> None:
        facade = _MemoryFacadeSpy()
        response = HistoricalDryRunAuditQueryService(facade).query_historical_dry_run_audit(
            DryRunAuditQueryRequest()
        )
        payload = response.as_dict()

        self.assertEqual(
            set(payload),
            {"items", "page_info", "applied_filters", "warnings", "degraded", "generated_at"},
        )
        item_keys = set(payload["items"][0])
        self.assertIn("persistence", item_keys)
        self.assertNotIn("raw_prompt", item_keys)
        self.assertNotIn("provider_payload", item_keys)

    def test_forbidden_fields_never_appear_in_list_or_detail_responses(self) -> None:
        facade = _MemoryFacadeSpy()
        service = HistoricalDryRunAuditQueryService(facade)

        list_payload = service.query_historical_dry_run_audit(DryRunAuditQueryRequest()).as_dict()
        detail = service.get_historical_dry_run_audit_detail("plan-safe")
        detail_payload = detail.as_dict() if detail is not None else {}
        serialized = f"{list_payload} {detail_payload}".lower()

        for forbidden in FORBIDDEN_TEXT:
            self.assertNotIn(forbidden, serialized)

    def test_memory_facade_query_error_degrades_without_raw_exception(self) -> None:
        facade = _MemoryFacadeSpy(raise_on_query=True)
        response = HistoricalDryRunAuditQueryService(facade).query_historical_dry_run_audit(
            DryRunAuditQueryRequest()
        ).as_dict()
        serialized = str(response).lower()

        self.assertTrue(response["degraded"])
        self.assertEqual(response["error_category"], "query_failed")
        for forbidden in FORBIDDEN_TEXT:
            self.assertNotIn(forbidden, serialized)

    def test_memory_facade_detail_error_degrades_to_none_without_raw_exception(self) -> None:
        audit_events: list[dict[str, Any]] = []
        facade = _MemoryFacadeSpy(raise_on_detail=True)
        service = HistoricalDryRunAuditQueryService(facade, audit_logger=audit_events.append)

        detail = service.get_historical_dry_run_audit_detail("plan-safe")

        self.assertIsNone(detail)
        self.assertEqual(audit_events[-1]["error_category"], "query_failed")
        for forbidden in FORBIDDEN_TEXT:
            self.assertNotIn(forbidden, str(audit_events).lower())

    def test_invalid_detail_plan_id_does_not_call_memory_facade(self) -> None:
        facade = _MemoryFacadeSpy()
        detail = HistoricalDryRunAuditQueryService(facade).get_historical_dry_run_audit_detail(
            "../secret"
        )

        self.assertIsNone(detail)
        self.assertEqual(facade.detail_calls, [])

    def test_invalid_memory_facade_response_degrades_safely(self) -> None:
        facade = _MemoryFacadeSpy(response={"raw_response": "provider_payload"})

        response = HistoricalDryRunAuditQueryService(facade).query_historical_dry_run_audit(
            DryRunAuditQueryRequest()
        ).as_dict()

        self.assertTrue(response["degraded"])
        self.assertEqual(response["error_category"], "invalid_memoryfacade_response")
        self.assertNotIn("provider_payload", str(response).lower())

    def test_unsafe_request_error_category_is_replaced(self) -> None:
        facade = _MemoryFacadeSpy()
        request = DryRunAuditQueryRequest()
        request.valid = False
        request.error_category = "raw sql select * from database row"

        response = HistoricalDryRunAuditQueryService(facade).query_historical_dry_run_audit(
            request
        ).as_dict()
        serialized = str(response).lower()

        self.assertTrue(response["degraded"])
        self.assertEqual(response["error_category"], "invalid_request")
        self.assertEqual(facade.query_calls, [])
        for forbidden in FORBIDDEN_TEXT:
            self.assertNotIn(forbidden, serialized)

    def test_unsafe_memory_facade_error_category_is_replaced(self) -> None:
        unsafe_response = DryRunAuditQueryResponse(
            items=[],
            page_info=DryRunAuditPageInfo(limit=25, offset=0, returned_count=0),
            degraded=True,
            error_category="raw jsonl raw sql database row",
        )
        facade = _MemoryFacadeSpy(response=unsafe_response)

        response = HistoricalDryRunAuditQueryService(facade).query_historical_dry_run_audit(
            DryRunAuditQueryRequest()
        ).as_dict()
        serialized = str(response).lower()

        self.assertTrue(response["degraded"])
        self.assertEqual(response["error_category"], "invalid_memoryfacade_response")
        for forbidden in FORBIDDEN_TEXT:
            self.assertNotIn(forbidden, serialized)

    def test_audit_logger_receives_safe_metadata_only(self) -> None:
        audit_events: list[dict[str, Any]] = []
        facade = _MemoryFacadeSpy()
        request = DryRunAuditQueryRequest.from_dict({
            "filters": {
                "request_id": "request-safe",
                "session_id": "session-safe",
                "trace_id": "trace-safe",
            },
            "limit": 10,
            "sort_field": "recorded_at",
            "sort_direction": "desc",
        })

        HistoricalDryRunAuditQueryService(
            facade,
            audit_logger=audit_events.append,
        ).query_historical_dry_run_audit(request)

        self.assertEqual(len(audit_events), 1)
        event = audit_events[0]
        self.assertEqual(event["operation_name"], "query_historical_dry_run_audit")
        self.assertEqual(event["filter_keys"], ["request_id", "session_id", "trace_id"])
        self.assertEqual(event["request_id"], "request-safe")
        self.assertNotIn("items", event)
        self.assertNotIn("raw_request", event)
        self.assertNotIn("raw_response", event)

    def test_audit_logger_failure_is_ignored(self) -> None:
        def bad_logger(_event: dict[str, Any]) -> None:
            raise RuntimeError("stack trace token=secret")

        facade = _MemoryFacadeSpy()
        service = HistoricalDryRunAuditQueryService(facade, audit_logger=bad_logger)

        response = service.query_historical_dry_run_audit(DryRunAuditQueryRequest())

        self.assertIs(response, facade.response)

    def test_runtime_provider_calls_are_not_made_and_results_are_not_execution_input(self) -> None:
        facade = _MemoryFacadeSpy()
        payload = HistoricalDryRunAuditQueryService(facade).query_historical_dry_run_audit(
            DryRunAuditQueryRequest()
        ).as_dict()
        serialized = str(payload).lower()

        self.assertNotIn("execute_retry", serialized)
        self.assertNotIn("execute_replan", serialized)
        self.assertNotIn("provider_call", serialized)
        self.assertNotIn("execution_input", serialized)


if __name__ == "__main__":
    unittest.main()
