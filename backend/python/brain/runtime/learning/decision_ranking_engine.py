from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


HIGH_RISK_LEVELS = {"high", "critical"}


@dataclass(slots=True)
class RankedDecision:
    strategy: str
    score: float
    source: str
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DecisionRankingResult:
    selected_strategy: str
    ranking: list[RankedDecision]
    model_used: bool
    decision_source: str
    fallback: bool
    ranked_confidence: float
    deterministic_strategy: str
    ambiguity_detected: bool
    ambiguity_score: float
    ranking_candidates_count: int
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ranking"] = [item.as_dict() for item in self.ranking]
        return payload


class DecisionRankingEngine:
    """Ranks ambiguous decision candidates while preserving deterministic priority."""

    def __init__(self, inference_engine: Any) -> None:
        self.inference_engine = inference_engine

    def rank(
        self,
        *,
        ambiguity_assessment: Any,
        candidates: list[Any],
        routing_decision: Any,
        oil_summary: dict[str, Any] | None,
        execution_manifest: dict[str, Any] | None,
    ) -> DecisionRankingResult:
        oil_summary = dict(oil_summary or {})
        execution_manifest = dict(execution_manifest or {})
        deterministic_strategy = str(getattr(routing_decision, "strategy", "") or "DIRECT_RESPONSE")
        confidence = float(getattr(routing_decision, "confidence", 0.0) or 0.0)
        if not bool(getattr(ambiguity_assessment, "is_ambiguous", False)):
            return DecisionRankingResult(
                selected_strategy=deterministic_strategy,
                ranking=[
                    RankedDecision(
                        strategy=deterministic_strategy,
                        score=round(confidence, 4),
                        source="rule",
                        confidence=round(confidence, 4),
                    )
                ],
                model_used=False,
                decision_source="rule_ranked",
                fallback=False,
                ranked_confidence=round(confidence, 4),
                deterministic_strategy=deterministic_strategy,
                ambiguity_detected=False,
                ambiguity_score=float(getattr(ambiguity_assessment, "ambiguity_score", 0.0) or 0.0),
                ranking_candidates_count=1,
                reason="not_ambiguous",
            )
        if not bool(getattr(ambiguity_assessment, "safe_to_rank", True)):
            return DecisionRankingResult(
                selected_strategy=deterministic_strategy,
                ranking=self._baseline_ranking(candidates),
                model_used=False,
                decision_source="rule_ranked",
                fallback=False,
                ranked_confidence=round(confidence, 4),
                deterministic_strategy=deterministic_strategy,
                ambiguity_detected=True,
                ambiguity_score=float(getattr(ambiguity_assessment, "ambiguity_score", 0.0) or 0.0),
                ranking_candidates_count=len(candidates),
                reason="unsafe_to_rank",
            )
        try:
            ranked_entries, model_used, model_preference, model_confidence = self._rank_candidates(
                candidates=candidates,
                deterministic_strategy=deterministic_strategy,
                oil_summary=oil_summary,
                execution_manifest=execution_manifest,
            )
            top = ranked_entries[0]
            return DecisionRankingResult(
                selected_strategy=top.strategy,
                ranking=ranked_entries,
                model_used=model_used,
                decision_source="hybrid_ranked" if model_used else "rule_ranked",
                fallback=False,
                ranked_confidence=top.confidence,
                deterministic_strategy=deterministic_strategy,
                ambiguity_detected=True,
                ambiguity_score=float(getattr(ambiguity_assessment, "ambiguity_score", 0.0) or 0.0),
                ranking_candidates_count=len(ranked_entries),
                reason="ranking_applied",
                metadata={
                    "model_preference": model_preference,
                    "model_confidence": model_confidence,
                },
            )
        except Exception as exc:
            return DecisionRankingResult(
                selected_strategy=deterministic_strategy,
                ranking=self._baseline_ranking(candidates),
                model_used=False,
                decision_source="rule_ranked",
                fallback=True,
                ranked_confidence=round(confidence, 4),
                deterministic_strategy=deterministic_strategy,
                ambiguity_detected=True,
                ambiguity_score=float(getattr(ambiguity_assessment, "ambiguity_score", 0.0) or 0.0),
                ranking_candidates_count=len(candidates),
                reason="ranking_exception",
                metadata={"error": str(exc)[:400]},
            )

    def _rank_candidates(
        self,
        *,
        candidates: list[Any],
        deterministic_strategy: str,
        oil_summary: dict[str, Any],
        execution_manifest: dict[str, Any],
    ) -> tuple[list[RankedDecision], bool, str, float]:
        urgency = str(oil_summary.get("urgency", "medium") or "medium").strip().lower()
        output_mode = str(execution_manifest.get("output_mode", "direct") or "direct").strip().lower()
        high_risk = any(str(getattr(candidate, "risk_level", "") or "").lower() in HIGH_RISK_LEVELS for candidate in candidates)
        model_preference = ""
        model_confidence = 0.0
        model_used = False
        if not high_risk and urgency != "high" and getattr(self.inference_engine, "adapter_available", lambda: False)():
            model_preference, model_confidence, model_used = self._model_preference(
                candidates=candidates,
                oil_summary=oil_summary,
                output_mode=output_mode,
            )
        ranked: list[RankedDecision] = []
        for candidate in candidates:
            score = float(getattr(candidate, "confidence", 0.0) or 0.0)
            strategy = str(getattr(candidate, "strategy", "") or "")
            expected_latency = str(getattr(candidate, "expected_latency", "") or "")
            expected_cost = str(getattr(candidate, "expected_cost", "") or "")
            risk_level = str(getattr(candidate, "risk_level", "") or "").lower()
            if strategy == deterministic_strategy:
                score += 0.08
            if urgency == "high" and expected_latency == "low":
                score += 0.08
            if urgency == "high" and risk_level in HIGH_RISK_LEVELS:
                score -= 0.25
            if expected_cost == "low":
                score += 0.04
            elif expected_cost == "high":
                score -= 0.04
            if output_mode == "hybrid" and strategy == "MULTI_STEP_REASONING":
                score += 0.06
            if strategy == "SAFE_FALLBACK":
                score += 0.05 if urgency == "high" else -0.02
            if model_used and model_preference == strategy:
                score += min(0.12, model_confidence * 0.18)
            ranked.append(
                RankedDecision(
                    strategy=strategy,
                    score=round(max(0.0, min(1.0, score)), 4),
                    source="hybrid" if model_used and model_preference == strategy else "rule",
                    confidence=round(max(0.0, min(1.0, score)), 4),
                    metadata={
                        "risk_level": risk_level,
                        "expected_cost": expected_cost,
                        "expected_latency": expected_latency,
                    },
                )
            )
        ranked.sort(key=lambda item: (item.score, item.strategy == deterministic_strategy), reverse=True)
        if len(ranked) > 1 and abs(ranked[0].score - ranked[1].score) < 0.035:
            ranked.sort(key=lambda item: item.strategy == deterministic_strategy, reverse=True)
        return ranked, model_used, model_preference, model_confidence

    def _model_preference(
        self,
        *,
        candidates: list[Any],
        oil_summary: dict[str, Any],
        output_mode: str,
    ) -> tuple[str, float, bool]:
        strategies = [str(getattr(candidate, "strategy", "") or "") for candidate in candidates]
        prompt = (
            "<|system|>\n"
            "Escolha apenas uma estratégia segura entre as opções listadas. "
            "Não explique, não invente opções e não exponha raciocínio interno.\n"
            "<|user|>\n"
            f"OIL_SUMMARY: {oil_summary}\n"
            f"OUTPUT_MODE: {output_mode}\n"
            f"CANDIDATES: {strategies}\n"
            "Retorne somente o nome exato da estratégia preferida.\n"
            "<|assistant|>\n"
        )
        result = self.inference_engine.generate_response(prompt, context={"mode": "decision_ranking"})
        if not result.model_used or result.fallback:
            return "", 0.0, False
        response_text = str(result.text or "").strip().upper()
        for strategy in strategies:
            if strategy.upper() in response_text:
                return strategy, float(result.confidence or 0.0), True
        return "", 0.0, False

    @staticmethod
    def _baseline_ranking(candidates: list[Any]) -> list[RankedDecision]:
        baseline = []
        for candidate in candidates:
            confidence = round(float(getattr(candidate, "confidence", 0.0) or 0.0), 4)
            baseline.append(
                RankedDecision(
                    strategy=str(getattr(candidate, "strategy", "") or ""),
                    score=confidence,
                    source="rule",
                    confidence=confidence,
                )
            )
        baseline.sort(key=lambda item: item.score, reverse=True)
        return baseline

