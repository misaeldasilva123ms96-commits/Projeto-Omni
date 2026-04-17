from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .strategy_trace import StrategyAdaptationTrace

ExecutionStrategyMode = Literal["fast", "deep", "critical"]
ExecutionStrategyPath = Literal["direct", "swarm", "guarded"]
ValidationLevel = Literal["low", "medium", "high"]


@dataclass(slots=True)
class ExecutionStrategy:
    """Phase 35 — bounded execution strategy (not a task plan)."""

    mode: ExecutionStrategyMode
    path: ExecutionStrategyPath
    validation_level: ValidationLevel
    reasoning_depth: int
    risk_tolerance: float

    def __post_init__(self) -> None:
        self.reasoning_depth = max(1, min(5, int(self.reasoning_depth)))
        self.risk_tolerance = max(0.0, min(1.0, float(self.risk_tolerance)))

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "path": self.path,
            "validation_level": self.validation_level,
            "reasoning_depth": self.reasoning_depth,
            "risk_tolerance": self.risk_tolerance,
        }


@dataclass(slots=True)
class StrategyDecision:
    """Audit-friendly strategy choice with explicit fallback (no self-mutation)."""

    selected_strategy: ExecutionStrategy
    fallback_strategy: ExecutionStrategy
    reason: str
    confidence: float
    signals_used: list[str]
    trace: StrategyAdaptationTrace
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "selected_strategy": self.selected_strategy.as_dict(),
            "fallback_strategy": self.fallback_strategy.as_dict(),
            "reason": self.reason[:800],
            "confidence": max(0.0, min(1.0, float(self.confidence))),
            "signals_used": list(self.signals_used),
            "trace": self.trace.as_dict(),
            "metadata": dict(self.metadata),
        }
