from __future__ import annotations

import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.goals import GoalFactory  # noqa: E402
from brain.runtime.memory import MemoryFacade  # noqa: E402
from brain.runtime.simulation import SimulationContextBuilder  # noqa: E402


class SimulationContextBuilderTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-simulation"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"context-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_simulation_context_prefers_explicit_goal_type(self) -> None:
        with self.temp_workspace() as workspace_root:
            memory = MemoryFacade(workspace_root)
            self.addCleanup(memory.close)
            goal = GoalFactory().create_goal(
                description="Concluir o fluxo com safety first.",
                intent="execution",
                metadata={"goal_type": "safety"},
            )
            builder = SimulationContextBuilder(memory_facade=memory)
            context = builder.build(plan=None, goal=goal, result={"ok": False, "error_payload": {"kind": "dependency_missing"}}, session_id="sess-sim")

            self.assertEqual(context.goal_type, "safety")
            self.assertEqual(context.metadata["goal_type_source"], "metadata")
