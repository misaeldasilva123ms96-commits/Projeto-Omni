"""Sandbox policy classification utilities.

Phase 4 only classifies command text. It does not execute commands, call MCP,
invoke agents, or perform network access.
"""

from .agent_policy import evaluate_agent_workflow_request
from .agent_reports import AgentSandboxReport, render_agent_sandbox_report
from .agent_runtime_truth import AgentWorkflowEvidence, build_agent_workflow_evidence
from .agent_types import AgentWorkflowPolicyDecision, AgentWorkflowRequest
from .command_gate import evaluate_command_gate, normalize_gate_command
from .command_runner import run_sandbox_command
from .command_runner_truth import (
    SandboxCommandExecutionEvidence,
    build_command_runner_evidence,
)
from .command_runner_types import SandboxCommandRunnerRequest, SandboxCommandRunnerResult
from .command_types import CommandGateDecision, CommandGateRequest
from .policy_engine import classify_command, normalize_command
from .policy_types import PolicyDecision, PolicyInput
from .reports import SandboxReport, redact_report_text, render_sandbox_policy_report
from .repair_planner import plan_autonomous_repair
from .repair_planner_truth import (
    AutonomousRepairPlannerEvidence,
    build_repair_planner_evidence,
)
from .repair_planner_types import (
    AutonomousRepairPlannerRequest,
    AutonomousRepairPlannerResult,
)
from .runtime_truth import SandboxPolicyEvidence, build_sandbox_policy_evidence
from .test_runner_loop import run_autonomous_test_loop
from .test_runner_truth import (
    AutonomousTestRunnerLoopEvidence,
    build_test_runner_loop_evidence,
)
from .test_runner_types import (
    AutonomousTestRunnerLoopRequest,
    AutonomousTestRunnerLoopResult,
)

__all__ = [
    "AgentWorkflowPolicyDecision",
    "AgentWorkflowRequest",
    "AgentWorkflowEvidence",
    "AgentSandboxReport",
    "AutonomousRepairPlannerEvidence",
    "AutonomousRepairPlannerRequest",
    "AutonomousRepairPlannerResult",
    "AutonomousTestRunnerLoopEvidence",
    "AutonomousTestRunnerLoopRequest",
    "AutonomousTestRunnerLoopResult",
    "CommandGateDecision",
    "CommandGateRequest",
    "SandboxCommandExecutionEvidence",
    "SandboxCommandRunnerRequest",
    "SandboxCommandRunnerResult",
    "PolicyDecision",
    "PolicyInput",
    "SandboxReport",
    "SandboxPolicyEvidence",
    "build_agent_workflow_evidence",
    "build_command_runner_evidence",
    "build_repair_planner_evidence",
    "build_sandbox_policy_evidence",
    "build_test_runner_loop_evidence",
    "classify_command",
    "evaluate_command_gate",
    "evaluate_agent_workflow_request",
    "normalize_gate_command",
    "normalize_command",
    "plan_autonomous_repair",
    "redact_report_text",
    "render_sandbox_policy_report",
    "render_agent_sandbox_report",
    "run_autonomous_test_loop",
    "run_sandbox_command",
]
