from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

from .historical_audit_query_models import (
    DRY_RUN_AUDIT_DEFAULT_LIMIT,
    DRY_RUN_AUDIT_MAX_LIMIT,
    DryRunAuditEvidenceDetail,
    DryRunAuditQueryRequest,
    DryRunAuditQueryResponse,
    REQUIRED_AUDIT_QUERY_WARNINGS,
    degraded_audit_response,
    safe_audit_id,
    safe_audit_string,
)
from .memory_models import utc_now_iso

INTERNAL_DRY_RUN_AUDIT_LIST_PATH = "/internal/audit/dry-run"
INTERNAL_DRY_RUN_AUDIT_DETAIL_PATH_PREFIX = "/internal/audit/dry-run/"
INTERNAL_DRY_RUN_AUDIT_MAX_QUERY_PARAMS = 24
INTERNAL_DRY_RUN_AUDIT_MAX_PARAM_LENGTH = 160
INTERNAL_DRY_RUN_AUDIT_MAX_PLAN_ID_LENGTH = 128

SAFE_INTERNAL_ENDPOINT_ERROR_CATEGORIES = frozenset({
    "internal_route_disabled",
    "invalid_request",
    "invalid_filter",
    "invalid_sort",
    "payload_too_large",
    "not_found",
    "query_failed",
    "invalid_service_response",
})

_FILTER_QUERY_PARAMS = frozenset({
    "plan_type",
    "event_type",
    "source_decision",
    "risk_level",
    "blocked",
    "recorded",
    "degraded",
    "storage_mode",
    "sqlite_enabled",
    "request_id",
    "trace_id",
    "session_id",
    "created_at_from",
    "created_at_to",
    "recorded_at_from",
    "recorded_at_to",
})
_CONTROL_QUERY_PARAMS = frozenset({"sort_by", "sort_direction", "limit", "offset"})
_ALLOWED_QUERY_PARAMS = _FILTER_QUERY_PARAMS | _CONTROL_QUERY_PARAMS


class HistoricalDryRunAuditEndpointService(Protocol):
    def query_historical_dry_run_audit(
        self,
        request: DryRunAuditQueryRequest,
    ) -> DryRunAuditQueryResponse:
        ...

    def get_historical_dry_run_audit_detail(
        self,
        plan_id: str,
    ) -> DryRunAuditEvidenceDetail | None:
        ...


@dataclass(slots=True)
class HistoricalDryRunAuditEndpointResponse:
    status_code: int
    body: dict[str, Any]
    headers: dict[str, str] = field(
        default_factory=lambda: {"content-type": "application/json; charset=utf-8"}
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "status_code": self.status_code,
            "body": dict(self.body),
            "headers": dict(self.headers),
        }


def query_historical_dry_run_audit_internal_endpoint(
    service: HistoricalDryRunAuditEndpointService,
    query_params: Mapping[str, Any] | None = None,
    *,
    internal_enabled: bool = False,
) -> HistoricalDryRunAuditEndpointResponse:
    if not internal_enabled:
        return _degraded_list_response(
            status_code=404,
            error_category="internal_route_disabled",
            warning="internal_route_disabled",
        )
    parsed = _parse_query_params(query_params)
    if parsed.error_category:
        return _degraded_list_response(
            status_code=parsed.status_code,
            error_category=parsed.error_category,
            warning=parsed.warning,
            request=parsed.request,
        )
    try:
        response = service.query_historical_dry_run_audit(parsed.request)
    except Exception:
        return _degraded_list_response(
            status_code=500,
            error_category="query_failed",
            warning="internal_endpoint_query_failed",
            request=parsed.request,
        )
    if not isinstance(response, DryRunAuditQueryResponse):
        return _degraded_list_response(
            status_code=500,
            error_category="invalid_service_response",
            warning="invalid_internal_service_response",
            request=parsed.request,
        )
    return HistoricalDryRunAuditEndpointResponse(
        status_code=200,
        body=response.as_dict(),
    )


def get_historical_dry_run_audit_internal_endpoint_detail(
    service: HistoricalDryRunAuditEndpointService,
    plan_id: Any,
    *,
    internal_enabled: bool = False,
) -> HistoricalDryRunAuditEndpointResponse:
    if not internal_enabled:
        return _detail_response(
            status_code=404,
            detail=None,
            degraded=True,
            error_category="internal_route_disabled",
            warnings=["internal_route_disabled"],
        )
    if _is_oversized_value(plan_id, max_length=INTERNAL_DRY_RUN_AUDIT_MAX_PLAN_ID_LENGTH):
        return _detail_response(
            status_code=413,
            detail=None,
            degraded=True,
            error_category="payload_too_large",
            warnings=["path_parameter_too_large"],
        )
    safe_plan_id = safe_audit_id(plan_id)
    if not safe_plan_id:
        return _detail_response(
            status_code=400,
            detail=None,
            degraded=True,
            error_category="invalid_request",
            warnings=["invalid_plan_id"],
        )
    try:
        detail = service.get_historical_dry_run_audit_detail(safe_plan_id)
    except Exception:
        return _detail_response(
            status_code=500,
            detail=None,
            degraded=True,
            error_category="query_failed",
            warnings=["internal_endpoint_detail_failed"],
        )
    if detail is None:
        return _detail_response(
            status_code=404,
            detail=None,
            degraded=True,
            error_category="not_found",
            warnings=["audit_detail_not_found"],
        )
    if not isinstance(detail, DryRunAuditEvidenceDetail):
        return _detail_response(
            status_code=500,
            detail=None,
            degraded=True,
            error_category="invalid_service_response",
            warnings=["invalid_internal_service_response"],
        )
    return _detail_response(
        status_code=200,
        detail=detail.as_dict(),
        degraded=False,
        error_category="",
        warnings=[],
    )


@dataclass(slots=True)
class _ParsedQuery:
    request: DryRunAuditQueryRequest
    status_code: int = 200
    error_category: str = ""
    warning: str = ""


def _parse_query_params(query_params: Mapping[str, Any] | None) -> _ParsedQuery:
    request = DryRunAuditQueryRequest()
    if query_params is None:
        return _ParsedQuery(request=request)
    if not isinstance(query_params, Mapping):
        return _ParsedQuery(
            request=request,
            status_code=400,
            error_category="invalid_request",
            warning="invalid_query_params",
        )
    if len(query_params) > INTERNAL_DRY_RUN_AUDIT_MAX_QUERY_PARAMS:
        return _ParsedQuery(
            request=request,
            status_code=413,
            error_category="payload_too_large",
            warning="too_many_query_params",
        )
    payload: dict[str, Any] = {"filters": {}}
    for raw_key, raw_value in query_params.items():
        key = safe_audit_string(raw_key, max_length=64)
        if key not in _ALLOWED_QUERY_PARAMS:
            return _ParsedQuery(
                request=request,
                status_code=400,
                error_category="invalid_request",
                warning="unsupported_query_param",
            )
        value = _first_value(raw_value)
        if _is_oversized_value(value):
            return _ParsedQuery(
                request=request,
                status_code=413,
                error_category="payload_too_large",
                warning="query_param_too_large",
            )
        if key in _FILTER_QUERY_PARAMS:
            payload["filters"][key] = value
        elif key == "sort_by":
            payload["sort_field"] = value
        elif key == "sort_direction":
            payload["sort_direction"] = value
        elif key == "limit":
            payload["limit"] = value
        elif key == "offset":
            payload["offset"] = value
    parsed_request = DryRunAuditQueryRequest.from_dict(payload)
    if not parsed_request.valid:
        category = parsed_request.error_category or "invalid_request"
        return _ParsedQuery(
            request=parsed_request,
            status_code=400,
            error_category=_safe_endpoint_error_category(category),
            warning="invalid_query_request",
        )
    return _ParsedQuery(request=parsed_request)


def _degraded_list_response(
    *,
    status_code: int,
    error_category: str,
    warning: str,
    request: DryRunAuditQueryRequest | None = None,
) -> HistoricalDryRunAuditEndpointResponse:
    safe_request = request if isinstance(request, DryRunAuditQueryRequest) else DryRunAuditQueryRequest()
    response = degraded_audit_response(
        safe_request,
        error_category=_safe_endpoint_error_category(error_category),
        warning=safe_audit_string(warning, max_length=96) or "internal_endpoint_degraded",
    )
    return HistoricalDryRunAuditEndpointResponse(
        status_code=status_code,
        body=response.as_dict(),
    )


def _detail_response(
    *,
    status_code: int,
    detail: dict[str, Any] | None,
    degraded: bool,
    error_category: str,
    warnings: list[str],
) -> HistoricalDryRunAuditEndpointResponse:
    body: dict[str, Any] = {
        "detail": detail,
        "warnings": _merge_required_warnings(warnings),
        "degraded": bool(degraded),
        "generated_at": utc_now_iso(),
    }
    if degraded:
        body["error_category"] = _safe_endpoint_error_category(error_category)
    return HistoricalDryRunAuditEndpointResponse(status_code=status_code, body=body)


def _merge_required_warnings(warnings: list[str]) -> list[str]:
    merged: list[str] = []
    for warning in [*warnings, *REQUIRED_AUDIT_QUERY_WARNINGS]:
        safe = safe_audit_string(warning, max_length=160)
        if safe and safe not in merged:
            merged.append(safe)
    return merged


def _first_value(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return value[0] if value else ""
    return value


def _is_oversized_value(value: Any, *, max_length: int = INTERNAL_DRY_RUN_AUDIT_MAX_PARAM_LENGTH) -> bool:
    if isinstance(value, (list, tuple)):
        return any(_is_oversized_value(item, max_length=max_length) for item in value)
    return len(str(value or "")) > max_length


def _safe_endpoint_error_category(error_category: str) -> str:
    category = safe_audit_string(error_category, max_length=64)
    if category in SAFE_INTERNAL_ENDPOINT_ERROR_CATEGORIES:
        return category
    return "invalid_request"
