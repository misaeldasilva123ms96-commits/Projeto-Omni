from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ImprovementCycle:
    """One governed improvement cycle (Phase 40) over Phase-39-shaped proposals."""

    id: str
    proposals: list[dict[str, Any]]
    simulation_result: dict[str, Any]
    approval_status: str
    rollout_stage: str
    monitoring_state: dict[str, Any]
    rollback_available: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SelfImprovingSystemTrace:
    trace_id: str
    session_id: str
    disabled: bool
    idle: bool
    cycle: dict[str, Any] | None
    simulation_outcome: dict[str, Any]
    approval_decision: str
    rollout_stage: str
    monitoring_result: dict[str, Any]
    rollback_status: str
    degraded: bool
    error: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "disabled": self.disabled,
            "idle": self.idle,
            "cycle": dict(self.cycle) if isinstance(self.cycle, dict) else None,
            "simulation_outcome": dict(self.simulation_outcome),
            "approval_decision": self.approval_decision,
            "rollout_stage": self.rollout_stage,
            "monitoring_result": dict(self.monitoring_result),
            "rollback_status": self.rollback_status,
            "degraded": self.degraded,
            "error": self.error,
        }
