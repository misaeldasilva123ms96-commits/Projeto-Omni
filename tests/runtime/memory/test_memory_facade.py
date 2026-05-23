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

from brain.runtime.goals import GoalFactory, GoalContext  # noqa: E402
from brain.runtime.memory import MemoryFacade  # noqa: E402


class MemoryFacadeTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-memory"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"facade-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_memory_facade_provides_stable_unified_access(self) -> None:
        with self.temp_workspace() as workspace_root:
            with patch.dict(
                os.environ,
                {
                    "OMINI_MEMORY_MIN_EPISODES_FOR_SEMANTIC_FACT": "1",
                    "OMINI_MEMORY_MIN_CONFIDENCE_FOR_SEMANTIC_RECALL": "0.0",
                },
            ):
                facade = MemoryFacade(workspace_root)
                self.addCleanup(facade.close)
                goal = GoalFactory().create_goal(description="Completar fluxo de execucao.", intent="execution")
                facade.set_active_goal(
                    session_id="sess-facade",
                    goal_id=goal.goal_id,
                    active_plan_id="plan-facade",
                    goal_context=GoalContext.from_goal(goal),
                )
                facade.record_event(
                    event_type="continuation_decision",
                    description="Executando rota principal.",
                    outcome="continue_execution",
                    progress_score=0.7,
                    metadata={"goal_type": "execution", "recommended_route": "continue_execution", "decision_type": "continue_execution"},
                )
                episode = facade.close_goal_episode(
                    outcome="continue_execution",
                    description="Fluxo reutilizavel gravado.",
                    event_type="continuation_decision",
                    metadata={"goal_type": "execution", "recommended_route": "continue_execution", "decision_type": "continue_execution"},
                )

                assert episode is not None
                similar = facade.recall_similar(event_type="continuation_decision", progress=0.7, limit=5)
                facts = facade.get_semantic_facts("continuation_decision", limit=5)
                recommendation = facade.get_procedural_recommendation("execution")

                self.assertEqual(len(similar), 1)
                self.assertTrue(facts)
                assert recommendation is not None
                self.assertEqual(recommendation.recommended_route, "continue_execution")
