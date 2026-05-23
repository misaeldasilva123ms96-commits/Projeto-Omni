from __future__ import annotations

from typing import Any, Callable

from brain.runtime.execution.strategy_executor_base import StrategyExecutorBase
from brain.runtime.execution.strategy_models import StrategyExecutionRequest, StrategyExecutionResult


class SafeFallbackExecutor(StrategyExecutorBase):
    strategy_name = "SAFE_FALLBACK"

    def execute(
        self,
        request: StrategyExecutionRequest,
        compat_execute: Callable[[], dict[str, Any]] | None = None,
    ) -> StrategyExecutionResult:
        return self.safe_fallback(request, reason="safe_fallback_strategy_selected")

