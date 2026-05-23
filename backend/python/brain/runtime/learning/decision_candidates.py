from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from brain.runtime.tooling.tool_registry_extensions import get_tool_metadata


@dataclass(slots=True)
class DecisionCandidate:
    strategy: str
    confidence: float
    requires_tools: bool
    requires_node_runtime: bool
    expected_cost: str
    expected_latency: str
    risk_level: str
    source: str
    rationale: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class DecisionCandidateBuilder:
    """Constructs bounded decision candidates from real runtime state."""

    def build(
        self,
        *,
        ambiguity_assessment: Any,
        routing_decision: Any,
        oil_summary: dict[str, Any] | None,
        execution_manifest: dict[str, Any] | None,
    ) -> list[DecisionCandidate]:
        oil_summary = dict(oil_summary or {})
        execution_manifest = dict(execution_manifest or {})
        selected_tools = [str(item).strip() for item in execution_manifest.get("selected_tools", []) if str(item).strip()]
        candidates: list[DecisionCandidate] = []
        for strategy in list(getattr(ambiguity_assessment, "candidate_strategies", []) or []):
            candidate = self._build_candidate(
                strategy=strategy,
                routing_decision=routing_decision,
                oil_summary=oil_summary,
                execution_manifest=execution_manifest,
                selected_tools=selected_tools,
            )
            candidates.append(candidate)
        if not candidates:
            candidates.append(
                self._build_candidate(
                    strategy=str(getattr(routing_decision, "strategy", "") or "DIRECT_RESPONSE"),
                    routing_decision=routing_decision,
                    oil_summary=oil_summary,
                    execution_manifest=execution_manifest,
                    selected_tools=selected_tools,
                )
            )
        return candidates

    def _build_candidate(
        self,
        *,
        strategy: str,
        routing_decision: Any,
        oil_summary: dict[str, Any],
        execution_manifest: dict[str, Any],
        selected_tools: list[str],
    ) -> DecisionCandidate:
        deterministic_strategy = str(getattr(routing_decision, "strategy", "") or "").strip()
        base_confidence = float(getattr(routing_decision, "confidence", 0.0) or 0.0)
        risk_level = str(getattr(routing_decision, "risk_level", "low") or "low").strip().lower()
        requires_tools = strategy in {"TOOL_ASSISTED", "NODE_RUNTIME_DELEGATION"}
        requires_node_runtime = strategy == "NODE_RUNTIME_DELEGATION"
        expected_cost, expected_latency = self._expected_cost_latency(
            strategy=strategy,
            selected_tools=selected_tools,
        )
        confidence = base_confidence if strategy == deterministic_strategy else max(0.35, base_confidence - 0.12)
        rationale = self._rationale_for_strategy(
            strategy=strategy,
            routing_decision=routing_decision,
            oil_summary=oil_summary,
            execution_manifest=execution_manifest,
        )
        return DecisionCandidate(
            strategy=strategy,
            confidence=round(max(0.0, min(1.0, confidence)), 4),
            requires_tools=requires_tools,
            requires_node_runtime=requires_node_runtime,
            expected_cost=expected_cost,
            expected_latency=expected_latency,
            risk_level="low" if strategy == "SAFE_FALLBACK" else risk_level,
            source="rule",
            rationale=rationale,
            metadata={
                "selected_tools": list(selected_tools),
                "deterministic_strategy": deterministic_strategy,
                "desired_output": str(oil_summary.get("desired_output", "") or ""),
            },
        )

    @staticmethod
    def _expected_cost_latency(*, strategy: str, selected_tools: list[str]) -> tuple[str, str]:
        if strategy == "SAFE_FALLBACK":
            return "low", "low"
        if strategy == "DIRECT_RESPONSE":
            return "low", "low"
        if strategy == "MULTI_STEP_REASONING":
            return "medium", "medium"
        if strategy == "NODE_RUNTIME_DELEGATION":
            return "medium", "medium"
        if selected_tools:
            tool_meta = get_tool_metadata(selected_tools[0])
            return str(tool_meta.estimated_cost), str(tool_meta.latency_class)
        return "medium", "medium"

    @staticmethod
    def _rationale_for_strategy(
        *,
        strategy: str,
        routing_decision: Any,
        oil_summary: dict[str, Any],
        execution_manifest: dict[str, Any],
    ) -> str:
        if strategy == "DIRECT_RESPONSE":
            return "Direct path favored due to low-complexity conversational shape."
        if strategy == "MULTI_STEP_REASONING":
            return "Reasoning path favored because the request implies staged analysis or planning."
        if strategy == "TOOL_ASSISTED":
            return "Tool path favored due to explicit operational or code-shaping request."
        if strategy == "NODE_RUNTIME_DELEGATION":
            return "Node runtime path favored because the bridge/runtime surface appears relevant."
        if strategy == "SAFE_FALLBACK":
            return "Fallback path favored to preserve safety and compatibility under uncertainty."
        return str(getattr(routing_decision, "internal_reasoning_hint", "") or execution_manifest.get("summary_rationale", "") or "bounded strategy candidate")

