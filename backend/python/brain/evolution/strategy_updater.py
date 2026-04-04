from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict


DEFAULT_PARAMS = {
    "max_length_threshold": 500,
    "direct_memory_strictness": 0.5,
    "complex_prompt_word_threshold": 20,
    "heuristic_success_floor": 0.72,
    "llm_success_floor": 0.68,
    "prefer_llm_margin": 0.05,
}


class StrategyUpdater:
    """
    Gera novas versoes da estrategia de evolucao com base em recomendacoes,
    metricas de estrategia e historico de aprendizado.
    """

    def __init__(self, snapshots_dir: Path):
        self.snapshots_dir = snapshots_dir
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def update(
        self,
        current_strategy: Dict[str, Any],
        analysis: Dict[str, Any] | None = None,
        learning_data: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        analysis = analysis or {}
        learning_data = learning_data or {}

        updated = self._normalize_state(current_strategy)
        previous_signature = self._state_signature(updated)

        recommended_adjustments = analysis.get("recommended_adjustments", [])
        updated["adjustments"] = list(dict.fromkeys([*(updated.get("adjustments", [])), *recommended_adjustments]))[-20:]
        updated["last_update"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        updated["params"] = {**DEFAULT_PARAMS, **dict(updated.get("params", {}))}
        updated["feedback_scores"] = dict(updated.get("feedback_scores", {}))
        updated["category_scores"] = dict(analysis.get("category_scores", updated.get("category_scores", {})))
        updated["intent_profiles"] = dict(analysis.get("intent_preferences", updated.get("intent_profiles", {})))

        learning_strategy_stats = learning_data.get("strategy_stats", {}) if isinstance(learning_data, dict) else {}
        strategies = learning_strategy_stats.get("strategies", {}) if isinstance(learning_strategy_stats, dict) else {}
        updated["strategies"] = self._normalize_strategies(strategies, updated.get("strategies", {}))

        registry_overrides = dict(updated.get("registry_overrides", {}))
        registry_overrides["strategy_bias"] = analysis.get("strategy_recommendations", registry_overrides.get("strategy_bias", {}))
        updated["registry_overrides"] = registry_overrides

        self._apply_adjustments(updated, recommended_adjustments)

        new_signature = self._state_signature(updated)
        if new_signature != previous_signature:
            updated["version"] = int(updated.get("version", 1) or 1) + 1
            self._save_snapshot(updated)
        else:
            updated["version"] = int(updated.get("version", 1) or 1)
            snapshot_file = self.snapshots_dir / f"strategy_v{updated['version']}.json"
            if not snapshot_file.exists():
                self._save_snapshot(updated)

        return updated

    def _normalize_state(self, current_strategy: Dict[str, Any]) -> Dict[str, Any]:
        state = dict(current_strategy or {})
        state.setdefault("version", 1)
        state.setdefault("last_update", None)
        state.setdefault("adjustments", [])
        state["params"] = {**DEFAULT_PARAMS, **dict(state.get("params", {}))}
        state.setdefault("registry_overrides", {})
        state.setdefault("feedback_scores", {})
        state.setdefault("strategies", {})
        state.setdefault("intent_profiles", {})
        state.setdefault("category_scores", {})
        return state

    def _normalize_strategies(self, latest: Dict[str, Any], previous: Dict[str, Any]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}
        for strategy_name, raw in {**(previous or {}), **(latest or {})}.items():
            source = dict(previous.get(strategy_name, {})) if isinstance(previous, dict) and isinstance(previous.get(strategy_name), dict) else {}
            if isinstance(raw, dict):
                source.update(raw)
            total_uses = int(source.get("total_uses", source.get("uses", 0)) or 0)
            success_count = int(source.get("success_count", 0) or 0)
            failure_count = int(source.get("failure_count", 0) or 0)
            total_score = float(source.get("total_score", 0.0) or 0.0)
            average_score = float(source.get("average_score", 0.0) or 0.0)
            if total_uses > 0 and average_score == 0.0 and total_score > 0:
                average_score = total_score / total_uses
            normalized[strategy_name] = {
                "total_uses": total_uses,
                "average_score": round(average_score, 3),
                "success_count": success_count,
                "failure_count": failure_count,
                "last_used_at": source.get("last_used_at"),
                "feedback_score": round(float(source.get("feedback_score", 0.0) or 0.0), 3),
                "positive_feedback": int(source.get("positive_feedback", 0) or 0),
                "negative_feedback": int(source.get("negative_feedback", 0) or 0),
                "llm_uses": int(source.get("llm_uses", 0) or 0),
                "heuristic_uses": int(source.get("heuristic_uses", 0) or 0),
                "fallback_uses": int(source.get("fallback_uses", 0) or 0),
                "execution_modes": source.get("execution_modes", {}),
                "per_intent": source.get("per_intent", {}),
                "per_category": source.get("per_category", {}),
            }
        return normalized

    def _apply_adjustments(self, strategy: Dict[str, Any], adjustments: list[str]) -> None:
        for adjustment in adjustments:
            if adjustment == "adjust_efficiency_threshold":
                current_max = int(strategy["params"].get("max_length_threshold", 500))
                strategy["params"]["max_length_threshold"] = max(220, current_max - 40)
            elif adjustment == "rebalance_intent_weights":
                overrides = dict(strategy["registry_overrides"].get("intent_priority", {}))
                for intent in ("comparativo", "planejamento", "explicacao"):
                    overrides[intent] = round(float(overrides.get(intent, 1.0) or 1.0) + 0.05, 3)
                strategy["registry_overrides"]["intent_priority"] = overrides
            elif adjustment == "reinforce_fallback_strategy":
                strategy["params"]["direct_memory_strictness"] = 0.8
                strategy["params"]["prefer_llm_margin"] = max(0.03, float(strategy["params"].get("prefer_llm_margin", 0.05)) - 0.01)
            elif adjustment == "prefer_llm_for_complex":
                strategy["params"]["complex_prompt_word_threshold"] = max(14, int(strategy["params"].get("complex_prompt_word_threshold", 20)) - 2)
                strategy["params"]["llm_success_floor"] = max(0.62, float(strategy["params"].get("llm_success_floor", 0.68)) - 0.02)
            elif adjustment == "increase_review_strictness":
                strategy["params"]["heuristic_success_floor"] = min(0.82, float(strategy["params"].get("heuristic_success_floor", 0.72)) + 0.03)

    def _save_snapshot(self, strategy: Dict[str, Any]):
        version = strategy.get("version", 0)
        snapshot_file = self.snapshots_dir / f"strategy_v{version}.json"
        with open(snapshot_file, "w", encoding="utf-8") as file:
            json.dump(strategy, file, indent=2, ensure_ascii=False)

    def rollback(self, version: int) -> Dict[str, Any]:
        snapshot_file = self.snapshots_dir / f"strategy_v{version}.json"
        if not snapshot_file.exists():
            raise FileNotFoundError(f"Snapshot version {version} not found.")

        with open(snapshot_file, "r", encoding="utf-8") as file:
            return json.load(file)

    def get_latest_version(self) -> int:
        snapshots = list(self.snapshots_dir.glob("strategy_v*.json"))
        if not snapshots:
            return 0

        versions = []
        for snapshot in snapshots:
            try:
                versions.append(int(snapshot.stem.replace("strategy_v", "")))
            except ValueError:
                continue

        return max(versions) if versions else 0

    @staticmethod
    def _state_signature(strategy: Dict[str, Any]) -> str:
        comparable = {
            "params": strategy.get("params", {}),
            "registry_overrides": strategy.get("registry_overrides", {}),
            "strategies": strategy.get("strategies", {}),
            "intent_profiles": strategy.get("intent_profiles", {}),
            "category_scores": strategy.get("category_scores", {}),
            "feedback_scores": strategy.get("feedback_scores", {}),
            "adjustments": strategy.get("adjustments", []),
        }
        return json.dumps(comparable, ensure_ascii=False, sort_keys=True)
