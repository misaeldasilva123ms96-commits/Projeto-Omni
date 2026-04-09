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

    def test_repository_analysis_route(self) -> None:
        decision = self.router.classify_task("analise o repositorio e dependencias")
        self.assertEqual(decision.task_type, "repository_analysis")

    def test_code_mutation_route(self) -> None:
        decision = self.router.classify_task("corrija este arquivo e aplique o patch")
        self.assertEqual(decision.task_type, "code_mutation")
        self.assertEqual(decision.preferred_mode.value, "PLAN")
        self.assertEqual(decision.risk_level, "high")

    def test_verification_route(self) -> None:
        decision = self.router.classify_task("rode os testes e valide")
        self.assertEqual(decision.task_type, "verification")
        self.assertEqual(decision.preferred_mode.value, "VERIFY")

    def test_reporting_route(self) -> None:
        decision = self.router.classify_task("gere um relatorio da execucao")
        self.assertEqual(decision.task_type, "reporting")
        self.assertEqual(decision.preferred_mode.value, "REPORT")


if __name__ == "__main__":
    unittest.main()
