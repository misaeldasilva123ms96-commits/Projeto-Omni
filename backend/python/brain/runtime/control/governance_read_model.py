"""Operational governance read layer (Phase 30.8)."""

from __future__ import annotations

from typing import Any

from .governance_taxonomy import GovernanceReason, GovernanceSeverity, build_governance_decision
from .program_closure import GOVERNANCE_TAXONOMY_VERSION
from .run_registry import RunRecord, RunRegistry, RunStatus


def _all_records(registry: RunRegistry, *, max_runs: int = 5000) -> list[RunRecord]:
    return registry.get_all(limit=max(1, int(max_runs or 5000)))


def latest_governance_event_view(record: RunRecord) -> dict[str, Any] | None:
    """Latest timeline row for a run, or None."""
    if not record.governance_timeline:
        return None
    last = record.governance_timeline[-1]
    return dict(last) if isinstance(last, dict) else None


def build_governance_run_view(record: RunRecord) -> dict[str, Any]:
    """Concise operational view of current governance for one run."""
    resolution = record.resolution
    gov: dict[str, Any]
    if resolution is not None:
        gov = build_governance_decision(
            reason=resolution.reason,
            decision_source=resolution.decision_source,
        ).as_dict()
        current_resolution = resolution.current_resolution
        reason = resolution.reason
    else:
        gov = {}
        current_resolution = ""
        reason = ""
    latest = latest_governance_event_view(record)
    return {
        "run_id": record.run_id,
        "session_id": record.session_id,
        "status": record.status.value,
        "updated_at": record.updated_at,
        "last_action": record.last_action,
        "progress_score": record.progress_score,
        "resolution": current_resolution,
        "reason": reason,
        "governance": gov,
        "latest_governance_event": latest,
    }


def attention_priority_for_run(record: RunRecord) -> tuple[int, str]:
    """
    Deterministic (priority, reason_code) for operator attention ordering.
    Lower priority value = inspect first.
    """
    resolution = record.resolution
    reason = str((resolution.reason if resolution else "") or "").strip()
    if reason == GovernanceReason.POLICY_BLOCK.value:
        return (0, "blocked_by_policy")
    if record.status == RunStatus.AWAITING_APPROVAL:
        return (1, "awaiting_approval")
    if record.status == RunStatus.PAUSED and str(record.last_action).startswith("operator_"):
        return (1, "operator_pause")
    if reason == GovernanceReason.PROMOTION_ROLLBACK_THRESHOLD.value:
        return (2, "rollback")
    if str((record.metadata or {}).get("promotion_rollback_reason", "")).strip():
        return (2, "rollback_metadata")
    if record.status == RunStatus.FAILED:
        last = record.governance_timeline[-1] if record.governance_timeline else {}
        gov = last.get("governance") if isinstance(last, dict) else {}
        sev = str((gov or {}).get("severity", "")).strip() if isinstance(gov, dict) else ""
        if sev == GovernanceSeverity.CRITICAL.value:
            return (3, "failed_critical")
        return (4, "failed")
    return (99, "none")


def list_operator_attention_runs(registry: RunRegistry, *, max_runs: int = 5000) -> list[dict[str, Any]]:
    """Runs that should be reviewed first, ordered by attention priority then ``updated_at``."""
    out: list[dict[str, Any]] = []
    for record in _all_records(registry, max_runs=max_runs):
        pri, code = attention_priority_for_run(record)
        if pri >= 99:
            continue
        view = build_governance_run_view(record)
        view["attention_priority"] = pri
        view["attention_reason"] = code
        out.append(view)
    out.sort(key=lambda item: (int(item.get("attention_priority", 99)), str(item.get("updated_at", ""))))
    return out


def list_waiting_operator_runs(registry: RunRegistry) -> list[dict[str, Any]]:
    return [build_governance_run_view(r) for r in registry.get_runs_waiting_operator()]


def list_rollback_affected_runs(registry: RunRegistry) -> list[dict[str, Any]]:
    return [build_governance_run_view(r) for r in registry.get_runs_with_rollback()]


def list_blocked_by_policy_runs(registry: RunRegistry) -> list[dict[str, Any]]:
    return [build_governance_run_view(r) for r in registry.get_runs_blocked_by_policy()]


def summarize_governance(registry: RunRegistry) -> dict[str, Any]:
    """Aggregate counts and taxonomy slice (wraps registry resolution summary)."""
    return registry.get_resolution_summary()


def build_operational_governance_snapshot(registry: RunRegistry, *, timeline_limit: int = 25) -> dict[str, Any]:
    """
    Single JSON-friendly governance read block for CLI / observability / API consumers.

    Preserves nested ``summary`` from ``get_resolution_summary`` for backward compatibility
    while exposing normalized top-level keys aligned with operational naming.
    """
    summary = summarize_governance(registry)
    gov = summary.get("governance", {}) if isinstance(summary.get("governance"), dict) else {}
    recent = registry.recent_governance_timeline_events(limit=max(1, int(timeline_limit or 25)))
    latest = registry.latest_governance_event_by_run()
    return {
        "taxonomy_version": str(gov.get("taxonomy_version", GOVERNANCE_TAXONOMY_VERSION)),
        "summary": summary,
        "total_runs": int(summary.get("total_runs", 0) or 0),
        "resolution_counts": dict(summary.get("resolution_counts", {}) or {}),
        "reason_counts": dict(summary.get("reason_counts", {}) or {}),
        "governance_source_counts": dict(gov.get("source_counts", {}) or {}),
        "governance_severity_counts": dict(gov.get("severity_counts", {}) or {}),
        "timeline_event_counts": dict(gov.get("timeline_event_counts", {}) or {}),
        "waiting_operator_runs": list_waiting_operator_runs(registry),
        "rollback_affected_runs": list_rollback_affected_runs(registry),
        "blocked_by_policy_runs": list_blocked_by_policy_runs(registry),
        "operator_attention_runs": list_operator_attention_runs(registry),
        "recent_governance_timeline_events": recent,
        "latest_governance_event_by_run": {str(k): dict(v) for k, v in latest.items()},
    }
