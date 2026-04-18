from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ImprovementOpportunity:
    opportunity_id: str
    session_id: str
    source_type: str
    category: str
    summary: str
    confidence: float
    evidence_refs: list[str]
    recommended_proposal_type: str
    governance_relevant: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class GovernedProposal:
    proposal_id: str
    opportunity_id: str
    proposal_type: str
    scope: str
    target_layer: str
    change_summary: str
    risk_class: str
    validation_requirements: list[str]
    approval_state: str
    apply_status: str
    monitor_status: str
    rollback_status: str
    payload: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ControlledSelfEvolutionTrace:
    trace_id: str
    session_id: str
    disabled: bool
    opportunity_count: int
    proposal_count: int
    validation_passed: bool
    validation_messages: list[str]
    apply_status: str
    monitor_status: str
    rollback_recommended: bool
    rollback_applied: bool
    degraded: bool
    error: str
    opportunities: list[dict[str, Any]] = field(default_factory=list)
    proposals: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "disabled": self.disabled,
            "opportunity_count": self.opportunity_count,
            "proposal_count": self.proposal_count,
            "validation_passed": self.validation_passed,
            "validation_messages": list(self.validation_messages),
            "apply_status": self.apply_status,
            "monitor_status": self.monitor_status,
            "rollback_recommended": self.rollback_recommended,
            "rollback_applied": self.rollback_applied,
            "degraded": self.degraded,
            "error": self.error,
            "opportunities": list(self.opportunities),
            "proposals": list(self.proposals),
        }


def governed_proposal_from_dict(d: dict[str, Any]) -> GovernedProposal:
    """Rehydrate a proposal emitted in CE traces (Phase 39+) for Phase 40 pipelines."""
    return GovernedProposal(
        proposal_id=str(d.get("proposal_id", "") or ""),
        opportunity_id=str(d.get("opportunity_id", "") or ""),
        proposal_type=str(d.get("proposal_type", "") or ""),
        scope=str(d.get("scope", "") or ""),
        target_layer=str(d.get("target_layer", "") or ""),
        change_summary=str(d.get("change_summary", "") or ""),
        risk_class=str(d.get("risk_class", "") or ""),
        validation_requirements=list(d.get("validation_requirements") or []),
        approval_state=str(d.get("approval_state", "") or ""),
        apply_status=str(d.get("apply_status", "") or ""),
        monitor_status=str(d.get("monitor_status", "") or ""),
        rollback_status=str(d.get("rollback_status", "") or ""),
        payload=dict(d.get("payload") or {}) if isinstance(d.get("payload"), dict) else {},
    )
