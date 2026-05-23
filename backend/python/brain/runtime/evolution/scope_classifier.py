from __future__ import annotations

from .models import EvolutionProposal, ScopeAssessment, ScopeClass, ScopeDecision


class ScopeClassifier:
    ALLOWED_SUBSYSTEMS = {"planning", "continuation", "self_repair", "orchestration", "learning"}

    def classify(self, *, proposal: EvolutionProposal) -> ScopeAssessment:
        affected = list(proposal.expected_affected_artifacts)
        if proposal.target_subsystem not in self.ALLOWED_SUBSYSTEMS:
            return ScopeAssessment(
                proposal_id=proposal.proposal_id,
                scope_class=ScopeClass.OUT_OF_SCOPE,
                decision=ScopeDecision.BLOCKED,
                reason_code="subsystem_out_of_scope",
                summary="The target subsystem is outside the bounded Phase 20 evolution scope.",
                affected_artifacts=affected,
            )
        if len(affected) > 2:
            return ScopeAssessment(
                proposal_id=proposal.proposal_id,
                scope_class=ScopeClass.MULTI_SUBSYSTEM_BLOCKED,
                decision=ScopeDecision.BLOCKED,
                reason_code="too_many_affected_artifacts",
                summary="The proposal affects too many artifacts for bounded governed evolution.",
                affected_artifacts=affected,
            )
        if proposal.proposal_type.value in {"policy_tuning", "routing_adjustment"}:
            decision = ScopeDecision.ALLOWED_WITH_GOVERNANCE
        else:
            decision = ScopeDecision.ALLOWED
        return ScopeAssessment(
            proposal_id=proposal.proposal_id,
            scope_class=ScopeClass.SINGLE_COMPONENT if len(affected) <= 1 else ScopeClass.SINGLE_SUBSYSTEM,
            decision=decision,
            reason_code="bounded_scope_matched",
            summary="The proposal remains within the conservative bounded evolution scope.",
            affected_artifacts=affected,
        )
