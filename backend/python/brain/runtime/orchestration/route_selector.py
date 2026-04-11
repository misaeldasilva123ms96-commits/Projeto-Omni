from __future__ import annotations

from typing import Any

from .capability_registry import CapabilityRegistry
from .models import OrchestrationContext, OrchestrationDecision, OrchestrationPolicy, OrchestrationRoute


class RouteSelector:
    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry

    def select(
        self,
        *,
        context: OrchestrationContext,
        policy: OrchestrationPolicy,
        engineering_tool: bool,
    ) -> OrchestrationDecision:
        continuation = context.continuation_decision_type
        action_type = str(context.action.get("action_type", "")).strip() or self._infer_action_type(context.action)
        selected_tool = str(context.action.get("selected_tool", "")).strip()
        route = OrchestrationRoute.DIRECT_EXECUTION
        capability = self.registry.default_for_action(
            action_type=action_type,
            selected_tool=selected_tool,
            engineering_tool=engineering_tool,
        )
        reason_code = "default_runtime_execution"
        reason_summary = "Route the action through the default bounded runtime execution path."
        confidence = capability.confidence_score

        if continuation == "pause_plan":
            route = OrchestrationRoute.PAUSE_PLAN
            capability = self.registry.get("continuation_management") or capability
            reason_code = "continuation_pause_authoritative"
            reason_summary = "Continuation marked the plan as paused, so orchestration preserves that route."
            confidence = 0.96
        elif continuation == "escalate_failure":
            route = OrchestrationRoute.ESCALATE_FAILURE
            capability = self.registry.get("continuation_management") or capability
            reason_code = "continuation_escalation_authoritative"
            reason_summary = "Continuation escalation is authoritative for unsafe execution states."
            confidence = 0.97
        elif continuation == "complete_plan":
            route = OrchestrationRoute.COMPLETE_PLAN
            capability = self.registry.get("continuation_management") or capability
            reason_code = "continuation_completion_authoritative"
            reason_summary = "Continuation marked the plan complete, so orchestration closes the route cleanly."
            confidence = 0.98
        elif continuation == "rebuild_plan":
            route = OrchestrationRoute.PLAN_REBUILD
            capability = self.registry.get("planning_execution") or capability
            reason_code = "continuation_rebuild_remaining_segment"
            reason_summary = "Continuation requested a bounded plan rebuild for the remaining segment."
            confidence = 0.84
        elif continuation == "retry_step":
            route = OrchestrationRoute.RETRY_EXECUTION
            reason_code = "continuation_retry_within_budget"
            reason_summary = "Continuation approved a bounded retry for the current operational step."
            confidence = 0.82
        elif selected_tool in {"filesystem_read", "read_file", "grep_search", "glob_search", "code_search"} and policy.allow_analysis_routing:
            route = OrchestrationRoute.ANALYSIS_STEP
            capability = self.registry.get("analysis_routine") or capability
            reason_code = "read_or_analysis_path"
            reason_summary = "Read-heavy work is routed through the bounded analysis path."
            confidence = 0.78
        elif engineering_tool and policy.allow_tool_delegation:
            route = OrchestrationRoute.TOOL_DELEGATION
            capability = self.registry.get("engineering_tool_execution") or capability
            reason_code = "engineering_tool_route"
            reason_summary = "The action maps to an approved engineering tool execution path."
            confidence = 0.86

        return OrchestrationDecision.build(
            context_id=context.context_id,
            plan_id=context.plan_id,
            task_id=context.task_id,
            step_id=context.current_step_id or str(context.action.get("step_id", "")).strip() or None,
            selected_capability_id=capability.capability_id,
            route=route,
            reason_code=reason_code,
            reason_summary=reason_summary,
            confidence_score=confidence,
            linked_execution_receipt_ids=context.recent_execution_receipt_ids,
            linked_repair_receipt_ids=context.recent_repair_receipt_ids,
            metadata={
                "subsystem": capability.subsystem,
                "selected_tool": selected_tool,
                "action_type": action_type,
            },
        )

    @staticmethod
    def _infer_action_type(action: dict[str, Any]) -> str:
        selected_tool = str(action.get("selected_tool", "")).strip()
        if selected_tool in {"filesystem_read", "read_file", "grep_search", "glob_search", "code_search"}:
            return "read"
        if selected_tool in {"filesystem_write", "filesystem_patch_set", "write_file"}:
            return "mutate"
        if selected_tool in {"verification_runner", "test_runner"}:
            return "verify"
        return "execute"
