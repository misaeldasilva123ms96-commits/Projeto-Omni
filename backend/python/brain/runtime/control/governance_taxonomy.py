"""Unified governance reason, source, and severity taxonomy (Phase 30.5)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class GovernanceReason(str, Enum):
    OPERATOR_PAUSE = "operator_pause"
    OPERATOR_APPROVE = "operator_approve"
    OPERATOR_RESUME = "operator_resume"
    GOVERNANCE_HOLD = "governance_hold"
    PROMOTION_ROLLBACK_THRESHOLD = "promotion_rollback_threshold"
    PACKAGED_IMPORT_FAILED = "packaged_import_failed"
    TIMEOUT = "timeout"
    POLICY_BLOCK = "policy_block"
    UNSAFE_STATE = "unsafe_state"
    COMPLETED = "completed"
    FAILED = "failed"


class GovernanceSource(str, Enum):
    OPERATOR = "operator"
    SYSTEM = "system"
    GOVERNANCE = "governance"
    PROMOTION = "promotion"
    RUNTIME = "runtime"
    POLICY = "policy"


class GovernanceSeverity(str, Enum):
    MANUAL = "manual"
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(slots=True)
class GovernanceDecision:
    """Normalized governance slice attached to resolution records and history."""

    reason: GovernanceReason
    source: GovernanceSource
    severity: GovernanceSeverity

    def as_dict(self) -> dict[str, Any]:
        return {
            "reason": self.reason.value,
            "source": self.source.value,
            "severity": self.severity.value,
        }


def infer_governance_reason(*, last_action: str, run_status: str) -> GovernanceReason:
    """Infer canonical reason from orchestrator/operator action text and run status."""
    text = str(last_action or "").strip().lower()
    status = str(run_status or "").strip().lower()
    if "governance_hold" in text:
        return GovernanceReason.GOVERNANCE_HOLD
    if "operator_pause" in text or "pause" in text:
        return GovernanceReason.OPERATOR_PAUSE
    if "operator_approve" in text or "approve" in text:
        return GovernanceReason.OPERATOR_APPROVE
    if "operator_resume" in text or "resume" in text:
        return GovernanceReason.OPERATOR_RESUME
    if "timeout" in text:
        return GovernanceReason.TIMEOUT
    if "packaged_import_failed" in text:
        return GovernanceReason.PACKAGED_IMPORT_FAILED
    if "rollback" in text:
        return GovernanceReason.PROMOTION_ROLLBACK_THRESHOLD
    if "control_layer_blocked" in text or "policy" in text or "simulation_stop" in text or "supervision_stop" in text:
        return GovernanceReason.POLICY_BLOCK
    if status == "completed" or "goal_completed" in text:
        return GovernanceReason.COMPLETED
    if status == "failed" or "goal_failed" in text:
        return GovernanceReason.FAILED
    return GovernanceReason.UNSAFE_STATE


def map_action_to_reason(action: str, *, run_status: str = "running") -> GovernanceReason:
    return infer_governance_reason(last_action=action, run_status=run_status)


def map_status_to_reason(run_status: str) -> GovernanceReason:
    """Map terminal run status to a coarse reason (use with action-based inference when possible)."""
    status = str(run_status or "").strip().lower()
    if status == "completed":
        return GovernanceReason.COMPLETED
    if status == "failed":
        return GovernanceReason.FAILED
    return GovernanceReason.UNSAFE_STATE


def map_legacy_reason_string(raw: str, *, fallback: GovernanceReason | None = None) -> GovernanceReason:
    value = str(raw or "").strip()
    try:
        return GovernanceReason(value)
    except ValueError:
        if fallback is not None:
            return fallback
        return GovernanceReason.UNSAFE_STATE


def normalize_governance_source(raw: str) -> GovernanceSource:
    text = str(raw or "").strip().lower()
    if not text:
        return GovernanceSource.RUNTIME
    if "operator" in text or "supabase" in text or "cli" in text:
        return GovernanceSource.OPERATOR
    if "governance" in text:
        return GovernanceSource.GOVERNANCE
    if "promotion" in text or "engine_promotion" in text:
        return GovernanceSource.PROMOTION
    if "policy" in text:
        return GovernanceSource.POLICY
    if "system" in text:
        return GovernanceSource.SYSTEM
    return GovernanceSource.RUNTIME


def infer_governance_severity(reason: GovernanceReason, source: GovernanceSource) -> GovernanceSeverity:
    if source == GovernanceSource.OPERATOR:
        return GovernanceSeverity.MANUAL
    if reason in {
        GovernanceReason.POLICY_BLOCK,
        GovernanceReason.UNSAFE_STATE,
        GovernanceReason.FAILED,
        GovernanceReason.PROMOTION_ROLLBACK_THRESHOLD,
        GovernanceReason.PACKAGED_IMPORT_FAILED,
    }:
        return GovernanceSeverity.CRITICAL
    if reason in {GovernanceReason.GOVERNANCE_HOLD, GovernanceReason.TIMEOUT}:
        return GovernanceSeverity.WARNING
    if reason == GovernanceReason.COMPLETED:
        return GovernanceSeverity.NORMAL
    return GovernanceSeverity.NORMAL


def build_governance_decision(*, reason: str, decision_source: str) -> GovernanceDecision:
    gr = map_legacy_reason_string(reason, fallback=GovernanceReason.UNSAFE_STATE)
    gs = normalize_governance_source(decision_source)
    sev = infer_governance_severity(gr, gs)
    return GovernanceDecision(reason=gr, source=gs, severity=sev)


def governance_dict_for_resolution(*, reason: str, decision_source: str) -> dict[str, Any]:
    return build_governance_decision(reason=reason, decision_source=decision_source).as_dict()
