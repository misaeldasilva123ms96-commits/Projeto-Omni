from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class LoRADecisionResult:
    final_strategy: str
    confidence: float
    model_used: bool
    fallback: bool
    decision_source: str
    dataset_origin: str
    lora_used: bool
    model_confidence: float
    refined_response: str = ""
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class LoRADecisionEngine:
    """Hybrid layer: deterministic strategy first, model only as bounded augmentation."""

    def __init__(self, inference_engine: Any, router_adapter: Any) -> None:
        self.inference_engine = inference_engine
        self.router_adapter = router_adapter

    def evaluate(
        self,
        *,
        message: str,
        base_response: str,
        oil_summary: dict[str, Any] | None,
        routing_decision: Any,
        execution_manifest: dict[str, Any] | None,
        provider_path: str = "",
    ) -> LoRADecisionResult:
        deterministic_strategy = str(getattr(routing_decision, "strategy", "") or "DIRECT_RESPONSE")
        deterministic_confidence = float(getattr(routing_decision, "confidence", 0.0) or 0.0)
        usage_plan = self.router_adapter.should_use_model(
            message=message,
            oil_summary=oil_summary,
            routing_decision=routing_decision,
            execution_manifest=execution_manifest,
            base_response=base_response,
        )
        if not usage_plan.should_use_model:
            return LoRADecisionResult(
                final_strategy=deterministic_strategy,
                confidence=deterministic_confidence,
                model_used=False,
                fallback=False,
                decision_source="rule",
                dataset_origin=usage_plan.dataset_origin,
                lora_used=False,
                model_confidence=0.0,
                refined_response=str(base_response or ""),
                reason=usage_plan.reason,
                metadata={"usage_plan": usage_plan.as_dict(), "provider_path": provider_path},
            )
        prompt = self._build_refinement_prompt(
            message=message,
            base_response=base_response,
            oil_summary=oil_summary,
            deterministic_strategy=deterministic_strategy,
        )
        model_result = self.inference_engine.generate_response(
            prompt,
            context={
                "oil_summary": dict(oil_summary or {}),
                "execution_manifest": dict(execution_manifest or {}),
                "provider_path": provider_path,
            },
        )
        if not model_result.model_used or model_result.fallback:
            return LoRADecisionResult(
                final_strategy=deterministic_strategy,
                confidence=deterministic_confidence,
                model_used=False,
                fallback=True,
                decision_source="rule",
                dataset_origin=model_result.dataset_origin,
                lora_used=False,
                model_confidence=0.0,
                refined_response=str(base_response or ""),
                reason=str(model_result.reason or "lora_fallback"),
                metadata={
                    "usage_plan": usage_plan.as_dict(),
                    "model_result": model_result.as_dict(),
                    "provider_path": provider_path,
                },
            )
        refined = self._safe_refined_response(base_response, model_result.text)
        return LoRADecisionResult(
            final_strategy=deterministic_strategy,
            confidence=max(deterministic_confidence, min(0.9, model_result.confidence)),
            model_used=True,
            fallback=False,
            decision_source="hybrid",
            dataset_origin=model_result.dataset_origin,
            lora_used=True,
            model_confidence=float(model_result.confidence),
            refined_response=refined or str(base_response or ""),
            reason=str(model_result.reason or "adapter_inference"),
            metadata={
                "usage_plan": usage_plan.as_dict(),
                "model_result": model_result.as_dict(),
                "provider_path": provider_path,
            },
        )

    @staticmethod
    def _build_refinement_prompt(
        *,
        message: str,
        base_response: str,
        oil_summary: dict[str, Any] | None,
        deterministic_strategy: str,
    ) -> str:
        return (
            "<|system|>\n"
            "Você é Omni em modo de refinamento governado. "
            "Melhore apenas clareza, coerência e precisão textual. "
            "Não altere política, não invente ferramentas e não exponha raciocínio interno.\n"
            "<|user|>\n"
            f"INPUT: {str(message or '').strip()}\n"
            f"BASE_RESPONSE: {str(base_response or '').strip()}\n"
            f"OIL_SUMMARY: {dict(oil_summary or {})}\n"
            f"DETERMINISTIC_STRATEGY: {deterministic_strategy}\n"
            "Retorne apenas a resposta final refinada.\n"
            "<|assistant|>\n"
        )

    @staticmethod
    def _safe_refined_response(base_response: str, refined_response: str) -> str:
        refined = str(refined_response or "").strip()
        if not refined:
            return str(base_response or "")
        if len(refined) < 40 and len(str(base_response or "").strip()) > len(refined):
            return str(base_response or "")
        if len(refined) > 4000:
            refined = refined[:4000].rstrip()
        return refined

