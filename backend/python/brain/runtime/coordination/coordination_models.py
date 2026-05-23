from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class SpecialistParticipation:
    """One specialist step in the coordination sequence (auditable, bounded)."""

    role: str
    status: str
    input_ref: str
    output_summary: str
    warnings: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    recommended_next_step: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MultiAgentCoordinationTrace:
    """Structured observability for Phase 37 coordination (audit JSONL friendly)."""

    coordination_id: str
    session_id: str
    run_id: str
    coordination_mode: str
    role_order: list[str]
    participations: list[SpecialistParticipation]
    execution_readiness: str
    governance_authority_preserved: bool
    control_execution_allowed: bool
    issues_aggregate: list[str]
    degraded: bool
    error: str
    summary: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "coordination_id": self.coordination_id,
            "session_id": self.session_id,
            "run_id": self.run_id,
            "coordination_mode": self.coordination_mode,
            "role_order": list(self.role_order),
            "participations": [p.as_dict() for p in self.participations],
            "execution_readiness": self.execution_readiness,
            "governance_authority_preserved": self.governance_authority_preserved,
            "control_execution_allowed": self.control_execution_allowed,
            "issues_aggregate": list(self.issues_aggregate),
            "degraded": self.degraded,
            "error": self.error,
            "summary": self.summary,
        }


@dataclass(slots=True)
class CoordinationResult:
    """Outcome attached to swarm boundary / session (never overrides control-plane allow/block)."""

    trace: MultiAgentCoordinationTrace
    handoff_bundle: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"trace": self.trace.as_dict(), "handoff_bundle": dict(self.handoff_bundle)}
