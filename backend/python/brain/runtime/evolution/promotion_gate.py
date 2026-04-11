from __future__ import annotations

from .models import EvolutionPolicy, GovernanceDecision, PromotionStatus, RiskAssessment, ScopeAssessment


class PromotionGate:
    def decide(
        self,
        *,
        policy: EvolutionPolicy,
        governance: GovernanceDecision | None,
        scope: ScopeAssessment | None,
        risk: RiskAssessment | None,
    ) -> PromotionStatus:
        if governance is None or scope is None or risk is None:
            return PromotionStatus.BLOCKED
        if scope.decision.value == "blocked":
            return PromotionStatus.BLOCKED
        if governance.decision_type.value != "approved_for_promotion":
            if governance.decision_type.value == "approved_for_validation":
                return PromotionStatus.VALIDATED if policy.allow_validation else PromotionStatus.BLOCKED
            return PromotionStatus.NOT_REQUESTED
        if not policy.allow_promotion:
            return PromotionStatus.BLOCKED
        if not risk.rollback_available:
            return PromotionStatus.BLOCKED
        return PromotionStatus.PROMOTED
