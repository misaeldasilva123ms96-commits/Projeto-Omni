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
        if compat_execute is None:
            return self.safe_fallback(request, reason="reasoning_execution_callback_missing")
        raw_result = dict(compat_execute() or {})
        response_text = str(raw_result.get("response", "") or "").strip() or request.fallback_response
        trace = self.build_trace(
            request,
            status="success",
            execution_trace_summary="Multi-step reasoning executor ran through the compatibility runtime path within bounded depth.",
            metadata={"step_count": len(step_plan), "max_reasoning_steps": max_steps},
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

