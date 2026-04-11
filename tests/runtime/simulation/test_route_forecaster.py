from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.memory.episodic import Episode  # noqa: E402
from brain.runtime.simulation import RouteType, SimulationContext  # noqa: E402
from brain.runtime.simulation.route_forecaster import RouteForecaster  # noqa: E402


class RouteForecasterTest(unittest.TestCase):
    def test_route_forecaster_falls_back_to_heuristic_when_history_below_threshold(self) -> None:
        forecaster = RouteForecaster()
        context = SimulationContext(
            goal_id="goal-1",
            goal_description="Retry the failed execution safely.",
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
        route, used_heuristic = forecaster.forecast(route=RouteType.RETRY, context=context, episodes=[])

        self.assertTrue(used_heuristic)
        self.assertEqual(route.metadata["forecast_mode"], "heuristic")
        self.assertLess(route.confidence, 0.5)

    def test_route_forecaster_uses_episode_based_estimation_when_history_is_sufficient(self) -> None:
        forecaster = RouteForecaster()
        context = SimulationContext(
            goal_id="goal-2",
            goal_description="Repair before continuing.",
            goal_type="repair",
            current_progress=0.3,
            last_action={"selected_tool": "filesystem_patch_set"},
            last_outcome="failure",
            active_constraints=[],
            retry_count=0,
            repair_count=1,
            session_id="sess-2",
            goal_present=True,
        )
        episodes = [
            Episode(
                episode_id=f"episode-{index}",
                goal_id="goal-2",
                subgoal_id=None,
                session_id="sess-2",
                description="Repair attempt",
                event_type="continuation_decision",
                outcome="repair",
                progress_at_start=0.2,
                progress_at_end=0.4,
                constraints_active=[],
                evidence_ids=[],
                duration_seconds=5.0,
                created_at=f"2026-04-11T12:00:0{index}+00:00",
                metadata={"decision_type": "repair", "goal_type": "repair"},
            )
            for index in range(3)
        ]

        route, used_heuristic = forecaster.forecast(route=RouteType.REPAIR, context=context, episodes=episodes)

        self.assertFalse(used_heuristic)
        self.assertEqual(route.metadata["forecast_mode"], "history")
        self.assertGreaterEqual(route.confidence, 0.69)
