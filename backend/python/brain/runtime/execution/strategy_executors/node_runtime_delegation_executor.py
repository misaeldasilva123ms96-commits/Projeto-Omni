from __future__ import annotations

from typing import Any, Callable

from brain.runtime.execution.strategy_executor_base import StrategyExecutorBase
from brain.runtime.execution.strategy_models import StrategyExecutionRequest, StrategyExecutionResult


class NodeRuntimeDelegationExecutor(StrategyExecutorBase):
    strategy_name = "NODE_RUNTIME_DELEGATION"

    def execute(
        self,
        request: StrategyExecutionRequest,
        compat_execute: Callable[[], dict[str, Any]] | None = None,
        node_execute: Callable[[], dict[str, Any]] | None = None,
        local_tool_execute: Callable[[], dict[str, Any]] | None = None,
        planner_execute: Callable[[], dict[str, Any]] | None = None,
    ) -> StrategyExecutionResult:
        node_runtime_available = bool(request.context.node_runtime_available) if request.context is not None else False
        if request.governance_blocked:
            return self.safe_fallback(request, reason="governance_blocked", blocked=True)
        if not node_runtime_available:
            return self.safe_fallback(request, reason="node_runtime_unavailable", response_text=request.node_fallback_response)
        raw_result, execution_path_used, failure_reason = self._execute_preferred_path(
            request,
            compat_execute=compat_execute,
            node_execute=node_execute,
            local_tool_execute=local_tool_execute,
            planner_execute=planner_execute,
        )
        if raw_result is None:
            return self.safe_fallback(
                request,
                reason=failure_reason or "node_runtime_callback_missing",
                response_text=request.node_fallback_response,
            )
        response_text = str(raw_result.get("response", "") or "").strip() or request.node_fallback_response or request.fallback_response
        trace = self.build_trace(
            request,
            status="success",
            execution_trace_summary=(
                "Node runtime delegation executor used the primary node execution path."
                if execution_path_used == "node_execution"
                else "Node runtime delegation executor used the compatibility runtime path with node bridge available."
            ),
            metadata={
                "delegation_path": "node_runtime_bridge",
                "execution_path_used": execution_path_used or "compatibility_execution",
            },
        )
        return StrategyExecutionResult(
            selected_strategy=request.selected_strategy,
            executor_used="node_runtime_delegation_executor",
            status="success",
            response_text=response_text,
            raw_result=raw_result,
            trace=trace,
            manifest_driven_execution=True,
            response_synthesis_mode=trace.response_synthesis_mode,
        )
