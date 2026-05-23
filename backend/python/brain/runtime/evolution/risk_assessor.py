from __future__ import annotations

from .models import EvolutionProposal, RiskAssessment, RiskLevel, ScopeAssessment


class RiskAssessor:
    HIGH_SENSITIVITY_SUBSYSTEMS = {"execution", "self_repair", "continuation", "evolution"}

    def assess(self, *, proposal: EvolutionProposal, scope: ScopeAssessment) -> RiskAssessment:
        factors: list[str] = []
        rollback_available = True
        risk = RiskLevel.LOW

        if proposal.target_subsystem in self.HIGH_SENSITIVITY_SUBSYSTEMS:
            risk = RiskLevel.HIGH
            factors.append("sensitive_runtime_subsystem")
        elif proposal.proposal_type.value in {"policy_tuning", "routing_adjustment"}:
            risk = RiskLevel.MEDIUM
            factors.append("policy_or_routing_semantics_change")

        if scope.scope_class.value == "single_subsystem" and risk == RiskLevel.LOW:
            risk = RiskLevel.MEDIUM
            factors.append("multiple_artifacts_in_single_subsystem")
        if scope.scope_class.value in {"multi_subsystem_blocked", "out_of_scope"}:
            risk = RiskLevel.CRITICAL
            rollback_available = False
            factors.append("scope_exceeds_governed_boundary")

        summary = "Risk remains bounded and manageable under governance."
        if risk == RiskLevel.HIGH:
            summary = "Risk is elevated because the proposal touches a sensitive runtime control area."
        if risk == RiskLevel.CRITICAL:
            summary = "Risk is unacceptable for governed self-evolution in Phase 20."

        return RiskAssessment(
            proposal_id=proposal.proposal_id,
            risk_level=risk,
            reason_code=f"risk_{risk.value}",
            summary=summary,
            rollback_available=rollback_available,
            factors=factors or ["bounded_change"],
        )
