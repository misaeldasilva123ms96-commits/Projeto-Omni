"""Types for controlled PR creation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class ControlledPRCreatorRequest:
    pr_creation_gate_result: Optional[dict[str, Any]] = None
    push_executor_result: Optional[dict[str, Any]] = None
    push_gate_result: Optional[dict[str, Any]] = None
    requested_by: str = "unknown"
    creator_mode: str = "disabled"
    repository_full_name: Optional[str] = None
    source_branch: Optional[str] = None
    head_branch: Optional[str] = None
    base_branch: str = "main"
    current_branch: Optional[str] = None
    remote_branch: Optional[str] = None
    pushed_ref: Optional[str] = None
    pushed_remote: Optional[str] = None
    commit_sha: Optional[str] = None
    pr_title: Optional[str] = None
    pr_body: Optional[str] = None
    draft: bool = True
    labels: list[str] = field(default_factory=list)
    reviewers: list[str] = field(default_factory=list)
    assignees: list[str] = field(default_factory=list)
    related_phase: Optional[str] = None
    related_pr: Optional[str] = None
    require_pr_gate_eligible: bool = True
    require_push_executed: bool = True
    require_non_main_head: bool = True
    require_base_main: bool = True
    require_runtime_truth: bool = True
    require_clean_evidence: bool = True
    require_commit_sha: bool = True
    allow_pr_creation: bool = True
    allow_ready_pr: bool = True
    allow_draft_pr: bool = True
    allow_labels: bool = False
    allow_reviewers: bool = False
    allow_assignees: bool = False
    allow_merge: bool = False
    allow_auto_merge: bool = False
    allow_push: bool = False
    allow_force_push: bool = False
    allow_main_push: bool = False
    allow_git_mutation: bool = False
    allow_command_execution: bool = False
    allow_network: bool = True
    allow_provider_call: bool = False
    allow_agent_call: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ControlledPRCreatorResult:
    pr_created: bool
    blocked: bool
    dry_run: bool
    success: bool
    partial: bool
    creator_mode: str
    requested_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    repository_full_name: Optional[str]
    source_branch: Optional[str]
    head_branch: Optional[str]
    base_branch: str
    current_branch: Optional[str]
    remote_branch: Optional[str]
    pushed_ref: Optional[str]
    pushed_remote: Optional[str]
    commit_sha: Optional[str]
    pr_gate_eligible: bool
    push_was_executed: bool
    title_safe: bool
    body_safe: bool
    repository_safe: bool
    branch_safe: bool
    labels_safe: bool
    reviewers_safe: bool
    assignees_safe: bool
    final_pr_title: Optional[str]
    final_pr_body: Optional[str]
    final_draft: bool
    final_labels: list[str]
    final_reviewers: list[str]
    final_assignees: list[str]
    github_operations_attempted: list[str]
    github_operations_completed: list[str]
    github_operations_blocked: list[str]
    duplicate_pr_detected: bool
    existing_pr_url: Optional[str]
    pr_number: Optional[int]
    pr_url: Optional[str]
    pr_node_id: Optional[str]
    pr_state: Optional[str]
    can_merge: bool
    can_auto_merge: bool
    can_push: bool
    can_force_push: bool
    can_push_main: bool
    can_rebase: bool
    can_create_branch: bool
    can_checkout: bool
    can_edit_code: bool
    can_apply_patch: bool
    can_call_provider: bool
    can_call_agent: bool
    requires_ci_monitor_phase: bool
    requires_merge_gate_phase: bool
    requires_human_intervention: bool
    reason: str
    blocked_reason: Optional[str]
    escalation_reason: Optional[str]
    runtime_truth: dict[str, object]
    evidence_version: str
    redacted: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
