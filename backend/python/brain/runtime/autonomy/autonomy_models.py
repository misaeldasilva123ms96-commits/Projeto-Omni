"""Autonomy Controller decision models.

Defines the contract types for runtime autonomy decisions:
- DecisionType: what the controller advises next
- AutonomyContext: input data the controller evaluates
- AutonomyDecision: the controller's advisory output
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DecisionType(str, Enum):
    CONTINUE = "CONTINUE"
    RETRY = "RETRY"
    REPLAN = "REPLAN"
    SELF_REPAIR = "SELF_REPAIR"
    SWITCH_PROVIDER = "SWITCH_PROVIDER"
    PAUSE = "PAUSE"
    ESCALATE_TO_MISAEL = "ESCALATE_TO_MISAEL"
    ABORT_SAFE = "ABORT_SAFE"


DECISION_RISK_MAP: dict[DecisionType, str] = {
    DecisionType.CONTINUE: "low",
    DecisionType.RETRY: "low",
    DecisionType.REPLAN: "medium",
    DecisionType.SELF_REPAIR: "medium",
    DecisionType.SWITCH_PROVIDER: "medium",
    DecisionType.PAUSE: "medium",
    DecisionType.ESCALATE_TO_MISAEL: "high",
    DecisionType.ABORT_SAFE: "high",
}

ADVISORY_ONLY_DECISIONS: frozenset[DecisionType] = frozenset({
    DecisionType.CONTINUE,
    DecisionType.RETRY,
    DecisionType.REPLAN,
    DecisionType.PAUSE,
    DecisionType.ESCALATE_TO_MISAEL,
    DecisionType.ABORT_SAFE,
})

DISABLED_DECISIONS: frozenset[DecisionType] = frozenset({
    DecisionType.SELF_REPAIR,
    DecisionType.SWITCH_PROVIDER,
})


@dataclass(slots=True)
class AutonomyContext:
    session_id: str = ""
    run_id: str = ""
    task_id: str = ""
    current_action: str = ""
    error_type: str = ""
    error_count: int = 0
    stagnation_count: int = 0
    distinct_errors: int = 0
    total_progressive_cycles: int = 0
    secret_detected: bool = False
    protected_file_involved: bool = False
    unsafe_ci_signal: bool = False
    security_signal: bool = False
    conflict_detected: bool = False
    production_action_required: bool = False
    no_safe_next_action: bool = False
    direct_main_push_attempted: bool = False
    merge_attempted: bool = False
    consecutive_same_error: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AutonomyDecision:
    decision: DecisionType
    reason: str
    risk_level: str = ""
    advisory: bool = True
    decision_id: str = ""
    created_at: str = field(default_factory=_utc_now)
    context_snapshot: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
