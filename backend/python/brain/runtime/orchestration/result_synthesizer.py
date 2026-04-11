from __future__ import annotations

from typing import Any

from .models import ConflictResolution, OrchestrationContext, OrchestrationDecision, OrchestrationResult


class ResultSynthesizer:
    def synthesize(
        self,
        *,
        context: OrchestrationContext,
        decision: OrchestrationDecision,
        resolution: ConflictResolution,
        primary_result: dict[str, Any] | None,
    ) -> OrchestrationResult:
        primary_result = dict(primary_result or {})
        artifact_references = {
            "execution_receipt_ids": list(context.recent_execution_receipt_ids),
            "repair_receipt_ids": list(context.recent_repair_receipt_ids),
            "checkpoint_id": context.checkpoint_id,
            "plan_id": context.plan_id,
        }
        summary = (
            f"Route {decision.route.value} selected via {decision.selected_capability_id}. "
            f"{resolution.reason_summary}"
        )
        return OrchestrationResult.build(
            context_id=context.context_id,
            decision_id=decision.decision_id,
            route=decision.route,
            synthesized_summary=summary,
            artifact_references=artifact_references,
            primary_result=primary_result,
            metadata={
                "resolution": resolution.as_dict(),
                "selected_capability_id": decision.selected_capability_id,
                "selected_subsystem": decision.metadata.get("subsystem"),
            },
        )
