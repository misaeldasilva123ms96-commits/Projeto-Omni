from __future__ import annotations

from typing import Any

from brain.runtime.goals import Goal
from brain.runtime.planning import TaskPlan
from brain.runtime.planning.progress_tracker import ProgressTracker
from brain.runtime.goals import GoalEvaluationResult
from brain.runtime.simulation import ActionSimulator, RouteType, SimulationContextBuilder, SimulationResult

from .continuation_policy import DeterministicContinuationPolicy
from .models import ContinuationDecision, ContinuationDecisionType, ContinuationPolicy, PlanEvaluation, PlanHealth


NON_RETRYABLE_FAILURES = {
    "control_layer_block",
    "policy_stop",
    "supervision_stop",
    "simulation_stop",
    "critical_risk_blocked",
    "preflight_failed",
}

PAUSE_FAILURES = {
    "dependency_missing",
    "dependency_unavailable",
    "manual_review_required",
}

REPLAN_FAILURES = {
    "verification_failed",
    "missing_result_payload",
    "missing_error_payload",
    "invalid_result_shape",
}


class ContinuationDecider:
    def __init__(
        self,
        tracker: ProgressTracker,
        *,
        simulator: ActionSimulator | None = None,
        simulation_context_builder: SimulationContextBuilder | None = None,
    ) -> None:
        self.tracker = tracker
        self.simulator = simulator
        self.simulation_context_builder = simulation_context_builder

    def decide(
        self,
        *,
        plan: TaskPlan,
        evaluation: PlanEvaluation,
        policy: ContinuationPolicy,
        checkpoint_id: str | None,
        goal: Goal | None = None,
        goal_evaluation: GoalEvaluationResult | None = None,
        result: dict[str, Any] | None = None,
        advisory_signals: list[Any] | None = None,
    ) -> ContinuationDecision:
        current_step = self.tracker.step_by_id(plan, plan.current_step_id) if plan.current_step_id else None
        failure_kind = self._failure_kind(result)
        replan_count = int(plan.metadata.get("continuation_replan_count", 0) or 0)
        retry_count = current_step.retry_count if current_step is not None else 0

        if goal_evaluation is not None and goal_evaluation.is_achieved:
            return self._build_decision(
                plan=plan,
                step_id=plan.current_step_id,
                decision_type=ContinuationDecisionType.COMPLETE_PLAN,
                reason_code="goal_achieved",
                reason_summary="The active runtime goal has been achieved.",
                confidence_score=self._confidence_with_signals(0.99, ContinuationDecisionType.COMPLETE_PLAN, advisory_signals),
                recommended_action="Complete the plan because the active goal criteria are satisfied.",
                checkpoint_id=checkpoint_id,
            )

        if goal_evaluation is not None and goal_evaluation.should_fail:
            return self._build_decision(
                plan=plan,
                step_id=plan.current_step_id,
                decision_type=ContinuationDecisionType.ESCALATE_FAILURE,
                reason_code="goal_blocked",
                reason_summary="Active goal constraints or failure tolerances no longer allow safe continuation.",
                confidence_score=self._confidence_with_signals(0.95, ContinuationDecisionType.ESCALATE_FAILURE, advisory_signals),
                recommended_action="Escalate because the active goal boundaries have been violated.",
                checkpoint_id=checkpoint_id,
            )

        if goal_evaluation is not None and goal_evaluation.should_stop:
            return self._build_decision(
                plan=plan,
                step_id=plan.current_step_id,
                decision_type=ContinuationDecisionType.PAUSE_PLAN,
                reason_code="goal_stop_condition",
                reason_summary="An active goal stop condition was triggered, so the plan should pause safely.",
                confidence_score=self._confidence_with_signals(0.91, ContinuationDecisionType.PAUSE_PLAN, advisory_signals),
                recommended_action="Pause the plan and preserve resumability because a goal stop condition fired.",
                checkpoint_id=checkpoint_id,
            )

        simulation_result = self._simulation_result(
            plan=plan,
            goal=goal,
            goal_evaluation=goal_evaluation,
            result=result,
        )
        if simulation_result is not None:
            high_confidence_decision = self._high_confidence_simulation_decision(
                plan=plan,
                checkpoint_id=checkpoint_id,
                simulation_result=simulation_result,
            )
            if high_confidence_decision is not None:
                return high_confidence_decision

        baseline = self._baseline_decision(
            plan=plan,
            evaluation=evaluation,
            policy=policy,
            checkpoint_id=checkpoint_id,
            failure_kind=failure_kind,
            retry_count=retry_count,
            replan_count=replan_count,
            result=result,
            advisory_signals=advisory_signals,
        )
        if simulation_result is not None:
            return self._blend_with_simulation(
                baseline=baseline,
                simulation_result=simulation_result,
            )
        return baseline

    def _simulation_result(
        self,
        *,
        plan: TaskPlan,
        goal: Goal | None,
        goal_evaluation: GoalEvaluationResult | None,
        result: dict[str, Any] | None,
    ) -> SimulationResult | None:
        if self.simulator is None or self.simulation_context_builder is None:
            return None
        if goal_evaluation is not None and (goal_evaluation.is_achieved or goal_evaluation.should_fail):
            return None
        context = self.simulation_context_builder.build(
            plan=plan,
            goal=goal,
            result=result,
            session_id=plan.session_id,
        )
        return self.simulator.simulate(context=context)

    def _high_confidence_simulation_decision(
        self,
        *,
        plan: TaskPlan,
        checkpoint_id: str | None,
        simulation_result: SimulationResult,
    ) -> ContinuationDecision | None:
        route = simulation_result.route_for(simulation_result.recommended_route)
        if route is None or route.confidence < 0.75 or route.constraint_risk > 0.7:
            return None
        if route.route == RouteType.RETRY:
            return self._decision_from_simulation(
                plan=plan,
                checkpoint_id=checkpoint_id,
                decision_type=ContinuationDecisionType.RETRY_STEP,
                simulation_result=simulation_result,
                reason_code="simulation_high_confidence_retry",
                reason_summary="Internal simulation strongly favors a bounded retry path.",
                recommended_action="Retry the current step because simulation indicates bounded retry is most promising.",
            )
        if route.route == RouteType.REPLAN:
            return self._decision_from_simulation(
                plan=plan,
                checkpoint_id=checkpoint_id,
                decision_type=ContinuationDecisionType.REBUILD_PLAN,
                simulation_result=simulation_result,
                reason_code="simulation_high_confidence_replan",
                reason_summary="Internal simulation strongly favors a bounded replan path.",
                recommended_action="Apply a bounded replan because simulation indicates it is the best available route.",
            )
        if route.route == RouteType.PAUSE:
            return self._decision_from_simulation(
                plan=plan,
                checkpoint_id=checkpoint_id,
                decision_type=ContinuationDecisionType.PAUSE_PLAN,
                simulation_result=simulation_result,
                reason_code="simulation_high_confidence_pause",
                reason_summary="Internal simulation strongly favors pausing the plan safely.",
                recommended_action="Pause the plan because simulation indicates pause is the safest bounded route.",
            )
        return None

    def _baseline_decision(
        self,
        *,
        plan: TaskPlan,
        evaluation: PlanEvaluation,
        policy: ContinuationPolicy,
        checkpoint_id: str | None,
        failure_kind: str,
        retry_count: int,
        replan_count: int,
        result: dict[str, Any] | None,
        advisory_signals: list[Any] | None,
    ) -> ContinuationDecision:
        if evaluation.plan_health == PlanHealth.COMPLETED:
            return self._build_decision(
                plan=plan,
                step_id=plan.current_step_id,
                decision_type=ContinuationDecisionType.COMPLETE_PLAN,
                reason_code="plan_completed",
                reason_summary="All required operational steps are complete.",
                confidence_score=self._confidence_with_signals(0.99, ContinuationDecisionType.COMPLETE_PLAN, advisory_signals),
                recommended_action="Finalize the plan and preserve the last successful summary.",
                checkpoint_id=checkpoint_id,
            )

        if (
            policy.allow_auto_escalate
            and (
                evaluation.plan_health == PlanHealth.BLOCKED
                or (failure_kind in NON_RETRYABLE_FAILURES)
                or (evaluation.repair_outcome_summary.startswith("rejected") and retry_count >= policy.max_retries_per_step)
            )
        ):
            return self._build_decision(
                plan=plan,
                step_id=plan.current_step_id,
                decision_type=ContinuationDecisionType.ESCALATE_FAILURE,
                reason_code="unsafe_to_continue",
                reason_summary="The plan is blocked or the latest failure is unsafe to continue automatically.",
                confidence_score=self._confidence_with_signals(0.93, ContinuationDecisionType.ESCALATE_FAILURE, advisory_signals),
                recommended_action="Escalate the failure and preserve the last safe checkpoint.",
                checkpoint_id=checkpoint_id,
            )

        if policy.allow_auto_pause and (
            failure_kind in PAUSE_FAILURES
            or evaluation.resumability_state == "unsafe_to_resume"
            or (not failure_kind and evaluation.dependency_health == "missing_dependencies")
        ):
            return self._build_decision(
                plan=plan,
                step_id=plan.current_step_id,
                decision_type=ContinuationDecisionType.PAUSE_PLAN,
                reason_code="continuation_requires_pause",
                reason_summary="Safe continuation is not currently available, so the plan should pause.",
                confidence_score=self._confidence_with_signals(0.88, ContinuationDecisionType.PAUSE_PLAN, advisory_signals),
                recommended_action="Pause the plan and preserve resumability metadata.",
                checkpoint_id=checkpoint_id,
            )

        if (
            failure_kind in REPLAN_FAILURES
            and DeterministicContinuationPolicy.replan_allowed(replan_count=replan_count, policy=policy)
        ):
            return self._build_decision(
                plan=plan,
                step_id=plan.current_step_id,
                decision_type=ContinuationDecisionType.REBUILD_PLAN,
                reason_code="bounded_replan_available",
                reason_summary="A bounded replan can safely adjust the remaining plan segment.",
                confidence_score=self._confidence_with_signals(0.76, ContinuationDecisionType.REBUILD_PLAN, advisory_signals),
                recommended_action="Apply a bounded replan to the remaining plan segment.",
                checkpoint_id=checkpoint_id,
            )

        if (
            isinstance(result, dict)
            and not result.get("ok")
            and failure_kind not in NON_RETRYABLE_FAILURES
            and DeterministicContinuationPolicy.retry_allowed(retry_count=retry_count, policy=policy)
        ):
            return self._build_decision(
                plan=plan,
                step_id=plan.current_step_id,
                decision_type=ContinuationDecisionType.RETRY_STEP,
                reason_code="retry_budget_available",
                reason_summary="The latest step failed, but bounded retry budget remains available.",
                confidence_score=self._confidence_with_signals(0.81, ContinuationDecisionType.RETRY_STEP, advisory_signals),
                recommended_action="Retry the current step once more within policy limits.",
                checkpoint_id=checkpoint_id,
            )

        return self._build_decision(
            plan=plan,
            step_id=plan.current_step_id,
            decision_type=ContinuationDecisionType.CONTINUE_EXECUTION,
            reason_code="safe_to_continue",
            reason_summary="Plan health is adequate and the next operational step can continue.",
            confidence_score=self._confidence_with_signals(0.87, ContinuationDecisionType.CONTINUE_EXECUTION, advisory_signals),
            recommended_action="Continue executing the next runnable step.",
            checkpoint_id=checkpoint_id,
        )

    def _blend_with_simulation(
        self,
        *,
        baseline: ContinuationDecision,
        simulation_result: SimulationResult,
    ) -> ContinuationDecision:
        route = simulation_result.route_for(simulation_result.recommended_route)
        if route is None:
            return baseline
        baseline.metadata = {
            **dict(baseline.metadata),
            "simulation_id": simulation_result.simulation_id,
            "simulation_recommended_route": simulation_result.recommended_route.value,
            "simulation_confidence": route.confidence,
        }
        if route.confidence < 0.75:
            baseline.reason_summary = f"{baseline.reason_summary} Simulation advisory favored {route.route.value} with low confidence."
            if baseline.decision_type == ContinuationDecisionType.RETRY_STEP and route.route in {RouteType.PAUSE, RouteType.REPAIR}:
                baseline.confidence_score = max(0.2, baseline.confidence_score - 0.12)
            elif self._route_to_decision_type(route.route) == baseline.decision_type:
                baseline.confidence_score = min(0.99, baseline.confidence_score + 0.05)
            return baseline
        return baseline

    def _decision_from_simulation(
        self,
        *,
        plan: TaskPlan,
        checkpoint_id: str | None,
        decision_type: ContinuationDecisionType,
        simulation_result: SimulationResult,
        reason_code: str,
        reason_summary: str,
        recommended_action: str,
    ) -> ContinuationDecision:
        route = simulation_result.route_for(simulation_result.recommended_route)
        confidence = route.confidence if route is not None else 0.8
        return self._build_decision(
            plan=plan,
            step_id=plan.current_step_id,
            decision_type=decision_type,
            reason_code=reason_code,
            reason_summary=reason_summary,
            confidence_score=confidence,
            recommended_action=recommended_action,
            checkpoint_id=checkpoint_id,
            metadata={
                "goal_id": plan.goal_id,
                "simulation_id": simulation_result.simulation_id,
                "simulation_recommended_route": simulation_result.recommended_route.value,
                "simulation_routes": [candidate.as_dict() for candidate in simulation_result.routes],
            },
        )

    @staticmethod
    def _route_to_decision_type(route: RouteType) -> ContinuationDecisionType | None:
        mapping = {
            RouteType.RETRY: ContinuationDecisionType.RETRY_STEP,
            RouteType.REPLAN: ContinuationDecisionType.REBUILD_PLAN,
            RouteType.PAUSE: ContinuationDecisionType.PAUSE_PLAN,
        }
        return mapping.get(route)

    @staticmethod
    def _confidence_with_signals(base_confidence: float, decision_type: ContinuationDecisionType, advisory_signals: list[Any] | None) -> float:
        confidence = base_confidence
        for signal in advisory_signals or []:
            signal_type = getattr(getattr(signal, "signal_type", None), "value", "")
            metadata = getattr(signal, "metadata", {}) if isinstance(getattr(signal, "metadata", {}), dict) else {}
            hinted_decision = str(metadata.get("decision_type", "")).strip()
            if signal_type == "preferred_continuation_decision" and hinted_decision in {"", decision_type.value}:
                confidence = min(0.99, confidence + float(getattr(signal, "weight", 0.0) or 0.0) * 0.25)
            if signal_type in {"discouraged_retry_pattern", "high_risk_recurrence_alert"} and decision_type == ContinuationDecisionType.RETRY_STEP:
                confidence = max(0.2, confidence - float(getattr(signal, "weight", 0.0) or 0.0) * 0.4)
        return confidence

    @staticmethod
    def _failure_kind(result: dict[str, Any] | None) -> str:
        if not isinstance(result, dict):
            return ""
        error_payload = result.get("error_payload", {}) if isinstance(result.get("error_payload"), dict) else {}
        return str(error_payload.get("kind", "")).strip()

    @staticmethod
    def _build_decision(
        *,
        plan: TaskPlan,
        step_id: str | None,
        decision_type: ContinuationDecisionType,
        reason_code: str,
        reason_summary: str,
        confidence_score: float,
        recommended_action: str,
        checkpoint_id: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> ContinuationDecision:
        return ContinuationDecision.build(
            plan_id=plan.plan_id,
            task_id=plan.task_id,
            step_id=step_id,
            decision_type=decision_type,
            reason_code=reason_code,
            reason_summary=reason_summary,
            confidence_score=confidence_score,
            recommended_action=recommended_action,
            linked_execution_receipt_ids=list(plan.linked_execution_receipt_ids[-3:]),
            linked_repair_receipt_ids=list(plan.linked_repair_receipt_ids[-3:]),
            linked_checkpoint_id=checkpoint_id,
            metadata={
                "goal_id": plan.goal_id,
                **dict(metadata or {}),
            },
        )
