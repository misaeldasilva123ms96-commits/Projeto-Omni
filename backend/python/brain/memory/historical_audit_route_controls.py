"""Dormant controls for future historical dry-run audit route registration.

This module is intentionally not imported by any router. It provides fail-closed
helpers for a future internal API boundary without exposing an endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .historical_audit_internal_api import (
    INTERNAL_DRY_RUN_AUDIT_MAX_PARAM_LENGTH,
    INTERNAL_DRY_RUN_AUDIT_MAX_PLAN_ID_LENGTH,
    INTERNAL_DRY_RUN_AUDIT_MAX_QUERY_PARAMS,
)
from .historical_audit_query_models import (
    ALLOWED_FILTERS,
    ALLOWED_SORT_DIRECTIONS,
    ALLOWED_SORT_FIELDS,
    DRY_RUN_AUDIT_DEFAULT_LIMIT,
    DRY_RUN_AUDIT_MAX_LIMIT,
    DRY_RUN_AUDIT_MAX_OFFSET,
    REQUIRED_AUDIT_QUERY_WARNINGS,
    safe_audit_id,
    safe_audit_string,
)
from .memory_models import utc_now_iso


HISTORICAL_AUDIT_ROUTE_ID = "historical_dry_run_audit"
HISTORICAL_AUDIT_READONLY_CAPABILITY = "historical_audit:read"
HISTORICAL_AUDIT_ROUTE_SWITCH_DEFAULT = False

_CONTROL_QUERY_PARAMS = frozenset({"limit", "offset", "sort_by", "sort_direction"})
_ALLOWED_QUERY_PARAMS = ALLOWED_FILTERS | _CONTROL_QUERY_PARAMS
_MAX_RATE_LIMIT_REQUESTS = 300
_MAX_RATE_LIMIT_WINDOW_SECONDS = 3_600
_MAX_QUERY_FILTERS = len(ALLOWED_FILTERS)

_FORBIDDEN_ROUTE_MARKERS = (
    "authorization",
    "bearer ",
    "cookie",
    "set-cookie",
    "secret",
    "password",
    "token",
    "api_key",
    "apikey",
    "jwt",
    "raw_jsonl",
    "jsonl",
    "raw_sqlite",
    "sqlite",
    "raw_sql",
    "select ",
    "insert ",
    "update ",
    "delete ",
    "memoryfacade",
    "raw_prompt",
    "prompt",
    "provider_payload",
    "provider_response",
    "tool_output",
    "stdout",
    "stderr",
    "traceback",
    "stack",
    "command_args",
    "file_contents",
    ".env",
    "raw_exception",
    "raw_repr",
    "retry_execution",
    "replan_execution",
    "provider_call",
)


@dataclass(frozen=True, slots=True)
class HistoricalAuditControlDecision:
    allowed: bool
    reason: str
    status_code: int = 403
    warnings: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": safe_audit_string(self.reason, max_length=96),
            "status_code": int(self.status_code),
            "warnings": tuple(
                safe_audit_string(warning, max_length=96) for warning in self.warnings
            ),
        }


@dataclass(frozen=True, slots=True)
class HistoricalAuditCallerIdentity:
    caller_id: str
    source: str = "supabase_sub"

    def __post_init__(self) -> None:
        if _safe_route_id(self.caller_id, max_length=128) != self.caller_id:
            raise ValueError("invalid_caller_id")
        safe_source = safe_audit_string(self.source, max_length=48)
        if safe_source != self.source or safe_source == "[REDACTED]":
            raise ValueError("invalid_caller_source")

    def as_dict(self) -> dict[str, str]:
        return {
            "caller_id": self.caller_id,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class HistoricalAuditRouteControlConfig:
    route_enabled: bool = HISTORICAL_AUDIT_ROUTE_SWITCH_DEFAULT
    rate_limit_max_requests: int = 30
    rate_limit_window_seconds: int = 60
    max_query_params: int = INTERNAL_DRY_RUN_AUDIT_MAX_QUERY_PARAMS
    max_param_length: int = INTERNAL_DRY_RUN_AUDIT_MAX_PARAM_LENGTH
    max_plan_id_length: int = INTERNAL_DRY_RUN_AUDIT_MAX_PLAN_ID_LENGTH
    max_filters: int = 8
    max_page_size: int = DRY_RUN_AUDIT_MAX_LIMIT
    max_offset: int = DRY_RUN_AUDIT_MAX_OFFSET
    safe_audit_logging_enabled: bool = True
    safe_observability_enabled: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "rate_limit_max_requests",
            _bounded_int(self.rate_limit_max_requests, 1, _MAX_RATE_LIMIT_REQUESTS, 30),
        )
        object.__setattr__(
            self,
            "rate_limit_window_seconds",
            _bounded_int(
                self.rate_limit_window_seconds,
                1,
                _MAX_RATE_LIMIT_WINDOW_SECONDS,
                60,
            ),
        )
        object.__setattr__(
            self,
            "max_query_params",
            _bounded_int(
                self.max_query_params,
                1,
                INTERNAL_DRY_RUN_AUDIT_MAX_QUERY_PARAMS,
                INTERNAL_DRY_RUN_AUDIT_MAX_QUERY_PARAMS,
            ),
        )
        object.__setattr__(
            self,
            "max_param_length",
            _bounded_int(
                self.max_param_length,
                1,
                INTERNAL_DRY_RUN_AUDIT_MAX_PARAM_LENGTH,
                INTERNAL_DRY_RUN_AUDIT_MAX_PARAM_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "max_plan_id_length",
            _bounded_int(
                self.max_plan_id_length,
                1,
                INTERNAL_DRY_RUN_AUDIT_MAX_PLAN_ID_LENGTH,
                INTERNAL_DRY_RUN_AUDIT_MAX_PLAN_ID_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "max_filters",
            _bounded_int(self.max_filters, 0, _MAX_QUERY_FILTERS, 8),
        )
        object.__setattr__(
            self,
            "max_page_size",
            _bounded_int(
                self.max_page_size,
                1,
                DRY_RUN_AUDIT_MAX_LIMIT,
                DRY_RUN_AUDIT_DEFAULT_LIMIT,
            ),
        )
        object.__setattr__(
            self,
            "max_offset",
            _bounded_int(self.max_offset, 0, DRY_RUN_AUDIT_MAX_OFFSET, DRY_RUN_AUDIT_MAX_OFFSET),
        )

    @classmethod
    def default(cls) -> "HistoricalAuditRouteControlConfig":
        return cls()

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any] | None) -> "HistoricalAuditRouteControlConfig":
        if not isinstance(values, Mapping):
            return cls()
        allowed = set(cls.__dataclass_fields__)
        return cls(**{key: value for key, value in values.items() if key in allowed})

    def as_dict(self) -> dict[str, Any]:
        return {
            "route_enabled": bool(self.route_enabled),
            "rate_limit_max_requests": self.rate_limit_max_requests,
            "rate_limit_window_seconds": self.rate_limit_window_seconds,
            "max_query_params": self.max_query_params,
            "max_param_length": self.max_param_length,
            "max_plan_id_length": self.max_plan_id_length,
            "max_filters": self.max_filters,
            "max_page_size": self.max_page_size,
            "max_offset": self.max_offset,
            "safe_audit_logging_enabled": bool(self.safe_audit_logging_enabled),
            "safe_observability_enabled": bool(self.safe_observability_enabled),
        }


@dataclass(frozen=True, slots=True)
class HistoricalAuditQueryComplexityResult:
    allowed: bool
    reason: str
    status_code: int = 400
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": safe_audit_string(self.reason, max_length=96),
            "status_code": int(self.status_code),
            "warnings": tuple(
                safe_audit_string(warning, max_length=96) for warning in self.warnings
            ),
        }


def extract_historical_audit_caller_from_supabase_sub(
    supabase_sub: Any,
) -> tuple[HistoricalAuditCallerIdentity | None, HistoricalAuditControlDecision]:
    if not isinstance(supabase_sub, str) or not supabase_sub.strip():
        return None, HistoricalAuditControlDecision(False, "missing_caller_identity", 401)
    caller_id = supabase_sub.strip()
    if _safe_route_id(caller_id, max_length=128) != caller_id:
        return None, HistoricalAuditControlDecision(False, "invalid_caller_identity", 401)
    try:
        caller = HistoricalAuditCallerIdentity(caller_id=caller_id)
    except ValueError:
        return None, HistoricalAuditControlDecision(False, "invalid_caller_identity", 401)
    return caller, HistoricalAuditControlDecision(True, "caller_identity_accepted", 200)


def check_historical_audit_route_enabled(
    config: HistoricalAuditRouteControlConfig | Mapping[str, Any] | None = None,
) -> HistoricalAuditControlDecision:
    resolved = _resolve_config(config)
    if not resolved.route_enabled:
        return HistoricalAuditControlDecision(False, "route_disabled", 404)
    return HistoricalAuditControlDecision(True, "route_enabled", 200)


def authorize_historical_audit_readonly(
    caller: HistoricalAuditCallerIdentity | None,
    capabilities: Any,
    config: HistoricalAuditRouteControlConfig | Mapping[str, Any] | None = None,
) -> HistoricalAuditControlDecision:
    enabled_decision = check_historical_audit_route_enabled(config)
    if not enabled_decision.allowed:
        return enabled_decision
    if caller is None:
        return HistoricalAuditControlDecision(False, "missing_caller_identity", 401)
    try:
        HistoricalAuditCallerIdentity(caller_id=caller.caller_id, source=caller.source)
    except (AttributeError, ValueError):
        return HistoricalAuditControlDecision(False, "invalid_caller_identity", 401)
    if not _has_readonly_capability(capabilities):
        return HistoricalAuditControlDecision(False, "missing_historical_audit_readonly_capability", 403)
    return HistoricalAuditControlDecision(True, "historical_audit_readonly_authorized", 200)


def validate_historical_audit_list_query_complexity(
    query_params: Mapping[str, Any] | None,
    config: HistoricalAuditRouteControlConfig | Mapping[str, Any] | None = None,
) -> HistoricalAuditQueryComplexityResult:
    resolved = _resolve_config(config)
    if not isinstance(query_params, Mapping):
        return HistoricalAuditQueryComplexityResult(False, "invalid_query_params")
    if len(query_params) > resolved.max_query_params:
        return HistoricalAuditQueryComplexityResult(False, "too_many_query_params")

    filter_count = 0
    for key, value in query_params.items():
        param = str(key or "").strip()
        if param not in _ALLOWED_QUERY_PARAMS:
            return HistoricalAuditQueryComplexityResult(False, "unsupported_query_param")
        if len(str(value or "")) > resolved.max_param_length:
            return HistoricalAuditQueryComplexityResult(False, "query_param_too_large")
        if param in ALLOWED_FILTERS:
            filter_count += 1

    if filter_count > resolved.max_filters:
        return HistoricalAuditQueryComplexityResult(False, "too_many_filters")

    if "sort_by" in query_params and str(query_params["sort_by"]) not in ALLOWED_SORT_FIELDS:
        return HistoricalAuditQueryComplexityResult(False, "unsupported_sort_field")
    if "sort_direction" in query_params:
        direction = str(query_params["sort_direction"]).strip().lower()
        if direction not in ALLOWED_SORT_DIRECTIONS:
            return HistoricalAuditQueryComplexityResult(False, "unsupported_sort_direction")
    limit_result = _parse_bounded_query_int(
        query_params.get("limit"),
        lower=1,
        upper=resolved.max_page_size,
        default=DRY_RUN_AUDIT_DEFAULT_LIMIT,
        reason="limit_out_of_bounds",
    )
    if limit_result is not None:
        return limit_result
    offset_result = _parse_bounded_query_int(
        query_params.get("offset"),
        lower=0,
        upper=resolved.max_offset,
        default=0,
        reason="offset_out_of_bounds",
    )
    if offset_result is not None:
        return offset_result

    return HistoricalAuditQueryComplexityResult(
        True,
        "query_complexity_accepted",
        200,
        tuple(REQUIRED_AUDIT_QUERY_WARNINGS),
    )


def validate_historical_audit_detail_query_complexity(
    plan_id: Any,
    config: HistoricalAuditRouteControlConfig | Mapping[str, Any] | None = None,
) -> HistoricalAuditQueryComplexityResult:
    resolved = _resolve_config(config)
    if not isinstance(plan_id, str) or not plan_id.strip():
        return HistoricalAuditQueryComplexityResult(False, "missing_plan_id")
    normalized = plan_id.strip()
    if len(normalized) > resolved.max_plan_id_length:
        return HistoricalAuditQueryComplexityResult(False, "plan_id_too_large")
    if _safe_route_id(normalized, max_length=resolved.max_plan_id_length) != normalized:
        return HistoricalAuditQueryComplexityResult(False, "invalid_plan_id")
    return HistoricalAuditQueryComplexityResult(
        True,
        "detail_query_complexity_accepted",
        200,
        tuple(REQUIRED_AUDIT_QUERY_WARNINGS),
    )


def build_historical_audit_route_audit_event(
    caller: HistoricalAuditCallerIdentity | None,
    decision: HistoricalAuditControlDecision,
    *,
    operation_name: str,
    query_summary: Mapping[str, Any] | None = None,
    config: HistoricalAuditRouteControlConfig | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved = _resolve_config(config)
    summary = _safe_query_summary(query_summary)
    return {
        "event_type": "historical_dry_run_audit_route_access",
        "route_id": HISTORICAL_AUDIT_ROUTE_ID,
        "operation_name": safe_audit_string(operation_name, max_length=64),
        "caller_id": caller.caller_id if caller else "",
        "caller_source": caller.source if caller else "",
        "decision_allowed": bool(decision.allowed),
        "decision_reason": safe_audit_string(decision.reason, max_length=96),
        "status_code": int(decision.status_code),
        "query_keys": tuple(summary.keys()),
        "page_size": summary.get("limit", ""),
        "safe_audit_logging_enabled": bool(resolved.safe_audit_logging_enabled),
        "warnings": tuple(safe_audit_string(warning, max_length=96) for warning in decision.warnings),
        "generated_at": utc_now_iso(),
    }


def build_historical_audit_route_observability_fields(
    decision: HistoricalAuditControlDecision,
    *,
    operation_name: str,
    latency_ms: Any = None,
    config: HistoricalAuditRouteControlConfig | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved = _resolve_config(config)
    return {
        "route_id": HISTORICAL_AUDIT_ROUTE_ID,
        "operation_name": safe_audit_string(operation_name, max_length=64),
        "decision_allowed": bool(decision.allowed),
        "decision_reason": safe_audit_string(decision.reason, max_length=96),
        "status_code": int(decision.status_code),
        "route_enabled": bool(resolved.route_enabled),
        "rate_limit_max_requests": resolved.rate_limit_max_requests,
        "rate_limit_window_seconds": resolved.rate_limit_window_seconds,
        "safe_observability_enabled": bool(resolved.safe_observability_enabled),
        "latency_ms": _bounded_int(latency_ms, 0, 60_000, 0),
    }


def _resolve_config(
    config: HistoricalAuditRouteControlConfig | Mapping[str, Any] | None,
) -> HistoricalAuditRouteControlConfig:
    if isinstance(config, HistoricalAuditRouteControlConfig):
        return config
    return HistoricalAuditRouteControlConfig.from_mapping(config)


def _bounded_int(value: Any, lower: int, upper: int, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(lower, min(upper, parsed))


def _parse_bounded_query_int(
    value: Any,
    *,
    lower: int,
    upper: int,
    default: int,
    reason: str,
) -> HistoricalAuditQueryComplexityResult | None:
    if value is None or value == "":
        return None
    parsed = _bounded_int(value, lower, upper, default)
    if str(value).strip() != str(parsed):
        return HistoricalAuditQueryComplexityResult(False, reason)
    return None


def _has_readonly_capability(capabilities: Any) -> bool:
    if isinstance(capabilities, Mapping):
        raw = capabilities.get(HISTORICAL_AUDIT_READONLY_CAPABILITY)
        return raw is True or raw == "true" or raw == HISTORICAL_AUDIT_READONLY_CAPABILITY
    if isinstance(capabilities, str):
        return capabilities == HISTORICAL_AUDIT_READONLY_CAPABILITY
    try:
        return HISTORICAL_AUDIT_READONLY_CAPABILITY in set(capabilities)
    except TypeError:
        return False


def _safe_query_summary(query_summary: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(query_summary, Mapping):
        return {}
    safe: dict[str, Any] = {}
    for key, value in query_summary.items():
        safe_key = safe_audit_string(str(key or ""), max_length=64)
        if safe_key == "[REDACTED]" or _contains_forbidden_marker(safe_key):
            continue
        if safe_key in _ALLOWED_QUERY_PARAMS:
            safe[safe_key] = _safe_scalar(value)
    return safe


def _safe_route_id(value: Any, *, max_length: int) -> str:
    text = safe_audit_string(value, max_length=max_length)
    if safe_audit_id(text) != text:
        return ""
    return text


def _safe_scalar(value: Any) -> str | int | bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return _bounded_int(value, 0, DRY_RUN_AUDIT_MAX_OFFSET, 0)
    safe = safe_audit_string(str(value or ""), max_length=96)
    if safe == "[REDACTED]" or _contains_forbidden_marker(safe):
        return "[REDACTED]"
    return safe


def _contains_forbidden_marker(value: Any) -> bool:
    lowered = str(value or "").lower()
    return any(marker in lowered for marker in _FORBIDDEN_ROUTE_MARKERS)


__all__ = [
    "HISTORICAL_AUDIT_READONLY_CAPABILITY",
    "HISTORICAL_AUDIT_ROUTE_ID",
    "HISTORICAL_AUDIT_ROUTE_SWITCH_DEFAULT",
    "HistoricalAuditCallerIdentity",
    "HistoricalAuditControlDecision",
    "HistoricalAuditQueryComplexityResult",
    "HistoricalAuditRouteControlConfig",
    "authorize_historical_audit_readonly",
    "build_historical_audit_route_audit_event",
    "build_historical_audit_route_observability_fields",
    "check_historical_audit_route_enabled",
    "extract_historical_audit_caller_from_supabase_sub",
    "validate_historical_audit_detail_query_complexity",
    "validate_historical_audit_list_query_complexity",
]
