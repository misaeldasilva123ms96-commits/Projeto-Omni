from __future__ import annotations

import pytest

from brain.memory.context_budget import ContextBudgetDecision, ContextBudgetManager, RetrievalPlan


@pytest.fixture
def manager() -> ContextBudgetManager:
    return ContextBudgetManager()


class TestContextBudgetDecision:
    def test_as_dict_shape(self):
        decision = ContextBudgetDecision(
            budget_level="low",
            max_context_items=3,
            preferred_memory_order=["working_memory"],
            summarization_required=False,
            excluded_context_types=[],
            reason="test",
        )
        d = decision.as_dict()
        assert d["budget_level"] == "low"
        assert d["max_context_items"] == 3
        assert d["summarization_required"] is False
        assert isinstance(d["excluded_context_types"], list)

    def test_is_frozen(self):
        decision = ContextBudgetDecision(
            budget_level="low",
            max_context_items=3,
            preferred_memory_order=[],
            summarization_required=False,
            excluded_context_types=[],
            reason="r",
        )
        with pytest.raises(AttributeError):
            decision.budget_level = "high"


class TestRetrievalPlan:
    def test_as_dict_shape(self):
        plan = RetrievalPlan(
            memory_types_to_load=["working_memory"],
            load_order=["working_memory"],
            summarized_memory_types=[],
            omitted_memory_types=[],
            reason="test",
        )
        d = plan.as_dict()
        assert isinstance(d["memory_types_to_load"], list)
        assert isinstance(d["load_order"], list)
        assert isinstance(d["summarized_memory_types"], list)
        assert isinstance(d["omitted_memory_types"], list)

    def test_is_frozen(self):
        plan = RetrievalPlan(
            memory_types_to_load=[],
            load_order=[],
            summarized_memory_types=[],
            omitted_memory_types=[],
            reason="r",
        )
        with pytest.raises(AttributeError):
            plan.memory_types_to_load = ["working_memory"]


class TestSelectBudget:
    def test_simple_query(self, manager: ContextBudgetManager):
        decision = manager.select_budget(
            task_type="simple_query",
            execution_strategy="default",
            risk_level="low",
            verification_intensity="low",
        )
        assert decision.budget_level == "low"
        assert decision.max_context_items == 3
        assert decision.summarization_required is False
        assert "decision_memory" in decision.excluded_context_types

    def test_repository_analysis(self, manager: ContextBudgetManager):
        decision = manager.select_budget(
            task_type="repository_analysis",
            execution_strategy="default",
            risk_level="low",
            verification_intensity="low",
        )
        assert decision.budget_level == "medium"
        assert decision.max_context_items == 6

    def test_reporting(self, manager: ContextBudgetManager):
        decision = manager.select_budget(
            task_type="reporting",
            execution_strategy="default",
            risk_level="low",
            verification_intensity="low",
        )
        assert decision.budget_level == "low"
        assert decision.summarization_required is True

    def test_recovery_low_risk(self, manager: ContextBudgetManager):
        decision = manager.select_budget(
            task_type="recovery",
            execution_strategy="default",
            risk_level="low",
            verification_intensity="low",
        )
        assert decision.budget_level == "medium"
        assert decision.max_context_items == 6

    def test_recovery_high_risk(self, manager: ContextBudgetManager):
        decision = manager.select_budget(
            task_type="recovery",
            execution_strategy="default",
            risk_level="high",
            verification_intensity="low",
        )
        assert decision.budget_level == "high"
        assert decision.max_context_items == 8

    def test_recovery_high_verification(self, manager: ContextBudgetManager):
        decision = manager.select_budget(
            task_type="recovery",
            execution_strategy="default",
            risk_level="low",
            verification_intensity="high",
        )
        assert decision.budget_level == "high"

    def test_verification(self, manager: ContextBudgetManager):
        decision = manager.select_budget(
            task_type="verification",
            execution_strategy="default",
            risk_level="low",
            verification_intensity="low",
        )
        assert decision.budget_level == "medium"
        assert decision.max_context_items == 6

    def test_code_mutation_default(self, manager: ContextBudgetManager):
        decision = manager.select_budget(
            task_type="code_mutation",
            execution_strategy="default",
            risk_level="low",
            verification_intensity="low",
        )
        assert decision.budget_level == "high"
        assert decision.max_context_items == 8
        assert decision.summarization_required is False

    def test_code_mutation_multi_step(self, manager: ContextBudgetManager):
        decision = manager.select_budget(
            task_type="code_mutation",
            execution_strategy="multi_step_engineering",
            risk_level="low",
            verification_intensity="low",
        )
        assert decision.budget_level == "high"
        assert decision.max_context_items == 10
        assert decision.summarization_required is True

    def test_default_unknown_type(self, manager: ContextBudgetManager):
        decision = manager.select_budget(
            task_type="unknown",
            execution_strategy="default",
            risk_level="low",
            verification_intensity="low",
        )
        assert decision.budget_level == "medium"
        assert decision.max_context_items == 5


class TestBuildRetrievalPlan:
    def test_simple_query(self, manager: ContextBudgetManager):
        budget = manager.select_budget(
            task_type="simple_query",
            execution_strategy="default",
            risk_level="low",
            verification_intensity="low",
        )
        plan = manager.build_retrieval_plan(task_type="simple_query", budget=budget)
        assert plan.memory_types_to_load == ["working_memory"]
        assert "decision_memory" in plan.omitted_memory_types

    def test_repository_analysis(self, manager: ContextBudgetManager):
        budget = manager.select_budget(
            task_type="repository_analysis",
            execution_strategy="default",
            risk_level="low",
            verification_intensity="low",
        )
        plan = manager.build_retrieval_plan(task_type="repository_analysis", budget=budget)
        assert "evidence_memory" in plan.memory_types_to_load
        assert plan.load_order == budget.preferred_memory_order

    def test_code_mutation(self, manager: ContextBudgetManager):
        budget = manager.select_budget(
            task_type="code_mutation",
            execution_strategy="multi_step_engineering",
            risk_level="low",
            verification_intensity="low",
        )
        plan = manager.build_retrieval_plan(task_type="code_mutation", budget=budget)
        assert "decision_memory" in plan.summarized_memory_types
        assert "evidence_memory" in plan.summarized_memory_types

    def test_verification(self, manager: ContextBudgetManager):
        budget = manager.select_budget(
            task_type="verification",
            execution_strategy="default",
            risk_level="low",
            verification_intensity="low",
        )
        plan = manager.build_retrieval_plan(task_type="verification", budget=budget)
        assert plan.memory_types_to_load == ["evidence_memory", "working_memory", "decision_memory"]

    def test_recovery(self, manager: ContextBudgetManager):
        budget = manager.select_budget(
            task_type="recovery",
            execution_strategy="default",
            risk_level="high",
            verification_intensity="low",
        )
        plan = manager.build_retrieval_plan(task_type="recovery", budget=budget)
        assert plan.memory_types_to_load == ["evidence_memory", "decision_memory", "working_memory"]

    def test_reporting(self, manager: ContextBudgetManager):
        budget = manager.select_budget(
            task_type="reporting",
            execution_strategy="default",
            risk_level="low",
            verification_intensity="low",
        )
        plan = manager.build_retrieval_plan(task_type="reporting", budget=budget)
        assert "decision_memory" in plan.summarized_memory_types
        assert "working_memory" in plan.summarized_memory_types

    def test_default_unknown_type(self, manager: ContextBudgetManager):
        budget = manager.select_budget(
            task_type="unknown",
            execution_strategy="default",
            risk_level="low",
            verification_intensity="low",
        )
        plan = manager.build_retrieval_plan(task_type="unknown", budget=budget)
        assert plan.memory_types_to_load == ["working_memory"]
        assert plan.reason == "default retrieval plan"
