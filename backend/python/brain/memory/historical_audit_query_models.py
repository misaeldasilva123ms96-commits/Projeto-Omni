from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from .memory_models import (
    DRY_RUN_REPLAN_PLAN_EVIDENCE_EVENT_TYPE,
    DRY_RUN_RETRY_PLAN_EVIDENCE_EVENT_TYPE,
    DryRunReplanPlanEvidenceRecord,
    DryRunRetryPlanEvidenceRecord,
    utc_now_iso,
)

DRY_RUN_AUDIT_DEFAULT_LIMIT = 25
DRY_RUN_AUDIT_MAX_LIMIT = 100
DRY_RUN_AUDIT_MAX_OFFSET = 10_000
DRY_RUN_AUDIT_SCAN_LIMIT = 200
DRY_RUN_AUDIT_STRING_MAX = 160
DRY_RUN_AUDIT_SUMMARY_MAX = 240
DRY_RUN_AUDIT_ID_MAX = 128
DRY_RUN_AUDIT_LIST_MAX = 20

ALLOWED_PLAN_TYPES = frozenset({"dry_run_retry", "dry_run_replan"})
ALLOWED_EVENT_TYPES = frozenset({
    DRY_RUN_RETRY_PLAN_EVIDENCE_EVENT_TYPE,
    DRY_RUN_REPLAN_PLAN_EVIDENCE_EVENT_TYPE,
})
ALLOWED_SOURCE_DECISIONS = frozenset({
    "CONTINUE",
    "RETRY",
    "REPLAN",
    "SELF_REPAIR",
    "SWITCH_PROVIDER",
    "PAUSE",
    "ESCALATE_TO_MISAEL",
    "ABORT_SAFE",
    "UNKNOWN",
})
ALLOWED_RISK_LEVELS = frozenset({"low", "medium", "high", "unknown"})
ALLOWED_STORAGE_MODES = frozenset({"jsonl", "sqlite", "unavailable", "unknown"})
ALLOWED_FILTERS = frozenset({
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
ALLOWED_SORT_FIELDS = frozenset({
    "created_at",
    "recorded_at",
    "risk_level",
    "source_decision",
})
ALLOWED_SORT_DIRECTIONS = frozenset({"asc", "desc"})
BOOLEAN_FILTERS = frozenset({"blocked", "recorded", "degraded", "sqlite_enabled"})
ID_FILTERS = frozenset({"request_id", "trace_id", "session_id"})
DATE_FILTERS = frozenset({
    "created_at_from",
    "created_at_to",
    "recorded_at_from",
    "recorded_at_to",
})

RISK_SORT_ORDER = {"low": 0, "medium": 1, "high": 2, "unknown": 3, "": 4}
SOURCE_DECISION_SORT_ORDER = {
    "CONTINUE": 0,
    "RETRY": 1,
    "REPLAN": 2,
    "SELF_REPAIR": 3,
    "SWITCH_PROVIDER": 4,
    "PAUSE": 5,
    "ESCALATE_TO_MISAEL": 6,
    "ABORT_SAFE": 7,
    "UNKNOWN": 8,
    "": 9,
}

_FORBIDDEN_MARKERS = (
    "sk-",
    "api_key",
    "api-key",
    "authorization:",
    "bearer ",
    "token=",
    "secret=",
    "password=",
    "raw_prompt",
    "rewritten_prompt",
    "raw_response",
    "provider_payload",
    "provider credentials",
    "traceback",
    "stack trace",
    "stdout",
    "stderr",
    "command args",
    "file contents",
    ".env",
    "tool output",
    "raw receipt",
    "raw exception",
    "python repr",
    "database row",
    "raw sql",
    "raw jsonl",
    "headers",
    "cookies",
)


def safe_audit_string(value: Any, *, max_length: int = DRY_RUN_AUDIT_STRING_MAX) -> str:
    if value is None:
        return ""
    text = str(value).replace("\x00", "").replace("\r", " ").replace("\n", " ").strip()
    lowered = text.lower()
    if any(marker in lowered for marker in _FORBIDDEN_MARKERS):
        return "[REDACTED]"
    allowed_chars: list[str] = []
    for char in text:
        if char.isalnum() or char in ("_", "-", ".", ":", "/", "+", " "):
            allowed_chars.append(char)
    return "".join(allowed_chars)[:max_length]


def safe_audit_id(value: Any) -> str:
    text = safe_audit_string(value, max_length=DRY_RUN_AUDIT_ID_MAX)
    if not text or text == "[REDACTED]":
        return ""
    if any(char in text for char in ("\\", "?", "&", "=", "*", "'", '"', "`", "|", "<", ">")):
        return ""
    if "/" in text:
        return ""
    return text


def _safe_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    return None


def _safe_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(number, maximum))


def _normalize_timestamp(value: Any) -> str | None:
    text = safe_audit_string(value, max_length=DRY_RUN_AUDIT_ID_MAX)
    if not text or text == "[REDACTED]":
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.isoformat().replace("+00:00", "Z")


def _safe_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    safe: list[str] = []
    for item in value:
        text = safe_audit_string(item, max_length=64)
        if text and text != "[REDACTED]":
            safe.append(text)
        if len(safe) >= DRY_RUN_AUDIT_LIST_MAX:
            break
    return safe


@dataclass(slots=True)
class DryRunAuditQueryRequest:
    filters: dict[str, Any] = field(default_factory=dict)
    limit: int = DRY_RUN_AUDIT_DEFAULT_LIMIT
    offset: int = 0
    sort_field: str = "recorded_at"
    sort_direction: str = "desc"
    applied_filters: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    valid: bool = True
    error_category: str = ""

    def __post_init__(self) -> None:
        self.limit = _safe_int(
            self.limit,
            default=DRY_RUN_AUDIT_DEFAULT_LIMIT,
            minimum=1,
            maximum=DRY_RUN_AUDIT_MAX_LIMIT,
        )
        self.offset = _safe_int(
            self.offset,
            default=0,
            minimum=0,
            maximum=DRY_RUN_AUDIT_MAX_OFFSET,
        )
        self.sort_field = safe_audit_string(self.sort_field, max_length=64) or "recorded_at"
        if self.sort_field not in ALLOWED_SORT_FIELDS:
            self.valid = False
            self.error_category = "invalid_sort"
            self.warnings.append("invalid_sort_field")
        self.sort_direction = safe_audit_string(self.sort_direction, max_length=8).lower() or "desc"
        if self.sort_direction not in ALLOWED_SORT_DIRECTIONS:
            self.valid = False
            self.error_category = "invalid_sort"
            self.warnings.append("invalid_sort_direction")
        self.applied_filters = self._normalize_filters(self.filters)
        self._validate_date_ranges()

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "DryRunAuditQueryRequest":
        if not isinstance(payload, dict):
            return cls()
        return cls(
            filters=payload.get("filters", {}) if isinstance(payload.get("filters", {}), dict) else {},
            limit=payload.get("limit", DRY_RUN_AUDIT_DEFAULT_LIMIT),
            offset=payload.get("offset", 0),
            sort_field=payload.get("sort_field", "recorded_at"),
            sort_direction=payload.get("sort_direction", "desc"),
        )

    def _mark_invalid(self, category: str, warning: str) -> None:
        self.valid = False
        self.error_category = category
        self.warnings.append(warning)

    def _normalize_filters(self, filters: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for raw_key, raw_value in filters.items():
            key = safe_audit_string(raw_key, max_length=64)
            if key not in ALLOWED_FILTERS:
                self.warnings.append("unsupported_filter")
                continue
            if key == "plan_type":
                value = safe_audit_string(raw_value, max_length=64)
                if value not in ALLOWED_PLAN_TYPES:
                    self._mark_invalid("invalid_filter", "invalid_plan_type")
                    continue
                normalized[key] = value
            elif key == "event_type":
                value = safe_audit_string(raw_value, max_length=80)
                if value not in ALLOWED_EVENT_TYPES:
                    self._mark_invalid("invalid_filter", "invalid_event_type")
                    continue
                normalized[key] = value
            elif key == "source_decision":
                value = safe_audit_string(raw_value, max_length=64).upper()
                if value not in ALLOWED_SOURCE_DECISIONS:
                    self._mark_invalid("invalid_filter", "invalid_source_decision")
                    continue
                normalized[key] = value
            elif key == "risk_level":
                value = safe_audit_string(raw_value, max_length=32).lower()
                if value not in ALLOWED_RISK_LEVELS:
                    self._mark_invalid("invalid_filter", "invalid_risk_level")
                    continue
                normalized[key] = value
            elif key == "storage_mode":
                value = safe_audit_string(raw_value, max_length=32).lower()
                if value not in ALLOWED_STORAGE_MODES:
                    self._mark_invalid("invalid_filter", "invalid_storage_mode")
                    continue
                normalized[key] = value
            elif key in BOOLEAN_FILTERS:
                value = _safe_bool(raw_value)
                if value is None:
                    self._mark_invalid("invalid_filter", f"invalid_{key}")
                    continue
                normalized[key] = value
            elif key in ID_FILTERS:
                value = safe_audit_id(raw_value)
                if not value:
                    self._mark_invalid("invalid_filter", f"invalid_{key}")
                    continue
                normalized[key] = value
            elif key in DATE_FILTERS:
                value = _normalize_timestamp(raw_value)
                if value is None:
                    self._mark_invalid("invalid_filter", f"invalid_{key}")
                    continue
                normalized[key] = value
        return normalized

    def _validate_date_ranges(self) -> None:
        created_from = self.applied_filters.get("created_at_from")
        created_to = self.applied_filters.get("created_at_to")
        recorded_from = self.applied_filters.get("recorded_at_from")
        recorded_to = self.applied_filters.get("recorded_at_to")
        if created_from and created_to and created_from > created_to:
            self._mark_invalid("invalid_filter", "invalid_created_at_range")
        if recorded_from and recorded_to and recorded_from > recorded_to:
            self._mark_invalid("invalid_filter", "invalid_recorded_at_range")


@dataclass(slots=True)
class DryRunAuditPageInfo:
    limit: int
    offset: int
    returned_count: int
    has_more: bool = False
    next_offset: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DryRunAuditEvidenceItem:
    event_type: str
    plan_id: str
    plan_type: str
    advisory: bool = True
    would_retry: bool | None = None
    would_replan: bool | None = None
    blocked: bool = False
    block_reasons: list[str] = field(default_factory=list)
    risk_level: str = "unknown"
    source_decision: str = "UNKNOWN"
    fingerprint_id: str = ""
    progress_score: int = 0
    stagnation_score: int = 0
    retry_eligibility_score: float | None = None
    replan_eligibility_score: float | None = None
    repeated_strategy_count: int = 0
    suggested_retry_strategy: str = ""
    suggested_strategy: str = ""
    evidence_summary: str = ""
    created_at: str = ""
    recorded_at: str = ""
    request_id: str = ""
    session_id: str = ""
    trace_id: str = ""
    recorded: bool = True
    degraded: bool = False
    storage_mode: str = "unknown"
    sqlite_enabled: bool = False

    @classmethod
    def from_retry_record(
        cls,
        record: DryRunRetryPlanEvidenceRecord,
        *,
        storage_mode: str,
        sqlite_enabled: bool,
    ) -> "DryRunAuditEvidenceItem":
        safe = DryRunRetryPlanEvidenceRecord.from_dict(record.as_dict())
        if safe is None:
            raise ValueError("invalid_retry_evidence")
        return cls(
            event_type=DRY_RUN_RETRY_PLAN_EVIDENCE_EVENT_TYPE,
            plan_id=safe.plan_id,
            plan_type="dry_run_retry",
            advisory=True,
            would_retry=safe.would_retry,
            would_replan=None,
            blocked=safe.blocked,
            block_reasons=list(safe.block_reasons),
            risk_level=safe.risk_level or "unknown",
            source_decision=safe.source_decision or "UNKNOWN",
            fingerprint_id=safe.fingerprint_id,
            progress_score=safe.progress_score,
            stagnation_score=safe.stagnation_score,
            retry_eligibility_score=safe.retry_eligibility_score,
            replan_eligibility_score=None,
            repeated_strategy_count=0,
            suggested_retry_strategy=safe.suggested_retry_strategy,
            suggested_strategy="",
            evidence_summary=safe.evidence_summary,
            created_at=safe.created_at,
            recorded_at=safe.recorded_at,
            request_id=safe.request_id,
            session_id=safe.session_id,
            trace_id=safe.trace_id,
            storage_mode=storage_mode,
            sqlite_enabled=sqlite_enabled,
        )

    @classmethod
    def from_replan_record(
        cls,
        record: DryRunReplanPlanEvidenceRecord,
        *,
        storage_mode: str,
        sqlite_enabled: bool,
    ) -> "DryRunAuditEvidenceItem":
        safe = DryRunReplanPlanEvidenceRecord.from_dict(record.as_dict())
        if safe is None:
            raise ValueError("invalid_replan_evidence")
        return cls(
            event_type=DRY_RUN_REPLAN_PLAN_EVIDENCE_EVENT_TYPE,
            plan_id=safe.plan_id,
            plan_type="dry_run_replan",
            advisory=True,
            would_retry=None,
            would_replan=safe.would_replan,
            blocked=safe.blocked,
            block_reasons=list(safe.block_reasons),
            risk_level=safe.risk_level or "unknown",
            source_decision=safe.source_decision or "UNKNOWN",
            fingerprint_id=safe.fingerprint_id,
            progress_score=safe.progress_score,
            stagnation_score=safe.stagnation_score,
            retry_eligibility_score=None,
            replan_eligibility_score=safe.replan_eligibility_score,
            repeated_strategy_count=safe.repeated_strategy_count,
            suggested_retry_strategy="",
            suggested_strategy=safe.suggested_strategy,
            evidence_summary=safe.evidence_summary,
            created_at=safe.created_at,
            recorded_at=safe.created_at,
            request_id=safe.request_id,
            session_id=safe.session_id,
            trace_id=safe.trace_id,
            storage_mode=storage_mode,
            sqlite_enabled=sqlite_enabled,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "plan_id": self.plan_id,
            "plan_type": self.plan_type,
            "advisory": True,
            "would_retry": self.would_retry,
            "would_replan": self.would_replan,
            "blocked": self.blocked,
            "block_reasons": list(self.block_reasons),
            "risk_level": self.risk_level,
            "source_decision": self.source_decision,
            "fingerprint_id": self.fingerprint_id,
            "progress_score": self.progress_score,
            "stagnation_score": self.stagnation_score,
            "retry_eligibility_score": self.retry_eligibility_score,
            "replan_eligibility_score": self.replan_eligibility_score,
            "repeated_strategy_count": self.repeated_strategy_count,
            "suggested_retry_strategy": self.suggested_retry_strategy,
            "suggested_strategy": self.suggested_strategy,
            "evidence_summary": self.evidence_summary,
            "created_at": self.created_at,
            "recorded_at": self.recorded_at,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "recorded": self.recorded,
            "degraded": self.degraded,
            "storage_mode": self.storage_mode,
            "sqlite_enabled": self.sqlite_enabled,
            "persistence": {
                "recorded": self.recorded,
                "degraded": self.degraded,
                "storage_mode": self.storage_mode,
                "sqlite_enabled": self.sqlite_enabled,
            },
        }


@dataclass(slots=True)
class DryRunAuditEvidenceDetail:
    item: DryRunAuditEvidenceItem
    diagnostic_details: dict[str, Any] = field(default_factory=dict)
    storage_metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = self.item.as_dict()
        payload["diagnostic_details"] = dict(self.diagnostic_details)
        payload["storage_metadata"] = dict(self.storage_metadata)
        return payload


@dataclass(slots=True)
class DryRunAuditQueryResponse:
    items: list[DryRunAuditEvidenceItem] = field(default_factory=list)
    page_info: DryRunAuditPageInfo = field(
        default_factory=lambda: DryRunAuditPageInfo(
            limit=DRY_RUN_AUDIT_DEFAULT_LIMIT,
            offset=0,
            returned_count=0,
        )
    )
    applied_filters: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    degraded: bool = False
    error_category: str = ""
    generated_at: str = field(default_factory=utc_now_iso)

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "items": [item.as_dict() for item in self.items],
            "page_info": self.page_info.as_dict(),
            "applied_filters": dict(self.applied_filters),
            "warnings": list(self.warnings),
            "degraded": self.degraded,
            "generated_at": self.generated_at,
        }
        if self.degraded:
            payload["error_category"] = self.error_category or "unknown"
        return payload


def apply_audit_query(
    items: list[DryRunAuditEvidenceItem],
    request: DryRunAuditQueryRequest,
) -> DryRunAuditQueryResponse:
    if not request.valid:
        return DryRunAuditQueryResponse(
            items=[],
            page_info=DryRunAuditPageInfo(
                limit=request.limit,
                offset=request.offset,
                returned_count=0,
            ),
            applied_filters=dict(request.applied_filters),
            warnings=list(request.warnings),
            degraded=True,
            error_category=request.error_category or "invalid_request",
        )
    filtered = [item for item in items if _matches_filters(item, request.applied_filters)]
    ordered = sorted(filtered, key=lambda item: _sort_key(item, request.sort_field))
    if request.sort_direction == "desc":
        ordered = list(reversed(ordered))
    start = request.offset
    end = start + request.limit
    page_items = ordered[start:end]
    has_more = len(ordered) > end
    return DryRunAuditQueryResponse(
        items=page_items,
        page_info=DryRunAuditPageInfo(
            limit=request.limit,
            offset=request.offset,
            returned_count=len(page_items),
            has_more=has_more,
            next_offset=end if has_more else None,
        ),
        applied_filters=dict(request.applied_filters),
        warnings=list(request.warnings),
        degraded=False,
    )


def degraded_audit_response(
    request: DryRunAuditQueryRequest,
    *,
    error_category: str,
    warning: str,
) -> DryRunAuditQueryResponse:
    warnings = list(request.warnings)
    warnings.append(warning)
    return DryRunAuditQueryResponse(
        items=[],
        page_info=DryRunAuditPageInfo(
            limit=request.limit,
            offset=request.offset,
            returned_count=0,
        ),
        applied_filters=dict(request.applied_filters),
        warnings=warnings,
        degraded=True,
        error_category=error_category,
    )


def detail_from_item(item: DryRunAuditEvidenceItem) -> DryRunAuditEvidenceDetail:
    return DryRunAuditEvidenceDetail(
        item=item,
        diagnostic_details={
            "recorded": item.recorded,
            "degraded": item.degraded,
            "storage_mode": item.storage_mode,
            "sqlite_enabled": item.sqlite_enabled,
        },
        storage_metadata={
            "storage_mode": item.storage_mode,
            "sqlite_enabled": item.sqlite_enabled,
        },
    )


def _matches_filters(item: DryRunAuditEvidenceItem, filters: dict[str, Any]) -> bool:
    for key, value in filters.items():
        if key == "created_at_from" and item.created_at < value:
            return False
        if key == "created_at_to" and item.created_at > value:
            return False
        if key == "recorded_at_from" and item.recorded_at < value:
            return False
        if key == "recorded_at_to" and item.recorded_at > value:
            return False
        if key in DATE_FILTERS:
            continue
        if getattr(item, key, None) != value:
            return False
    return True


def _sort_key(item: DryRunAuditEvidenceItem, sort_field: str) -> tuple[Any, str, str, str]:
    if sort_field == "risk_level":
        primary: Any = RISK_SORT_ORDER.get(item.risk_level, RISK_SORT_ORDER["unknown"])
    elif sort_field == "source_decision":
        primary = SOURCE_DECISION_SORT_ORDER.get(
            item.source_decision,
            SOURCE_DECISION_SORT_ORDER["UNKNOWN"],
        )
    else:
        primary = getattr(item, sort_field, "")
    return (primary, item.recorded_at, item.created_at, item.plan_id)
