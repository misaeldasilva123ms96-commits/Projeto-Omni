from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class LoRAUsagePlan:
    should_use_model: bool
    reason: str
    ambiguity_score: float
    dataset_origin: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class LoRARouterAdapter:
    """Conservative gate for optional LoRA consultation."""

    def __init__(self, inference_engine: Any) -> None:
        self.inference_engine = inference_engine

    def should_use_model(
        self,
        *,
        message: str,
        oil_summary: dict[str, Any] | None,
        routing_decision: Any,
        execution_manifest: dict[str, Any] | None,
        base_response: str,
    ) -> LoRAUsagePlan:
        if not getattr(self.inference_engine, "adapter_available", lambda: False)():
            return LoRAUsagePlan(
                should_use_model=False,
                reason="adapter_unavailable",
                ambiguity_score=0.0,
                dataset_origin=str(getattr(self.inference_engine, "dataset_origin", "") or ""),
            )
        confidence = float(getattr(routing_decision, "confidence", 0.0) or 0.0)
        strategy = str(getattr(routing_decision, "strategy", "") or "")
        urgency = str((oil_summary or {}).get("urgency", "medium") or "medium")
        output_mode = str((execution_manifest or {}).get("output_mode", "direct") or "direct")
        lowered = str(message or "").lower()
        ambiguous_terms = ("talvez", "ambiguous", "nao tenho certeza", "não tenho certeza", "refine", "melhore", "rewrite")
        ambiguity_score = 0.25
        if confidence < 0.75:
            ambiguity_score += 0.35
        if any(term in lowered for term in ambiguous_terms):
            ambiguity_score += 0.25
        if len(str(base_response or "").strip()) < 120:
            ambiguity_score += 0.15
        if output_mode == "hybrid":
            ambiguity_score += 0.1
        if urgency == "high":
            ambiguity_score -= 0.15
        if strategy == "SAFE_FALLBACK":
            ambiguity_score -= 0.25
        ambiguity_score = max(0.0, min(1.0, ambiguity_score))
        return LoRAUsagePlan(
            should_use_model=ambiguity_score >= 0.55,
            reason="ambiguous_or_text_refinement" if ambiguity_score >= 0.55 else "deterministic_path_sufficient",
            ambiguity_score=ambiguity_score,
            dataset_origin=str(getattr(self.inference_engine, "dataset_origin", "") or ""),
            metadata={
                "routing_confidence": confidence,
                "strategy": strategy,
                "urgency": urgency,
                "output_mode": output_mode,
            },
        )

