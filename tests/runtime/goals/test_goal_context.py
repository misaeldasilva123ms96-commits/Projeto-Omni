from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.goals import GoalContext, GoalFactory  # noqa: E402


class GoalContextTest(unittest.TestCase):
    def test_goal_context_from_goal_and_prompt_block(self) -> None:
        goal = GoalFactory().infer_from_task("Concluir o fluxo com seguranca.")
        context = GoalContext.from_goal(goal)
        prompt_block = context.to_prompt_block()

        self.assertEqual(context.goal_id, goal.goal_id)
        self.assertIn(goal.description, prompt_block)
        self.assertIn("Success Criteria:", prompt_block)
        self.assertIsInstance(context.active_constraints, tuple)


if __name__ == "__main__":
    unittest.main()
