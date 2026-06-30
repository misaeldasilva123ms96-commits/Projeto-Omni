from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

for parent in Path(__file__).resolve().parents:
    candidate = parent / "backend" / "python"
    if candidate.exists():
        sys.path.insert(0, str(candidate))
        break

from brain.memory.historical_audit_internal_api import (  # noqa: E402
    get_historical_dry_run_audit_internal_endpoint_detail,
    query_historical_dry_run_audit_internal_endpoint,
)
from brain.memory.historical_audit_query_models import (  # noqa: E402
    DryRunAuditEvidenceDetail,
    DryRunAuditEvidenceItem,
    DryRunAuditPageInfo,
    DryRunAuditQueryRequest,
    DryRunAuditQueryResponse,
    REQUIRED_AUDIT_QUERY_WARNINGS,
)
from brain.memory.memory_models import DRY_RUN_RETRY_PLAN_EVIDENCE_EVENT_TYPE  # noqa: E402


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
    "memoryfacade",
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


class _AuditEndpointServiceSpy:
    def __init__(
        self,
        *,
        response: DryRunAuditQueryResponse | Any | None = None,
        detail: DryRunAuditEvidenceDetail | Any | None = None,
        raise_on_query: bool = False,
        raise_on_detail: bool = False,
    ) -> None:
        item = _safe_item()
        self.response = response if response is not None else DryRunAuditQueryResponse(
            items=[item],
            page_info=DryRunAuditPageInfo(limit=25, offset=0, returned_count=1),
            applied_filters={},
            warnings=[],
            degraded=False,
        )
        self.detail = detail if detail is not None else DryRunAuditEvidenceDetail(item)
        self.raise_on_query = raise_on_query
        self.raise_on_detail = raise_on_detail
        self.query_calls: list[DryRunAuditQueryRequest] = []
        self.detail_calls: list[str] = []

    def query_historical_dry_run_audit(
        self,
        request: DryRunAuditQueryRequest,
    ) -> DryRunAuditQueryResponse:
        self.query_calls.append(request)
        if self.raise_on_query:
            raise RuntimeError("raw_prompt token=secret traceback select * from database row")
        return self.response

    def get_historical_dry_run_audit_detail(
        self,
        plan_id: str,
    ) -> DryRunAuditEvidenceDetail | None:
        self.detail_calls.append(plan_id)
        if self.raise_on_detail:
            raise RuntimeError("raw_response provider_payload stack trace")
        return self.detail

    def __getattr__(self, name: str) -> Any:
        lowered = name.lower()
        if any(marker in lowered for marker in ("memory", "sqlite", "jsonl", "sql", "runtime", "provider")):
            raise AssertionError(f"unsafe access attempted: {name}")
        raise AttributeError(name)


class HistoricalDryRunAuditInternalApiEndpointTest(unittest.TestCase):
    def test_list_endpoint_fails_closed_when_internal_guard_disabled(self) -> None:
        service = _AuditEndpointServiceSpy()

        response = query_historical_dry_run_audit_internal_endpoint(
            service,
            {"limit": "10"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(response.body["degraded"])
        self.assertEqual(response.body["error_category"], "internal_route_disabled")
        self.assertEqual(service.query_calls, [])

    def test_detail_endpoint_fails_closed_when_internal_guard_disabled(self) -> None:
        service = _AuditEndpointServiceSpy()

        response = get_historical_dry_run_audit_internal_endpoint_detail(
            service,
            "plan-safe",
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(response.body["degraded"])
        self.assertEqual(response.body["error_category"], "internal_route_disabled")
        self.assertEqual(service.detail_calls, [])

    def test_list_endpoint_delegates_to_service_only_when_enabled(self) -> None:
        service = _AuditEndpointServiceSpy()

        response = query_historical_dry_run_audit_internal_endpoint(
            service,
            {
                "plan_type": "dry_run_retry",
                "source_decision": "RETRY",
                "risk_level": "low",
                "blocked": "false",
                "limit": "10",
                "offset": "2",
                "sort_by": "created_at",
                "sort_direction": "asc",
            },
            internal_enabled=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(service.query_calls), 1)
        request = service.query_calls[0]
        self.assertEqual(request.limit, 10)
        self.assertEqual(request.offset, 2)
        self.assertEqual(request.sort_field, "created_at")
        self.assertEqual(request.sort_direction, "asc")
        self.assertEqual(request.applied_filters["blocked"], False)

    def test_detail_endpoint_delegates_to_service_only_when_enabled(self) -> None:
        service = _AuditEndpointServiceSpy()

        response = get_historical_dry_run_audit_internal_endpoint_detail(
            service,
            "plan-safe",
            internal_enabled=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(service.detail_calls, ["plan-safe"])
        self.assertEqual(response.body["detail"]["plan_id"], "plan-safe")

    def test_invalid_query_params_degrade_before_service_call(self) -> None:
        service = _AuditEndpointServiceSpy()

        response = query_historical_dry_run_audit_internal_endpoint(
            service,
            {"risk_level": "critical"},
            internal_enabled=True,
        )

        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.body["degraded"])
        self.assertEqual(response.body["error_category"], "invalid_filter")
        self.assertEqual(service.query_calls, [])

    def test_unsupported_query_param_is_rejected_without_service_call(self) -> None:
        service = _AuditEndpointServiceSpy()

        response = query_historical_dry_run_audit_internal_endpoint(
            service,
            {"raw_sql": "select *"},
            internal_enabled=True,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.body["error_category"], "invalid_request")
        self.assertEqual(service.query_calls, [])

    def test_size_guard_rejects_oversized_query_without_service_call(self) -> None:
        service = _AuditEndpointServiceSpy()

        response = query_historical_dry_run_audit_internal_endpoint(
            service,
            {"request_id": "a" * 200},
            internal_enabled=True,
        )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.body["error_category"], "payload_too_large")
        self.assertEqual(service.query_calls, [])

    def test_invalid_plan_id_degrades_without_service_call(self) -> None:
        service = _AuditEndpointServiceSpy()

        response = get_historical_dry_run_audit_internal_endpoint_detail(
            service,
            "../secret",
            internal_enabled=True,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.body["error_category"], "invalid_request")
        self.assertEqual(service.detail_calls, [])

    def test_service_failures_return_categorical_errors_without_raw_exception(self) -> None:
        service = _AuditEndpointServiceSpy(raise_on_query=True)

        response = query_historical_dry_run_audit_internal_endpoint(
            service,
            {},
            internal_enabled=True,
        )
        serialized = str(response.as_dict()).lower()

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.body["error_category"], "query_failed")
        for forbidden in FORBIDDEN_TEXT:
            self.assertNotIn(forbidden, serialized)

    def test_detail_service_failures_return_categorical_errors_without_raw_exception(self) -> None:
        service = _AuditEndpointServiceSpy(raise_on_detail=True)

        response = get_historical_dry_run_audit_internal_endpoint_detail(
            service,
            "plan-safe",
            internal_enabled=True,
        )
        serialized = str(response.as_dict()).lower()

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.body["error_category"], "query_failed")
        for forbidden in FORBIDDEN_TEXT:
            self.assertNotIn(forbidden, serialized)

    def test_invalid_service_response_degrades_safely(self) -> None:
        service = _AuditEndpointServiceSpy(response={"raw_response": "provider_payload"})

        response = query_historical_dry_run_audit_internal_endpoint(
            service,
            {},
            internal_enabled=True,
        )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.body["error_category"], "invalid_service_response")
        self.assertNotIn("provider_payload", str(response.as_dict()).lower())

    def test_required_warnings_are_preserved(self) -> None:
        service = _AuditEndpointServiceSpy()

        list_response = query_historical_dry_run_audit_internal_endpoint(
            service,
            {},
            internal_enabled=True,
        )
        detail_response = get_historical_dry_run_audit_internal_endpoint_detail(
            service,
            "plan-safe",
            internal_enabled=True,
        )

        for warning in REQUIRED_AUDIT_QUERY_WARNINGS:
            self.assertIn(warning, list_response.body["warnings"])
            self.assertIn(warning, detail_response.body["warnings"])

    def test_forbidden_fields_are_not_returned_in_success_responses(self) -> None:
        service = _AuditEndpointServiceSpy()

        list_response = query_historical_dry_run_audit_internal_endpoint(
            service,
            {},
            internal_enabled=True,
        )
        detail_response = get_historical_dry_run_audit_internal_endpoint_detail(
            service,
            "plan-safe",
            internal_enabled=True,
        )
        serialized = f"{list_response.as_dict()} {detail_response.as_dict()}".lower()

        for forbidden in FORBIDDEN_TEXT:
            self.assertNotIn(forbidden, serialized)

    def test_results_do_not_include_runtime_provider_or_execution_controls(self) -> None:
        service = _AuditEndpointServiceSpy()

        response = query_historical_dry_run_audit_internal_endpoint(
            service,
            {},
            internal_enabled=True,
        )
        serialized = str(response.as_dict()).lower()

        self.assertNotIn("execute_retry", serialized)
        self.assertNotIn("execute_replan", serialized)
        self.assertNotIn("provider_call", serialized)
        self.assertNotIn("runtime_call", serialized)
        self.assertNotIn("execution_input", serialized)


if __name__ == "__main__":
    unittest.main()
