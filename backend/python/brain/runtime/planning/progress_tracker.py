from __future__ import annotations

from typing import Any

from .models import PlanStep, PlanStepStatus, TaskPlan, TaskPlanStatus, utc_now_iso


class ProgressTracker:
    def step_by_id(self, plan: TaskPlan, step_id: str) -> PlanStep | None:
        return next((item for item in plan.steps if item.step_id == step_id), None)

    def step_for_action(self, plan: TaskPlan, action_step_id: str) -> PlanStep | None:
        return next(
            (
                item
                for item in plan.steps
                if item.step_type == "execute_action"
                and str(item.metadata.get("action_step_id", "")) == action_step_id
            ),
            None,
        )

    def mark_step_started(self, plan: TaskPlan, step_id: str) -> PlanStep | None:
        step = self.step_by_id(plan, step_id)
        if step is None:
            return None
        if step.status == PlanStepStatus.PENDING:
            step.status = PlanStepStatus.IN_PROGRESS
            step.started_at = step.started_at or utc_now_iso()
        plan.status = TaskPlanStatus.ACTIVE
        plan.current_step_id = step.step_id
        plan.updated_at = utc_now_iso()
        self._refresh_counts(plan)
        return step

    def mark_step_completed(
        self,
        plan: TaskPlan,
        step_id: str,
        *,
        produced_artifacts_summary: list[str] | None = None,
        execution_receipt_id: str | None = None,
        repair_receipt_id: str | None = None,
    ) -> PlanStep | None:
        step = self.step_by_id(plan, step_id)
        if step is None:
            return None
        step.status = PlanStepStatus.COMPLETED
        step.started_at = step.started_at or utc_now_iso()
        step.completed_at = utc_now_iso()
        if produced_artifacts_summary:
            step.produced_artifacts_summary = [str(item)[:180] for item in produced_artifacts_summary if str(item).strip()][:8]
        step.failure_summary = ""
        self._link_receipts(plan, execution_receipt_id, repair_receipt_id)
        self._refresh_plan_state(plan)
        return step

    def mark_step_failed(
        self,
        plan: TaskPlan,
        step_id: str,
        *,
        failure_summary: str,
        execution_receipt_id: str | None = None,
        repair_receipt_id: str | None = None,
    ) -> PlanStep | None:
        step = self.step_by_id(plan, step_id)
        if step is None:
            return None
        step.status = PlanStepStatus.FAILED
        step.started_at = step.started_at or utc_now_iso()
        step.completed_at = utc_now_iso()
        step.failure_summary = failure_summary[:280]
        step.retry_count += 1
        self._link_receipts(plan, execution_receipt_id, repair_receipt_id)
        self._refresh_plan_state(plan, force_status=TaskPlanStatus.FAILED)
        return step

    def mark_step_blocked(self, plan: TaskPlan, step_id: str, *, failure_summary: str) -> PlanStep | None:
        step = self.step_by_id(plan, step_id)
        if step is None:
            return None
        step.status = PlanStepStatus.BLOCKED
        step.started_at = step.started_at or utc_now_iso()
        step.failure_summary = failure_summary[:280]
        self._refresh_plan_state(plan, force_status=TaskPlanStatus.BLOCKED)
        return step

    def mark_step_paused(self, plan: TaskPlan, step_id: str, *, failure_summary: str = "") -> PlanStep | None:
        step = self.step_by_id(plan, step_id)
        if step is None:
            return None
        step.status = PlanStepStatus.PAUSED
        if failure_summary:
            step.failure_summary = failure_summary[:280]
        self._refresh_plan_state(plan, force_status=TaskPlanStatus.PAUSED)
        return step

    def next_executable_step(self, plan: TaskPlan) -> PlanStep | None:
        for step in plan.steps:
            if step.status not in {PlanStepStatus.PENDING, PlanStepStatus.PAUSED, PlanStepStatus.IN_PROGRESS}:
                continue
            if all(
                (dependency := self.step_by_id(plan, dependency_id)) is not None
                and dependency.status in {PlanStepStatus.COMPLETED, PlanStepStatus.SKIPPED}
                for dependency_id in step.dependency_step_ids
            ):
                return step
        return None

    def compute_progress_summary(self, plan: TaskPlan) -> dict[str, Any]:
        self._refresh_counts(plan)
        return {
            "plan_id": plan.plan_id,
            "status": plan.status.value,
            "classification": plan.classification.value,
            "current_step_id": plan.current_step_id,
            "total_step_count": plan.total_step_count,
            "completed_step_count": plan.completed_step_count,
            "failed_step_count": plan.failed_step_count,
        }

    def detect_stalled_plan(self, plan: TaskPlan) -> bool:
        if plan.status not in {TaskPlanStatus.ACTIVE, TaskPlanStatus.PAUSED, TaskPlanStatus.BLOCKED}:
            return False
        if any(step.status == PlanStepStatus.IN_PROGRESS for step in plan.steps):
            return False
        return self.next_executable_step(plan) is None and plan.completed_step_count < plan.total_step_count

    def _refresh_plan_state(self, plan: TaskPlan, force_status: TaskPlanStatus | None = None) -> None:
        self._refresh_counts(plan)
        plan.updated_at = utc_now_iso()
        next_step = self.next_executable_step(plan)
        plan.current_step_id = next_step.step_id if next_step else None

        if force_status is not None:
            plan.status = force_status
            return
        if plan.completed_step_count >= plan.total_step_count and plan.total_step_count > 0:
            plan.status = TaskPlanStatus.COMPLETED
            return
        if plan.failed_step_count > 0:
            plan.status = TaskPlanStatus.FAILED
            return
        if any(step.status == PlanStepStatus.BLOCKED for step in plan.steps):
            plan.status = TaskPlanStatus.BLOCKED
            return
        if any(step.status == PlanStepStatus.PAUSED for step in plan.steps):
            plan.status = TaskPlanStatus.PAUSED
            return
        plan.status = TaskPlanStatus.ACTIVE

    def _refresh_counts(self, plan: TaskPlan) -> None:
        plan.total_step_count = len(plan.steps)
        plan.completed_step_count = sum(1 for step in plan.steps if step.status == PlanStepStatus.COMPLETED)
        plan.failed_step_count = sum(1 for step in plan.steps if step.status == PlanStepStatus.FAILED)

    @staticmethod
    def _link_receipts(plan: TaskPlan, execution_receipt_id: str | None, repair_receipt_id: str | None) -> None:
        if execution_receipt_id and execution_receipt_id not in plan.linked_execution_receipt_ids:
            plan.linked_execution_receipt_ids.append(execution_receipt_id)
        if repair_receipt_id and repair_receipt_id not in plan.linked_repair_receipt_ids:
            plan.linked_repair_receipt_ids.append(repair_receipt_id)
