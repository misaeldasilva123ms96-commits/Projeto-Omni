from __future__ import annotations

from typing import Any

from .models import LearningSourceType


class RuntimeArtifactIngestor:
    def collect(
        self,
        *,
        action: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
        plan: Any = None,
        checkpoint: Any = None,
        summary: Any = None,
        continuation_evaluation: dict[str, Any] | None = None,
        continuation_decision: dict[str, Any] | None = None,
    ) -> list[tuple[LearningSourceType, dict[str, Any], dict[str, Any]]]:
        artifacts: list[tuple[LearningSourceType, dict[str, Any], dict[str, Any]]] = []
        context = {
            "action": action or {},
            "goal_id": getattr(plan, "goal_id", None) or ((action or {}).get("goal_id") if isinstance(action, dict) else None),
            "goal_description": getattr(plan, "metadata", {}).get("goal_description", "") if plan is not None else "",
            "plan_id": getattr(plan, "plan_id", None),
            "task_id": getattr(plan, "task_id", None),
            "session_id": getattr(plan, "session_id", None),
            "run_id": getattr(plan, "run_id", None),
        }
        if isinstance(result, dict):
            execution_receipt = result.get("execution_receipt")
            if isinstance(execution_receipt, dict):
                artifacts.append((LearningSourceType.EXECUTION_RECEIPT, execution_receipt, context))
            repair_receipt = result.get("repair_receipt")
            if isinstance(repair_receipt, dict):
                artifacts.append((LearningSourceType.REPAIR_RECEIPT, repair_receipt, context))
        if checkpoint is not None:
            payload = checkpoint.as_dict() if hasattr(checkpoint, "as_dict") else checkpoint
            if isinstance(payload, dict):
                artifacts.append((LearningSourceType.PLAN_CHECKPOINT, payload, context))
        if summary is not None:
            payload = summary.as_dict() if hasattr(summary, "as_dict") else summary
            if isinstance(payload, dict):
                artifacts.append((LearningSourceType.OPERATIONAL_SUMMARY, payload, context))
        if isinstance(continuation_evaluation, dict):
            artifacts.append((LearningSourceType.CONTINUATION_EVALUATION, continuation_evaluation, context))
        if isinstance(continuation_decision, dict):
            artifacts.append((LearningSourceType.CONTINUATION_DECISION, continuation_decision, context))
        return artifacts
