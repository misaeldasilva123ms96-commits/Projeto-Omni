from __future__ import annotations

from typing import Any

from .models import OrchestrationContext


class OrchestrationContextBuilder:
    def build(
        self,
        *,
        session_id: str | None,
        task_id: str | None,
        run_id: str | None,
        action: dict[str, Any],
        plan: Any = None,
        checkpoint: Any = None,
        summary: Any = None,
        goal_context: Any = None,
        continuation_decision: dict[str, Any] | None = None,
        step_results: list[dict[str, Any]] | None = None,
        learning_signals: list[dict[str, Any]] | None = None,
    ) -> OrchestrationContext:
        current_step = None
        current_step_status = ""
        if plan is not None and getattr(plan, "current_step_id", None):
            current_step = getattr(plan, "current_step_id", None)
            steps = getattr(plan, "steps", [])
            for step in steps:
                if getattr(step, "step_id", None) == current_step:
                    current_step_status = getattr(getattr(step, "status", None), "value", "")
                    break
        recent_execution_receipt_ids: list[str] = []
        recent_repair_receipt_ids: list[str] = []
        for item in (step_results or [])[-5:]:
            if not isinstance(item, dict):
                continue
            execution_receipt = item.get("execution_receipt")
            if isinstance(execution_receipt, dict):
                receipt_id = str(execution_receipt.get("receipt_id", "")).strip()
                if receipt_id:
                    recent_execution_receipt_ids.append(receipt_id)
            repair_receipt = item.get("repair_receipt")
            if isinstance(repair_receipt, dict):
                receipt_id = str(repair_receipt.get("repair_receipt_id", "")).strip()
                if receipt_id:
                    recent_repair_receipt_ids.append(receipt_id)
        operational_summary = summary.as_dict() if hasattr(summary, "as_dict") else summary if isinstance(summary, dict) else {}
        goal_payload = None
        if goal_context is not None:
            if hasattr(goal_context, "as_dict"):
                goal_payload = goal_context.as_dict()
            elif isinstance(goal_context, dict):
                goal_payload = dict(goal_context)
            elif all(hasattr(goal_context, field_name) for field_name in ("goal_id", "description", "intent", "active_constraints", "success_criteria_descriptions", "stop_condition_descriptions", "status", "priority")):
                goal_payload = {
                    "goal_id": getattr(goal_context, "goal_id"),
                    "description": getattr(goal_context, "description"),
                    "intent": getattr(goal_context, "intent"),
                    "active_constraints": list(getattr(goal_context, "active_constraints")),
                    "success_criteria_descriptions": list(getattr(goal_context, "success_criteria_descriptions")),
                    "stop_condition_descriptions": list(getattr(goal_context, "stop_condition_descriptions")),
                    "status": getattr(goal_context, "status"),
                    "priority": getattr(goal_context, "priority"),
                    "prompt_block": goal_context.to_prompt_block() if hasattr(goal_context, "to_prompt_block") else "",
                }
        return OrchestrationContext.build(
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            plan_id=getattr(plan, "plan_id", None),
            plan_status=getattr(getattr(plan, "status", None), "value", str(getattr(plan, "status", ""))),
            current_step_id=current_step,
            current_step_status=current_step_status,
            continuation_decision_type=str((continuation_decision or {}).get("decision_type", "")),
            checkpoint_id=getattr(checkpoint, "checkpoint_id", None) or ((checkpoint or {}).get("checkpoint_id") if isinstance(checkpoint, dict) else None),
            checkpoint_status=getattr(getattr(checkpoint, "status", None), "value", str((checkpoint or {}).get("status", "")) if isinstance(checkpoint, dict) else ""),
            goal_id=getattr(plan, "goal_id", None) or (goal_payload or {}).get("goal_id"),
            goal_context=goal_payload,
            operational_summary=operational_summary if isinstance(operational_summary, dict) else {},
            action=dict(action),
            recent_execution_receipt_ids=recent_execution_receipt_ids,
            recent_repair_receipt_ids=recent_repair_receipt_ids,
            learning_signals=learning_signals or [],
            metadata={
                "selected_tool": str(action.get("selected_tool", "")),
                "selected_agent": str(action.get("selected_agent", "")),
                "action_type": str(action.get("action_type", "")),
                "goal_present": bool(goal_payload),
            },
        )
