from __future__ import annotations

import os
import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.memory.episodic import Episode  # noqa: E402
from brain.runtime.memory.semantic import FactConsolidator, SemanticFact, SemanticIndex  # noqa: E402


class SemanticIndexTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-memory"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"semantic-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_semantic_memory_stores_and_retrieves_facts_correctly(self) -> None:
        with self.temp_workspace() as workspace_root:
            index = SemanticIndex(workspace_root)
            self.addCleanup(index.close)
            fact = SemanticFact(
                fact_id="fact-1",
                subject="continuation_decision",
                predicate="tends_to_result_in",
                object_value="continue_execution",
                confidence=0.8,
                source_episode_ids=["episode-1"],
                goal_types=["execution"],
                created_at="2026-04-11T12:00:00+00:00",
                last_reinforced_at="2026-04-11T12:00:00+00:00",
                metadata={"sample_size": 5},
            )
            index.upsert_fact(fact)

            facts = index.get_facts(subject="continuation_decision")
            self.assertEqual(len(facts), 1)
            self.assertEqual(facts[0].object_value, "continue_execution")
            self.assertEqual(index.current_journal_mode(), "wal")

    def test_semantic_fact_consolidation_respects_minimum_evidence_threshold(self) -> None:
        episodes = [
            Episode(
                episode_id=f"episode-{index}",
                goal_id="goal-1",
                subgoal_id=None,
                session_id="sess-1",
                description="Pattern sample",
                event_type="continuation_decision",
                outcome="continue_execution",
                progress_at_start=0.1,
                progress_at_end=0.2,
                constraints_active=[],
                evidence_ids=[],
                duration_seconds=1.0,
                created_at=f"2026-04-11T12:00:0{index}+00:00",
                metadata={"goal_type": "execution"},
            )
            for index in range(2)
        ]
        with patch.dict(os.environ, {"OMINI_MEMORY_MIN_EPISODES_FOR_SEMANTIC_FACT": "3"}):
            consolidator = FactConsolidator()
            facts = consolidator.consolidate(episodes=episodes)
        self.assertEqual(facts, [])
