from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List


class PatternAnalyzer:
    """
    Analisa o historico de evaluations para identificar padroes de falha e sucesso
    e gerar recomendacoes leves para a estrategia adaptativa.
    """

    def analyze(
        self,
        evaluations: List[Dict[str, Any]],
        strategy_stats: Dict[str, Any] | None = None,
        explicit_feedback: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        if not evaluations:
            return {
                "evaluation_count": 0,
                "weak_patterns": [],
                "strong_patterns": [],
                "underused_capabilities": [],
                "recommended_adjustments": [],
                "category_scores": {},
                "intent_preferences": {},
                "strategy_recommendations": {},
            }

        low_scores = [ev for ev in evaluations if float(ev.get("overall", 0)) < 0.55]
        high_scores = [ev for ev in evaluations if float(ev.get("overall", 0)) >= 0.8]

        weak_patterns = self._extract_dominant_flags(low_scores)
        strong_patterns = self._extract_dominant_flags(high_scores)
        category_scores = self._aggregate_category_scores(evaluations)
        strategy_recommendations = self._build_strategy_recommendations(strategy_stats or {})
        intent_preferences = self._build_intent_preferences(strategy_stats or {}, category_scores)

        recommended_adjustments = []
        if "too_long" in weak_patterns:
            recommended_adjustments.append("adjust_efficiency_threshold")
        if "off_topic" in weak_patterns:
            recommended_adjustments.append("rebalance_intent_weights")
        if "empty_response" in weak_patterns or "generic_fallback" in weak_patterns:
            recommended_adjustments.append("reinforce_fallback_strategy")
        if any(score_info.get("average_score", 0.0) < 0.62 for score_info in category_scores.values() if score_info.get("count", 0) >= 2):
            recommended_adjustments.append("prefer_llm_for_complex")

        if explicit_feedback:
            negatives = [item for item in explicit_feedback if item.get("value") == "down"]
            if len(negatives) >= 3:
                recommended_adjustments.append("increase_review_strictness")

        return {
            "evaluation_count": len(evaluations),
            "weak_patterns": weak_patterns,
            "strong_patterns": strong_patterns,
            "underused_capabilities": [],
            "recommended_adjustments": list(dict.fromkeys(recommended_adjustments)),
            "category_scores": category_scores,
            "intent_preferences": intent_preferences,
            "strategy_recommendations": strategy_recommendations,
        }

    def _extract_dominant_flags(self, evaluations: List[Dict[str, Any]]) -> List[str]:
        flag_counts: Dict[str, int] = {}
        for ev in evaluations:
            for flag in ev.get("flags", []):
                flag_counts[flag] = flag_counts.get(flag, 0) + 1

        threshold = max(1, int(len(evaluations) * 0.2)) if evaluations else 1
        return [flag for flag, count in flag_counts.items() if count >= threshold]

    def _aggregate_category_scores(self, evaluations: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "total": 0.0, "success_count": 0, "failure_count": 0})
        for evaluation in evaluations:
            category = str(evaluation.get("task_category") or "explanation")
            grouped[category]["count"] += 1
            grouped[category]["total"] += float(evaluation.get("overall", 0.0) or 0.0)
            if evaluation.get("success"):
                grouped[category]["success_count"] += 1
            else:
                grouped[category]["failure_count"] += 1

        results: Dict[str, Dict[str, Any]] = {}
        for category, data in grouped.items():
            count = int(data["count"])
            average = (float(data["total"]) / count) if count else 0.0
            results[category] = {
                "count": count,
                "average_score": round(average, 3),
                "success_count": int(data["success_count"]),
                "failure_count": int(data["failure_count"]),
            }
        return results

    def _build_strategy_recommendations(self, strategy_stats: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        strategies = strategy_stats.get("strategies", {}) if isinstance(strategy_stats, dict) else {}
        if not isinstance(strategies, dict):
            return {}

        recommendations: Dict[str, Dict[str, Any]] = {}
        for strategy_name, raw in strategies.items():
            if not isinstance(raw, dict):
                continue
            average_score = float(raw.get("average_score", raw.get("feedback_score", 0.0)) or 0.0)
            total_uses = int(raw.get("total_uses", raw.get("uses", 0)) or 0)
            failures = int(raw.get("failure_count", 0) or 0)
            bias = 0.0
            if total_uses >= 3 and average_score >= 0.78:
                bias += 0.12
            if failures >= 3 and average_score <= 0.6:
                bias -= 0.12
            recommendations[strategy_name] = {
                "bias": round(bias, 3),
                "average_score": round(average_score, 3),
                "sample_size": total_uses,
            }
        return recommendations

    def _build_intent_preferences(
        self,
        strategy_stats: Dict[str, Any],
        category_scores: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        strategies = strategy_stats.get("strategies", {}) if isinstance(strategy_stats, dict) else {}
        preferences: Dict[str, Dict[str, Any]] = {}

        for strategy_name, raw in strategies.items():
            if not isinstance(raw, dict):
                continue
            per_intent = raw.get("per_intent", {})
            if not isinstance(per_intent, dict):
                continue
            for intent, data in per_intent.items():
                if not isinstance(data, dict):
                    continue
                current = preferences.get(intent)
                candidate_score = float(data.get("average_score", 0.0) or 0.0)
                if not current or candidate_score > float(current.get("average_score", 0.0) or 0.0):
                    execution_modes = raw.get("execution_modes", {})
                    heuristic_avg = float((execution_modes.get("heuristic") or {}).get("average_score", 0.0) or 0.0)
                    llm_avg = float((execution_modes.get("llm") or {}).get("average_score", 0.0) or 0.0)
                    preferred_mode = "llm" if llm_avg >= heuristic_avg else "heuristic"
                    preferences[intent] = {
                        "preferred_strategy": strategy_name,
                        "average_score": round(candidate_score, 3),
                        "preferred_mode": preferred_mode,
                    }

        if not preferences:
            for category, score_info in category_scores.items():
                average_score = float(score_info.get("average_score", 0.0) or 0.0)
                if average_score < 0.65 and category in {"logic", "creativity", "multi_perspective", "planning"}:
                    preferences[category] = {
                        "preferred_strategy": "structured_explanation",
                        "average_score": round(average_score, 3),
                        "preferred_mode": "llm",
                    }

        return preferences
