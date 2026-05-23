from __future__ import annotations

from typing import Any, Callable

from .base_specialist import BaseSpecialist
from .models import ExecutionDecision


class ExecutorSpecialist(BaseSpecialist):
    def execute(
        self,
        *,
        goal_id: str | None,
        simulation_id: str | None,
        action: dict[str, Any],
        execute_callback: Callable[[], dict[str, Any]],
    ) -> ExecutionDecision:
        result = execute_callback()
        evidence_ids = [
            item
            for item in [
                str((result.get("execution_receipt") or {}).get("receipt_id", "")).strip(),
                str((result.get("repair_receipt") or {}).get("repair_receipt_id", "")).strip(),
            ]
            if item
        ]
        ok = bool(result.get("ok"))
        summary = "Delegated execution completed successfully." if ok else "Delegated execution returned a bounded failure."
        return ExecutionDecision.build(
            goal_id=goal_id,
            simulation_id=simulation_id,
            reasoning="Executor specialist wrapped the existing runtime execution path without creating a parallel engine.",
            confidence=0.9 if ok else 0.72,
            executed_step_id=str(action.get("step_id", "")) or None,
            execution_summary=summary,
            evidence_ids=evidence_ids,
            result=result,
            metadata={
                "selected_tool": action.get("selected_tool"),
                "selected_agent": action.get("selected_agent"),
                "delegated_execution": True,
            },
        )
