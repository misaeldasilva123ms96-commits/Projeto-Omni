from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STRATEGY_SCHEMA_VERSION = 1


def default_strategy_state() -> dict[str, Any]:
    return {
        "schema_version": STRATEGY_SCHEMA_VERSION,
        "version": 0,
        "updated_at": "",
        "capability_weights": {
            "generate_idea": 1.0,
            "give_advice": 1.0,
            "create_plan": 1.0,
        },
        "decision_thresholds": {
            "critic_min_score": 0.4,
            "apply_score_gain": 0.03,
        },
        "memory_rules": {
            "history_limit": 6,
            "consolidate_min_score": 0.55,
        },
        "orchestrator_hints": {
            "prefer_planner_for_complex": True,
            "prefer_memory_when_repeated": True,
        },
        "justification": "Initial strategy state",
    }


class StrategyUpdater:
    def __init__(self, evolution_dir: Path) -> None:
        self.evolution_dir = evolution_dir
        self.evolution_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir = self.evolution_dir / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.evolution_dir / "strategy_state.json"
        self.log_path = self.evolution_dir / "strategy_log.json"
        self._ensure_files()

    def _ensure_files(self) -> None:
        if not self.state_path.exists():
            self._write_json(self.state_path, default_strategy_state())
        if not self.log_path.exists():
            self._write_json(self.log_path, {"changes": []})

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_current_state(self) -> dict[str, Any]:
        self._ensure_files()
        try:
            raw = self.state_path.read_text(encoding="utf-8").strip()
            parsed = json.loads(raw) if raw else {}
            return parsed if isinstance(parsed, dict) else default_strategy_state()
        except Exception:
            return default_strategy_state()

    def propose_update(self, analysis: dict[str, Any], average_score: float) -> dict[str, Any]:
        state = self.load_current_state()
        proposal = json.loads(json.dumps(state))
        adjustments = analysis.get("recommended_adjustments", [])
        score_gain = 0.0

        if any(item.get("action") == "raise_priority" for item in adjustments if isinstance(item, dict)):
            proposal["capability_weights"]["create_plan"] = round(float(proposal["capability_weights"].get("create_plan", 1.0)) + 0.08, 3)
            proposal["capability_weights"]["give_advice"] = round(float(proposal["capability_weights"].get("give_advice", 1.0)) + 0.05, 3)
            score_gain += 0.04

        underused = analysis.get("underused_capabilities", [])
        if isinstance(underused, list) and underused:
            for capability in underused:
                if capability in proposal["capability_weights"]:
                    proposal["capability_weights"][capability] = round(max(0.8, float(proposal["capability_weights"][capability]) - 0.03), 3)
            score_gain += 0.01

        weak_patterns = analysis.get("weak_patterns", [])
        if isinstance(weak_patterns, list) and weak_patterns:
            proposal["memory_rules"]["history_limit"] = min(10, int(proposal["memory_rules"].get("history_limit", 6)) + 1)
            score_gain += 0.015

        proposal["justification"] = "; ".join(
            str(item.get("reason", "")).strip()
            for item in adjustments
            if isinstance(item, dict) and str(item.get("reason", "")).strip()
        ) or "No significant adjustments proposed"

        return {
            "current_state": state,
            "proposed_state": proposal,
            "estimated_score_gain": round(score_gain, 3),
            "baseline_score": average_score,
        }

    def apply_update(self, proposal: dict[str, Any]) -> dict[str, Any]:
        current_state = proposal["current_state"]
        next_state = proposal["proposed_state"]
        version = int(current_state.get("version", 0)) + 1
        next_state["version"] = version
        next_state["updated_at"] = datetime.now(timezone.utc).isoformat()
        next_state["schema_version"] = STRATEGY_SCHEMA_VERSION

        snapshot_path = self.snapshots_dir / f"strategy_v{version}.json"
        self._write_json(snapshot_path, next_state)
        self._write_json(self.state_path, next_state)

        log = self._load_log()
        log["changes"].append(
            {
                "version": version,
                "timestamp": next_state["updated_at"],
                "estimated_score_gain": proposal["estimated_score_gain"],
                "justification": next_state["justification"],
            }
        )
        self._write_json(self.log_path, {"changes": log["changes"][-100:]})
        return next_state

    def rollback(self, version: int) -> dict[str, Any]:
        snapshot_path = self.snapshots_dir / f"strategy_v{version}.json"
        if not snapshot_path.exists():
            raise FileNotFoundError(f"Strategy version {version} not found")
        raw = snapshot_path.read_text(encoding="utf-8").strip()
        snapshot = json.loads(raw) if raw else default_strategy_state()
        self._write_json(self.state_path, snapshot)
        return snapshot

    def _load_log(self) -> dict[str, Any]:
        try:
            raw = self.log_path.read_text(encoding="utf-8").strip()
            parsed = json.loads(raw) if raw else {"changes": []}
            return parsed if isinstance(parsed, dict) else {"changes": []}
        except Exception:
            return {"changes": []}
