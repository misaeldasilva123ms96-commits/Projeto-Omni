from __future__ import annotations

from .models import EvolutionProposal, ValidationPlan


class ValidationPlanner:
    def build(self, *, proposal: EvolutionProposal) -> ValidationPlan:
        targeted_tests = ["tests.runtime.test_operational_learning", "tests.runtime.test_cognitive_orchestration"]
        replay_requirements = [f"Replay evidence class for {proposal.target_subsystem}"]
        if proposal.target_subsystem == "continuation":
            targeted_tests = ["tests.runtime.test_adaptive_continuation", "tests.runtime.test_cognitive_orchestration"]
        elif proposal.target_subsystem == "self_repair":
            targeted_tests = ["tests.runtime.test_controlled_self_repair", "tests.runtime.test_trusted_execution_layer"]
        elif proposal.target_subsystem == "planning":
            targeted_tests = ["tests.runtime.test_operational_planning", "tests.runtime.test_cognitive_orchestration"]
        return ValidationPlan.build(
            proposal_id=proposal.proposal_id,
            validation_modes=["targeted_unit_tests", "import_validation", "policy_consistency_check"],
            targeted_tests=targeted_tests,
            policy_checks=[
                "trusted_execution_policy_intact",
                "repair_policy_not_bypassed",
                "promotion_still_gated",
            ],
            replay_requirements=replay_requirements,
            summary="Validation plan generated deterministically for a bounded evolution proposal.",
        )
