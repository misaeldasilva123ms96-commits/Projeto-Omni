from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.control.evidence_gate import EvidenceGate  # noqa: E402


class EvidenceGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.gate = EvidenceGate()

    def test_read_only_low_risk_task_passes(self) -> None:
        result = self.gate.evaluate_evidence(task_type="simple_query", risk_level="low", available_evidence={})
        self.assertTrue(result.enough_evidence)
        self.assertEqual(result.recommendation, "proceed_read_only")

    def test_code_mutation_without_evidence_is_blocked(self) -> None:
        result = self.gate.evaluate_evidence(task_type="code_mutation", risk_level="high", available_evidence={})
        self.assertFalse(result.enough_evidence)
        self.assertEqual(
            result.recommendation,
            "gather_file_or_runtime_evidence_before_mutation",
        )
        self.assertIn("file_evidence", result.missing_evidence_types)
        self.assertIn("runtime_evidence", result.missing_evidence_types)

    def test_code_mutation_with_file_evidence_passes(self) -> None:
        result = self.gate.evaluate_evidence(
            task_type="code_mutation",
            risk_level="high",
            available_evidence={"file_evidence": True},
        )
        self.assertTrue(result.enough_evidence)


if __name__ == "__main__":
    unittest.main()
