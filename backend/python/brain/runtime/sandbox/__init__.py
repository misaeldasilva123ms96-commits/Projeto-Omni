"""Sandbox policy classification utilities.

Phase 4 only classifies command text. It does not execute commands, call MCP,
invoke agents, or perform network access.
"""

from .policy_engine import classify_command, normalize_command
from .policy_types import PolicyDecision, PolicyInput
from .reports import SandboxReport, redact_report_text, render_sandbox_policy_report
from .runtime_truth import SandboxPolicyEvidence, build_sandbox_policy_evidence

__all__ = [
    "PolicyDecision",
    "PolicyInput",
    "SandboxReport",
    "SandboxPolicyEvidence",
    "build_sandbox_policy_evidence",
    "classify_command",
    "normalize_command",
    "redact_report_text",
    "render_sandbox_policy_report",
]
