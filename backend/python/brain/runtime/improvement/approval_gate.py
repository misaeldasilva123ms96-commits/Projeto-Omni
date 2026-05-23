from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from brain.runtime.evolution.controlled_evolution_models import GovernedProposal


@dataclass(slots=True)
class ApprovalResult:
    status: str
    reasons: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.status, "reasons": list(self.reasons)}


def evaluate_approval(
    *,
    simulation: dict[str, Any],
    proposal: GovernedProposal,
) -> ApprovalResult:
    """
    Policy gate: never approves unsafe simulations; optional auto-approve for low risk.
    Human/operator intent: OMINI_PHASE40_APPROVE=true required when auto path off.
    """
    reasons: list[str] = []
    if not simulation.get("constraints_ok"):
        return ApprovalResult("rejected", ["simulation_constraints_failed"])

    risk = float(simulation.get("risk_score") or 1.0)
    if risk > 0.82:
        return ApprovalResult("rejected", [f"risk_above_gate:{risk:.3f}"])

    force = str(os.getenv("OMINI_PHASE40_FORCE_APPROVE", "")).strip().lower() in ("1", "true", "yes")
    if force:
        return ApprovalResult("approved_force", ["force_approve_env"])

    auto = str(os.getenv("OMINI_PHASE40_AUTO_APPROVE", "")).strip().lower() in ("1", "true", "yes")
    auto_max = float(os.getenv("OMINI_PHASE40_AUTO_APPROVE_MAX_RISK", "0.36") or 0.36)
    if auto and risk <= auto_max:
        return ApprovalResult("approved_auto", [f"low_risk_auto:{risk:.3f}"])

    explicit = str(os.getenv("OMINI_PHASE40_APPROVE", "")).strip().lower() in ("1", "true", "yes")
    if explicit:
        return ApprovalResult("approved_operator", ["explicit_approve_env"])

    reasons.append(f"pending_operator:risk={risk:.3f}")
    return ApprovalResult("pending", reasons)
