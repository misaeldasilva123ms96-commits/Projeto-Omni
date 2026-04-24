from __future__ import annotations

from typing import Any, Callable

from brain.runtime.execution.strategy_executor_base import StrategyExecutorBase
from brain.runtime.execution.strategy_models import StrategyExecutionRequest, StrategyExecutionResult


class DirectResponseExecutor(StrategyExecutorBase):
    strategy_name = "DIRECT_RESPONSE"

    def execute(
        self,
        request: StrategyExecutionRequest,
        compat_execute: Callable[[], dict[str, Any]] | None = None,
        node_execute: Callable[[], dict[str, Any]] | None = None,
        local_tool_execute: Callable[[], dict[str, Any]] | None = None,
        planner_execute: Callable[[], dict[str, Any]] | None = None,
    ) -> StrategyExecutionResult:
        direct_response = str(request.metadata.get("direct_response", "") or "").strip()
        if direct_response:
            raw_result = {
                "response": direct_response,
                "intent": request.routing_decision.get("intent", ""),
                "delegates": [],
                "agent_trace": [],
                "memory_signal": {},
                "metadata": {"execution_path": "direct_memory"},
            }
            trace = self.build_trace(
                request,
                status="success",
                execution_trace_summary="Direct response executor returned the precomputed direct-memory answer.",
            )
            return StrategyExecutionResult(
                selected_strategy=request.selected_strategy,
                executor_used="direct_response_executor",
                status="success",
                response_text=direct_response,
                raw_result=raw_result,
                trace=trace,
                manifest_driven_execution=True,
                response_synthesis_mode=trace.response_synthesis_mode,
            )
        raw_result, execution_path_used, failure_reason = self._execute_preferred_path(
            request,
            compat_execute=compat_execute,
            node_execute=node_execute,
            local_tool_execute=local_tool_execute,
            planner_execute=planner_execute,
        )
        if raw_result is None:
            return self.safe_fallback(request, reason=failure_reason or "direct_execution_callback_missing")
        response_text = str(raw_result.get("response", "") or "").strip() or request.fallback_response
        trace = self.build_trace(
            request,
            status="success",
            execution_trace_summary=(
                "Direct response executor used the primary node execution path."
                if execution_path_used == "node_execution"
                else "Direct response executor used the primary local tool execution path."
                if execution_path_used == "local_tool_execution"
                else "Direct response executor used the primary planner execution path."
                if execution_path_used == "planner_execution"
                else "Direct response executor used the compatibility runtime path."
            ),
            metadata={"execution_path_used": execution_path_used or "compatibility_execution"},
        )
        return StrategyExecutionResult(
            selected_strategy=request.selected_strategy,
            executor_used="direct_response_executor",
            status="success",
            response_text=response_text,
            raw_result=raw_result,
            trace=trace,
            manifest_driven_execution=True,
            response_synthesis_mode=trace.response_synthesis_mode,
        )
