from __future__ import annotations

from .models import (
    EvolutionPolicy,
    EvolutionProposal,
    GovernanceDecision,
    GovernanceDecisionType,
    RiskAssessment,
    ScopeAssessment,
)


class GovernanceRecorder:
    def decide(
        self,
        *,
        proposal: EvolutionProposal,
        scope: ScopeAssessment,
        risk: RiskAssessment,
        validation_plan_id: str | None,
        policy: EvolutionPolicy,
        linked_evidence_ids: list[str],
    ) -> GovernanceDecision:
        if scope.decision.value == "blocked":
            return GovernanceDecision.build(
                proposal_id=proposal.proposal_id,
                decision_type=GovernanceDecisionType.BLOCKED_BY_POLICY,
                reason_code=scope.reason_code,
                reason_summary=scope.summary,
                approver_type="policy_engine",
                linked_validation_plan_id=validation_plan_id,
                linked_evidence_ids=linked_evidence_ids,
            )
        if risk.risk_level.value == "critical" and policy.block_critical:
            return GovernanceDecision.build(
                proposal_id=proposal.proposal_id,
                decision_type=GovernanceDecisionType.BLOCKED_BY_POLICY,
                reason_code="critical_risk_blocked",
                reason_summary="Critical-risk evolution proposals remain blocked in Phase 20.",
                approver_type="policy_engine",
                linked_validation_plan_id=validation_plan_id,
                linked_evidence_ids=linked_evidence_ids,
            )
        if not policy.enabled:
            return GovernanceDecision.build(
                proposal_id=proposal.proposal_id,
                decision_type=GovernanceDecisionType.DEFERRED,
                reason_code="evolution_disabled",
                reason_summary="Governed self-evolution is disabled by policy, so proposals are recorded but deferred.",
                approver_type="policy_engine",
                linked_validation_plan_id=validation_plan_id,
                linked_evidence_ids=linked_evidence_ids,
            )
        if policy.allow_validation:
            return GovernanceDecision.build(
                proposal_id=proposal.proposal_id,
                decision_type=GovernanceDecisionType.APPROVED_FOR_VALIDATION,
                reason_code="validation_allowed",
                reason_summary="The bounded proposal is approved for validation but not for direct promotion.",
                approver_type="governance_policy",
                linked_validation_plan_id=validation_plan_id,
                linked_evidence_ids=linked_evidence_ids,
            )
        return GovernanceDecision.build(
            proposal_id=proposal.proposal_id,
            decision_type=GovernanceDecisionType.REJECTED,
            reason_code="validation_disallowed",
            reason_summary="The proposal could not proceed because validation is disabled by policy.",
            approver_type="policy_engine",
            linked_validation_plan_id=validation_plan_id,
            linked_evidence_ids=linked_evidence_ids,
        )
