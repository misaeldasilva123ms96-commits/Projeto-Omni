from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.language import normalize_input_to_oil_request  # noqa: E402
from brain.runtime.strategy.strategy_engine import StrategyEngine  # noqa: E402
from brain.runtime.strategy.strategy_rules import conservative_fallback_strategy  # noqa: E402


class StrategyEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = PROJECT_ROOT / ".logs" / "test-strategy35" / f"s-{uuid4().hex[:8]}"
        self.root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.root.parent, ignore_errors=True)

    def _oil(self, text: str) -> object:
        return normalize_input_to_oil_request(
            text,
            session_id="sess",
            run_id="",
            metadata={"source_component": "test", "confidence": 0.5},
        )

    def test_critical_message_selects_guarded_critical(self) -> None:
        eng = StrategyEngine(self.root)
        msg = "We must rotate production credentials and audit security."
        oil = self._oil(msg)
        dec = eng.select(
            session_id="sess",
            run_id="",
            message=msg,
            oil_request=oil,
            memory_context={"selected_count": 0},
            learning_record=None,
        )
        self.assertEqual(dec.selected_strategy.mode, "critical")
        self.assertEqual(dec.selected_strategy.path, "guarded")
        self.assertEqual(dec.fallback_strategy.mode, conservative_fallback_strategy().mode)
        self.assertGreater(len(dec.signals_used), 0)

    def test_learning_failure_deepens_strategy(self) -> None:
        eng = StrategyEngine(self.root)
        oil = self._oil("What is 2+2?")
        learning = {
            "record_id": "lr-test",
            "assessment": {"outcome_class": "failure", "duration_ms": 100},
            "signals": [{"polarity": "negative"}, {"polarity": "negative"}],
        }
        dec = eng.select(
            session_id="sess",
            run_id="",
            message="What is 2+2?",
            oil_request=oil,
            memory_context={"selected_count": 0},
            learning_record=learning,
        )
        self.assertIn("learning_outcome:failure", dec.signals_used)
        self.assertEqual(dec.selected_strategy.path, "guarded")
        self.assertIn(dec.selected_strategy.mode, {"deep", "critical"})

    def test_slow_success_downgrades_deep(self) -> None:
        eng = StrategyEngine(self.root)
        long_msg = ("Explain repository architecture trade-offs and migration risks. " * 6).strip()
        self.assertGreater(len(long_msg), 160)
        oil = self._oil(long_msg)
        learning = {
            "record_id": "lr-slow",
            "assessment": {"outcome_class": "success", "duration_ms": 50_000},
            "signals": [{"polarity": "positive"}],
        }
        dec = eng.select(
            session_id="sess",
            run_id="",
            message=long_msg,
            oil_request=oil,
            memory_context={"selected_count": 1},
            learning_record=learning,
        )
        self.assertEqual(dec.selected_strategy.mode, "fast")


if __name__ == "__main__":
    unittest.main()
