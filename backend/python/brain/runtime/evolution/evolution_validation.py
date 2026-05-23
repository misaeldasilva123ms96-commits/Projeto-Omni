from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

from .evolution_models import EvolutionProposalRecord
from .models import utc_now_iso

ALLOWED_PROPOSAL_TYPES = {
    "policy_tuning",
    "template_adjustment",
    "routing_adjustment",
    "validation_insertion",
    "bounded_runtime_refinement",
}


class EvolutionValidationOutcome(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    RISKY = "risky"
    INCONCLUSIVE = "inconclusive"


@dataclass(slots=True)
class EvolutionValidationResult:
    validation_id: str
    proposal_id: str
    validation_type: str
    outcome: str
    score: float
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    evaluated_at: str = field(default_factory=utc_now_iso)
    evaluator: str = "rule_engine"
    governance: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        proposal_id: str,
        validation_type: str,
        outcome: EvolutionValidationOutcome,
        score: float,
        issues: list[str],
        recommendations: list[str],
        evaluator: str = "rule_engine",
        governance_reason: str,
        governance_source: str = "system_validation",
        governance_severity: str = "normal",
        extensions: dict[str, Any] | None = None,
    ) -> "EvolutionValidationResult":
        now = utc_now_iso()
        bounded_score = max(0.0, min(1.0, float(score)))
        return cls(
            validation_id=f"evo-validation-{uuid4().hex}",
            proposal_id=str(proposal_id),
            validation_type=str(validation_type or "deterministic_rule_engine").strip(),
            outcome=outcome.value,
            score=bounded_score,
            issues=[str(item).strip() for item in issues if str(item).strip()],
            recommendations=[str(item).strip() for item in recommendations if str(item).strip()],
            evaluated_at=now,
            evaluator=str(evaluator or "rule_engine").strip(),
            governance={
                "governed": True,
                "reason": str(governance_reason).strip(),
                "source": str(governance_source).strip() or "system_validation",
                "severity": str(governance_severity).strip().lower() or "normal",
                "at": now,
            },
            extensions=dict(extensions or {}),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "validation_id": self.validation_id,
            "proposal_id": self.proposal_id,
            "validation_type": self.validation_type,
            "outcome": self.outcome,
            "score": self.score,
            "issues": list(self.issues),
            "recommendations": list(self.recommendations),
            "evaluated_at": self.evaluated_at,
            "evaluator": self.evaluator,
            "governance": dict(self.governance),
            "extensions": dict(self.extensions),
        }


def validate_evolution_proposal(
    proposal: EvolutionProposalRecord,
    *,
    evaluator: str = "rule_engine",
) -> EvolutionValidationResult:
    """Deterministic, rule-based proposal validation (no patch generation/application)."""
    issues: list[str] = []
    recommendations: list[str] = []
    target = str(proposal.target_area or "").strip().lower()
    proposal_type = str(proposal.proposal_type or "").strip().lower()
    rationale = str(proposal.rationale or "").strip()
    requested_change = str(proposal.requested_change or "").strip()
    expected_benefit = str(proposal.expected_benefit or "").strip()
    risk = str(proposal.risk_level or "").strip().lower()

    required = {
        "title": proposal.title,
        "summary": proposal.summary,
        "target_area": proposal.target_area,
        "proposal_type": proposal.proposal_type,
        "rationale": proposal.rationale,
        "requested_change": proposal.requested_change,
        "expected_benefit": proposal.expected_benefit,
    }
    for key, value in required.items():
        if not str(value or "").strip():
            issues.append(f"missing_required_field:{key}")

    if proposal_type not in ALLOWED_PROPOSAL_TYPES:
        issues.append("unsupported_proposal_type")
        recommendations.append("Use one of the governed proposal types from Phase 20.")

    known_target = (
        target.startswith("runtime.")
        or target.startswith("brain.runtime.")
        or target.startswith("backend/python/brain/runtime/")
    )
    if not known_target:
        issues.append("unknown_target_area")
        recommendations.append("Target area should map to a bounded runtime subsystem path.")

    broad_markers = ("*", " all ", "entire", "full rewrite", "global")
    if any(marker in f" {requested_change.lower()} " for marker in broad_markers):
        issues.append("overly_broad_requested_change")
        recommendations.append("Reduce scope to a bounded subsystem-level refinement.")

    if len(rationale) < 24:
        issues.append("weak_rationale")
        recommendations.append("Provide explicit evidence-backed rationale.")

    if len(expected_benefit) < 12:
        issues.append("weak_expected_benefit")
        recommendations.append("Describe measurable expected benefit.")

    risky = False
    if risk in {"high", "critical"} and "policy" not in proposal_type and "validation" not in proposal_type:
        issues.append("risk_scope_mismatch")
        recommendations.append("High-risk proposals should constrain scope or be validation-first.")
        risky = True

    if any(item.startswith("missing_required_field") for item in issues) or "unsupported_proposal_type" in issues:
        outcome = EvolutionValidationOutcome.INVALID
        score = 0.15
        governance_reason = "validation_failed"
        governance_severity = "critical"
    elif risky or "overly_broad_requested_change" in issues:
        outcome = EvolutionValidationOutcome.RISKY
        score = 0.45
        governance_reason = "validation_risky"
        governance_severity = "warning"
    elif "weak_rationale" in issues or "weak_expected_benefit" in issues or "unknown_target_area" in issues:
        outcome = EvolutionValidationOutcome.INCONCLUSIVE
        score = 0.6
        governance_reason = "validation_inconclusive"
        governance_severity = "warning"
    else:
        outcome = EvolutionValidationOutcome.VALID
        score = 0.9
        governance_reason = "validation_passed"
        governance_severity = "normal"

    return EvolutionValidationResult.build(
        proposal_id=proposal.proposal_id,
        validation_type="deterministic_rule_engine",
        outcome=outcome,
        score=score,
        issues=issues,
        recommendations=recommendations,
        evaluator=evaluator,
        governance_reason=governance_reason,
        governance_source="system_validation",
        governance_severity=governance_severity,
    )
