from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    from uuid import uuid4
    return str(uuid4())


MEMORY_BACKEND_JSONL = "jsonl"
MEMORY_BACKEND_SQLITE = "sqlite"

SAFE_DEFAULT_BACKEND = MEMORY_BACKEND_JSONL


@dataclass(slots=True)
class MemoryRecord:
    record_id: str
    record_type: str
    payload: dict[str, Any]
    created_at: str = field(default_factory=utc_now_iso)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ConversationRecord:
    conversation_id: str = field(default_factory=new_id)
    session_id: str = ""
    title: str = ""
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MessageRecord:
    message_id: str = field(default_factory=new_id)
    conversation_id: str = ""
    role: str = ""
    content: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    token_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EpisodeRecord:
    episode_id: str = field(default_factory=new_id)
    session_id: str = ""
    goal_id: str = ""
    event_type: str = ""
    outcome: str = ""
    description: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SemanticFactRecord:
    fact_id: str = field(default_factory=new_id)
    subject: str = ""
    predicate: str = ""
    object_value: str = ""
    confidence: float = 0.0
    source_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RuntimeEventRecord:
    event_id: str = field(default_factory=new_id)
    event_type: str = ""
    source: str = ""
    session_id: str = ""
    run_id: str = ""
    summary: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ProviderAttemptRecord:
    attempt_id: str = field(default_factory=new_id)
    provider: str = ""
    model: str = ""
    session_id: str = ""
    run_id: str = ""
    status: str = ""
    duration_ms: int = 0
    token_count: int = 0
    error_type: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        safe = asdict(self)
        safe.pop("metadata", None)
        return safe


@dataclass(slots=True)
class GovernanceEventRecord:
    event_id: str = field(default_factory=new_id)
    event_type: str = ""
    source: str = ""
    session_id: str = ""
    run_id: str = ""
    status: str = ""
    reason: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class LearningArtifactRecord:
    artifact_id: str = field(default_factory=new_id)
    artifact_type: str = ""
    source: str = ""
    session_id: str = ""
    content_summary: str = ""
    confidence: float = 0.0
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


AUTONOMY_SESSION_STRING_MAX = 80
AUTONOMY_SESSION_ID_MAX = 128
AUTONOMY_SESSION_FINGERPRINT_MAX = 64
AUTONOMY_SESSION_LIST_MAX = 20
AUTONOMY_SESSION_COUNT_MAX = 1_000_000

_AUTONOMY_SESSION_ALLOWED_FIELDS = frozenset({
    "session_id",
    "last_error_type",
    "current_error_count",
    "stagnant_attempts",
    "distinct_error_count",
    "distinct_error_types",
    "progressive_cycles",
    "last_runtime_mode",
    "last_provider_failure_type",
    "last_response_length",
    "last_response_was_safe_fallback",
    "last_decision",
    "last_fingerprint_id",
    "last_progress_score",
    "last_stagnation_score",
    "repeated_strategy_count",
    "strategies_attempted",
    "updated_at",
    "expires_at",
})

_AUTONOMY_SESSION_FORBIDDEN_FIELDS = frozenset({
    "raw_prompt",
    "prompt",
    "raw_response",
    "response",
    "raw_receipt",
    "receipt",
    "stack_trace",
    "stacktrace",
    "traceback",
    "stdout",
    "stderr",
    "command_args",
    "args",
    "headers",
    "cookies",
    "api_key",
    "api-key",
    "apikey",
    "token",
    "secret",
    "password",
    "credential",
    "credentials",
    "provider_credentials",
    "file_contents",
    "file_content",
    ".env",
    "env_content",
    "user_message",
    "tool_output",
    "provider_payload",
})


def _safe_autonomy_string(value: Any, *, max_length: int = AUTONOMY_SESSION_STRING_MAX) -> str:
    if value is None:
        return ""
    text = str(value).replace("\x00", "").strip()
    lowered = text.lower()
    if any(marker in lowered for marker in ("sk-", "api_key", "authorization:", "bearer ", "token=", "secret=")):
        return "[REDACTED]"
    allowed_chars: list[str] = []
    for char in text:
        if char.isalnum() or char in ("_", "-", ".", ":", "/", "+", " "):
            allowed_chars.append(char)
    return "".join(allowed_chars)[:max_length]


def _safe_autonomy_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(number, AUTONOMY_SESSION_COUNT_MAX))


def _safe_autonomy_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes")
    return bool(value)


def _safe_autonomy_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    safe: list[str] = []
    for item in value:
        text = _safe_autonomy_string(item)
        if text and text != "[REDACTED]":
            safe.append(text)
        if len(safe) >= AUTONOMY_SESSION_LIST_MAX:
            break
    return safe


@dataclass(slots=True)
class AutonomySessionStateRecord:
    session_id: str
    last_error_type: str = ""
    current_error_count: int = 0
    stagnant_attempts: int = 0
    distinct_error_count: int = 0
    distinct_error_types: list[str] = field(default_factory=list)
    progressive_cycles: int = 0
    last_runtime_mode: str = ""
    last_provider_failure_type: str = ""
    last_response_length: int = 0
    last_response_was_safe_fallback: bool = False
    last_decision: str = ""
    last_fingerprint_id: str = ""
    last_progress_score: int = 0
    last_stagnation_score: int = 0
    repeated_strategy_count: int = 0
    strategies_attempted: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=utc_now_iso)
    expires_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        self.session_id = _safe_autonomy_string(self.session_id, max_length=AUTONOMY_SESSION_ID_MAX)
        self.last_error_type = _safe_autonomy_string(self.last_error_type)
        self.current_error_count = _safe_autonomy_int(self.current_error_count)
        self.stagnant_attempts = _safe_autonomy_int(self.stagnant_attempts)
        self.distinct_error_types = _safe_autonomy_list(self.distinct_error_types)
        self.distinct_error_count = _safe_autonomy_int(
            self.distinct_error_count or len(self.distinct_error_types)
        )
        self.progressive_cycles = _safe_autonomy_int(self.progressive_cycles)
        self.last_runtime_mode = _safe_autonomy_string(self.last_runtime_mode)
        self.last_provider_failure_type = _safe_autonomy_string(self.last_provider_failure_type)
        self.last_response_length = _safe_autonomy_int(self.last_response_length)
        self.last_response_was_safe_fallback = _safe_autonomy_bool(self.last_response_was_safe_fallback)
        self.last_decision = _safe_autonomy_string(self.last_decision)
        self.last_fingerprint_id = _safe_autonomy_string(
            self.last_fingerprint_id,
            max_length=AUTONOMY_SESSION_FINGERPRINT_MAX,
        )
        self.last_progress_score = _safe_autonomy_int(self.last_progress_score)
        self.last_stagnation_score = _safe_autonomy_int(self.last_stagnation_score)
        self.repeated_strategy_count = _safe_autonomy_int(self.repeated_strategy_count)
        self.strategies_attempted = _safe_autonomy_list(self.strategies_attempted)
        self.updated_at = _safe_autonomy_string(self.updated_at, max_length=AUTONOMY_SESSION_ID_MAX)
        self.expires_at = _safe_autonomy_string(self.expires_at, max_length=AUTONOMY_SESSION_ID_MAX)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AutonomySessionStateRecord | None":
        if not isinstance(payload, dict):
            return None
        safe = {
            key: value
            for key, value in payload.items()
            if key in _AUTONOMY_SESSION_ALLOWED_FIELDS
            and key.lower() not in _AUTONOMY_SESSION_FORBIDDEN_FIELDS
        }
        session_id = _safe_autonomy_string(
            safe.get("session_id", ""),
            max_length=AUTONOMY_SESSION_ID_MAX,
        )
        if not session_id:
            return None
        safe["session_id"] = session_id
        return cls(**safe)

    def as_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "last_error_type": self.last_error_type,
            "current_error_count": self.current_error_count,
            "stagnant_attempts": self.stagnant_attempts,
            "distinct_error_count": self.distinct_error_count,
            "distinct_error_types": list(self.distinct_error_types),
            "progressive_cycles": self.progressive_cycles,
            "last_runtime_mode": self.last_runtime_mode,
            "last_provider_failure_type": self.last_provider_failure_type,
            "last_response_length": self.last_response_length,
            "last_response_was_safe_fallback": self.last_response_was_safe_fallback,
            "last_decision": self.last_decision,
            "last_fingerprint_id": self.last_fingerprint_id,
            "last_progress_score": self.last_progress_score,
            "last_stagnation_score": self.last_stagnation_score,
            "repeated_strategy_count": self.repeated_strategy_count,
            "strategies_attempted": list(self.strategies_attempted),
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
        }


DRY_RUN_REPLAN_PLAN_EVIDENCE_EVENT_TYPE = "dry_run_replan_plan_evidence"
DRY_RUN_REPLAN_EVIDENCE_STRING_MAX = 120
DRY_RUN_REPLAN_EVIDENCE_ID_MAX = 128
DRY_RUN_REPLAN_EVIDENCE_SUMMARY_MAX = 240
DRY_RUN_REPLAN_EVIDENCE_LIST_MAX = 20
DRY_RUN_REPLAN_EVIDENCE_COUNT_MAX = 1_000_000

_DRY_RUN_REPLAN_EVIDENCE_ALLOWED_FIELDS = frozenset({
    "event_type",
    "plan_id",
    "plan_type",
    "advisory",
    "would_replan",
    "replan_reason",
    "blocked",
    "block_reasons",
    "replan_eligibility_score",
    "risk_level",
    "source_decision",
    "fingerprint_id",
    "stagnation_score",
    "progress_score",
    "repeated_strategy_count",
    "suggested_strategy",
    "evidence_summary",
    "created_at",
    "session_id",
    "request_id",
    "trace_id",
})

_DRY_RUN_REPLAN_EVIDENCE_FORBIDDEN_FIELDS = frozenset({
    "raw_prompt",
    "prompt",
    "rewritten_prompt",
    "raw_rewritten_prompt",
    "raw_response",
    "response",
    "provider_payload",
    "raw_provider_payload",
    "provider_credentials",
    "api_key",
    "api-key",
    "apikey",
    "token",
    "secret",
    "password",
    "credential",
    "credentials",
    "headers",
    "cookies",
    "stack_trace",
    "stacktrace",
    "traceback",
    "stdout",
    "stderr",
    "command_args",
    "args",
    "file_contents",
    "file_content",
    ".env",
    "env_content",
    "tool_output",
    "full_tool_output",
    "raw_receipt",
    "receipt",
    "exception",
    "raw_exception",
    "context",
    "raw_context",
    "repr",
})


def _safe_dry_run_replan_string(
    value: Any,
    *,
    max_length: int = DRY_RUN_REPLAN_EVIDENCE_STRING_MAX,
) -> str:
    if value is None:
        return ""
    text = str(value).replace("\x00", "").replace("\r", " ").replace("\n", " ").strip()
    lowered = text.lower()
    forbidden_markers = (
        "sk-",
        "api_key",
        "authorization:",
        "bearer ",
        "token=",
        "secret=",
        "password=",
        "raw_prompt",
        "rewritten_prompt",
        "raw_response",
        "provider_payload",
        "traceback",
        "stack trace",
        "stdout",
        "stderr",
        ".env",
    )
    if any(marker in lowered for marker in forbidden_markers):
        return "[REDACTED]"
    allowed_chars: list[str] = []
    for char in text:
        if char.isalnum() or char in ("_", "-", ".", ":", "/", "+", " "):
            allowed_chars.append(char)
    return "".join(allowed_chars)[:max_length]


def _safe_dry_run_replan_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes")
    return bool(value)


def _safe_dry_run_replan_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(number, DRY_RUN_REPLAN_EVIDENCE_COUNT_MAX))


def _safe_dry_run_replan_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if score < 0:
        return 0.0
    if score > 1:
        return 1.0
    return round(score, 3)


def _safe_dry_run_replan_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    safe: list[str] = []
    for item in value:
        text = _safe_dry_run_replan_string(item, max_length=64)
        if text and text != "[REDACTED]":
            safe.append(text)
        if len(safe) >= DRY_RUN_REPLAN_EVIDENCE_LIST_MAX:
            break
    return safe


@dataclass(slots=True)
class DryRunReplanPlanEvidenceRecord:
    plan_id: str
    plan_type: str = "dry_run_replan"
    advisory: bool = True
    would_replan: bool = False
    replan_reason: str = ""
    blocked: bool = False
    block_reasons: list[str] = field(default_factory=list)
    replan_eligibility_score: float = 0.0
    risk_level: str = ""
    source_decision: str = ""
    fingerprint_id: str = ""
    stagnation_score: int = 0
    progress_score: int = 0
    repeated_strategy_count: int = 0
    suggested_strategy: str = ""
    evidence_summary: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    session_id: str = ""
    request_id: str = ""
    trace_id: str = ""
    event_type: str = DRY_RUN_REPLAN_PLAN_EVIDENCE_EVENT_TYPE

    def __post_init__(self) -> None:
        self.event_type = DRY_RUN_REPLAN_PLAN_EVIDENCE_EVENT_TYPE
        self.plan_id = _safe_dry_run_replan_string(
            self.plan_id,
            max_length=DRY_RUN_REPLAN_EVIDENCE_ID_MAX,
        )
        self.plan_type = _safe_dry_run_replan_string(self.plan_type, max_length=64) or "dry_run_replan"
        self.advisory = True
        self.would_replan = _safe_dry_run_replan_bool(self.would_replan)
        self.replan_reason = _safe_dry_run_replan_string(self.replan_reason, max_length=64)
        self.blocked = _safe_dry_run_replan_bool(self.blocked)
        self.block_reasons = _safe_dry_run_replan_list(self.block_reasons)
        self.replan_eligibility_score = _safe_dry_run_replan_score(self.replan_eligibility_score)
        self.risk_level = _safe_dry_run_replan_string(self.risk_level, max_length=24)
        self.source_decision = _safe_dry_run_replan_string(self.source_decision, max_length=48)
        self.fingerprint_id = _safe_dry_run_replan_string(self.fingerprint_id, max_length=64)
        self.stagnation_score = _safe_dry_run_replan_int(self.stagnation_score)
        self.progress_score = _safe_dry_run_replan_int(self.progress_score)
        self.repeated_strategy_count = _safe_dry_run_replan_int(self.repeated_strategy_count)
        self.suggested_strategy = _safe_dry_run_replan_string(self.suggested_strategy, max_length=64)
        self.evidence_summary = _safe_dry_run_replan_string(
            self.evidence_summary,
            max_length=DRY_RUN_REPLAN_EVIDENCE_SUMMARY_MAX,
        )
        self.created_at = _safe_dry_run_replan_string(
            self.created_at,
            max_length=DRY_RUN_REPLAN_EVIDENCE_ID_MAX,
        )
        self.session_id = _safe_dry_run_replan_string(
            self.session_id,
            max_length=DRY_RUN_REPLAN_EVIDENCE_ID_MAX,
        )
        self.request_id = _safe_dry_run_replan_string(
            self.request_id,
            max_length=DRY_RUN_REPLAN_EVIDENCE_ID_MAX,
        )
        self.trace_id = _safe_dry_run_replan_string(
            self.trace_id,
            max_length=DRY_RUN_REPLAN_EVIDENCE_ID_MAX,
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DryRunReplanPlanEvidenceRecord | None":
        if not isinstance(payload, dict):
            return None
        safe = {
            key: value
            for key, value in payload.items()
            if key in _DRY_RUN_REPLAN_EVIDENCE_ALLOWED_FIELDS
            and key.lower() not in _DRY_RUN_REPLAN_EVIDENCE_FORBIDDEN_FIELDS
        }
        plan_id = _safe_dry_run_replan_string(
            safe.get("plan_id", ""),
            max_length=DRY_RUN_REPLAN_EVIDENCE_ID_MAX,
        )
        if not plan_id:
            return None
        safe["plan_id"] = plan_id
        safe["event_type"] = DRY_RUN_REPLAN_PLAN_EVIDENCE_EVENT_TYPE
        return cls(**safe)

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_type": DRY_RUN_REPLAN_PLAN_EVIDENCE_EVENT_TYPE,
            "plan_id": self.plan_id,
            "plan_type": self.plan_type,
            "advisory": True,
            "would_replan": self.would_replan,
            "replan_reason": self.replan_reason,
            "blocked": self.blocked,
            "block_reasons": list(self.block_reasons),
            "replan_eligibility_score": self.replan_eligibility_score,
            "risk_level": self.risk_level,
            "source_decision": self.source_decision,
            "fingerprint_id": self.fingerprint_id,
            "stagnation_score": self.stagnation_score,
            "progress_score": self.progress_score,
            "repeated_strategy_count": self.repeated_strategy_count,
            "suggested_strategy": self.suggested_strategy,
            "evidence_summary": self.evidence_summary,
            "created_at": self.created_at,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "trace_id": self.trace_id,
        }


SENSITIVE_KEYS = frozenset({
    "api_key", "api-key", "apikey",
    "token", "secret", "password",
    "credential", "auth_token", "authorization",
    "raw_prompt", "raw_response",
})


def redact_payload(payload: dict[str, Any], depth: int = 0) -> dict[str, Any]:
    if depth > 5:
        return {"_redacted": "max_depth"}
    redacted: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(key, str) and key.lower() in SENSITIVE_KEYS:
            redacted[key] = "[REDACTED]"
        elif isinstance(value, dict):
            redacted[key] = redact_payload(value, depth + 1)
        elif isinstance(value, list):
            redacted[key] = [
                redact_payload(item, depth + 1) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            redacted[key] = value
    return redacted
