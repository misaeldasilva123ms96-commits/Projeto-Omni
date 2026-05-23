from __future__ import annotations

from .base_specialist import BaseSpecialist
from .models import DecisionStatus, RepairDecision


class RepairSpecialist(BaseSpecialist):
    def advise(
        self,
        *,
        goal_id: str | None,
        result: dict,
        simulation_id: str | None = None,
        simulation_route: str | None = None,
        max_repairs: int = 2,
        current_repairs: int = 0,
    ) -> RepairDecision | None:
        if result.get("ok"):
            return None
        history = self.recall_memory(
            event_type="continuation_outcome",
            progress=float(result.get("progress_score", 0.0) or 0.0),
            limit=8,
        )
        poor_history = len([item for item in history if getattr(item, "outcome", "") in {"escalate_failure", "rebuild_plan"}])
        require_replan = poor_history >= 2 or simulation_route == "replan"
        if current_repairs >= max_repairs:
            status = DecisionStatus.DEFERRED
            strategy = "repair_budget_exhausted"
            impact = "Repair budget is exhausted, so a replan or escalation is safer."
        else:
            status = DecisionStatus.DECIDED
            strategy = "bounded_template_repair"
            impact = "A bounded repair may recover the current failure without changing governance boundaries."
        if require_replan:
            strategy = "replan_after_repair_history"
            impact = "Repair history suggests the remaining plan segment likely needs bounded replanning."
        return RepairDecision.build(
            goal_id=goal_id,
            simulation_id=simulation_id,
            reasoning="Repair specialist used bounded repair history and optional simulation guidance to estimate the safest next repair posture.",
            confidence=0.7 if require_replan else 0.62,
            recommended_strategy=strategy,
            estimated_impact=impact,
            require_replan=require_replan,
            repair_history_score=min(1.0, poor_history / 4.0),
            status=status,
            metadata={
                "current_repairs": current_repairs,
                "max_repairs": max_repairs,
                "simulation_route": simulation_route,
            },
        )
