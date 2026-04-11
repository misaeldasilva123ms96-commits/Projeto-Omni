from __future__ import annotations

import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.memory.episodic import Episode, EpisodicStore  # noqa: E402


class EpisodicStoreTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-memory"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"episodic-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_episodic_store_saves_and_queries_episodes_correctly(self) -> None:
        with self.temp_workspace() as workspace_root:
            store = EpisodicStore(workspace_root)
            self.addCleanup(store.close)
            episode = Episode(
                episode_id="episode-1",
                goal_id="goal-episodic",
                subgoal_id=None,
                session_id="sess-episodic",
                description="Continuacao bem-sucedida.",
                event_type="continuation_decision",
                outcome="continue_execution",
                progress_at_start=0.2,
                progress_at_end=0.4,
                constraints_active=["scope"],
                evidence_ids=["receipt-1"],
                duration_seconds=3.5,
                created_at="2026-04-11T12:00:00+00:00",
                metadata={"goal_type": "execution"},
            )
            store.save_episode(episode)

            by_goal = store.query_by_goal("goal-episodic")
            similar = store.query_similar_context(event_type="continuation_decision", progress_min=0.1, progress_max=0.5, limit=5)

            self.assertEqual(len(by_goal), 1)
            self.assertEqual(by_goal[0].episode_id, "episode-1")
            self.assertEqual(len(similar), 1)

    def test_sqlite_store_initializes_safely_with_wal_mode(self) -> None:
        with self.temp_workspace() as workspace_root:
            store = EpisodicStore(workspace_root)
            self.addCleanup(store.close)
            self.assertEqual(store.current_journal_mode(), "wal")
            self.assertEqual(store.current_synchronous_mode(), 1)
