from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

from brain.evolution.pattern_analyzer import PatternAnalyzer
from brain.evolution.strategy_updater import StrategyUpdater
from brain.memory.hybrid import HybridMemory
from brain.runtime.session_store import SessionStore


_LOOP_THREAD: threading.Thread | None = None
_LOOP_LOCK = threading.Lock()


class EvolutionLoop:
    def __init__(self, python_root: Path) -> None:
        self.python_root = python_root
        self.memory_dir = python_root / "memory"
        self.sessions_dir = python_root / "brain" / "runtime" / "sessions"
        self.evolution_dir = python_root / "brain" / "evolution"
        self.loop_log_path = self.evolution_dir / "loop_log.json"
        self.hybrid_memory = HybridMemory(self.memory_dir)
        self.session_store = SessionStore(self.sessions_dir)
        self.pattern_analyzer = PatternAnalyzer()
        self.strategy_updater = StrategyUpdater(self.evolution_dir)
        self._ensure_log()

    def _ensure_log(self) -> None:
        self.evolution_dir.mkdir(parents=True, exist_ok=True)
        if not self.loop_log_path.exists():
            self.loop_log_path.write_text(json.dumps({"runs": []}, ensure_ascii=False, indent=2), encoding="utf-8")

    def run_forever(self) -> None:
        interval_seconds = int(os.getenv("OMINI_EVOLUTION_INTERVAL_SECONDS", "300"))
        min_sessions = int(os.getenv("OMINI_EVOLUTION_MIN_SESSIONS", "1"))

        while True:
            try:
                self.run_cycle(min_sessions=min_sessions)
            except Exception:
                pass
            time.sleep(max(60, interval_seconds))

    def run_cycle(self, *, min_sessions: int = 1) -> dict[str, Any]:
        learning = self.hybrid_memory.load_learning()
        evaluations = learning.get("evaluations", [])
        if not isinstance(evaluations, list):
            evaluations = []

        sessions = self._load_sessions()
        if len(sessions) < min_sessions or not evaluations:
            result = {
                "status": "skipped",
                "reason": "not_enough_data",
                "sessions": len(sessions),
                "evaluations": len(evaluations),
            }
            self._append_log(result)
            return result

        phase41_sketch: dict[str, Any] | list[dict[str, Any]] | None = None
        if str(os.getenv("OMINI_PHASE41_EVOLUTION_FEED", "0")).strip().lower() in ("1", "true", "yes"):
            try:
                from brain.runtime.policy.performance_store import PerformanceStore

                project_root = self.python_root.parents[1] if len(self.python_root.parents) > 1 else self.python_root
                ps = PerformanceStore(project_root)
                p42 = ps.phase42_snapshot()
                phase41_sketch = {
                    "top_provider_buckets": ps.top_buckets(limit=5),
                    "phase42_rollups": dict(p42.get("rollups") or {}),
                    "phase42_policy_match_rate": p42.get("policy_match_rate"),
                    "phase42_provenance_completeness_rate": p42.get("provenance_completeness_rate"),
                }
            except Exception:
                phase41_sketch = None

        analysis = self.pattern_analyzer.analyze(
            evaluations=evaluations[-100:],
            learning=learning,
            sessions=sessions[-50:],
            phase41_performance_sketch=phase41_sketch,
        )
        average_score = round(
            sum(float(item.get("overall", 0.0)) for item in evaluations[-100:]) / max(1, len(evaluations[-100:])),
            3,
        )
        proposal = self.strategy_updater.propose_update(analysis, average_score)
        threshold = float(proposal["current_state"].get("decision_thresholds", {}).get("apply_score_gain", 0.03))

        if proposal["estimated_score_gain"] > threshold:
            new_state = self.strategy_updater.apply_update(proposal)
            self.hybrid_memory.record_strategy_version(
                {
                    "version": new_state["version"],
                    "justification": new_state.get("justification", ""),
                    "estimated_score_gain": proposal["estimated_score_gain"],
                }
            )
            result = {
                "status": "applied",
                "version": new_state["version"],
                "estimated_score_gain": proposal["estimated_score_gain"],
                "average_score": average_score,
            }
        else:
            result = {
                "status": "rejected",
                "estimated_score_gain": proposal["estimated_score_gain"],
                "threshold": threshold,
                "average_score": average_score,
            }

        self._append_log(result | {"analysis": analysis})
        return result

    def _load_sessions(self) -> list[dict[str, Any]]:
        sessions: list[dict[str, Any]] = []
        if not self.sessions_dir.exists():
            return sessions
        for path in sorted(self.sessions_dir.glob("*.json")):
            session_id = path.stem
            sessions.append(self.session_store.load(session_id))
        return sessions

    def _append_log(self, event: dict[str, Any]) -> None:
        try:
            raw = self.loop_log_path.read_text(encoding="utf-8").strip()
            parsed = json.loads(raw) if raw else {"runs": []}
            runs = parsed.get("runs", [])
            if not isinstance(runs, list):
                runs = []
            runs.append(event)
            self.loop_log_path.write_text(
                json.dumps({"runs": runs[-100:]}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            return


def start_evolution_loop(python_root: Path) -> threading.Thread:
    global _LOOP_THREAD
    with _LOOP_LOCK:
        if _LOOP_THREAD is not None and _LOOP_THREAD.is_alive():
            return _LOOP_THREAD

        loop = EvolutionLoop(python_root)
        _LOOP_THREAD = threading.Thread(
            target=loop.run_forever,
            name="omini-evolution-loop",
            daemon=True,
        )
        _LOOP_THREAD.start()
        return _LOOP_THREAD
