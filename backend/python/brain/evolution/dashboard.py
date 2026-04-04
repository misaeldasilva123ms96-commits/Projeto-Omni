from __future__ import annotations

import json
from pathlib import Path


def _load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    try:
        raw = path.read_text(encoding="utf-8").strip()
        parsed = json.loads(raw) if raw else fallback
        return parsed
    except Exception:
        return fallback


def run_dashboard() -> None:
    python_root = Path(__file__).resolve().parents[2]
    learning_path = python_root / "memory" / "learning.json"
    strategy_state_path = python_root / "brain" / "evolution" / "strategy_state.json"
    loop_log_path = python_root / "brain" / "evolution" / "loop_log.json"
    snapshots_dir = python_root / "brain" / "evolution" / "snapshots"

    learning_data = _load_json(learning_path, {})
    strategy_state = _load_json(strategy_state_path, {"version": 1})
    loop_log = _load_json(loop_log_path, [])
    evaluations = learning_data.get("evaluations", []) if isinstance(learning_data, dict) else []
    if not isinstance(evaluations, list):
        evaluations = []

    avg_score = 0.0
    if evaluations:
        avg_score = sum(float(item.get("overall", 0.0)) for item in evaluations) / len(evaluations)

    print("Omini Evolution Dashboard")
    print("=========================")
    print(f"Current evolution version: {int(strategy_state.get('version', 1))}")
    print(f"Average score (recent): {avg_score:.3f}")

    if loop_log:
        latest = loop_log[-1]
        analysis = latest.get("analysis", {}) if isinstance(latest, dict) else {}
        weak = analysis.get("weak_patterns", []) if isinstance(analysis, dict) else []
        recommended = analysis.get("recommended_adjustments", []) if isinstance(analysis, dict) else []
        print(f"Latest weak patterns: {', '.join(weak[:5]) if weak else 'none'}")
        print(f"Recommended adjustments: {', '.join(recommended[:5]) if recommended else 'none'}")

    snapshots = sorted(snapshots_dir.glob("strategy_v*.json")) if snapshots_dir.exists() else []
    print(f"Snapshots available: {len(snapshots)}")


if __name__ == "__main__":
    run_dashboard()