from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SpecialistType(str, Enum):
    PLANNER = "planner"
    EXECUTOR = "executor"
    VALIDATOR = "validator"
    REPAIR = "repair"
    GOVERNANCE = "governance"
    SYNTHESIS = "synthesis"


class GovernanceVerdict(str, Enum):
    APPROVE = "approve"
    HOLD = "hold"
    BLOCK = "block"


class DecisionStatus(str, Enum):
    DECIDED = "decided"
    DEFERRED = "deferred"
    BLOCKED = "blocked"


@dataclass(slots=True)
class SpecialistDecision:
    decision_id: str
    specialist_type: SpecialistType
    status: DecisionStatus
    goal_id: str | None
    simulation_id: str | None
    reasoning: str
    confidence: float
    decided_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["specialist_type"] = self.specialist_type.value
        payload["status"] = self.status.value
        return payload


@dataclass(slots=True)
class PlanDecision(SpecialistDecision):
    plan_steps: list[dict[str, Any]] = field(default_factory=list)
    estimated_cycles: int = 0
    replan: bool = False

    @classmethod
    def build(
        cls,
        *,
        goal_id: str | None,
        simulation_id: str | None,
        reasoning: str,
        confidence: float,
        plan_steps: list[dict[str, Any]],
        estimated_cycles: int,
        replan: bool,
        metadata: dict[str, Any] | None = None,
    ) -> "PlanDecision":
        return cls(
            decision_id=f"plan-decision-{uuid4()}",
            specialist_type=SpecialistType.PLANNER,
            status=DecisionStatus.DECIDED,
            goal_id=goal_id,
            simulation_id=simulation_id,
            reasoning=reasoning,
            confidence=confidence,
            decided_at=utc_now_iso(),
            metadata=metadata or {},
            plan_steps=plan_steps,
            estimated_cycles=estimated_cycles,
            replan=replan,
        )


@dataclass(slots=True)
class ExecutionDecision(SpecialistDecision):
    executed_step_id: str | None = None
    delegated_execution: bool = True
    execution_summary: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        goal_id: str | None,
        simulation_id: str | None,
        reasoning: str,
        confidence: float,
        executed_step_id: str | None,
        execution_summary: str,
        evidence_ids: list[str],
        result: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> "ExecutionDecision":
        return cls(
            decision_id=f"execution-decision-{uuid4()}",
            specialist_type=SpecialistType.EXECUTOR,
            status=DecisionStatus.DECIDED,
            goal_id=goal_id,
            simulation_id=simulation_id,
            reasoning=reasoning,
            confidence=confidence,
            decided_at=utc_now_iso(),
            metadata=metadata or {},
            executed_step_id=executed_step_id,
            delegated_execution=True,
            execution_summary=execution_summary,
            evidence_ids=evidence_ids,
            result=result,
        )


@dataclass(slots=True)
class ValidationDecision(SpecialistDecision):
    criteria_met: list[str] = field(default_factory=list)
    criteria_failed: list[str] = field(default_factory=list)
    criteria_pending: list[str] = field(default_factory=list)
    progress_score: float = 0.0
    should_stop: bool = False
    should_fail: bool = False
    is_achieved: bool = False

    @classmethod
    def build(
        cls,
        *,
        goal_id: str | None,
        simulation_id: str | None,
        reasoning: str,
        confidence: float,
        criteria_met: list[str],
        criteria_failed: list[str],
        criteria_pending: list[str],
        progress_score: float,
        should_stop: bool,
        should_fail: bool,
        is_achieved: bool,
        metadata: dict[str, Any] | None = None,
    ) -> "ValidationDecision":
        return cls(
            decision_id=f"validation-decision-{uuid4()}",
            specialist_type=SpecialistType.VALIDATOR,
            status=DecisionStatus.DECIDED if not should_fail else DecisionStatus.BLOCKED,
            goal_id=goal_id,
            simulation_id=simulation_id,
            reasoning=reasoning,
            confidence=confidence,
            decided_at=utc_now_iso(),
            metadata=metadata or {},
            criteria_met=criteria_met,
            criteria_failed=criteria_failed,
            criteria_pending=criteria_pending,
            progress_score=progress_score,
            should_stop=should_stop,
            should_fail=should_fail,
            is_achieved=is_achieved,
        )


@dataclass(slots=True)
class RepairDecision(SpecialistDecision):
    recommended_strategy: str = ""
    estimated_impact: str = ""
    require_replan: bool = False
    repair_history_score: float = 0.0

    @classmethod
    def build(
        cls,
        *,
        goal_id: str | None,
        simulation_id: str | None,
        reasoning: str,
        confidence: float,
        recommended_strategy: str,
        estimated_impact: str,
        require_replan: bool,
        repair_history_score: float,
        status: DecisionStatus = DecisionStatus.DECIDED,
        metadata: dict[str, Any] | None = None,
    ) -> "RepairDecision":
        return cls(
            decision_id=f"repair-decision-{uuid4()}",
            specialist_type=SpecialistType.REPAIR,
            status=status,
            goal_id=goal_id,
            simulation_id=simulation_id,
            reasoning=reasoning,
            confidence=confidence,
            decided_at=utc_now_iso(),
            metadata=metadata or {},
            recommended_strategy=recommended_strategy,
            estimated_impact=estimated_impact,
            require_replan=require_replan,
            repair_history_score=repair_history_score,
        )


@dataclass(slots=True)
class GovernanceDecision(SpecialistDecision):
    verdict: GovernanceVerdict = GovernanceVerdict.HOLD
    blocked_reasons: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    risk_level: str = "medium"

    @classmethod
    def build(
        cls,
        *,
        goal_id: str | None,
        simulation_id: str | None,
        reasoning: str,
        confidence: float,
        verdict: GovernanceVerdict,
        blocked_reasons: list[str],
        violations: list[str],
        risk_level: str,
        metadata: dict[str, Any] | None = None,
    ) -> "GovernanceDecision":
        status = DecisionStatus.DECIDED
        if verdict == GovernanceVerdict.BLOCK:
            status = DecisionStatus.BLOCKED
        elif verdict == GovernanceVerdict.HOLD:
            status = DecisionStatus.DEFERRED
        return cls(
            decision_id=f"governance-decision-{uuid4()}",
            specialist_type=SpecialistType.GOVERNANCE,
            status=status,
            goal_id=goal_id,
            simulation_id=simulation_id,
            reasoning=reasoning,
            confidence=confidence,
            decided_at=utc_now_iso(),
            metadata=metadata or {},
            verdict=verdict,
            blocked_reasons=blocked_reasons,
            violations=violations,
            risk_level=risk_level,
        )

    def as_dict(self) -> dict[str, Any]:
        payload = super().as_dict()
        payload["verdict"] = self.verdict.value
        return payload


@dataclass(slots=True)
class SynthesisDecision(SpecialistDecision):
    summary: str = ""
    artifact_refs: list[str] = field(default_factory=list)
    learning_highlights: list[str] = field(default_factory=list)

    @classmethod
    def build(
        cls,
        *,
        goal_id: str | None,
        simulation_id: str | None,
        reasoning: str,
        confidence: float,
        summary: str,
        artifact_refs: list[str],
        learning_highlights: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> "SynthesisDecision":
        return cls(
            decision_id=f"synthesis-decision-{uuid4()}",
            specialist_type=SpecialistType.SYNTHESIS,
            status=DecisionStatus.DECIDED,
            goal_id=goal_id,
            simulation_id=simulation_id,
            reasoning=reasoning,
            confidence=confidence,
            decided_at=utc_now_iso(),
            metadata=metadata or {},
            summary=summary,
            artifact_refs=artifact_refs,
            learning_highlights=learning_highlights,
        )


@dataclass(slots=True)
class CoordinationTrace:
    trace_id: str
    goal_id: str | None
    session_id: str | None
    decisions: list[dict[str, Any]]
    governance_verdicts: list[dict[str, Any]]
    final_outcome: str
    started_at: str
    completed_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        goal_id: str | None,
        session_id: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> "CoordinationTrace":
        return cls(
            trace_id=f"coordination-trace-{uuid4()}",
            goal_id=goal_id,
            session_id=session_id,
            decisions=[],
            governance_verdicts=[],
            final_outcome="in_progress",
            started_at=utc_now_iso(),
            metadata=metadata or {},
        )

    def append_decision(self, decision: SpecialistDecision) -> None:
        payload = decision.as_dict()
        self.decisions.append(payload)
        if isinstance(decision, GovernanceDecision):
            self.governance_verdicts.append(payload)

    def finish(self, final_outcome: str, *, metadata: dict[str, Any] | None = None) -> None:
        self.final_outcome = final_outcome
        self.completed_at = utc_now_iso()
        if metadata:
            self.metadata.update(metadata)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
