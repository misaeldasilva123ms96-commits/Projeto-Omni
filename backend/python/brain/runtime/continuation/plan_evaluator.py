from __future__ import annotations

from typing import Any

from brain.runtime.planning import TaskPlan, TaskPlanStatus
from brain.runtime.planning.progress_tracker import ProgressTracker

from .models import PlanEvaluation, PlanHealth


class PlanEvaluator:
    def __init__(self, tracker: ProgressTracker) -> None:
        self.tracker = tracker

    def evaluate(
        self,
        *,
        plan: TaskPlan,
        result: dict[str, Any] | None = None,
        checkpoint: dict[str, Any] | None = None,
        summary: dict[str, Any] | None = None,
    ) -> PlanEvaluation:
        blocked_step_count = sum(1 for step in plan.steps if step.status.value == "blocked")
        failed_step_count = sum(1 for step in plan.steps if step.status.value == "failed")
        current_step = self.tracker.step_by_id(plan, plan.current_step_id) if plan.current_step_id else None
        retry_count = current_step.retry_count if current_step is not None else 0
        progress_ratio = 1.0 if plan.total_step_count == 0 else round(plan.completed_step_count / max(plan.total_step_count, 1), 4)
        repair_outcome_summary = self._repair_outcome_summary(result)
        resumability_state = str((summary or {}).get("resumability_state", "unknown"))
        dependency_health = self._dependency_health(plan)
        plan_health = self._health(
            plan=plan,
            failed_step_count=failed_step_count,
            blocked_step_count=blocked_step_count,
            dependency_health=dependency_health,
        )
        recommendation_hints = self._recommendation_hints(
            plan=plan,
            result=result,
            dependency_health=dependency_health,
            repair_outcome_summary=repair_outcome_summary,
        )

        return PlanEvaluation.build(
            plan_id=plan.plan_id,
            current_step_id=plan.current_step_id,
            plan_health=plan_health,
            progress_ratio=progress_ratio,
            failed_step_count=failed_step_count,
            blocked_step_count=blocked_step_count,
            retry_pressure=float(retry_count),
            repair_outcome_summary=repair_outcome_summary,
            resumability_state=resumability_state,
            dependency_health=dependency_health,
            recent_receipt_summary={
                "execution_receipt_ids": list(plan.linked_execution_receipt_ids[-3:]),
                "repair_receipt_ids": list(plan.linked_repair_receipt_ids[-3:]),
                "latest_checkpoint_id": (checkpoint or {}).get("checkpoint_id"),
                "latest_result_kind": self._result_kind(result),
            },
            recommendation_hints=recommendation_hints,
        )

    def _health(
        self,
        *,
        plan: TaskPlan,
        failed_step_count: int,
        blocked_step_count: int,
        dependency_health: str,
    ) -> PlanHealth:
        if plan.status == TaskPlanStatus.COMPLETED or plan.completed_step_count >= plan.total_step_count:
            return PlanHealth.COMPLETED
        if plan.status == TaskPlanStatus.BLOCKED or blocked_step_count > 0:
            return PlanHealth.BLOCKED
        if dependency_health == "missing_dependencies":
            return PlanHealth.STALLED
        if failed_step_count > 0 or plan.status == TaskPlanStatus.FAILED:
            return PlanHealth.DEGRADED
        return PlanHealth.HEALTHY

    def _dependency_health(self, plan: TaskPlan) -> str:
        next_step = self.tracker.next_executable_step(plan)
        if next_step is not None:
            return "satisfied"
        if any(step.status.value in {"pending", "paused", "in_progress"} for step in plan.steps):
            return "missing_dependencies"
        return "settled"

    @staticmethod
    def _repair_outcome_summary(result: dict[str, Any] | None) -> str:
        if not isinstance(result, dict):
            return ""
        repair_receipt = result.get("repair_receipt", {}) if isinstance(result.get("repair_receipt"), dict) else {}
        if repair_receipt:
            return f"{repair_receipt.get('promotion_status', '')}:{repair_receipt.get('rejection_reason', '')}".strip(":")
        return ""

    @staticmethod
    def _result_kind(result: dict[str, Any] | None) -> str:
        if not isinstance(result, dict):
            return ""
        error_payload = result.get("error_payload", {}) if isinstance(result.get("error_payload"), dict) else {}
        return str(error_payload.get("kind", "")).strip()

    def _recommendation_hints(
        self,
        *,
        plan: TaskPlan,
        result: dict[str, Any] | None,
        dependency_health: str,
        repair_outcome_summary: str,
    ) -> list[str]:
        hints: list[str] = []
        if plan.completed_step_count >= plan.total_step_count and plan.total_step_count > 0:
            hints.append("plan_completed")
        if dependency_health == "missing_dependencies":
            hints.append("dependency_gap")
        if repair_outcome_summary.startswith("rejected"):
            hints.append("repair_rejected")
        if isinstance(result, dict) and not result.get("ok"):
            hints.append("step_failed")
        if not hints:
            hints.append("safe_to_continue")
        return hints
