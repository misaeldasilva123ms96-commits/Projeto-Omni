from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from brain.evolution.pattern_analyzer import PatternAnalyzer
from brain.evolution.strategy_updater import StrategyUpdater
from brain.memory.hybrid import HybridMemory
from brain.runtime.session_store import SessionStore


def _load_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8").strip()
        parsed = json.loads(raw) if raw else fallback
        return parsed if isinstance(parsed, dict) else fallback
    except Exception:
        return fallback


def _python_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_sessions(python_root: Path) -> list[dict[str, Any]]:
    sessions_dir = python_root / "brain" / "runtime" / "sessions"
    store = SessionStore(sessions_dir)
    sessions: list[dict[str, Any]] = []
    for path in sorted(sessions_dir.glob("*.json")):
        sessions.append(store.load(path.stem))
    return sessions


def show_report() -> int:
    python_root = _python_root()
    learning = HybridMemory(python_root / "memory").load_learning()
    evaluations = learning.get("evaluations", [])
    if not isinstance(evaluations, list):
        evaluations = []
    sessions = _load_sessions(python_root)
    analysis = PatternAnalyzer().analyze(
        evaluations=evaluations[-100:],
        learning=learning,
        sessions=sessions[-50:],
    )
    strategy_updater = StrategyUpdater(python_root / "brain" / "evolution")
    strategy_state = strategy_updater.load_current_state()

    average_score = round(
        sum(float(item.get("overall", 0.0)) for item in evaluations[-100:]) / max(1, len(evaluations[-100:])),
        3,
    ) if evaluations else 0.0

    print("Omini Evolution Dashboard")
    print("=========================")
    print(f"Current evolution version: {strategy_state.get('version', 0)}")
    print(f"Average score (recent): {average_score}")
    print("")
    print("Top weak patterns:")
    for item in analysis.get("weak_patterns", [])[:5]:
        print(f"- {item['pattern']}: {item['average_score']} ({item['samples']} samples)")
    if not analysis.get("weak_patterns"):
        print("- none")
    print("")
    print("Top strong patterns:")
    for item in analysis.get("strong_patterns", [])[:5]:
        print(f"- {item['pattern']}: {item['average_score']} ({item['samples']} samples)")
    if not analysis.get("strong_patterns"):
        print("- none")
    print("")
    print("Underused capabilities:")
    underused = analysis.get("underused_capabilities", [])
    print("- " + ", ".join(underused) if underused else "- none")
    print("")
    print("Strategy versions:")
    for item in learning.get("strategy_versions", [])[-5:]:
        if isinstance(item, dict):
            print(f"- v{item.get('version', 0)}: {item.get('justification', '')}")
    return 0


def rollback(version_arg: str) -> int:
    version = int(version_arg)
    python_root = _python_root()
    strategy_updater = StrategyUpdater(python_root / "brain" / "evolution")
    snapshot = strategy_updater.rollback(version)
    print(f"Rolled back to strategy version {snapshot.get('version', version)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        return show_report()
    if args[0] == "rollback" and len(args) > 1:
        return rollback(args[1])
    print("Usage:")
    print("  python -m brain.evolution.dashboard")
    print("  python -m brain.evolution.dashboard rollback <version>")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
