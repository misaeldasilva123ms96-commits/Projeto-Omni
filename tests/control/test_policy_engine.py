from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.control.evidence_gate import EvidenceGateResult  # noqa: E402
from brain.control.mode_engine import RuntimeMode  # noqa: E402
from brain.control.policy_engine import PolicyEngine  # noqa: E402


class PolicyEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = PolicyEngine()

    def test_execution_policy_blocks_mutate_in_explore(self) -> None:
        result = self.engine.evaluate_execution_policy(RuntimeMode.EXPLORE, "mutate")
        self.assertFalse(result.allowed)
        self.assertEqual(result.policy_name, "ExecutionPolicy")

    def test_mutation_policy_blocks_high_risk_without_evidence(self) -> None:
        result = self.engine.evaluate_mutation_policy(
            "code_mutation",
            "high",
            EvidenceGateResult(
                enough_evidence=False,
                missing_evidence_types=["file_evidence", "runtime_evidence"],
                recommendation="gather_file_or_runtime_evidence_before_mutation",
                severity="high",
            ),
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.policy_name, "MutationPolicy")

    def test_scope_policy_blocks_missing_scope_metadata(self) -> None:
        result = self.engine.evaluate_scope_policy("code_mutation", {})
        self.assertFalse(result.allowed)
        self.assertEqual(result.policy_name, "ScopePolicy")

    def test_allow_path_returns_structured_bundle(self) -> None:
        bundle = self.engine.evaluate_policies(
            mode=RuntimeMode.VERIFY,
            requested_action="test",
            task_type="verification",
            risk_level="medium",
            metadata={},
            evidence_result=EvidenceGateResult(
                enough_evidence=True,
                missing_evidence_types=[],
                recommendation="proceed_verification",
                severity="info",
            ),
        )
        self.assertTrue(bundle.allowed)
        self.assertTrue(bundle.results)
        self.assertEqual(bundle.blocking_results, [])


if __name__ == "__main__":
    unittest.main()
