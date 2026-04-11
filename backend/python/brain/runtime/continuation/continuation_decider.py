from __future__ import annotations

from typing import Any

from brain.runtime.planning import TaskPlan
from brain.runtime.planning.progress_tracker import ProgressTracker

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
    def __init__(self, tracker: ProgressTracker) -> None:
        self.tracker = tracker

    def decide(
        self,
        *,
        plan: TaskPlan,
        evaluation: PlanEvaluation,
        policy: ContinuationPolicy,
        checkpoint_id: str | None,
        result: dict[str, Any] | None = None,
        advisory_signals: list[Any] | None = None,
    ) -> ContinuationDecision:
        current_step = self.tracker.step_by_id(plan, plan.current_step_id) if plan.current_step_id else None
        failure_kind = self._failure_kind(result)
        replan_count = int(plan.metadata.get("continuation_replan_count", 0) or 0)
        retry_count = current_step.retry_count if current_step is not None else 0

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
        )
