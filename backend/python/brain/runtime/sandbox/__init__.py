"""Sandbox policy classification utilities.

Phase 4 only classifies command text. It does not execute commands, call MCP,
invoke agents, or perform network access.
"""

from .agent_policy import evaluate_agent_workflow_request
from .agent_reports import AgentSandboxReport, render_agent_sandbox_report
from .agent_runtime_truth import AgentWorkflowEvidence, build_agent_workflow_evidence
from .agent_types import AgentWorkflowPolicyDecision, AgentWorkflowRequest
from .command_gate import evaluate_command_gate, normalize_gate_command
from .command_types import CommandGateDecision, CommandGateRequest
from .policy_engine import classify_command, normalize_command
from .policy_types import PolicyDecision, PolicyInput
from .reports import SandboxReport, redact_report_text, render_sandbox_policy_report
from .runtime_truth import SandboxPolicyEvidence, build_sandbox_policy_evidence

__all__ = [
    "AgentWorkflowPolicyDecision",
    "AgentWorkflowRequest",
    "AgentWorkflowEvidence",
    "AgentSandboxReport",
    "CommandGateDecision",
    "CommandGateRequest",
    "PolicyDecision",
    "PolicyInput",
    "SandboxReport",
    "SandboxPolicyEvidence",
    "build_agent_workflow_evidence",
    "build_sandbox_policy_evidence",
    "classify_command",
    "evaluate_command_gate",
    "evaluate_agent_workflow_request",
    "normalize_gate_command",
    "normalize_command",
    "redact_report_text",
    "render_sandbox_policy_report",
    "render_agent_sandbox_report",
]
