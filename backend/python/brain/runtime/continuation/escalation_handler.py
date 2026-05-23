from __future__ import annotations

import json
from pathlib import Path

from brain.runtime.planning import TaskPlan, TaskPlanStatus
from brain.runtime.planning.checkpoint_manager import CheckpointManager
from brain.runtime.planning.operational_summary import OperationalSummaryBuilder
from brain.runtime.planning.task_state_store import TaskStateStore


class EscalationHandler:
    def __init__(
        self,
        *,
        root: Path,
        store: TaskStateStore,
        checkpoints: CheckpointManager,
        summary_builder: OperationalSummaryBuilder,
    ) -> None:
        self.store = store
        self.checkpoints = checkpoints
        self.summary_builder = summary_builder
        self.escalations_dir = root / ".logs" / "fusion-runtime" / "continuation" / "escalations"
        self.escalations_dir.mkdir(parents=True, exist_ok=True)

    def escalate(self, *, plan: TaskPlan, reason: str, payload: dict[str, object]) -> TaskPlan:
        plan.status = TaskPlanStatus.BLOCKED
        if plan.current_step_id:
            for step in plan.steps:
                if step.step_id == plan.current_step_id:
                    step.failure_summary = reason
                    if step.status.value not in {"completed", "skipped"}:
                        step.status = step.status.__class__("blocked")
                    break
        self.store.save_plan(plan)
        self.checkpoints.create_checkpoint(
            plan=plan,
            step_id=plan.current_step_id,
            snapshot_summary="Plan escalated by adaptive continuation.",
            resumable_state_payload={
                "status": plan.status.value,
                "current_step_id": plan.current_step_id,
                "reason": reason,
            },
            last_outcome_summary=reason,
        )
        self.store.save_summary(self.summary_builder.build(plan))
        path = self.escalations_dir / f"{plan.plan_id}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False))
            handle.write("\n")
        return plan
