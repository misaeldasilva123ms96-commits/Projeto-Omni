from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.simulation import RouteSimulation, RouteType, SimulationBasis, SimulationResult  # noqa: E402


class SimulationModelsTest(unittest.TestCase):
    def test_simulation_result_serializes_all_routes(self) -> None:
        result = SimulationResult.build(
            recommended_route=RouteType.RETRY,
            routes=[
                RouteSimulation(RouteType.RETRY, 0.6, 0.3, 0.2, 0.7, [], "retry", 0.7),
                RouteSimulation(RouteType.REPAIR, 0.6, 0.4, 0.3, 0.75, [], "repair", 0.7),
                RouteSimulation(RouteType.REPLAN, 0.5, 0.5, 0.4, 0.55, [], "replan", 0.7),
                RouteSimulation(RouteType.PAUSE, 0.2, 0.05, 0.1, 0.2, [], "pause", 0.7),
            ],
            simulation_basis=SimulationBasis(1, [], None, False),
            goal_id="goal-model",
        )

        payload = result.as_dict()
        self.assertEqual(len(payload["routes"]), 4)
        self.assertEqual(payload["recommended_route"], "retry")
