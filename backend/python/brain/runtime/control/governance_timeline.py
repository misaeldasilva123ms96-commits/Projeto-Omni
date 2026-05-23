"""Unified governance timeline events (Phase 30.6)."""

from __future__ import annotations

from enum import Enum
from typing import Any

from .governance_taxonomy import (
    GovernanceReason,
    governance_dict_for_resolution,
    infer_governance_reason,
)


class GovernanceTimelineEventType(str, Enum):
    START = "start"
    HOLD = "hold"
    PAUSE = "pause"
    RESUME = "resume"
    APPROVE = "approve"
    ROLLBACK = "rollback"
    TIMEOUT = "timeout"
    COMPLETE = "complete"
    FAIL = "fail"
    BLOCKED = "blocked"
    UPDATE = "update"


def infer_event_type_from_transition(
    *,
    reason: str,
    run_status: str,
    current_resolution: str,
    previous_resolution: str,
) -> str:
    """Map a resolution transition + run status to a normalized timeline event type."""
    r = str(reason or "").strip()
    rs = str(run_status or "").strip().lower()
    cur = str(current_resolution or "").strip().lower()

    if r == GovernanceReason.OPERATOR_PAUSE.value:
        return GovernanceTimelineEventType.PAUSE.value
    if r == GovernanceReason.OPERATOR_RESUME.value:
        return GovernanceTimelineEventType.RESUME.value
    if r == GovernanceReason.OPERATOR_APPROVE.value:
        return GovernanceTimelineEventType.APPROVE.value
    if r == GovernanceReason.GOVERNANCE_HOLD.value:
        return GovernanceTimelineEventType.HOLD.value
    if r == GovernanceReason.PROMOTION_ROLLBACK_THRESHOLD.value:
        return GovernanceTimelineEventType.ROLLBACK.value
    if r == GovernanceReason.TIMEOUT.value:
        return GovernanceTimelineEventType.TIMEOUT.value
    if r == GovernanceReason.POLICY_BLOCK.value or cur == "blocked":
        return GovernanceTimelineEventType.BLOCKED.value
    if r == GovernanceReason.COMPLETED.value or rs == "completed":
        return GovernanceTimelineEventType.COMPLETE.value
    if r == GovernanceReason.FAILED.value or rs == "failed":
        return GovernanceTimelineEventType.FAIL.value
    if cur == "hold":
        return GovernanceTimelineEventType.HOLD.value
    if cur == "paused":
        return GovernanceTimelineEventType.PAUSE.value
    if cur == "approved":
        return GovernanceTimelineEventType.APPROVE.value
    if cur == "resumed":
        return GovernanceTimelineEventType.RESUME.value
    return GovernanceTimelineEventType.UPDATE.value


def map_resolution_to_event_type(current_resolution: str, *, reason: str, run_status: str) -> str:
    return infer_event_type_from_transition(
        reason=reason,
        run_status=run_status,
        current_resolution=current_resolution,
        previous_resolution="",
    )


def build_governance_timeline_event(
    *,
    event_type: str,
    timestamp: str,
    current_resolution: str,
    previous_resolution: str,
    reason: str,
    decision_source: str,
    run_status: str,
    operator_id: str | None = None,
    promotion_metadata: dict[str, Any] | None = None,
    engine_mode: str | None = None,
    extensions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event_type": str(event_type).strip(),
        "timestamp": str(timestamp).strip(),
        "resolution": str(current_resolution).strip(),
        "previous_resolution": str(previous_resolution).strip(),
        "run_status": str(run_status).strip(),
        "governance": governance_dict_for_resolution(reason=reason, decision_source=decision_source),
    }
    if operator_id:
        payload["operator_id"] = str(operator_id).strip()
    if promotion_metadata:
        payload["promotion_metadata"] = dict(promotion_metadata)
    if engine_mode:
        payload["engine_mode"] = str(engine_mode).strip()
    if extensions:
        payload["extensions"] = dict(extensions)
    return payload


def timeline_event_from_resolution_dict(
    item: dict[str, Any],
    *,
    run_status: str,
    event_type: str | None = None,
) -> dict[str, Any]:
    """Build a timeline row from a legacy resolution_history / resolution dict."""
    reason = str(item.get("reason", "") or "")
    decision_source = str(item.get("decision_source", "") or "runtime_orchestrator")
    current = str(item.get("current_resolution", "") or "")
    previous = str(item.get("previous_resolution", "") or "")
    ts = str(item.get("timestamp", "") or "").strip()
    gov = item.get("governance")
    if not isinstance(gov, dict):
        gov = governance_dict_for_resolution(reason=reason, decision_source=decision_source)
    et = event_type or infer_event_type_from_transition(
        reason=reason,
        run_status=run_status,
        current_resolution=current,
        previous_resolution=previous,
    )
    return build_governance_timeline_event(
        event_type=et,
        timestamp=ts,
        current_resolution=current,
        previous_resolution=previous,
        reason=reason,
        decision_source=decision_source,
        run_status=run_status,
        operator_id=str(item.get("operator_id", "")).strip() or None,
        promotion_metadata=dict(item.get("promotion_metadata", {}) or {}) if item.get("promotion_metadata") else None,
        engine_mode=str(item.get("engine_mode", "")).strip() or None,
    )


def synthesize_timeline_from_legacy(
    *,
    resolution_history: list[dict[str, Any]],
    resolution: dict[str, Any] | None,
    run_status: str,
) -> list[dict[str, Any]]:
    """Derive a governance timeline from legacy resolution fields when none was persisted."""
    rows: list[dict[str, Any]] = list(resolution_history)
    if not rows and resolution:
        rows = [dict(resolution)]
    out: list[dict[str, Any]] = []
    for index, item in enumerate(rows):
        if not isinstance(item, dict):
            continue
        et: str | None = GovernanceTimelineEventType.START.value if index == 0 else None
        out.append(timeline_event_from_resolution_dict(item, run_status=run_status, event_type=et))
    return out


def infer_event_type_from_last_action(*, last_action: str, run_status: str) -> str:
    """Infer a coarse event type from orchestrator-style last_action text (fallback)."""
    inferred = infer_governance_reason(last_action=last_action, run_status=run_status)
    return infer_event_type_from_transition(
        reason=inferred.value,
        run_status=run_status,
        current_resolution="",
        previous_resolution="",
    )
