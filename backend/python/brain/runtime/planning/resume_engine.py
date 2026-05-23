from __future__ import annotations

from .models import PlanStepStatus, ResumeDecision, ResumeDecisionType, TaskPlan, TaskPlanStatus
from .progress_tracker import ProgressTracker
from .task_state_store import TaskStateStore


class ResumeEngine:
    def __init__(self, store: TaskStateStore, tracker: ProgressTracker) -> None:
        self.store = store
        self.tracker = tracker

    def decide(self, plan: TaskPlan) -> ResumeDecision:
        checkpoint = self.store.load_latest_checkpoint(plan.plan_id)
        if checkpoint is None:
            return ResumeDecision(
                decision=ResumeDecisionType.REBUILD_PLAN,
                reason_code="missing_checkpoint",
                summary="No checkpoint is available, so the plan must be rebuilt before resume.",
                plan_id=plan.plan_id,
            )

        if checkpoint.step_id and self.tracker.step_by_id(plan, checkpoint.step_id) is None:
            return ResumeDecision(
                decision=ResumeDecisionType.MANUAL_INTERVENTION_REQUIRED,
                reason_code="checkpoint_step_missing",
                summary="The latest checkpoint references a step that is not present in the current plan state.",
                plan_id=plan.plan_id,
                checkpoint_id=checkpoint.checkpoint_id,
                step_id=checkpoint.step_id,
            )

        if any(
            self.tracker.step_by_id(plan, dependency_id) is None
            for step in plan.steps
            for dependency_id in step.dependency_step_ids
        ):
            return ResumeDecision(
                decision=ResumeDecisionType.MANUAL_INTERVENTION_REQUIRED,
                reason_code="missing_step_dependency",
                summary="The persisted plan contains step dependencies that no longer exist.",
                plan_id=plan.plan_id,
                checkpoint_id=checkpoint.checkpoint_id,
            )

        current_step = self.tracker.step_by_id(plan, plan.current_step_id) if plan.current_step_id else None
        if current_step and current_step.status == PlanStepStatus.IN_PROGRESS:
            return ResumeDecision(
                decision=ResumeDecisionType.RESTART_CURRENT_STEP,
                reason_code="step_was_in_progress",
                summary="The current step was in progress, so resume should restart that step safely.",
                plan_id=plan.plan_id,
                checkpoint_id=checkpoint.checkpoint_id,
                step_id=current_step.step_id,
                resumable_state_payload=dict(checkpoint.resumable_state_payload),
            )

        next_step = self.tracker.next_executable_step(plan)
        if next_step is None and plan.status == TaskPlanStatus.COMPLETED:
            return ResumeDecision(
                decision=ResumeDecisionType.RESUME_FROM_CHECKPOINT,
                reason_code="plan_already_completed",
                summary="The plan is already completed and does not require further operational work.",
                plan_id=plan.plan_id,
                checkpoint_id=checkpoint.checkpoint_id,
                resumable_state_payload=dict(checkpoint.resumable_state_payload),
            )
        if next_step is None:
            return ResumeDecision(
                decision=ResumeDecisionType.MANUAL_INTERVENTION_REQUIRED,
                reason_code="no_runnable_step",
                summary="No runnable step could be identified from the latest consistent checkpoint.",
                plan_id=plan.plan_id,
                checkpoint_id=checkpoint.checkpoint_id,
                resumable_state_payload=dict(checkpoint.resumable_state_payload),
            )

        return ResumeDecision(
            decision=ResumeDecisionType.RESUME_FROM_CHECKPOINT,
            reason_code="latest_checkpoint_valid",
            summary="A valid checkpoint is available and the next runnable step can continue from persisted state.",
            plan_id=plan.plan_id,
            checkpoint_id=checkpoint.checkpoint_id,
            step_id=next_step.step_id,
            resumable_state_payload=dict(checkpoint.resumable_state_payload),
        )
