from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from ._reader_utils import open_sqlite_readonly, read_json_resilient, read_tail_jsonl
from .models import EpisodeSnapshot, ProceduralPatternSnapshot, SemanticFactSnapshot


class MemoryReader:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.memory_dir = root / ".logs" / "fusion-runtime" / "memory"
        self.db_dir = self.memory_dir / "db"
        self.episodic_path = self.db_dir / "episodic.db"
        self.semantic_path = self.db_dir / "semantic.db"
        self.procedural_path = self.memory_dir / "procedural_patterns.json"
        self.learning_signals_dir = root / ".logs" / "fusion-runtime" / "learning" / "signals"
        self.evolution_proposals_path = root / ".logs" / "fusion-runtime" / "evolution" / "proposals" / "proposals.jsonl"

    def read_recent_episodes(self, *, goal_id: str | None = None, limit: int = 8) -> list[EpisodeSnapshot]:
        query = (
            "SELECT * FROM episodes WHERE goal_id = ? ORDER BY created_at DESC LIMIT ?"
            if goal_id
            else "SELECT * FROM episodes ORDER BY created_at DESC LIMIT ?"
        )
        params: tuple[Any, ...] = (goal_id, max(1, limit)) if goal_id else (max(1, limit),)
        with open_sqlite_readonly(self.episodic_path) as conn:
            if conn is None:
                return []
            try:
                rows = conn.execute(query, params).fetchall()
            except sqlite3.Error:
                return []
        return [self._episode_from_row(row) for row in rows]

    def read_top_semantic_facts(self, *, subject: str | None = None, limit: int = 8) -> list[SemanticFactSnapshot]:
        if subject:
            query = (
                "SELECT * FROM semantic_facts WHERE subject = ? "
                "ORDER BY confidence DESC, last_reinforced_at DESC LIMIT ?"
            )
            params: tuple[Any, ...] = (subject, max(1, limit))
        else:
            query = "SELECT * FROM semantic_facts ORDER BY confidence DESC, last_reinforced_at DESC LIMIT ?"
            params = (max(1, limit),)
        with open_sqlite_readonly(self.semantic_path) as conn:
            if conn is None:
                return []
            try:
                rows = conn.execute(query, params).fetchall()
            except sqlite3.Error:
                return []
        return [self._semantic_from_row(row) for row in rows]

    def read_recent_semantic_reinforcements(self, *, limit: int = 6) -> list[SemanticFactSnapshot]:
        with open_sqlite_readonly(self.semantic_path) as conn:
            if conn is None:
                return []
            try:
                rows = conn.execute(
                    "SELECT * FROM semantic_facts ORDER BY last_reinforced_at DESC LIMIT ?",
                    (max(1, limit),),
                ).fetchall()
            except sqlite3.Error:
                return []
        return [self._semantic_from_row(row) for row in rows]

    def read_active_procedural_pattern(self, goal_type: str | None) -> ProceduralPatternSnapshot | None:
        patterns = self._load_patterns()
        if goal_type:
            candidates = [
                pattern
                for pattern in patterns
                if goal_type in pattern.applicable_goal_types or not pattern.applicable_goal_types
            ]
        else:
            candidates = patterns
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item.success_rate, item.sample_size, item.last_updated), reverse=True)
        return candidates[0]

    def read_recent_procedural_updates(self, *, limit: int = 5) -> list[ProceduralPatternSnapshot]:
        patterns = self._load_patterns()
        patterns.sort(key=lambda item: item.last_updated, reverse=True)
        return patterns[: max(1, limit)]

    def read_recent_learning_signals(self, *, limit: int = 8) -> list[dict[str, Any]]:
        signals: list[dict[str, Any]] = []
        for path in self.learning_signals_dir.glob("*.jsonl"):
            signals.extend(read_tail_jsonl(path, limit=max(3, limit)))
        signals.sort(key=lambda item: str(item.get("timestamp", "")), reverse=True)
        return signals[: max(1, limit)]

    def read_pending_evolution_proposals(self, *, limit: int = 8) -> tuple[int, list[dict[str, Any]]]:
        payloads = read_tail_jsonl(self.evolution_proposals_path, limit=max(limit * 3, limit))
        proposals = [payload for payload in payloads if isinstance(payload, dict)]
        pending = [
            proposal
            for proposal in proposals
            if str(proposal.get("promotion_status", "")).strip() not in {"promoted", "blocked"}
        ]
        pending.sort(key=lambda item: str(item.get("timestamp", "")), reverse=True)
        return len(pending), pending[: max(1, limit)]

    @staticmethod
    def _episode_from_row(row: sqlite3.Row) -> EpisodeSnapshot:
        return EpisodeSnapshot(
            episode_id=str(row["episode_id"]),
            goal_id=str(row["goal_id"]),
            subgoal_id=str(row["subgoal_id"]) if row["subgoal_id"] else None,
            session_id=str(row["session_id"]),
            description=str(row["description"]),
            event_type=str(row["event_type"]),
            outcome=str(row["outcome"]),
            progress_at_start=float(row["progress_at_start"]),
            progress_at_end=float(row["progress_at_end"]),
            duration_seconds=float(row["duration_seconds"]),
            created_at=str(row["created_at"]),
            evidence_ids=[str(item) for item in json.loads(row["evidence_ids"] or "[]") if str(item).strip()],
            constraints_active=[str(item) for item in json.loads(row["constraints_active"] or "[]") if str(item).strip()],
            metadata=dict(json.loads(row["metadata"] or "{}")),
        )

    @staticmethod
    def _semantic_from_row(row: sqlite3.Row) -> SemanticFactSnapshot:
        return SemanticFactSnapshot(
            fact_id=str(row["fact_id"]),
            subject=str(row["subject"]),
            predicate=str(row["predicate"]),
            object_value=str(row["object_value"]),
            confidence=float(row["confidence"]),
            source_episode_ids=[str(item) for item in json.loads(row["source_episode_ids"] or "[]") if str(item).strip()],
            goal_types=[str(item) for item in json.loads(row["goal_types"] or "[]") if str(item).strip()],
            created_at=str(row["created_at"]),
            last_reinforced_at=str(row["last_reinforced_at"]),
            metadata=dict(json.loads(row["metadata"] or "{}")),
        )

    def _load_patterns(self) -> list[ProceduralPatternSnapshot]:
        payload = read_json_resilient(self.procedural_path)
        if not isinstance(payload, dict):
            return []
        patterns: list[ProceduralPatternSnapshot] = []
        for item in payload.get("patterns", []):
            if not isinstance(item, dict):
                continue
            patterns.append(
                ProceduralPatternSnapshot(
                    pattern_id=str(item.get("pattern_id", "")),
                    name=str(item.get("name", "")),
                    description=str(item.get("description", "")),
                    applicable_goal_types=[str(goal_type) for goal_type in item.get("applicable_goal_types", []) if str(goal_type).strip()],
                    applicable_constraint_types=[
                        str(constraint_type)
                        for constraint_type in item.get("applicable_constraint_types", [])
                        if str(constraint_type).strip()
                    ],
                    recommended_route=str(item.get("recommended_route", "")),
                    success_rate=float(item.get("success_rate", 0.0) or 0.0),
                    sample_size=int(item.get("sample_size", 0) or 0),
                    last_updated=str(item.get("last_updated", "")),
                    metadata=dict(item.get("metadata", {}) or {}),
                )
            )
        return patterns
