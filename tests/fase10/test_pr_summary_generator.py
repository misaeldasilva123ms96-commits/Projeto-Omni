from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.pr_summary_generator import build_pr_summary  # noqa: E402


class PrSummaryGeneratorTest(unittest.TestCase):
    def test_build_pr_summary_with_valid_inputs(self) -> None:
        summary = build_pr_summary(
            message="corrija testes",
            milestone_state={"milestones": [{"state": "completed"}]},
            patch_sets=[{"affected_files": ["a.py", "b.py"]}],
            verification_summary={"ok": True},
            repository_analysis={"language_profile": {"dominant_language": "python"}},
            impact_analysis={"integration_risk_summary": {"flags": ["module-coupling"]}},
        )
        self.assertEqual(summary["merge_readiness"]["status"], "ready")
        self.assertEqual(summary["files_changed"], ["a.py", "b.py"])
        self.assertEqual(summary["why"]["dominant_language"], "python")

    def test_build_pr_summary_handles_missing_inputs_safely(self) -> None:
        summary = build_pr_summary(
            message="",
            milestone_state=None,
            patch_sets=None,
            verification_summary=None,
            repository_analysis=None,
            impact_analysis=None,
        )
        self.assertIsInstance(summary["files_changed"], list)
        self.assertEqual(summary["merge_readiness"]["status"], "needs-review")
        self.assertIsInstance(summary["known_risks"], list)


if __name__ == "__main__":
    unittest.main()
