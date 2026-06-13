"""Types for the Autonomy Operating Model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class AutonomyPolicyRequest:
    requested_level: str = "L1_ADVISORY"
    requested_action: str = "analyze_task"
    requested_by: str = "unknown"
    task_type: Optional[str] = None
    target_branch: Optional[str] = None
    base_branch: str = "main"
    risk_level: Optional[str] = None
    files_changed: list[str] = field(default_factory=list)
    checks_green: bool = False
    secrets_detected: bool = False
    ci_threshold_changed: bool = False
    tests_skipped: bool = False
    security_policy_changed: bool = False
    governance_policy_changed: bool = False
    production_targeted: bool = False
    billing_or_cost_impact: bool = False
    destructive_action_requested: bool = False
    requires_human_decision: bool = False
    related_phase: Optional[str] = None
    related_pr: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AutonomyPolicyDecision:
    allowed: bool
    blocked: bool
    requires_human_intervention: bool
    autonomy_level: str
    requested_action: str
    category: str
    risk_level: str
    reason: str
    escalation_reason: Optional[str]
    target_branch: Optional[str]
    base_branch: str
    main_branch_protected: bool
    can_analyze: bool
    can_plan: bool
    can_edit_branch: bool
    can_run_tests: bool
    can_commit: bool
    can_push_branch: bool
    can_open_pr: bool
    can_repair_ci: bool
    can_merge_pr: bool
    can_write_vault_draft: bool
    can_execute_sandbox: bool
    can_call_provider: bool
    can_use_mcp: bool
    can_push_main: bool
    can_bypass_ci: bool
    can_lower_security: bool
    runtime_truth_required: bool
    report_required: bool
    human_exception_required: bool
    evidence_version: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
