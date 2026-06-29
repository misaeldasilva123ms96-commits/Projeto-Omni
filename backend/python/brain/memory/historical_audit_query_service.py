from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from .historical_audit_query_models import (
    DryRunAuditEvidenceDetail,
    DryRunAuditQueryRequest,
    DryRunAuditQueryResponse,
    degraded_audit_response,
    safe_audit_id,
    safe_audit_string,
)
from .memory_models import utc_now_iso


AuditLogger = Callable[[dict[str, Any]], None]


class HistoricalDryRunAuditMemoryFacade(Protocol):
    def query_historical_dry_run_audit_evidence(
        self,
        request: DryRunAuditQueryRequest,
    ) -> DryRunAuditQueryResponse:
        ...

    def get_historical_dry_run_audit_evidence_detail(
        self,
        plan_id: str,
    ) -> DryRunAuditEvidenceDetail | None:
        ...


@dataclass(slots=True)
class HistoricalDryRunAuditQueryService:
    """Readonly service boundary for sanitized dry-run historical audit queries."""

    memory_facade: HistoricalDryRunAuditMemoryFacade
    audit_logger: AuditLogger | None = None

    def query_historical_dry_run_audit(
        self,
        request: DryRunAuditQueryRequest,
    ) -> DryRunAuditQueryResponse:
        if not isinstance(request, DryRunAuditQueryRequest):
            fallback_request = DryRunAuditQueryRequest()
            response = degraded_audit_response(
                fallback_request,
                error_category="invalid_request",
                warning="invalid_service_request",
            )
            self._log_query_event(
                operation_name="query_historical_dry_run_audit",
                request=fallback_request,
                response=response,
            )
            return response
        if not request.valid:
            response = degraded_audit_response(
                request,
                error_category=request.error_category or "invalid_request",
                warning="invalid_service_request",
            )
            self._log_query_event(
                operation_name="query_historical_dry_run_audit",
                request=request,
                response=response,
            )
            return response
        try:
            response = self.memory_facade.query_historical_dry_run_audit_evidence(request)
        except Exception:
            response = degraded_audit_response(
                request,
                error_category="query_failed",
                warning="historical_audit_service_query_failed",
            )
            self._log_query_event(
                operation_name="query_historical_dry_run_audit",
                request=request,
                response=response,
            )
            return response
        if not isinstance(response, DryRunAuditQueryResponse):
            response = degraded_audit_response(
                request,
                error_category="invalid_memoryfacade_response",
                warning="invalid_memoryfacade_response",
            )
        self._log_query_event(
            operation_name="query_historical_dry_run_audit",
            request=request,
            response=response,
        )
        return response

    def get_historical_dry_run_audit_detail(
        self,
        plan_id: str,
    ) -> DryRunAuditEvidenceDetail | None:
        safe_plan_id = safe_audit_id(plan_id)
        if not safe_plan_id:
            self._log_detail_event(
                operation_name="get_historical_dry_run_audit_detail",
                plan_id="",
                degraded=True,
                error_category="invalid_request",
            )
            return None
        try:
            detail = self.memory_facade.get_historical_dry_run_audit_evidence_detail(
                safe_plan_id
            )
        except Exception:
            self._log_detail_event(
                operation_name="get_historical_dry_run_audit_detail",
                plan_id=safe_plan_id,
                degraded=True,
                error_category="query_failed",
            )
            return None
        if detail is not None and not isinstance(detail, DryRunAuditEvidenceDetail):
            self._log_detail_event(
                operation_name="get_historical_dry_run_audit_detail",
                plan_id=safe_plan_id,
                degraded=True,
                error_category="invalid_memoryfacade_response",
            )
            return None
        self._log_detail_event(
            operation_name="get_historical_dry_run_audit_detail",
            plan_id=safe_plan_id,
            degraded=False,
            error_category="",
        )
        return detail

    def _log_query_event(
        self,
        *,
        operation_name: str,
        request: DryRunAuditQueryRequest,
        response: DryRunAuditQueryResponse,
    ) -> None:
        if self.audit_logger is None:
            return
        event: dict[str, Any] = {
            "operation_name": safe_audit_string(operation_name, max_length=96),
            "filter_keys": sorted(request.applied_filters),
            "sort_field": safe_audit_string(request.sort_field, max_length=64),
            "sort_direction": safe_audit_string(request.sort_direction, max_length=8),
            "limit": request.limit,
            "offset": request.offset,
            "generated_at": utc_now_iso(),
            "degraded": bool(response.degraded),
            "error_category": (
                safe_audit_string(response.error_category, max_length=64)
                if response.degraded
                else ""
            ),
        }
        for key in ("request_id", "session_id", "trace_id"):
            value = request.applied_filters.get(key)
            if value:
                event[key] = safe_audit_id(value)
        self._emit_audit_event(event)

    def _log_detail_event(
        self,
        *,
        operation_name: str,
        plan_id: str,
        degraded: bool,
        error_category: str,
    ) -> None:
        if self.audit_logger is None:
            return
        event: dict[str, Any] = {
            "operation_name": safe_audit_string(operation_name, max_length=96),
            "plan_id": safe_audit_id(plan_id),
            "generated_at": utc_now_iso(),
            "degraded": bool(degraded),
            "error_category": (
                safe_audit_string(error_category, max_length=64) if degraded else ""
            ),
        }
        self._emit_audit_event(event)

    def _emit_audit_event(self, event: dict[str, Any]) -> None:
        if self.audit_logger is None:
            return
        try:
            self.audit_logger(event)
        except Exception:
            return


def query_historical_dry_run_audit(
    memory_facade: HistoricalDryRunAuditMemoryFacade,
    request: DryRunAuditQueryRequest,
    *,
    audit_logger: AuditLogger | None = None,
) -> DryRunAuditQueryResponse:
    service = HistoricalDryRunAuditQueryService(
        memory_facade=memory_facade,
        audit_logger=audit_logger,
    )
    return service.query_historical_dry_run_audit(request)


def get_historical_dry_run_audit_detail(
    memory_facade: HistoricalDryRunAuditMemoryFacade,
    plan_id: str,
    *,
    audit_logger: AuditLogger | None = None,
) -> DryRunAuditEvidenceDetail | None:
    service = HistoricalDryRunAuditQueryService(
        memory_facade=memory_facade,
        audit_logger=audit_logger,
    )
    return service.get_historical_dry_run_audit_detail(plan_id)
