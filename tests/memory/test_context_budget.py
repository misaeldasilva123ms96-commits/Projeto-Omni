from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.memory.context_budget import ContextBudgetManager  # noqa: E402


class ContextBudgetManagerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = ContextBudgetManager()

    def test_simple_query_gets_low_budget(self) -> None:
        budget = self.manager.select_budget(
            task_type="simple_query",
            execution_strategy="direct_response",
            risk_level="low",
            verification_intensity="low",
        )
        self.assertEqual(budget.budget_level, "low")
        self.assertFalse(budget.summarization_required)

    def test_repository_analysis_gets_medium_budget(self) -> None:
        budget = self.manager.select_budget(
            task_type="repository_analysis",
            execution_strategy="analyze_then_report",
            risk_level="low",
            verification_intensity="medium",
        )
        self.assertEqual(budget.budget_level, "medium")

    def test_code_mutation_gets_high_budget(self) -> None:
        budget = self.manager.select_budget(
            task_type="code_mutation",
            execution_strategy="plan_then_execute",
            risk_level="high",
            verification_intensity="high",
        )
        self.assertEqual(budget.budget_level, "high")

    def test_large_engineering_requires_summarization(self) -> None:
        budget = self.manager.select_budget(
            task_type="code_mutation",
            execution_strategy="multi_step_engineering",
            risk_level="high",
            verification_intensity="high",
        )
        self.assertTrue(budget.summarization_required)
        plan = self.manager.build_retrieval_plan(task_type="code_mutation", budget=budget)
        self.assertIn("decision_memory", plan.summarized_memory_types)

    def test_budget_output_is_deterministic(self) -> None:
        first = self.manager.select_budget(
            task_type="reporting",
            execution_strategy="report_only",
            risk_level="low",
            verification_intensity="low",
        )
        second = self.manager.select_budget(
            task_type="reporting",
            execution_strategy="report_only",
            risk_level="low",
            verification_intensity="low",
        )
        self.assertEqual(first.as_dict(), second.as_dict())


if __name__ == "__main__":
    unittest.main()
