"""Runtime Truth evidence for sandbox policy decisions.

Phase 5 records policy classification outcomes as evidence. It does not execute
commands, perform network access, call MCP, or invoke agents.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional

from .policy_types import PolicyDecision, PolicyInput

SANDBOX_POLICY_EVENT_TYPE = "sandbox.policy_decision"
SANDBOX_POLICY_RUNTIME_MODE = "SANDBOX_POLICY_ONLY"
SANDBOX_EVIDENCE_VERSION = "1.0"


@dataclass(frozen=True)
class SandboxPolicyEvidence:
    event_type: str
    timestamp: str
    sandbox_mode: str
    requested_by: str
    command: str
    normalized_command: str
    policy_allowed: bool
    policy_blocked: bool
    policy_requires_approval: bool
    policy_category: str
    policy_risk_level: str
    policy_reason: str
    matched_rule: Optional[str]
    runtime_mode: str
    execution_attempted: bool
    command_executed: bool
    network_used: bool
    secrets_detected: bool
    governance_decision: str
    evidence_version: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_sandbox_policy_evidence(
    policy_input: PolicyInput,
    policy_decision: PolicyDecision,
    *,
    timestamp: Optional[str] = None,
) -> SandboxPolicyEvidence:
    """Build JSON-safe evidence for a sandbox policy decision."""
    return SandboxPolicyEvidence(
        event_type=SANDBOX_POLICY_EVENT_TYPE,
        timestamp=timestamp or _utc_timestamp(),
        sandbox_mode=policy_decision.sandbox_mode or policy_input.sandbox_mode,
        requested_by=policy_input.requested_by or "unknown",
        command=policy_input.command,
        normalized_command=policy_decision.normalized_command,
        policy_allowed=policy_decision.allowed,
        policy_blocked=policy_decision.blocked,
        policy_requires_approval=policy_decision.requires_approval,
        policy_category=policy_decision.category,
        policy_risk_level=policy_decision.risk_level,
        policy_reason=policy_decision.reason,
        matched_rule=policy_decision.matched_rule,
        runtime_mode=SANDBOX_POLICY_RUNTIME_MODE,
        execution_attempted=False,
        command_executed=False,
        network_used=False,
        secrets_detected=False,
        governance_decision=_governance_decision(policy_decision),
        evidence_version=SANDBOX_EVIDENCE_VERSION,
    )


def sandbox_policy_decision_to_evidence(
    policy_input: PolicyInput,
    policy_decision: PolicyDecision,
    *,
    timestamp: Optional[str] = None,
) -> SandboxPolicyEvidence:
    return build_sandbox_policy_evidence(
        policy_input,
        policy_decision,
        timestamp=timestamp,
    )


def _governance_decision(policy_decision: PolicyDecision) -> str:
    if policy_decision.blocked:
        return "blocked"
    if policy_decision.requires_approval:
        return "requires_approval"
    if policy_decision.allowed:
        return "allowed"
    return "blocked"


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
