from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.control.capability_router import CapabilityRouter  # noqa: E402


class CapabilityRouterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.router = CapabilityRouter()

    def test_simple_query_route(self) -> None:
        decision = self.router.classify_task("explique este fluxo")
        self.assertEqual(decision.task_type, "simple_query")
        self.assertEqual(decision.preferred_mode.value, "EXPLORE")
        self.assertEqual(decision.risk_level, "low")
        self.assertEqual(decision.execution_strategy, "direct_response")
        self.assertEqual(decision.verification_intensity, "low")
        self.assertEqual(decision.recommended_specialists, [])
        self.assertFalse(decision.specialist_delegation_recommended)

    def test_repository_analysis_route(self) -> None:
        decision = self.router.classify_task("analise o repositorio e dependencias")
        self.assertEqual(decision.task_type, "repository_analysis")
        self.assertEqual(decision.execution_strategy, "analyze_then_report")
        self.assertEqual(decision.verification_intensity, "medium")
        self.assertIn("repoImpactAnalyzer", decision.recommended_specialists)
        self.assertTrue(decision.specialist_delegation_recommended)

    def test_single_file_code_mutation_route(self) -> None:
        decision = self.router.classify_task("corrija este arquivo e aplique o patch")
        self.assertEqual(decision.task_type, "code_mutation")
        self.assertEqual(decision.preferred_mode.value, "PLAN")
        self.assertEqual(decision.risk_level, "high")
        self.assertEqual(decision.execution_strategy, "plan_then_execute")
        self.assertEqual(decision.verification_intensity, "high")
        self.assertIn("advancedPlannerSpecialist", decision.recommended_specialists)
        self.assertIn("dependencyImpactSpecialist", decision.recommended_specialists)
        self.assertIn("testSelectionSpecialist", decision.recommended_specialists)
        self.assertTrue(decision.specialist_delegation_recommended)

    def test_large_task_mutation_route(self) -> None:
        decision = self.router.classify_task(
            "faça uma mudanca ampla em varios arquivos por todo o repositorio"
        )
        self.assertEqual(decision.task_type, "code_mutation")
        self.assertEqual(decision.preferred_mode.value, "PLAN")
        self.assertEqual(decision.execution_strategy, "multi_step_engineering")
        self.assertEqual(decision.verification_intensity, "high")
        self.assertEqual(decision.risk_level, "high")

    def test_large_task_detection_from_metadata(self) -> None:
        decision = self.router.classify_task(
            "corrija o fluxo",
            metadata={"target_files": ["a.py", "b.py"]},
        )
        self.assertEqual(decision.task_type, "code_mutation")
        self.assertEqual(decision.execution_strategy, "multi_step_engineering")

    def test_verification_route(self) -> None:
        decision = self.router.classify_task("rode os testes e valide")
        self.assertEqual(decision.task_type, "verification")
        self.assertEqual(decision.preferred_mode.value, "VERIFY")
        self.assertEqual(decision.execution_strategy, "verify_only")
        self.assertEqual(decision.verification_intensity, "high")
        self.assertIn("testSelectionSpecialist", decision.recommended_specialists)

    def test_recovery_route(self) -> None:
        decision = self.router.classify_task("debug why this failed and retry after failure")
        self.assertEqual(decision.task_type, "recovery")
        self.assertEqual(decision.preferred_mode.value, "RECOVER")
        self.assertEqual(decision.execution_strategy, "recover_then_verify")
        self.assertEqual(decision.verification_intensity, "high")
        self.assertIn("dependencyImpactSpecialist", decision.recommended_specialists)

    def test_reporting_route(self) -> None:
        decision = self.router.classify_task("gere um relatorio da execucao")
        self.assertEqual(decision.task_type, "reporting")
        self.assertEqual(decision.preferred_mode.value, "REPORT")
        self.assertEqual(decision.execution_strategy, "report_only")
        self.assertEqual(decision.verification_intensity, "low")
        self.assertIn("pr_summary_generator", decision.recommended_specialists)


if __name__ == "__main__":
    unittest.main()
