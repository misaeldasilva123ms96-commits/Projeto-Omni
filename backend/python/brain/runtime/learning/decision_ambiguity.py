from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


HIGH_RISK_LEVELS = {"high", "critical"}


@dataclass(slots=True)
class AmbiguityAssessment:
    is_ambiguous: bool
    ambiguity_score: float
    candidate_strategies: list[str]
    reason_codes: list[str] = field(default_factory=list)
    safe_to_rank: bool = True

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class DecisionAmbiguityDetector:
    """Conservative ambiguity detector for bounded strategy ranking."""

    def detect(
        self,
        *,
        routing_decision: Any,
        oil_summary: dict[str, Any] | None,
        execution_manifest: dict[str, Any] | None,
    ) -> AmbiguityAssessment:
        oil_summary = dict(oil_summary or {})
        execution_manifest = dict(execution_manifest or {})
        deterministic_strategy = str(getattr(routing_decision, "strategy", "") or "DIRECT_RESPONSE").strip()
        confidence = float(getattr(routing_decision, "confidence", 0.0) or 0.0)
        risk_level = str(getattr(routing_decision, "risk_level", "") or "").strip().lower()
        urgency = str(oil_summary.get("urgency", "medium") or "medium").strip().lower()
        desired_output = str(oil_summary.get("desired_output", "") or "").strip().lower()
        output_mode = str(execution_manifest.get("output_mode", "direct") or "direct").strip().lower()
        candidate_strategies = [deterministic_strategy]
        reason_codes: list[str] = []
        safe_to_rank = True

        if risk_level in HIGH_RISK_LEVELS:
            safe_to_rank = False
            reason_codes.append("risk_level_high")
        if urgency == "high":
            safe_to_rank = False
            reason_codes.append("urgency_high")

        if deterministic_strategy == "DIRECT_RESPONSE":
            if confidence < 0.75 or output_mode == "hybrid" or desired_output in {"analysis", "plan", "execution_plan"}:
                candidate_strategies.append("MULTI_STEP_REASONING")
                reason_codes.append("direct_vs_reasoning")
        elif deterministic_strategy == "TOOL_ASSISTED":
            if bool(getattr(routing_decision, "requires_node_runtime", False)) or "node_runtime_delegation" in list(
                execution_manifest.get("safety_notes", []) or []
            ):
                candidate_strategies.append("NODE_RUNTIME_DELEGATION")
                reason_codes.append("tool_vs_node")
        elif deterministic_strategy == "NODE_RUNTIME_DELEGATION":
            if not bool(getattr(routing_decision, "requires_node_runtime", False)):
                candidate_strategies.append("TOOL_ASSISTED")
                reason_codes.append("node_vs_tool")
        elif deterministic_strategy == "MULTI_STEP_REASONING":
            if bool(getattr(routing_decision, "fallback_allowed", True)) and (
                confidence < 0.7 or urgency == "high" or risk_level == "medium"
            ):
                candidate_strategies.append("SAFE_FALLBACK")
                reason_codes.append("reasoning_vs_fallback")
        elif deterministic_strategy == "SAFE_FALLBACK":
            if confidence >= 0.78 and urgency != "high":
                candidate_strategies.append("MULTI_STEP_REASONING")
                reason_codes.append("fallback_vs_reasoning")

        deduped: list[str] = []
        for strategy in candidate_strategies:
            if strategy and strategy not in deduped:
                deduped.append(strategy)

        ambiguity_score = 0.18
        if len(deduped) > 1:
            ambiguity_score += 0.35
        if confidence < 0.75:
            ambiguity_score += 0.2
        if output_mode == "hybrid":
            ambiguity_score += 0.1
        if desired_output in {"analysis", "plan", "execution_plan"}:
            ambiguity_score += 0.1
        if not safe_to_rank:
            ambiguity_score -= 0.25
        ambiguity_score = max(0.0, min(1.0, ambiguity_score))

        return AmbiguityAssessment(
            is_ambiguous=len(deduped) > 1,
            ambiguity_score=ambiguity_score,
            candidate_strategies=deduped,
            reason_codes=reason_codes,
            safe_to_rank=safe_to_rank,
        )

