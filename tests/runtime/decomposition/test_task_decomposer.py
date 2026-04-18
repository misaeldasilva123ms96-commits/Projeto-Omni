from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.decomposition.decomposition_limits import MAX_BRANCHES_PER_NODE, MAX_DEPTH, MAX_SUBTASKS
from brain.runtime.decomposition.task_decomposer import TaskDecomposer  # noqa: E402


def _step(sid: str, summary: str, *, req_val: bool = False, stype: str = "analyze") -> dict:
    return {
        "step_id": sid,
        "step_type": stype,
        "summary": summary,
        "description": summary,
        "depends_on": [],
        "requires_validation": req_val,
    }


class TaskDecomposerTest(unittest.TestCase):
    def test_subtasks_linked_to_plan_steps(self) -> None:
        d = TaskDecomposer().decompose(
            execution_plan={
                "plan_id": "p1",
                "steps": [_step("a", "First"), _step("b", "Second")],
            },
            reasoning_trace={"trace_id": "r1"},
            strategy_summary={"selected_strategy": {"mode": "fast"}, "strategy_trace": {"trace_id": "s1"}},
            coordination_hint=None,
        )
        self.assertTrue(all(st.parent_step_id in {"a", "b"} for st in d.subtasks))
        self.assertEqual(d.trace.plan_id, "p1")
        self.assertEqual(d.trace.reasoning_link, "r1")
        self.assertEqual(d.trace.strategy_trace_link, "s1")

    def test_max_subtasks_truncates(self) -> None:
        # Two subtasks per analyze step; exceed MAX_SUBTASKS quickly.
        steps = [_step(f"s{i}", f"Step {i}", req_val=False) for i in range(5)]
        d = TaskDecomposer().decompose(
            execution_plan={"plan_id": "big", "steps": steps},
            reasoning_trace={},
            strategy_summary={"selected_strategy": {"mode": "fast"}},
            coordination_hint=None,
        )
        self.assertLessEqual(len(d.subtasks), MAX_SUBTASKS)
        self.assertTrue(d.trace.truncated)

    def test_max_branches_per_node(self) -> None:
        # Four branch types possible; only MAX_BRANCHES_PER_NODE per step.
        d = TaskDecomposer().decompose(
            execution_plan={
                "plan_id": "p2",
                "steps": [_step("only", "Work", req_val=True, stype="implement_code")],
            },
            reasoning_trace={},
            strategy_summary={"selected_strategy": {"mode": "deep"}},
            coordination_hint=None,
        )
        per_parent = sum(1 for st in d.subtasks if st.parent_step_id == "only")
        self.assertLessEqual(per_parent, MAX_BRANCHES_PER_NODE)

    def test_depth_bounded(self) -> None:
        d = TaskDecomposer().decompose(
            execution_plan={"plan_id": "p3", "steps": [_step("x", "Y")]},
            reasoning_trace={},
            strategy_summary={},
            coordination_hint=None,
        )
        self.assertTrue(all(st.depth <= MAX_DEPTH for st in d.subtasks))


if __name__ == "__main__":
    unittest.main()
