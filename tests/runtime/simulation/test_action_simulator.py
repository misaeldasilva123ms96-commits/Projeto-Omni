from __future__ import annotations

import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.memory import MemoryFacade  # noqa: E402
from brain.runtime.simulation import ActionSimulator, RouteType, SimulationContext  # noqa: E402


class ActionSimulatorTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-simulation"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"simulator-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_simulation_result_contains_four_routes(self) -> None:
        with self.temp_workspace() as workspace_root:
            memory = MemoryFacade(workspace_root)
            self.addCleanup(memory.close)
            simulator = ActionSimulator(workspace_root, memory_facade=memory)
            context = SimulationContext(
                goal_id="goal-1",
                goal_description="Recover execution safely.",
                goal_type="execution",
                current_progress=0.4,
                last_action={"selected_tool": "verification_runner"},
                last_outcome="verification_failed",
                active_constraints=[],
                retry_count=1,
                repair_count=0,
                session_id="sess-1",
                goal_present=True,
            )

            result = simulator.simulate(context=context)

            self.assertEqual(len(result.routes), 4)
            self.assertEqual({route.route for route in result.routes}, set(RouteType))

    def test_pause_does_not_dominate_merely_for_safety(self) -> None:
        with self.temp_workspace() as workspace_root:
            simulator = ActionSimulator(workspace_root, memory_facade=None)
            context = SimulationContext(
                goal_id="goal-2",
                goal_description="Finish the current execution.",
                goal_type="execution",
                current_progress=0.5,
                last_action={"selected_tool": "verification_runner"},
                last_outcome="failure",
                active_constraints=[],
                retry_count=0,
                repair_count=0,
                session_id="sess-2",
                goal_present=True,
            )

            result = simulator.simulate(context=context)

            self.assertNotEqual(result.recommended_route, RouteType.PAUSE)

    def test_simulator_is_goal_none_safe(self) -> None:
        with self.temp_workspace() as workspace_root:
            simulator = ActionSimulator(workspace_root, memory_facade=None)
            context = SimulationContext(
                goal_id=None,
                goal_description="",
                goal_type="general",
                current_progress=0.2,
                last_action={},
                last_outcome="failure",
                active_constraints=[],
                retry_count=0,
                repair_count=0,
                session_id="sess-3",
                goal_present=False,
            )

            result = simulator.simulate(context=context)

            self.assertIsNotNone(result.recommended_route)
            self.assertTrue(all(0.0 <= route.goal_alignment <= 1.0 for route in result.routes))

    def test_high_risk_hard_constraint_routes_are_suppressed(self) -> None:
        with self.temp_workspace() as workspace_root:
            simulator = ActionSimulator(workspace_root, memory_facade=None)
            context = SimulationContext(
                goal_id="goal-4",
                goal_description="Preserve safety under hard constraints.",
                goal_type="safety",
                current_progress=0.9,
                last_action={"selected_tool": "verification_runner"},
                last_outcome="dependency_missing",
                active_constraints=["hard-scope"],
                retry_count=3,
                repair_count=2,
                session_id="sess-4",
                goal_present=True,
                hard_constraint_active=True,
            )

            result = simulator.simulate(context=context)

            retry_route = result.route_for(RouteType.RETRY)
            assert retry_route is not None
            self.assertTrue(retry_route.metadata.get("filtered_for_hard_constraints", False))
