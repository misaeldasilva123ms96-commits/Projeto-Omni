from __future__ import annotations

from typing import Any

from brain.runtime.evolution.controlled_evolution_models import GovernedProposal
from brain.runtime.evolution.controlled_validation import validate_governed_proposal


def _numeric_bounds_for_key(key: str) -> tuple[float, float] | None:
    bounds: dict[str, tuple[float, float]] = {
        "decomposition_max_subtasks": (4.0, 8.0),
        "performance_max_cache_entries": (16.0, 128.0),
        "strategy_risk_bias": (-0.15, 0.15),
        "coordination_issue_budget": (1.0, 6.0),
        "observability_tail_lines": (32.0, 256.0),
    }
    return bounds.get(key)


def simulate_proposal_impact(
    *,
    proposal: GovernedProposal,
    current_tuning: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """
    Deterministic dry-run: re-validate, estimate risk, summarize evidence linkage.
    No mutation.
    """
    vr = validate_governed_proposal(proposal)
    key = str(proposal.payload.get("key", "") or "")
    bounds = _numeric_bounds_for_key(key)
    base_risk = 0.18 if proposal.risk_class == "low" else 0.42
    delta_risk = 0.0
    cur_raw = current_tuning.get(key)
    tgt_raw = proposal.payload.get("new_value")
    try:
        cur = float(cur_raw) if cur_raw is not None else float("nan")
        tgt = float(tgt_raw) if tgt_raw is not None else float("nan")
        if bounds and not (cur != cur):  # not NaN
            lo, hi = bounds
            span = max(hi - lo, 1e-6)
            # Bounded knob moves are inherently low blast-radius; keep scores conservative for auto-approve.
            delta_risk = min(0.22, (abs(tgt - cur) / span) * 0.35)
    except (TypeError, ValueError):
        delta_risk = 0.25

    risk_score = min(0.95, base_risk + delta_risk)
    duration_ms = evidence.get("duration_ms")
    try:
        dur = float(duration_ms) if duration_ms is not None else 0.0
    except (TypeError, ValueError):
        dur = 0.0

    return {
        "constraints_ok": bool(vr.accepted),
        "validation_messages": list(vr.messages),
        "risk_score": round(risk_score, 4),
        "proposal_type": proposal.proposal_type,
        "tuning_key": key,
        "evidence_duration_ms": dur,
        "learning_outcome": str((evidence.get("learning_trace") or {}).get("outcome_class", "") or ""),
        "decomposition_truncated": bool(
            (evidence.get("task_decomposition") or {}).get("truncated", False)
        ),
    }
