from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.control.mode_engine import RuntimeMode, can_transition, get_allowed_actions  # noqa: E402


class ModeEngineTest(unittest.TestCase):
    def test_all_required_modes_exist(self) -> None:
        self.assertEqual(
            {mode.value for mode in RuntimeMode},
            {"EXPLORE", "PLAN", "EXECUTE", "VERIFY", "RECOVER", "REPORT"},
        )

    def test_valid_transition_passes(self) -> None:
        self.assertTrue(can_transition(RuntimeMode.EXPLORE, RuntimeMode.PLAN))
        self.assertTrue(can_transition(RuntimeMode.EXECUTE, RuntimeMode.RECOVER))

    def test_invalid_transition_fails(self) -> None:
        self.assertFalse(can_transition(RuntimeMode.EXPLORE, RuntimeMode.EXECUTE))
        self.assertFalse(can_transition(RuntimeMode.REPORT, RuntimeMode.VERIFY))

    def test_allowed_actions_are_mode_specific(self) -> None:
        self.assertIn("execute", get_allowed_actions(RuntimeMode.EXECUTE))
        self.assertNotIn("mutate", get_allowed_actions(RuntimeMode.REPORT))


if __name__ == "__main__":
    unittest.main()
