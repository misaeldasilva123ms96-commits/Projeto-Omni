from __future__ import annotations

from typing import Any, Callable

from .response_synthesis import synthesize_strategy_response
from .strategy_executors import (
    DirectResponseExecutor,
    MultiStepReasoningExecutor,
    NodeRuntimeDelegationExecutor,
    SafeFallbackExecutor,
    ToolAssistedExecutor,
)
from .strategy_models import StrategyExecutionRequest, StrategyExecutionResult


class StrategyDispatcher:
    def __init__(self) -> None:
        self.executors = [
            DirectResponseExecutor(),
            ToolAssistedExecutor(),
            MultiStepReasoningExecutor(),
            NodeRuntimeDelegationExecutor(),
            SafeFallbackExecutor(),
        ]
        self.safe_fallback_executor = SafeFallbackExecutor()

    def dispatch(
        self,
        request: StrategyExecutionRequest,
        *,
        compat_execute: Callable[[], dict[str, Any]] | None = None,
    ) -> StrategyExecutionResult:
        executor = self._find_executor(request.selected_strategy)
        try:
            result = executor.execute(request, compat_execute=compat_execute)
        except Exception as exc:
            result = self.safe_fallback_executor.safe_fallback(
                request,
                reason=f"strategy_dispatch_exception:{str(exc)[:120]}",
            )
            result.error = str(exc)[:400]
        response_text, synthesis_mode = synthesize_strategy_response(request, result)
        result.response_text = response_text
        result.response_synthesis_mode = synthesis_mode
        if result.trace is not None:
            result.trace.response_synthesis_mode = synthesis_mode
            result.trace.metadata.setdefault("selected_strategy", request.selected_strategy)
        result.metadata.setdefault("selected_strategy", request.selected_strategy)
        result.metadata.setdefault("executor_used", result.executor_used)
        result.metadata.setdefault("strategy_execution_status", result.status)
        return result

    def _find_executor(self, strategy: str):
        normalized = str(strategy or "SAFE_FALLBACK").strip().upper()
        for executor in self.executors:
            if executor.strategy_name == normalized:
                return executor
        return self.safe_fallback_executor
