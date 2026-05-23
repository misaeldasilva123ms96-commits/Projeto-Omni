from __future__ import annotations

from typing import Any, Callable

from brain.runtime.execution.strategy_executor_base import StrategyExecutorBase
from brain.runtime.execution.strategy_models import StrategyExecutionRequest, StrategyExecutionResult


class MultiStepReasoningExecutor(StrategyExecutorBase):
    strategy_name = "MULTI_STEP_REASONING"

    def execute(
        self,
        request: StrategyExecutionRequest,
        compat_execute: Callable[[], dict[str, Any]] | None = None,
        node_execute: Callable[[], dict[str, Any]] | None = None,
        local_tool_execute: Callable[[], dict[str, Any]] | None = None,
        planner_execute: Callable[[], dict[str, Any]] | None = None,
    ) -> StrategyExecutionResult:
        if request.governance_blocked:
            return self.safe_fallback(request, reason="governance_blocked", blocked=True)
        step_plan = list(request.manifest.get("step_plan", []) or [])
        max_steps = int((request.context.max_reasoning_steps if request.context is not None else 3) or 3)
        if len(step_plan) > max_steps:
            return self.safe_fallback(
                request,
                reason="reasoning_depth_exceeded",
                governance_downgrade_applied=True,
                downgraded=True,
            )
        raw_result, execution_path_used, failure_reason = self._execute_preferred_path(
            request,
            compat_execute=compat_execute,
            node_execute=node_execute,
            local_tool_execute=local_tool_execute,
            planner_execute=planner_execute,
        )
        if raw_result is None:
            return self.safe_fallback(request, reason=failure_reason or "reasoning_execution_callback_missing")
        response_text = str(raw_result.get("response", "") or "").strip() or request.fallback_response
        trace = self.build_trace(
            request,
            status="success",
            execution_trace_summary=(
                "Multi-step reasoning executor used the primary planner execution path within bounded depth."
                if execution_path_used == "planner_execution"
                else "Multi-step reasoning executor used the primary node execution path within bounded depth."
                if execution_path_used == "node_execution"
                else "Multi-step reasoning executor ran through the compatibility runtime path within bounded depth."
            ),
            metadata={
                "step_count": len(step_plan),
                "max_reasoning_steps": max_steps,
                "execution_path_used": execution_path_used or "compatibility_execution",
            },
        )
        return StrategyExecutionResult(
            selected_strategy=request.selected_strategy,
            executor_used="multi_step_reasoning_executor",
            status="success",
            response_text=response_text,
            raw_result=raw_result,
            trace=trace,
            manifest_driven_execution=True,
            response_synthesis_mode=trace.response_synthesis_mode,
        )
