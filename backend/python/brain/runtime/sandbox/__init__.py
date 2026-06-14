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
from .patch_applier import apply_controlled_patch
from .patch_applier_truth import (
    ControlledPatchApplierEvidence,
    build_patch_applier_evidence,
)
from .patch_applier_types import (
    ControlledPatchApplierRequest,
    ControlledPatchApplierResult,
)
from .patch_proposal import propose_scoped_patch
from .patch_proposal_truth import (
    ScopedPatchProposalEvidence,
    build_patch_proposal_evidence,
)
from .patch_proposal_types import (
    ScopedPatchProposalRequest,
    ScopedPatchProposalResult,
)
from .policy_engine import classify_command, normalize_command
from .policy_types import PolicyDecision, PolicyInput
from .post_patch_validator import validate_post_patch
from .post_patch_validator_truth import (
    PostPatchValidationEvidence,
    build_post_patch_validation_evidence,
)
from .post_patch_validator_types import (
    PostPatchValidationRequest,
    PostPatchValidationResult,
)
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
    "ControlledPatchApplierEvidence",
    "ControlledPatchApplierRequest",
    "ControlledPatchApplierResult",
    "SandboxCommandExecutionEvidence",
    "SandboxCommandRunnerRequest",
    "SandboxCommandRunnerResult",
    "PolicyDecision",
    "PolicyInput",
    "PostPatchValidationEvidence",
    "PostPatchValidationRequest",
    "PostPatchValidationResult",
    "ScopedPatchProposalEvidence",
    "ScopedPatchProposalRequest",
    "ScopedPatchProposalResult",
    "SandboxReport",
    "SandboxPolicyEvidence",
    "apply_controlled_patch",
    "build_agent_workflow_evidence",
    "build_command_runner_evidence",
    "build_patch_applier_evidence",
    "build_patch_proposal_evidence",
    "build_post_patch_validation_evidence",
    "build_repair_planner_evidence",
    "build_sandbox_policy_evidence",
    "build_test_runner_loop_evidence",
    "classify_command",
    "evaluate_command_gate",
    "evaluate_agent_workflow_request",
    "normalize_gate_command",
    "normalize_command",
    "plan_autonomous_repair",
    "propose_scoped_patch",
    "redact_report_text",
    "render_sandbox_policy_report",
    "render_agent_sandbox_report",
    "run_autonomous_test_loop",
    "run_sandbox_command",
    "validate_post_patch",
]
