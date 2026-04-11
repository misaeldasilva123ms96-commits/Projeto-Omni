from __future__ import annotations

from pathlib import Path
from typing import Any

from brain.runtime.goals import ConstraintRegistry, Goal, GoalEvaluator, GoalStore

from .evolution_store import EvolutionStore
from .governance_policy import DeterministicGovernancePolicy
from .governance_recorder import GovernanceRecorder
from .models import EvolutionOutcome, GovernanceDecisionType, PromotionStatus
from .opportunity_detector import EvolutionOpportunityDetector
from .promotion_gate import PromotionGate
from .proposal_builder import EvolutionProposalBuilder
from .risk_assessor import RiskAssessor
from .scope_classifier import ScopeClassifier
from .validation_planner import ValidationPlanner


class EvolutionExecutor:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.policy = DeterministicGovernancePolicy.from_env()
        self.detector = EvolutionOpportunityDetector()
        self.builder = EvolutionProposalBuilder()
        self.scope_classifier = ScopeClassifier()
        self.risk_assessor = RiskAssessor()
        self.validation_planner = ValidationPlanner()
        self.governance = GovernanceRecorder()
        self.promotion_gate = PromotionGate()
        self.store = EvolutionStore(root)
        self.goal_store = GoalStore(root)
        self.goal_registry = ConstraintRegistry()
        self.goal_evaluator = GoalEvaluator(self.goal_registry)

    def evaluate(
        self,
        *,
        learning_update: dict[str, Any] | None = None,
        orchestration_update: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
        continuation_payload: dict[str, Any] | None = None,
        goal: Goal | None = None,
    ) -> dict[str, Any]:
        opportunity = self.detector.detect(
            learning_update=learning_update,
            orchestration_update=orchestration_update,
            result=result,
            continuation_payload=continuation_payload,
        )
        if opportunity is None:
            return EvolutionOutcome(
                opportunity=None,
                proposal=None,
                scope=None,
                risk=None,
                validation_plan=None,
                governance=None,
                promotion_status=PromotionStatus.NOT_REQUESTED,
                summary="No bounded governed evolution opportunity was detected.",
            ).as_dict()

        self.store.append_opportunity(opportunity)
        proposal = self.builder.build(opportunity=opportunity)
        scope = self.scope_classifier.classify(proposal=proposal)
        risk = self.risk_assessor.assess(proposal=proposal, scope=scope)
        validation_plan = self.validation_planner.build(proposal=proposal)
        governance = self.governance.decide(
            proposal=proposal,
            scope=scope,
            risk=risk,
            validation_plan_id=validation_plan.validation_plan_id,
            policy=self.policy,
            linked_evidence_ids=opportunity.evidence_ids,
        )
        active_goal = goal
        if active_goal is None:
            goal_id = self._goal_id_from_inputs(learning_update=learning_update, orchestration_update=orchestration_update, continuation_payload=continuation_payload)
            if goal_id:
                active_goal = self.goal_store.get_by_id(goal_id)
        if active_goal is not None:
            goal_evaluation = self.goal_evaluator.evaluate(
                goal=active_goal,
                runtime_state={"proposal_target_subsystem": proposal.target_subsystem},
            )
            if goal_evaluation.should_fail and goal_evaluation.violated_constraints:
                governance.decision_type = GovernanceDecisionType.BLOCKED_BY_POLICY
                governance.reason_code = "goal_constraint_block"
                governance.reason_summary = "Active goal constraints block this evolution proposal."
                governance.metadata = {
                    **dict(governance.metadata),
                    "goal_id": active_goal.goal_id,
                    "violated_constraints": list(goal_evaluation.violated_constraints),
                }
        promotion_status = self.promotion_gate.decide(
            policy=self.policy,
            governance=governance,
            scope=scope,
            risk=risk,
        )

        proposal.governance_status = governance.decision_type.value
        proposal.promotion_status = promotion_status.value
        self.store.append_proposal(proposal)
        self.store.append_validation(validation_plan)
        self.store.append_governance(governance)
        self.store.append_promotion(
            {
                "proposal_id": proposal.proposal_id,
                "promotion_status": promotion_status.value,
                "governance_decision_id": governance.governance_decision_id,
                "validation_plan_id": validation_plan.validation_plan_id,
            }
        )
        return EvolutionOutcome(
            opportunity=opportunity,
            proposal=proposal,
            scope=scope,
            risk=risk,
            validation_plan=validation_plan,
            governance=governance,
            promotion_status=promotion_status,
            summary="Governed evolution opportunity evaluated and recorded.",
        ).as_dict()

    @staticmethod
    def _goal_id_from_inputs(
        *,
        learning_update: dict[str, Any] | None,
        orchestration_update: dict[str, Any] | None,
        continuation_payload: dict[str, Any] | None,
    ) -> str | None:
        for payload in (learning_update, orchestration_update, continuation_payload):
            if not isinstance(payload, dict):
                continue
            goal_id = str(payload.get("goal_id", "")).strip()
            if goal_id:
                return goal_id
            context = payload.get("context", {}) if isinstance(payload.get("context"), dict) else {}
            goal_id = str(context.get("goal_id", "")).strip()
            if goal_id:
                return goal_id
        return None
