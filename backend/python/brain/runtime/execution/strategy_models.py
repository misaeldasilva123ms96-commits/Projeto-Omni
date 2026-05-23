from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class StrategyExecutionTrace:
    selected_strategy: str
    executor_used: str
    status: str
    manifest_driven_execution: bool
    governance_blocked: bool = False
    governance_downgrade_applied: bool = False
    fallback_applied: bool = False
    downgraded: bool = False
    blocked_reason: str = ""
    fallback_reason: str = ""
    response_synthesis_mode: str = "direct"
    observability_tags: list[str] = field(default_factory=list)
    execution_trace_summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class StrategyExecutionContext:
    session_id: str
    run_id: str
    task_id: str
    current_runtime_mode: str
    current_runtime_reason: str
    direct_memory_hit: bool = False
    node_runtime_available: bool = True
    current_provider_path: str = ""
    max_reasoning_steps: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class StrategyExecutionRequest:
    selected_strategy: str
    manifest_id: str
    manifest: dict[str, Any]
    oil_summary: dict[str, Any]
    routing_decision: dict[str, Any]
    ranked_decision: dict[str, Any]
    tool_metadata: list[dict[str, Any]] = field(default_factory=list)
    governance_blocked: bool = False
    governance_flags: dict[str, Any] = field(default_factory=dict)
    fallback_allowed: bool = True
    fallback_response: str = ""
    node_fallback_response: str = ""
    context: StrategyExecutionContext | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.context is not None:
            payload["context"] = self.context.as_dict()
        return payload


@dataclass(slots=True)
class StrategyExecutionResult:
    selected_strategy: str
    executor_used: str
    status: str
    response_text: str
    raw_result: dict[str, Any] = field(default_factory=dict)
    trace: StrategyExecutionTrace | None = None
    blocked: bool = False
    downgraded: bool = False
    fallback_applied: bool = False
    governance_downgrade_applied: bool = False
    manifest_driven_execution: bool = True
    response_synthesis_mode: str = "direct"
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["trace"] = self.trace.as_dict() if self.trace is not None else None
        return payload

