from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ContextBudgetDecision:
    budget_level: str
    max_context_items: int
    preferred_memory_order: list[str]
    summarization_required: bool
    excluded_context_types: list[str]
    reason: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RetrievalPlan:
    memory_types_to_load: list[str]
    load_order: list[str]
    summarized_memory_types: list[str]
    omitted_memory_types: list[str]
    reason: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class ContextBudgetManager:
    def select_budget(
        self,
        *,
        task_type: str,
        execution_strategy: str,
        risk_level: str,
        verification_intensity: str,
    ) -> ContextBudgetDecision:
        if task_type == "simple_query":
            return ContextBudgetDecision(
                budget_level="low",
                max_context_items=3,
                preferred_memory_order=["working_memory"],
                summarization_required=False,
                excluded_context_types=["decision_memory", "evidence_memory"],
                reason="simple conversational request keeps context narrow",
            )
        if task_type == "repository_analysis":
            return ContextBudgetDecision(
                budget_level="medium",
                max_context_items=6,
                preferred_memory_order=["working_memory", "evidence_memory", "decision_memory"],
                summarization_required=False,
                excluded_context_types=[],
                reason="repository analysis benefits from evidence-backed context",
            )
        if task_type == "reporting":
            return ContextBudgetDecision(
                budget_level="low",
                max_context_items=4,
                preferred_memory_order=["decision_memory", "working_memory"],
                summarization_required=True,
                excluded_context_types=["evidence_memory"],
                reason="reporting prefers summarized prior decisions over raw execution context",
            )
        if task_type == "recovery":
            return ContextBudgetDecision(
                budget_level="high" if risk_level == "high" or verification_intensity == "high" else "medium",
                max_context_items=8 if risk_level == "high" else 6,
                preferred_memory_order=["evidence_memory", "decision_memory", "working_memory"],
                summarization_required=False,
                excluded_context_types=[],
                reason="recovery requires recent evidence and decision trail",
            )
        if task_type == "verification":
            return ContextBudgetDecision(
                budget_level="medium",
                max_context_items=6,
                preferred_memory_order=["evidence_memory", "working_memory", "decision_memory"],
                summarization_required=False,
                excluded_context_types=[],
                reason="verification needs evidence-first context without loading broad history",
            )
        if task_type == "code_mutation":
            is_large = execution_strategy == "multi_step_engineering"
            return ContextBudgetDecision(
                budget_level="high",
                max_context_items=10 if is_large else 8,
                preferred_memory_order=["working_memory", "evidence_memory", "decision_memory"],
                summarization_required=is_large,
                excluded_context_types=[],
                reason="mutation requires high-context, evidence-backed execution planning",
            )
        return ContextBudgetDecision(
            budget_level="medium",
            max_context_items=5,
            preferred_memory_order=["working_memory"],
            summarization_required=False,
            excluded_context_types=[],
            reason="default balanced context budget",
        )

    def build_retrieval_plan(
        self,
        *,
        task_type: str,
        budget: ContextBudgetDecision,
    ) -> RetrievalPlan:
        if task_type == "simple_query":
            return RetrievalPlan(
                memory_types_to_load=["working_memory"],
                load_order=["working_memory"],
                summarized_memory_types=[],
                omitted_memory_types=["decision_memory", "evidence_memory"],
                reason="simple query loads only current working state",
            )
        if task_type == "repository_analysis":
            return RetrievalPlan(
                memory_types_to_load=["working_memory", "evidence_memory", "decision_memory"],
                load_order=budget.preferred_memory_order,
                summarized_memory_types=["decision_memory"] if budget.summarization_required else [],
                omitted_memory_types=budget.excluded_context_types,
                reason="repository analysis loads working state plus evidence and selected decisions",
            )
        if task_type == "code_mutation":
            summarized = ["decision_memory", "evidence_memory"] if budget.summarization_required else []
            return RetrievalPlan(
                memory_types_to_load=["working_memory", "evidence_memory", "decision_memory"],
                load_order=budget.preferred_memory_order,
                summarized_memory_types=summarized,
                omitted_memory_types=budget.excluded_context_types,
                reason="mutation routing loads planning context, evidence, and reusable decisions",
            )
        if task_type == "verification":
            return RetrievalPlan(
                memory_types_to_load=["evidence_memory", "working_memory", "decision_memory"],
                load_order=budget.preferred_memory_order,
                summarized_memory_types=[],
                omitted_memory_types=budget.excluded_context_types,
                reason="verification prioritizes evidence and current execution context",
            )
        if task_type == "recovery":
            return RetrievalPlan(
                memory_types_to_load=["evidence_memory", "decision_memory", "working_memory"],
                load_order=budget.preferred_memory_order,
                summarized_memory_types=["decision_memory"] if budget.summarization_required else [],
                omitted_memory_types=budget.excluded_context_types,
                reason="recovery loads failure evidence before broader working context",
            )
        if task_type == "reporting":
            return RetrievalPlan(
                memory_types_to_load=["decision_memory", "working_memory"],
                load_order=budget.preferred_memory_order,
                summarized_memory_types=["decision_memory", "working_memory"],
                omitted_memory_types=budget.excluded_context_types,
                reason="reporting prefers summarized decisions and working-memory highlights",
            )
        return RetrievalPlan(
            memory_types_to_load=["working_memory"],
            load_order=["working_memory"],
            summarized_memory_types=[],
            omitted_memory_types=[],
            reason="default retrieval plan",
        )
