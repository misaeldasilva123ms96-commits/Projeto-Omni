from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.evolution.evaluator import Evaluator  # noqa: E402
from brain.evolution.strategy_updater import StrategyUpdater  # noqa: E402


class EvolutionSafetyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.evolution_dir = PROJECT_ROOT / ".phase9-temp" / f"fase2-evolution-{uuid4().hex[:8]}"
        shutil.rmtree(self.evolution_dir, ignore_errors=True)
        self.updater = StrategyUpdater(self.evolution_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.evolution_dir, ignore_errors=True)

    def test_evaluation_path_returns_structured_result(self) -> None:
        result = Evaluator().evaluate(
            session_id="fase2",
            message="como funciona o runtime",
            response="O runtime funciona com orquestracao entre Rust, Python e Node para responder a tarefa.",
            history=[{"content": "explique o runtime"}],
        )
        self.assertIn("overall", result)
        self.assertIn("scores", result)
        self.assertIsInstance(result["flags"], list)

    def test_strategy_update_and_rollback_keep_state_readable(self) -> None:
        proposal = self.updater.propose_update(
            {
                "recommended_adjustments": [{"action": "raise_priority", "reason": "planning helped"}],
                "underused_capabilities": ["give_advice"],
                "weak_patterns": ["short replies"],
            },
            average_score=0.72,
        )
        updated = self.updater.apply_update(proposal)
        state_on_disk = json.loads((self.evolution_dir / "strategy_state.json").read_text(encoding="utf-8"))
        self.assertEqual(updated["version"], 1)
        self.assertEqual(state_on_disk["version"], 1)

        rolled_back = self.updater.rollback(1)
        self.assertEqual(rolled_back["version"], 1)
        reloaded = self.updater.load_current_state()
        self.assertEqual(reloaded["version"], 1)
        self.assertIn("create_plan", reloaded["capability_weights"])


if __name__ == "__main__":
    unittest.main()
