from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable

from .strategy_models import StrategyExecutionRequest, StrategyExecutionResult, StrategyExecutionTrace


class StrategyExecutorBase(ABC):
    strategy_name = "SAFE_FALLBACK"

    def can_execute(self, request: StrategyExecutionRequest) -> bool:
        return str(request.selected_strategy or "").strip().upper() == self.strategy_name

    @abstractmethod
    def execute(
        self,
        request: StrategyExecutionRequest,
        compat_execute: Callable[[], dict[str, Any]] | None = None,
    ) -> StrategyExecutionResult:
        raise NotImplementedError

    def build_trace(
        self,
        request: StrategyExecutionRequest,
        *,
        status: str,
        blocked_reason: str = "",
        fallback_reason: str = "",
        governance_blocked: bool = False,
        governance_downgrade_applied: bool = False,
        fallback_applied: bool = False,
        downgraded: bool = False,
        response_synthesis_mode: str = "direct",
        execution_trace_summary: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> StrategyExecutionTrace:
        manifest_tags = list(request.manifest.get("observability_tags", []) or [])
        return StrategyExecutionTrace(
            selected_strategy=str(request.selected_strategy or ""),
            executor_used=self.strategy_name.lower(),
            status=status,
            manifest_driven_execution=bool(request.manifest),
            governance_blocked=governance_blocked,
            governance_downgrade_applied=governance_downgrade_applied,
            fallback_applied=fallback_applied,
            downgraded=downgraded,
            blocked_reason=blocked_reason,
            fallback_reason=fallback_reason,
            response_synthesis_mode=response_synthesis_mode,
            observability_tags=manifest_tags,
            execution_trace_summary=execution_trace_summary or f"{self.strategy_name} executor completed with status={status}",
            metadata=dict(metadata or {}),
        )

    def safe_fallback(
        self,
        request: StrategyExecutionRequest,
        *,
        reason: str,
        response_text: str | None = None,
        blocked: bool = False,
        governance_downgrade_applied: bool = False,
        downgraded: bool = False,
    ) -> StrategyExecutionResult:
        fallback_response = str(
            response_text
            or request.fallback_response
            or request.node_fallback_response
            or "Nao consegui processar isso ainda, mas estou aprendendo."
        ).strip()
        raw_result = {
            "response": fallback_response,
            "intent": request.routing_decision.get("intent", ""),
            "delegates": [],
            "agent_trace": [],
            "memory_signal": {},
            "metadata": {
                "strategy_execution_fallback": True,
                "fallback_reason": reason,
            },
        }
        trace = self.build_trace(
            request,
            status="blocked" if blocked else "fallback",
            blocked_reason=reason if blocked else "",
            fallback_reason=reason,
            governance_blocked=blocked,
            governance_downgrade_applied=governance_downgrade_applied,
            fallback_applied=True,
            downgraded=downgraded,
            execution_trace_summary=f"{self.strategy_name} executor degraded to safe fallback due to {reason}",
            metadata={"fallback_strategy": request.manifest.get("fallback_strategy", "SAFE_FALLBACK")},
        )
        return StrategyExecutionResult(
            selected_strategy=str(request.selected_strategy or self.strategy_name),
            executor_used=self.strategy_name.lower(),
            status="blocked" if blocked else "fallback",
            response_text=fallback_response,
            raw_result=raw_result,
            trace=trace,
            blocked=blocked,
            downgraded=downgraded,
            fallback_applied=True,
            governance_downgrade_applied=governance_downgrade_applied,
            manifest_driven_execution=bool(request.manifest),
            response_synthesis_mode=trace.response_synthesis_mode,
            error=reason,
            metadata={"fallback_reason": reason},
        )

