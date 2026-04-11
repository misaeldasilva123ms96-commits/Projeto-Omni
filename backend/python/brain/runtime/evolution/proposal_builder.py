from __future__ import annotations

from .models import EvolutionOpportunity, EvolutionProposal, EvolutionProposalType, RiskLevel, ScopeClass


class EvolutionProposalBuilder:
    def build(self, *, opportunity: EvolutionOpportunity) -> EvolutionProposal:
        proposal_type = EvolutionProposalType.BOUNDED_RUNTIME_REFINEMENT
        expected_affected_artifacts = [f"backend/python/brain/runtime/{opportunity.target_subsystem}"]
        validation_requirements = ["import_validation", "targeted_tests", "policy_consistency_check"]
        if opportunity.target_subsystem == "planning":
            proposal_type = EvolutionProposalType.VALIDATION_INSERTION
            expected_affected_artifacts = ["backend/python/brain/runtime/planning/plan_builder.py"]
            validation_requirements = ["targeted_tests", "policy_consistency_check"]
        elif opportunity.target_subsystem == "continuation":
            proposal_type = EvolutionProposalType.POLICY_TUNING
            expected_affected_artifacts = [
                "backend/python/brain/runtime/continuation/continuation_policy.py",
                "backend/python/brain/runtime/continuation/continuation_decider.py",
            ]
        elif opportunity.target_subsystem == "self_repair":
            proposal_type = EvolutionProposalType.TEMPLATE_ADJUSTMENT
            expected_affected_artifacts = ["backend/python/brain/runtime/self_repair/repair_proposer.py"]
        elif opportunity.target_subsystem == "orchestration":
            proposal_type = EvolutionProposalType.ROUTING_ADJUSTMENT
            expected_affected_artifacts = ["backend/python/brain/runtime/orchestration/route_selector.py"]

        return EvolutionProposal.build(
            source_opportunity_id=opportunity.opportunity_id,
            title=f"Governed refinement for {opportunity.target_subsystem}",
            summary=opportunity.summary,
            target_subsystem=opportunity.target_subsystem,
            proposal_type=proposal_type,
            scope_class=ScopeClass.SINGLE_COMPONENT,
            risk_level=RiskLevel.MEDIUM,
            expected_benefit="Reduce recurrence of the observed bounded operational weakness.",
            expected_affected_artifacts=expected_affected_artifacts,
            evidence_summary=opportunity.evidence_summary,
            validation_requirements=validation_requirements,
            governance_status="pending",
            promotion_status="not_requested",
            metadata={
                "opportunity_type": opportunity.opportunity_type.value,
                "recurrence_count": opportunity.recurrence_count,
            },
        )
