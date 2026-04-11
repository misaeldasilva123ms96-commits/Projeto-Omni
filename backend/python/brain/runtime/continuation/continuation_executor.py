from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from brain.runtime.goals import ConstraintRegistry, GoalEvaluator, GoalStore
from brain.runtime.memory import MemoryFacade
from brain.runtime.planning import TaskPlan, TaskPlanStatus
from brain.runtime.planning.checkpoint_manager import CheckpointManager
from brain.runtime.planning.operational_summary import OperationalSummaryBuilder
from brain.runtime.planning.progress_tracker import ProgressTracker
from brain.runtime.planning.task_state_store import TaskStateStore
from brain.runtime.simulation import ActionSimulator, SimulationContextBuilder

from .continuation_decider import ContinuationDecider
from .continuation_policy import DeterministicContinuationPolicy
from .escalation_handler import EscalationHandler
from .models import ContinuationDecision, ContinuationDecisionType, ContinuationPolicy, PlanEvaluation
from .pause_handler import PauseHandler
from .plan_evaluator import PlanEvaluator
from .replan_engine import ReplanEngine


class ContinuationExecutor:
    def __init__(
        self,
        root: Path,
        *,
        memory_facade: MemoryFacade | None = None,
        simulator: ActionSimulator | None = None,
    ) -> None:
        self.root = root
        self.memory_facade = memory_facade
        self.simulator = simulator
        self.policy = DeterministicContinuationPolicy.from_env()
        self.store = TaskStateStore(root)
        self.tracker = ProgressTracker()
        self.checkpoints = CheckpointManager(self.store)
        self.summary_builder = OperationalSummaryBuilder(self.tracker)
        self.evaluator = PlanEvaluator(self.tracker)
        self.simulation_context_builder = SimulationContextBuilder(memory_facade=memory_facade)
        self.decider = ContinuationDecider(
            self.tracker,
            simulator=simulator,
            simulation_context_builder=self.simulation_context_builder,
        )
        self.goal_store = GoalStore(root)
        self.goal_registry = ConstraintRegistry()
        self.goal_evaluator = GoalEvaluator(self.goal_registry)
        self.replanner = ReplanEngine(self.tracker)
        self.pause_handler = PauseHandler(
            store=self.store,
            tracker=self.tracker,
            checkpoints=self.checkpoints,
            summary_builder=self.summary_builder,
        )
        self.escalation_handler = EscalationHandler(
            root=root,
            store=self.store,
            checkpoints=self.checkpoints,
            summary_builder=self.summary_builder,
        )
        self.base_dir = root / ".logs" / "fusion-runtime" / "continuation"
        self.decisions_dir = self.base_dir / "decisions"
        self.evaluations_dir = self.base_dir / "evaluations"
        self.decisions_dir.mkdir(parents=True, exist_ok=True)
        self.evaluations_dir.mkdir(parents=True, exist_ok=True)

    def evaluate_and_decide(
        self,
        *,
        plan: TaskPlan | None,
        result: dict[str, Any] | None = None,
        advisory_signals: list[Any] | None = None,
    ) -> tuple[PlanEvaluation | None, ContinuationDecision | None, TaskPlan | None]:
        if plan is None:
            return None, None, None
        focus_step = self._resolve_focus_step(plan)
        if focus_step is not None:
            plan.current_step_id = focus_step.step_id
        checkpoint = self.store.load_latest_checkpoint(plan.plan_id)
        summary = self.store.load_summary(plan.plan_id)
        evaluation = self.evaluator.evaluate(
            plan=plan,
            result=result,
            checkpoint=checkpoint.as_dict() if checkpoint else None,
            summary=summary.as_dict() if summary else None,
        )
        goal_evaluation = None
        goal = None
        if plan.goal_id:
            goal = self.goal_store.get_by_id(plan.goal_id)
            if goal is not None:
                goal_evaluation = self.goal_evaluator.evaluate(
                    goal=goal,
                    runtime_state=self._build_goal_runtime_state(plan=plan, result=result, checkpoint=checkpoint, summary=summary),
                    memory_facade=self.memory_facade,
                )
        decision = self.decider.decide(
            plan=plan,
            evaluation=evaluation,
            policy=self.policy,
            checkpoint_id=checkpoint.checkpoint_id if checkpoint else None,
            goal=goal,
            goal_evaluation=goal_evaluation,
            result=result,
            advisory_signals=advisory_signals,
        )
        updated_plan = self._apply_decision(
            plan=plan,
            decision=decision,
            result=result,
        )
        self._persist_evaluation(evaluation)
        self._persist_decision(decision)
        if self.memory_facade is not None and plan.goal_id:
            self.memory_facade.record_event(
                event_type="continuation_decision",
                description=decision.reason_summary,
                outcome=decision.decision_type.value,
                progress_score=evaluation.progress_ratio,
                evidence_ids=[
                    item
                    for item in [decision.linked_checkpoint_id, *decision.linked_execution_receipt_ids, *decision.linked_repair_receipt_ids]
                    if item
                ],
                metadata={
                    "decision_type": decision.decision_type.value,
                    "reason_code": decision.reason_code,
                    "plan_id": plan.plan_id,
                    "task_id": plan.task_id,
                    "goal_id": plan.goal_id,
                },
            )
            self.memory_facade.update_progress(evaluation.progress_ratio)
        if updated_plan is not None:
            self.store.save_plan(updated_plan)
            self.store.save_summary(self.summary_builder.build(updated_plan))
        return evaluation, decision, updated_plan

    @classmethod
    def _build_goal_runtime_state(
        cls,
        *,
        plan: TaskPlan,
        result: dict[str, Any] | None,
        checkpoint: Any,
        summary: Any,
    ) -> dict[str, Any]:
        completed_steps = len([step for step in plan.steps if step.status.value == "completed"])
        failed_steps = len([step for step in plan.steps if step.status.value == "failed"])
        current_step = next((step for step in plan.steps if step.step_id == plan.current_step_id), None)
        current_tool = ""
        if isinstance(result, dict):
            current_tool = str(result.get("selected_tool", "")).strip()
            if not current_tool:
                action = result.get("action", {}) if isinstance(result.get("action"), dict) else {}
                current_tool = str(action.get("selected_tool", "")).strip()
        return {
            "result_ok": bool(isinstance(result, dict) and result.get("ok")),
            "successful_steps_count": completed_steps,
            "failed_steps_count": failed_steps,
            "max_retries": float(getattr(current_step, "retry_count", 0) or 0),
            "max_repairs": float(1 if isinstance(result, dict) and result.get("repair_receipt") else 0),
            "error_rate": float(failed_steps / max(len(plan.steps), 1)),
            "partial_success": float(completed_steps / max(plan.total_step_count or len(plan.steps), 1)),
            "cycle_count": float(completed_steps + failed_steps),
            "max_cycles": float(len(plan.steps)),
            "timeout": False,
            "dependency_failed": bool(isinstance(result, dict) and str(((result.get("error_payload") or {}).get("kind", ""))).strip() in {"dependency_failed", "dependency_missing"}),
            "proposal_target_subsystem": cls._subsystem_from_tool(current_tool),
            "summary_status": getattr(summary, "plan_status", "") if summary is not None else "",
        }

    @staticmethod
    def _subsystem_from_tool(selected_tool: str) -> str:
        if selected_tool in {"filesystem_read", "read_file", "filesystem_write", "filesystem_patch_set"}:
            return "planning"
        if selected_tool in {"verification_runner", "test_runner"}:
            return "continuation"
        return "orchestration"

    def _apply_decision(
        self,
        *,
        plan: TaskPlan,
        decision: ContinuationDecision,
        result: dict[str, Any] | None,
    ) -> TaskPlan:
        if decision.decision_type == ContinuationDecisionType.CONTINUE_EXECUTION:
            if plan.status not in {TaskPlanStatus.COMPLETED, TaskPlanStatus.BLOCKED, TaskPlanStatus.PAUSED}:
                plan.status = TaskPlanStatus.ACTIVE
            return plan
        if decision.decision_type == ContinuationDecisionType.RETRY_STEP:
            if plan.current_step_id:
                step = self.tracker.step_by_id(plan, plan.current_step_id)
                if step is not None:
                    step.status = step.status.__class__("pending")
                    plan.current_step_id = step.step_id
            plan.status = TaskPlanStatus.ACTIVE
            return plan
        if decision.decision_type == ContinuationDecisionType.PAUSE_PLAN:
            return self.pause_handler.pause(plan=plan, reason=decision.reason_summary)
        if decision.decision_type == ContinuationDecisionType.REBUILD_PLAN:
            updated = self.replanner.rebuild_remaining_segment(
                plan=plan,
                current_step_id=plan.current_step_id,
                reason_code=decision.reason_code,
            )
            self.checkpoints.create_checkpoint(
                plan=updated,
                step_id=updated.current_step_id,
                snapshot_summary="Bounded continuation replan applied.",
                resumable_state_payload={
                    "status": updated.status.value,
                    "current_step_id": updated.current_step_id,
                    "replan_count": updated.metadata.get("continuation_replan_count", 0),
                },
                last_outcome_summary=decision.reason_summary,
            )
            return updated
        if decision.decision_type == ContinuationDecisionType.ESCALATE_FAILURE:
            payload = {
                "decision": decision.as_dict(),
                "latest_result": result or {},
            }
            return self.escalation_handler.escalate(
                plan=plan,
                reason=decision.reason_summary,
                payload=payload,
            )
        if decision.decision_type == ContinuationDecisionType.COMPLETE_PLAN:
            plan.status = TaskPlanStatus.COMPLETED
            self.checkpoints.create_checkpoint(
                plan=plan,
                step_id=plan.current_step_id,
                snapshot_summary="Plan completed by adaptive continuation.",
                resumable_state_payload={
                    "status": plan.status.value,
                    "current_step_id": plan.current_step_id,
                },
                last_outcome_summary=decision.reason_summary,
            )
            return plan
        return plan

    def _resolve_focus_step(self, plan: TaskPlan):
        if plan.current_step_id:
            step = self.tracker.step_by_id(plan, plan.current_step_id)
            if step is not None:
                return step
        for status in ("failed", "blocked", "paused", "in_progress", "pending"):
            for step in reversed(plan.steps):
                if step.step_type != "execute_action":
                    continue
                if step.status.value == status:
                    return step
        return self.tracker.next_executable_step(plan)

    def _persist_evaluation(self, evaluation: PlanEvaluation) -> None:
        path = self.evaluations_dir / f"{evaluation.plan_id}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(evaluation.as_dict(), ensure_ascii=False))
            handle.write("\n")

    def _persist_decision(self, decision: ContinuationDecision) -> None:
        path = self.decisions_dir / f"{decision.plan_id}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(decision.as_dict(), ensure_ascii=False))
            handle.write("\n")
