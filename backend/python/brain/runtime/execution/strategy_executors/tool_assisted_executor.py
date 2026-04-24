from __future__ import annotations

from typing import Any, Callable

from brain.runtime.execution.strategy_executor_base import StrategyExecutorBase
from brain.runtime.execution.strategy_models import StrategyExecutionRequest, StrategyExecutionResult


class ToolAssistedExecutor(StrategyExecutorBase):
    strategy_name = "TOOL_ASSISTED"

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
        high_risk_tools = [
            item for item in list(request.tool_metadata or []) if str(item.get("risk_level", "")).lower() in {"high", "critical"}
        ]
        if high_risk_tools:
            return self.safe_fallback(
                request,
                reason="high_risk_tool_downgraded",
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
            return self.safe_fallback(request, reason=failure_reason or "tool_execution_callback_missing")
        response_text = str(raw_result.get("response", "") or "").strip() or request.fallback_response
        trace = self.build_trace(
            request,
            status="success",
            execution_trace_summary=(
                "Tool-assisted executor used the primary local tool execution path."
                if execution_path_used == "local_tool_execution"
                else "Tool-assisted executor used the primary node execution path."
                if execution_path_used == "node_execution"
                else "Tool-assisted executor used the primary planner execution path."
                if execution_path_used == "planner_execution"
                else "Tool-assisted executor used the compatibility runtime path with manifest-selected tool metadata."
            ),
            metadata={
                "selected_tools": [item.get("name", "") for item in request.tool_metadata],
                "execution_path_used": execution_path_used or "compatibility_execution",
            },
        )
        return StrategyExecutionResult(
            selected_strategy=request.selected_strategy,
            executor_used="tool_assisted_executor",
            status="success",
            response_text=response_text,
            raw_result=raw_result,
            trace=trace,
            manifest_driven_execution=True,
            response_synthesis_mode=trace.response_synthesis_mode,
        )
