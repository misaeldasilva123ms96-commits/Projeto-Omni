from __future__ import annotations

from brain.runtime.planning import TaskPlan, TaskPlanStatus
from brain.runtime.planning.checkpoint_manager import CheckpointManager
from brain.runtime.planning.operational_summary import OperationalSummaryBuilder
from brain.runtime.planning.progress_tracker import ProgressTracker
from brain.runtime.planning.task_state_store import TaskStateStore


class PauseHandler:
    def __init__(
        self,
        *,
        store: TaskStateStore,
        tracker: ProgressTracker,
        checkpoints: CheckpointManager,
        summary_builder: OperationalSummaryBuilder,
    ) -> None:
        self.store = store
        self.tracker = tracker
        self.checkpoints = checkpoints
        self.summary_builder = summary_builder

    def pause(self, *, plan: TaskPlan, reason: str) -> TaskPlan:
        if plan.current_step_id:
            self.tracker.mark_step_paused(plan, plan.current_step_id, failure_summary=reason)
        plan.status = TaskPlanStatus.PAUSED
        self.store.save_plan(plan)
        self.checkpoints.create_checkpoint(
            plan=plan,
            step_id=plan.current_step_id,
            snapshot_summary="Plan paused by adaptive continuation.",
            resumable_state_payload={
                "status": plan.status.value,
                "current_step_id": plan.current_step_id,
                "reason": reason,
            },
            last_outcome_summary=reason,
        )
        self.store.save_summary(self.summary_builder.build(plan))
        return plan
