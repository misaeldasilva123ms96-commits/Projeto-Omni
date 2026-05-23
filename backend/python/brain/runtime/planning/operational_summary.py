from __future__ import annotations

from .models import OperationalSummary, TaskPlan, TaskPlanStatus
from .progress_tracker import ProgressTracker


class OperationalSummaryBuilder:
    def __init__(self, tracker: ProgressTracker) -> None:
        self.tracker = tracker

    def build(self, plan: TaskPlan) -> OperationalSummary:
        completed_steps = [step.title for step in plan.steps if step.status.value == "completed"]
        current_step = self.tracker.step_by_id(plan, plan.current_step_id) if plan.current_step_id else None
        last_failure = next(
            (
                step.failure_summary
                for step in reversed(plan.steps)
                if step.failure_summary and step.status.value in {"failed", "blocked", "paused"}
            ),
            "",
        )
        next_step = self.tracker.next_executable_step(plan)
        if plan.status == TaskPlanStatus.COMPLETED:
            resumability_state = "completed"
            next_action = "No further operational action is required."
        elif next_step is not None:
            resumability_state = "resumable"
            next_action = f"Continue with step: {next_step.title}"
        elif self.tracker.detect_stalled_plan(plan):
            resumability_state = "unsafe_to_resume"
            next_action = "Review checkpoint and plan consistency before resuming."
        else:
            resumability_state = "waiting"
            next_action = "Wait for a new operational trigger or manual intervention."

        return OperationalSummary(
            plan_id=plan.plan_id,
            task_id=plan.task_id,
            goal_id=plan.goal_id,
            current_objective=plan.objective,
            plan_status=plan.status.value,
            completed_steps=completed_steps,
            current_step=current_step.title if current_step else None,
            last_failure=last_failure,
            next_recommended_action=next_action,
            resumability_state=resumability_state,
            linked_execution_receipt_ids=list(plan.linked_execution_receipt_ids),
            linked_repair_receipt_ids=list(plan.linked_repair_receipt_ids),
            metadata={
                "classification": plan.classification.value,
                "checkpoint_pointer": plan.checkpoint_pointer,
                "goal_description": str(plan.metadata.get("goal_description", "")),
            },
        )
