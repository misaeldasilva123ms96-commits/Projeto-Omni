from __future__ import annotations

import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / 'backend' / 'python'))

from brain.runtime.goals import GoalFactory, GoalStore  # noqa: E402
from brain.runtime.observability.goal_reader import GoalReader  # noqa: E402


class GoalReaderTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / '.logs' / 'test-observability'
        base.mkdir(parents=True, exist_ok=True)
        path = base / f'goal-reader-{uuid4().hex[:8]}'
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_goal_reader_handles_no_goal(self) -> None:
        with self.temp_workspace() as workspace_root:
            reader = GoalReader(workspace_root)
            self.assertIsNone(reader.read_active_goal())
            self.assertEqual(reader.read_goal_history(limit=5), [])

    def test_goal_reader_handles_active_goal(self) -> None:
        with self.temp_workspace() as workspace_root:
            store = GoalStore(workspace_root)
            goal = GoalFactory().create_goal(description='Executar observabilidade.', intent='execution')
            store.save_goal(goal)
            reader = GoalReader(workspace_root)
            snapshot = reader.read_active_goal(progress_score=0.4)
            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            self.assertEqual(snapshot.goal_id, goal.goal_id)
            self.assertEqual(snapshot.progress_score, 0.4)
            self.assertGreaterEqual(len(reader.read_goal_history(limit=5)), 1)
