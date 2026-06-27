"""Read-only autonomy evidence view.

Builds Cockpit-safe autonomy evidence from persisted governance events.
No raw prompts, responses, receipts, command data, stack traces, or secrets are
returned. Read failures degrade to an empty advisory-only payload.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from brain.memory.memory_facade import MemoryFacade
from brain.runtime.observability.public_runtime_payload import sanitize_public_runtime_payload

_AUTONOMY_EVENT_TYPES = frozenset({"autonomy_decision", "autonomy_decision_evidence"})
_ALLOWED_METADATA_KEYS = frozenset({
    "decision_id",
    "risk_level",
    "advisory",
    "fingerprint_id",
    "progress_score",
    "stagnation_score",
    "recommended_decision_hint",
    "repeated_strategy_count",
    "strategies_attempted",
    "is_progress",
    "is_stagnation",
    "stagnant_attempts",
})


def _safe_str(value: Any, limit: int = 240) -> str:
    text = str(value or "").strip()
    return text[:limit]


def _safe_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("true", "1", "yes"):
            return True
        if normalized in ("false", "0", "no"):
            return False
    return None


def _safe_number(value: Any) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


def _safe_metadata(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return {}
    safe: dict[str, Any] = {}
    for key in _ALLOWED_METADATA_KEYS:
        if key not in raw:
            continue
        value = raw.get(key)
        if isinstance(value, list):
            safe[key] = [_safe_str(item, 80) for item in value if _safe_str(item, 80)]
        elif isinstance(value, bool):
            safe[key] = value
        elif isinstance(value, (int, float)):
            safe[key] = value
        else:
            safe[key] = _safe_str(value, 160)
    return safe


def _record_to_evidence_item(record: Any) -> dict[str, Any] | None:
    if not isinstance(record, Mapping) or record.get("type") != "governance_event":
        return None
    payload = record.get("payload")
    if not isinstance(payload, Mapping):
        return None
    event_type = _safe_str(payload.get("event_type"), 80)
    if event_type not in _AUTONOMY_EVENT_TYPES:
        return None

    metadata = _safe_metadata(payload.get("metadata"))
    status = _safe_str(payload.get("status"), 80) or "unknown"
    advisory = _safe_bool(metadata.get("advisory"))
    if advisory is None:
        advisory = True

    item: dict[str, Any] = {
        "id": _safe_str(payload.get("event_id"), 96),
        "event_type": event_type,
        "session_id": _safe_str(payload.get("session_id"), 128),
        "run_id": _safe_str(payload.get("run_id"), 128),
        "decision": status,
        "advisory": advisory,
        "risk_level": _safe_str(metadata.get("risk_level"), 32),
        "reason_summary": _safe_str(payload.get("reason"), 300),
        "created_at": _safe_str(payload.get("created_at"), 64),
        "metadata": metadata,
    }

    for key in (
        "fingerprint_id",
        "recommended_decision_hint",
        "strategies_attempted",
        "repeated_strategy_count",
        "progress_score",
        "stagnation_score",
        "is_progress",
        "is_stagnation",
        "stagnant_attempts",
    ):
        if key in metadata:
            item[key] = metadata[key]

    return sanitize_public_runtime_payload(item)


def build_autonomy_evidence_payload(
    *,
    facade: MemoryFacade | None = None,
    session_id: str = "",
    limit: int = 50,
) -> dict[str, Any]:
    """Return a read-only, safe autonomy evidence payload.

    Uses the existing MemoryFacade, so JSONL remains the default mirror and
    SQLite remains opt-in. Any read failure returns an empty safe payload.
    """

    safe_limit = min(max(int(limit or 0), 1), 200)
    try:
        reader = facade or MemoryFacade()
        reader.initialize()
        records = reader.audit_records()
    except Exception:
        records = []

    items: list[dict[str, Any]] = []
    wanted_session = _safe_str(session_id, 128)
    for record in reversed(records):
        item = _record_to_evidence_item(record)
        if item is None:
            continue
        if wanted_session and item.get("session_id") != wanted_session:
            continue
        items.append(item)
        if len(items) >= safe_limit:
            break

    escalation_items = [item for item in items if item.get("decision") == "ESCALATE_TO_MISAEL"]
    return {
        "mode": "advisory-only",
        "read_only": True,
        "source": "memory_facade_governance_events",
        "session_id": wanted_session,
        "items": items,
        "summary": {
            "total": len(items),
            "escalation_count": len(escalation_items),
            "latest_decision": items[0].get("decision") if items else "",
            "latest_escalation_at": escalation_items[0].get("created_at") if escalation_items else "",
        },
    }
