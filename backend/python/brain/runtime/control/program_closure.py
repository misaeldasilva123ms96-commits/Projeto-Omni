"""
Phase 30.9 — runtime control plane closure anchors (30.1–30.9).

Single source for taxonomy version strings, empty read-model fallbacks,
and operational snapshot shape validation. Not a hot path for transitions.
"""

from __future__ import annotations

from typing import Any

# Governance taxonomy shipped with Phase 30.5; referenced across summaries and fallbacks.
GOVERNANCE_TAXONOMY_VERSION = "30.5"

# Program identifier for operators and tests (no runtime behavior change).
OMNI_RUNTIME_CONVERGENCE_PROGRAM = "30.1-30.9"
OMNI_RUNTIME_CONVERGENCE_PHASE = "30.9"

# Keys returned by build_operational_governance_snapshot (contract surface).
OPERATIONAL_GOVERNANCE_SNAPSHOT_KEYS: frozenset[str] = frozenset(
    {
        "taxonomy_version",
        "summary",
        "total_runs",
        "resolution_counts",
        "reason_counts",
        "governance_source_counts",
        "governance_severity_counts",
        "timeline_event_counts",
        "waiting_operator_runs",
        "rollback_affected_runs",
        "blocked_by_policy_runs",
        "operator_attention_runs",
        "recent_governance_timeline_events",
        "latest_governance_event_by_run",
    }
)


def empty_resolution_summary_fallback() -> dict[str, Any]:
    """Stable empty shape aligned with RunRegistry.get_resolution_summary()."""
    return {
        "total_runs": 0,
        "resolution_counts": {},
        "reason_counts": {},
        "governance": {
            "taxonomy_version": GOVERNANCE_TAXONOMY_VERSION,
            "source_counts": {},
            "severity_counts": {},
            "blocked_by_policy": 0,
            "waiting_operator": 0,
            "timeline_event_counts": {},
        },
    }


def empty_operational_governance_fallback(
    summary: dict[str, Any] | None = None,
    *,
    taxonomy_version: str | None = None,
) -> dict[str, Any]:
    """Stable empty operational snapshot; optional nested summary for chained fallbacks."""
    s = empty_resolution_summary_fallback() if summary is None else summary
    tv = taxonomy_version or GOVERNANCE_TAXONOMY_VERSION
    return {
        "taxonomy_version": tv,
        "summary": s,
        "total_runs": int(s.get("total_runs", 0) or 0),
        "resolution_counts": dict(s.get("resolution_counts", {}) or {}),
        "reason_counts": dict(s.get("reason_counts", {}) or {}),
        "governance_source_counts": dict((s.get("governance") or {}).get("source_counts", {}) or {}),
        "governance_severity_counts": dict((s.get("governance") or {}).get("severity_counts", {}) or {}),
        "timeline_event_counts": dict((s.get("governance") or {}).get("timeline_event_counts", {}) or {}),
        "waiting_operator_runs": [],
        "rollback_affected_runs": [],
        "blocked_by_policy_runs": [],
        "operator_attention_runs": [],
        "recent_governance_timeline_events": [],
        "latest_governance_event_by_run": {},
    }


def validate_operational_governance_shape(payload: Any) -> list[str]:
    """Return missing required keys; empty list means shape matches contract."""
    if not isinstance(payload, dict):
        return ["payload_not_object"]
    return [key for key in OPERATIONAL_GOVERNANCE_SNAPSHOT_KEYS if key not in payload]


def assert_operational_governance_contract(payload: dict[str, Any]) -> None:
    """Raise AssertionError with details if contract violated (tests / diagnostics)."""
    missing = validate_operational_governance_shape(payload)
    if missing:
        raise AssertionError(f"operational governance snapshot missing keys: {missing}")
