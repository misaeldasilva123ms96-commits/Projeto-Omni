from __future__ import annotations

from typing import Any

from brain.runtime.evolution.controlled_evolution_models import GovernedProposal

from .approval_gate import ApprovalResult, evaluate_approval
from .improvement_simulator import simulate_proposal_impact


def run_simulation_and_approval(
    *,
    proposal: GovernedProposal,
    current_tuning: dict[str, Any],
    evidence: dict[str, Any],
) -> tuple[dict[str, Any], ApprovalResult]:
    sim = simulate_proposal_impact(proposal=proposal, current_tuning=current_tuning, evidence=evidence)
    approval = evaluate_approval(simulation=sim, proposal=proposal)
    return sim, approval


def monitoring_snapshot(*, rollout_state: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    base_dur = rollout_state.get("baseline_duration_ms")
    try:
        cur = float(evidence.get("duration_ms") or 0.0)
    except (TypeError, ValueError):
        cur = 0.0
    regression = False
    reasons: list[str] = []
    if base_dur is not None:
        try:
            b = float(base_dur)
            if b > 0 and cur > 0 and cur > b * 1.35:
                regression = True
                reasons.append("duration_regression_vs_baseline")
        except (TypeError, ValueError):
            pass
    lt = evidence.get("learning_trace") or {}
    if bool(lt.get("execution_degraded")):
        regression = True
        reasons.append("learning_execution_degraded")
    if str(lt.get("outcome_class", "")).lower() in ("failure", "error"):
        regression = True
        reasons.append("learning_negative_outcome")
    return {
        "regression": regression,
        "current_duration_ms": cur,
        "baseline_duration_ms": base_dur,
        "reasons": reasons,
    }
