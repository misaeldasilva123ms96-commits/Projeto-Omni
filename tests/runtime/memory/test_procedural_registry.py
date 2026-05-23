from __future__ import annotations

import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.memory.procedural import ProceduralPattern, ProceduralRegistry  # noqa: E402


class ProceduralRegistryTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-memory"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"procedural-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_procedural_registry_returns_bounded_recommendation(self) -> None:
        with self.temp_workspace() as workspace_root:
            registry = ProceduralRegistry(workspace_root)
            registry.upsert(
                ProceduralPattern(
                    pattern_id="pattern-1",
                    name="execution:continue_execution",
                    description="Continue when the plan remains healthy.",
                    applicable_goal_types=["execution"],
                    applicable_constraint_types=["scope"],
                    recommended_route="continue_execution",
                    success_rate=0.9,
                    sample_size=6,
                    last_updated="2026-04-11T12:00:00+00:00",
                    metadata={},
                )
            )

            recommendation = registry.best_pattern_for(goal_type="execution", constraint_types=["scope"])
            assert recommendation is not None
            self.assertEqual(recommendation.recommended_route, "continue_execution")
