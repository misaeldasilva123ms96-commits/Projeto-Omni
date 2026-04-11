from __future__ import annotations

from pathlib import Path
from typing import Any

from .checkpoint_manager import CheckpointManager
from .models import PlanStepStatus, TaskClassificationDecision, TaskPlan, TaskPlanStatus
from .operational_summary import OperationalSummaryBuilder
from .plan_builder import OperationalPlanBuilder
from .progress_tracker import ProgressTracker
from .resume_engine import ResumeEngine
from .task_classifier import DeterministicTaskClassifier
from .task_state_store import TaskStateStore


class PlanningExecutor:
    def __init__(self, root: Path) -> None:
        self.store = TaskStateStore(root)
        self.classifier = DeterministicTaskClassifier()
        self.builder = OperationalPlanBuilder()
        self.tracker = ProgressTracker()
        self.checkpoints = CheckpointManager(self.store)
        self.summary_builder = OperationalSummaryBuilder(self.tracker)
        self.resume_engine = ResumeEngine(self.store, self.tracker)

    def classify_task(self, **kwargs: Any) -> TaskClassificationDecision:
        return self.classifier.classify(**kwargs)

    def ensure_plan(
        self,
        *,
        session_id: str,
        task_id: str,
        run_id: str,
        message: str,
        actions: list[dict[str, Any]],
        plan_kind: str,
        branch_plan: dict[str, Any] | None = None,
        start_index: int = 0,
        engineering_workflow: dict[str, Any] | None = None,
        advisory_signals: list[dict[str, Any]] | None = None,
    ) -> tuple[TaskClassificationDecision, TaskPlan | None]:
        classification = self.classify_task(
            message=message,
            actions=actions,
            plan_kind=plan_kind,
            branch_plan=branch_plan,
            start_index=start_index,
            engineering_workflow=engineering_workflow,
        )
        existing = self.store.find_plan(session_id=session_id, task_id=task_id, run_id=run_id)
        if existing is not None:
            return classification, existing
        if not classification.should_plan:
            return classification, None

        plan = self.builder.build_plan(
            task_id=task_id,
            session_id=session_id,
            run_id=run_id,
            message=message,
            actions=actions,
            classification=classification.classification,
            plan_kind=plan_kind,
            advisory_signals=advisory_signals,
        )
        inspect_step = self.tracker.step_by_id(plan, "inspect_context")
        if inspect_step is not None and inspect_step.status == PlanStepStatus.PENDING:
            self.tracker.mark_step_completed(
                plan,
                inspect_step.step_id,
                produced_artifacts_summary=["Runtime context prepared for operational execution."],
            )
        self.store.save_plan(plan)
        self.checkpoints.create_checkpoint(
            plan=plan,
            step_id=inspect_step.step_id if inspect_step else plan.current_step_id,
            snapshot_summary="Operational plan initialized.",
            resumable_state_payload={
                "task_id": task_id,
                "run_id": run_id,
                "pending_steps": [step.step_id for step in plan.steps if step.status == PlanStepStatus.PENDING][:8],
            },
            last_outcome_summary=classification.summary,
        )
        self.store.save_summary(self.summary_builder.build(plan))
        return classification, plan

    def record_step_started(self, plan: TaskPlan | None, *, action: dict[str, Any]) -> TaskPlan | None:
        if plan is None:
            return None
        step = self.tracker.step_for_action(plan, str(action.get("step_id", "")))
        if step is None:
            return plan
        self.tracker.mark_step_started(plan, step.step_id)
        self.store.save_plan(plan)
        self.checkpoints.create_checkpoint(
            plan=plan,
            step_id=step.step_id,
            snapshot_summary=f"Starting operational step {step.title}.",
            resumable_state_payload={
                "current_step_id": step.step_id,
                "selected_tool": step.metadata.get("selected_tool"),
                "selected_agent": step.metadata.get("selected_agent"),
            },
            last_outcome_summary=f"Step {step.title} entered in_progress.",
        )
        self.store.save_summary(self.summary_builder.build(plan))
        return plan

    def record_step_result(
        self,
        plan: TaskPlan | None,
        *,
        action: dict[str, Any],
        result: dict[str, Any],
    ) -> TaskPlan | None:
        if plan is None:
            return None
        step = self.tracker.step_for_action(plan, str(action.get("step_id", "")))
        if step is None:
            return plan
        execution_receipt_id = str((result.get("execution_receipt") or {}).get("receipt_id", "")).strip() or None
        repair_receipt_id = str((result.get("repair_receipt") or {}).get("repair_receipt_id", "")).strip() or None
        summary = self._result_summary(action=action)
        if result.get("ok"):
            self.tracker.mark_step_completed(
                plan,
                step.step_id,
                produced_artifacts_summary=summary,
                execution_receipt_id=execution_receipt_id,
                repair_receipt_id=repair_receipt_id,
            )
            snapshot_summary = f"Completed operational step {step.title}."
            last_outcome_summary = "Step completed successfully."
        else:
            status = str((result.get("evaluation") or {}).get("decision", "")).strip()
            if status == "stop_blocked":
                self.tracker.mark_step_blocked(
                    plan,
                    step.step_id,
                    failure_summary=self._failure_summary(result),
                )
            else:
                self.tracker.mark_step_failed(
                    plan,
                    step.step_id,
                    failure_summary=self._failure_summary(result),
                    execution_receipt_id=execution_receipt_id,
                    repair_receipt_id=repair_receipt_id,
                )
            snapshot_summary = f"Stopped at operational step {step.title}."
            last_outcome_summary = self._failure_summary(result)
        self.store.save_plan(plan)
        self.checkpoints.create_checkpoint(
            plan=plan,
            step_id=step.step_id,
            snapshot_summary=snapshot_summary,
            resumable_state_payload={
                "current_step_id": step.step_id,
                "step_status": step.status.value,
                "execution_receipt_id": execution_receipt_id,
                "repair_receipt_id": repair_receipt_id,
            },
            last_outcome_summary=last_outcome_summary,
        )
        self.store.save_summary(self.summary_builder.build(plan))
        return plan

    def finalize_plan(
        self,
        plan: TaskPlan | None,
        *,
        status_hint: str,
        step_results: list[dict[str, Any]],
    ) -> TaskPlan | None:
        if plan is None:
            return None
        summarize_step = self.tracker.step_by_id(plan, "summarize_outcome")
        if summarize_step and summarize_step.status in {PlanStepStatus.PENDING, PlanStepStatus.IN_PROGRESS}:
            artifact_summary = [self._failure_summary(step_results[-1])] if step_results and not step_results[-1].get("ok") else [
                f"{len([item for item in step_results if item.get('ok')])} steps completed successfully."
            ]
            if status_hint == "completed":
                self.tracker.mark_step_completed(plan, summarize_step.step_id, produced_artifacts_summary=artifact_summary)
            else:
                self.tracker.mark_step_blocked(plan, summarize_step.step_id, failure_summary=artifact_summary[0])

        checkpoint_step = self.tracker.step_by_id(plan, "persist_checkpoint")
        if checkpoint_step and checkpoint_step.status in {PlanStepStatus.PENDING, PlanStepStatus.IN_PROGRESS}:
            if status_hint == "completed":
                self.tracker.mark_step_completed(
                    plan,
                    checkpoint_step.step_id,
                    produced_artifacts_summary=["Operational checkpoint persisted."],
                )
            else:
                self.tracker.mark_step_blocked(
                    plan,
                    checkpoint_step.step_id,
                    failure_summary="Plan ended without a fully successful operational checkpoint.",
                )

        if status_hint == "completed":
            plan.status = TaskPlanStatus.COMPLETED
        elif plan.status not in {TaskPlanStatus.FAILED, TaskPlanStatus.BLOCKED}:
            plan.status = TaskPlanStatus.BLOCKED

        self.store.save_plan(plan)
        self.checkpoints.create_checkpoint(
            plan=plan,
            step_id=plan.current_step_id,
            snapshot_summary=f"Operational plan finalized with status {plan.status.value}.",
            resumable_state_payload={
                "status": plan.status.value,
                "completed_steps": plan.completed_step_count,
                "failed_steps": plan.failed_step_count,
            },
            last_outcome_summary=f"Plan finalized with status {plan.status.value}.",
        )
        self.store.save_summary(self.summary_builder.build(plan))
        return plan

    def resume_decision(self, plan: TaskPlan | None):
        if plan is None:
            return None
        return self.resume_engine.decide(plan)

    def summary_for_plan(self, plan: TaskPlan | None):
        if plan is None:
            return None
        summary = self.summary_builder.build(plan)
        self.store.save_summary(summary)
        return summary

    @staticmethod
    def _result_summary(*, action: dict[str, Any]) -> list[str]:
        selected_tool = str(action.get("selected_tool", "runtime action")).strip() or "runtime action"
        if selected_tool in {"filesystem_read", "read_file"}:
            return [f"{selected_tool} returned a readable payload."]
        if selected_tool in {"filesystem_write", "filesystem_patch_set"}:
            return [f"{selected_tool} reported a workspace mutation payload."]
        return [f"{selected_tool} completed with structured output."]

    @staticmethod
    def _failure_summary(result: dict[str, Any]) -> str:
        error_payload = result.get("error_payload", {}) if isinstance(result.get("error_payload"), dict) else {}
        message = str(error_payload.get("message", "")).strip()
        kind = str(error_payload.get("kind", "")).strip()
        if message and kind:
            return f"{kind}: {message}"
        return message or kind or "Operational step failed."
