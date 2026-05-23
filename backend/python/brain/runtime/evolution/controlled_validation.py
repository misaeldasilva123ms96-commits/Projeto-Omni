from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .controlled_evolution_models import GovernedProposal

_ALLOWED_TYPES = frozenset(
    {
        "decomposition_limit_tune",
        "performance_cache_tune",
        "compression_cache_tune",
        "strategy_bias_shift",
        "advisory_routing_preference",
        "observability_threshold_tune",
    }
)

_BOUNDS: dict[str, tuple[int | float, int | float]] = {
    "decomposition_max_subtasks": (4, 8),
    "performance_max_cache_entries": (16, 128),
    "strategy_risk_bias": (-0.15, 0.15),
    "coordination_issue_budget": (1, 6),
    "observability_tail_lines": (32, 256),
}


@dataclass(slots=True)
class ControlledValidationResult:
    accepted: bool
    messages: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {"accepted": self.accepted, "messages": list(self.messages)}


def validate_governed_proposal(proposal: GovernedProposal) -> ControlledValidationResult:
    messages: list[str] = []
    if proposal.proposal_type not in _ALLOWED_TYPES:
        return ControlledValidationResult(False, [f"disallowed_proposal_type:{proposal.proposal_type}"])
    if proposal.risk_class not in ("low", "medium"):
        return ControlledValidationResult(False, ["risk_class_out_of_phase39_scope"])
    key = str(proposal.payload.get("key", "") or "").strip()
    if key not in _BOUNDS:
        return ControlledValidationResult(False, [f"unknown_tuning_key:{key}"])
    lo, hi = _BOUNDS[key]
    raw_new = proposal.payload.get("new_value")
    try:
        if isinstance(lo, int):
            new_v = int(raw_new)
        else:
            new_v = float(raw_new)
    except (TypeError, ValueError):
        return ControlledValidationResult(False, ["new_value_not_numeric"])
    if new_v < lo or new_v > hi:
        return ControlledValidationResult(False, [f"new_value_out_of_bounds:{key}:{new_v}"])
    messages.append("bounds_ok")
    if proposal.scope != "runtime_tuning_file":
        return ControlledValidationResult(False, ["scope_must_be_runtime_tuning_file"])
    messages.append("shape_ok")
    messages.append("governance_safe")
    return ControlledValidationResult(True, messages)
