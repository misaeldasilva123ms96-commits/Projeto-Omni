from __future__ import annotations

from brain.runtime.goals import Goal, Severity

from .base_specialist import BaseSpecialist
from .models import GovernanceDecision, GovernanceVerdict, SpecialistDecision


class GovernanceSpecialist(BaseSpecialist):
    def review(
        self,
        *,
        decision: SpecialistDecision,
        goal: Goal | None,
        constraint_registry_available: bool = True,
    ) -> GovernanceDecision:
        hard_constraints = [constraint for constraint in getattr(goal, "constraints", []) if constraint.active and constraint.severity == Severity.HARD]
        risk_level = self._risk_level(decision=decision, hard_constraint_count=len(hard_constraints))
        violations: list[str] = []
        blocked_reasons: list[str] = []
        if decision.metadata.get("hard_constraint_violation"):
            violations.append("hard_constraint_violation")
        if float(decision.metadata.get("constraint_risk", 0.0) or 0.0) > 0.7 and hard_constraints:
            violations.append("high_constraint_risk")
        if risk_level == "high" and violations:
            verdict = GovernanceVerdict.BLOCK
            blocked_reasons.append("Unsafe specialist action under active hard constraints.")
        elif not constraint_registry_available and risk_level in {"medium", "high"}:
            verdict = GovernanceVerdict.HOLD
            blocked_reasons.append("Constraint registry context is incomplete, so medium/high-risk actions cannot auto-approve.")
        elif decision.status.value == "blocked":
            verdict = GovernanceVerdict.BLOCK
            blocked_reasons.append("The incoming specialist decision was already blocked by prior safety checks.")
        else:
            verdict = GovernanceVerdict.APPROVE
        reasoning = (
            "Governance specialist approved a clearly bounded specialist action."
            if verdict == GovernanceVerdict.APPROVE
            else "Governance specialist retained veto power because risk or constraint certainty was insufficient."
        )
        return GovernanceDecision.build(
            goal_id=decision.goal_id,
            simulation_id=decision.simulation_id,
            reasoning=reasoning,
            confidence=0.9 if verdict != GovernanceVerdict.HOLD else 0.74,
            verdict=verdict,
            blocked_reasons=blocked_reasons,
            violations=violations,
            risk_level=risk_level,
            metadata={"reviewed_specialist_type": decision.specialist_type.value},
        )

    @staticmethod
    def _risk_level(*, decision: SpecialistDecision, hard_constraint_count: int) -> str:
        if decision.metadata.get("hard_constraint_violation"):
            return "high"
        if decision.specialist_type.value == "executor" and not decision.metadata.get("result_ok", True):
            return "medium" if hard_constraint_count == 0 else "high"
        if decision.specialist_type.value in {"planner", "repair"}:
            return "medium"
        if decision.specialist_type.value == "governance":
            return "high"
        return "low"
