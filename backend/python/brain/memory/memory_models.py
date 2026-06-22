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
