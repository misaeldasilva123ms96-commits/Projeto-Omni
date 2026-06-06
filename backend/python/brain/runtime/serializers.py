from __future__ import annotations

from typing import Any

from brain.control.evidence_gate import EvidenceGateResult
from brain.control.policy_engine import PolicyBundleResult, PolicyResult
from brain.memory.context_budget import ContextBudgetDecision, RetrievalPlan


def policy_result_to_dict(result: PolicyResult) -> dict[str, Any]:
    return {
        "allowed": result.allowed,
        "policy_name": result.policy_name,
        "reason": result.reason,
        "severity": result.severity,
        "details": result.details,
    }


def bundle_to_dict(bundle: PolicyBundleResult) -> dict[str, Any]:
    return {
        "allowed": bundle.allowed,
        "results": [policy_result_to_dict(item) for item in bundle.results],
        "blocking_results": [policy_result_to_dict(item) for item in bundle.blocking_results],
    }


def evidence_to_dict(evidence: EvidenceGateResult) -> dict[str, Any]:
    return {
        "enough_evidence": evidence.enough_evidence,
        "missing_evidence_types": evidence.missing_evidence_types,
        "recommendation": evidence.recommendation,
        "severity": evidence.severity,
    }


def budget_to_dict(budget: ContextBudgetDecision) -> dict[str, Any]:
    return budget.as_dict()


def retrieval_plan_to_dict(plan: RetrievalPlan) -> dict[str, Any]:
    return plan.as_dict()


def history_limit_for_budget(budget_level: str) -> int:
    return {"low": 2, "medium": 4, "high": 6}.get(budget_level, 4)


def summary_limit_for_budget(budget_level: str) -> int:
    return {"low": 600, "medium": 1200, "high": 1800}.get(budget_level, 1200)
