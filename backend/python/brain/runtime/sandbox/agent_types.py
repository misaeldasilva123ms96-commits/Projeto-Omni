"""Types for future supervised agent workflow policy."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class AgentWorkflowRequest:
    agent_id: str
    requested_action: str
    workflow_mode: str = "disabled"
    target_branch: Optional[str] = None
    base_branch: str = "main"
    requested_by: str = "unknown"
    risk_context: dict[str, Any] = field(default_factory=dict)
    requires_human_approval: bool = True
    related_phase: Optional[str] = None
    related_pr: Optional[str] = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AgentWorkflowPolicyDecision:
    allowed: bool
    blocked: bool
    requires_approval: bool
    agent_id: str
    agent_role: str
    requested_action: str
    workflow_mode: str
    category: str
    risk_level: str
    reason: str
    target_branch: str
    base_branch: str
    main_branch_protected: bool
    command_execution_allowed: bool
    direct_file_edit_allowed: bool
    git_push_allowed: bool
    git_merge_allowed: bool
    pr_open_allowed: bool
    network_allowed: bool
    provider_call_allowed: bool
    vault_write_allowed: bool
    mcp_write_allowed: bool
    runtime_truth_required: bool
    sandbox_required: bool
    evidence_version: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
