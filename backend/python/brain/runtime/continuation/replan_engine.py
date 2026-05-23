from __future__ import annotations

from brain.runtime.planning import PlanStep, PlanStepStatus, TaskPlan
from brain.runtime.planning.progress_tracker import ProgressTracker


class ReplanEngine:
    def __init__(self, tracker: ProgressTracker) -> None:
        self.tracker = tracker

    def rebuild_remaining_segment(self, *, plan: TaskPlan, current_step_id: str | None, reason_code: str) -> TaskPlan:
        if not current_step_id:
            return plan
        current_step = self.tracker.step_by_id(plan, current_step_id)
        if current_step is None:
            return plan

        replan_count = int(plan.metadata.get("continuation_replan_count", 0) or 0) + 1
        plan.metadata["continuation_replan_count"] = replan_count
        replacement_step_id = f"replan:{current_step_id}:{replan_count}"
        if self.tracker.step_by_id(plan, replacement_step_id) is not None:
            return plan

        current_step.status = PlanStepStatus.SKIPPED
        current_step.failure_summary = f"Skipped after bounded replan ({reason_code})."

        replacement = PlanStep(
            step_id=replacement_step_id,
            title="Adjust Remaining Segment",
            description="Bounded continuation replan for the remaining operational segment.",
            step_type="validate_result",
            dependency_step_ids=list(current_step.dependency_step_ids),
            status=PlanStepStatus.PENDING,
            expected_outcome="Remaining steps are safe to continue after bounded replan.",
            metadata={
                "auto_managed": True,
                "replan_reason_code": reason_code,
                "replaces_step_id": current_step_id,
            },
        )

        current_index = next((index for index, step in enumerate(plan.steps) if step.step_id == current_step_id), len(plan.steps))
        plan.steps.insert(current_index + 1, replacement)
        for step in plan.steps[current_index + 2 :]:
            if current_step_id in step.dependency_step_ids:
                step.dependency_step_ids = [
                    replacement_step_id if dependency == current_step_id else dependency
                    for dependency in step.dependency_step_ids
                ]
        plan.current_step_id = replacement_step_id
        return plan
