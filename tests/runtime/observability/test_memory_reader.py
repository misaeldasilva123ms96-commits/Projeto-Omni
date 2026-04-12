from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / 'backend' / 'python'))

from brain.runtime.memory.episodic.models import Episode  # noqa: E402
from brain.runtime.memory.episodic.episodic_store import EpisodicStore  # noqa: E402
from brain.runtime.memory.procedural.models import ProceduralPattern  # noqa: E402
from brain.runtime.memory.procedural.procedural_registry import ProceduralRegistry  # noqa: E402
from brain.runtime.memory.semantic.models import SemanticFact  # noqa: E402
from brain.runtime.memory.semantic.semantic_index import SemanticIndex  # noqa: E402
from brain.runtime.observability.memory_reader import MemoryReader  # noqa: E402


class MemoryReaderTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / '.logs' / 'test-observability'
        base.mkdir(parents=True, exist_ok=True)
        path = base / f'memory-reader-{uuid4().hex[:8]}'
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_memory_reader_opens_sqlite_in_readonly_mode(self) -> None:
        with self.temp_workspace() as workspace_root:
            db_dir = workspace_root / '.logs' / 'fusion-runtime' / 'memory' / 'db'
            db_dir.mkdir(parents=True, exist_ok=True)
            sqlite3.connect(db_dir / 'episodic.db').close()
            with patch('brain.runtime.observability._reader_utils.sqlite3.connect') as connect:
                mocked = connect.return_value
                mocked.execute.return_value.fetchall.return_value = []
                reader = MemoryReader(workspace_root)
                reader.read_recent_episodes(limit=1)
                self.assertTrue(connect.called)
                self.assertIn('mode=ro', connect.call_args.args[0])
                self.assertTrue(connect.call_args.kwargs.get('uri'))

    def test_memory_reader_retrieves_bounded_recent_episodes_and_top_facts(self) -> None:
        with self.temp_workspace() as workspace_root:
            episodic = EpisodicStore(workspace_root)
            semantic = SemanticIndex(workspace_root)
            self.addCleanup(episodic.close)
            self.addCleanup(semantic.close)
            episodic.save_episode(
                Episode(
                    episode_id='episode-1',
                    goal_id='goal-1',
                    subgoal_id=None,
                    session_id='sess-1',
                    description='Episode stored.',
                    event_type='continuation',
                    outcome='retry',
                    progress_at_start=0.2,
                    progress_at_end=0.6,
                    constraints_active=['scope'],
                    evidence_ids=['e1'],
                    duration_seconds=1.2,
                    created_at='2026-04-11T00:00:00+00:00',
                    metadata={},
                )
            )
            semantic.upsert_fact(
                SemanticFact(
                    fact_id='fact-1',
                    subject='execution',
                    predicate='supports',
                    object_value='retry',
                    confidence=0.9,
                    source_episode_ids=['episode-1'],
                    goal_types=['execution'],
                    created_at='2026-04-11T00:00:00+00:00',
                    last_reinforced_at='2026-04-11T00:00:00+00:00',
                    metadata={},
                )
            )
            ProceduralRegistry(workspace_root).upsert(
                ProceduralPattern(
                    pattern_id='pattern-1',
                    name='Retry route',
                    description='Prefer retry for this goal type.',
                    applicable_goal_types=['execution'],
                    applicable_constraint_types=[],
                    recommended_route='retry',
                    success_rate=0.8,
                    sample_size=3,
                    last_updated='2026-04-11T00:00:00+00:00',
                    metadata={},
                )
            )
            reader = MemoryReader(workspace_root)
            reader.episodic_path = episodic.path
            reader.semantic_path = semantic.path
            episodes = reader.read_recent_episodes(goal_id='goal-1', limit=3)
            facts = reader.read_top_semantic_facts(subject='execution', limit=3)
            patterns = reader.read_recent_procedural_updates(limit=3)
            self.assertEqual(len(episodes), 1)
            self.assertEqual(len(facts), 1)
            self.assertGreaterEqual(len(patterns), 1)
