from __future__ import annotations

from typing import Any

from .models import ExecutionIntent, RiskClassification, RiskLevel


READ_ONLY_TOOLS = {
    "read_file",
    "filesystem_read",
    "directory_tree",
    "glob_search",
    "grep_search",
    "code_search",
    "dependency_inspection",
    "git_status",
    "git_diff",
}
MEMORY_WRITE_TOOLS = {"memory_write", "decision_memory_write", "working_memory_write"}
HIGH_RISK_TOOLS = {
    "write_file",
    "filesystem_write",
    "filesystem_patch_set",
    "autonomous_debug_loop",
    "verification_runner",
    "test_runner",
}
CRITICAL_TOOLS = {"shell_command", "git_commit", "package_manager"}
EXTERNAL_IMPACT_SUBSYSTEMS = {"deployment", "external_api", "payments", "network_mutation"}


class DeterministicRiskClassifier:
    def classify(self, intent: ExecutionIntent) -> RiskClassification:
        capability = str(intent.capability or "").strip().lower()
        action_type = str(intent.action_type or "").strip().lower()
        subsystem = str(intent.target_subsystem or "").strip().lower()
        summary = intent.input_payload_summary if isinstance(intent.input_payload_summary, dict) else {}
        tool_arguments = summary.get("tool_arguments", {}) if isinstance(summary.get("tool_arguments", {}), dict) else {}
        subcommand = str(tool_arguments.get("subcommand", "")).strip().lower()

        if capability in CRITICAL_TOOLS or action_type in {"delete", "destroy", "deploy", "publish"}:
            return RiskClassification(
                level=RiskLevel.CRITICAL,
                reason_code="critical_tool_or_action",
                rationale=f"Action targets {capability or action_type}, which is considered externally impactful or difficult to reverse.",
            )

        if capability == "package_manager" and subcommand in {"install", "update", "publish"}:
            return RiskClassification(
                level=RiskLevel.CRITICAL,
                reason_code="package_mutation",
                rationale="Package mutations can alter runtime dependencies and are treated as critical.",
            )

        if subsystem in EXTERNAL_IMPACT_SUBSYSTEMS:
            return RiskClassification(
                level=RiskLevel.CRITICAL,
                reason_code="external_impact_subsystem",
                rationale=f"Subsystem {subsystem} can create external side effects and is treated as critical.",
            )

        if capability in HIGH_RISK_TOOLS or action_type in {"write", "patch", "fix", "mutate"}:
            return RiskClassification(
                level=RiskLevel.HIGH,
                reason_code="mutation_or_code_change",
                rationale="Code edits, patch application, or autonomous repair actions require high trust.",
            )

        if capability in MEMORY_WRITE_TOOLS or action_type in {"memory_write", "state_update"}:
            return RiskClassification(
                level=RiskLevel.MEDIUM,
                reason_code="state_mutation",
                rationale="State and memory mutations are classified as medium risk.",
            )

        if capability in READ_ONLY_TOOLS or action_type in {"read", "inspect", "reason"}:
            return RiskClassification(
                level=RiskLevel.LOW,
                reason_code="read_only",
                rationale="Read-only or reasoning-oriented actions are low risk.",
            )

        return RiskClassification(
            level=RiskLevel.MEDIUM,
            reason_code="default_medium",
            rationale="Unrecognized actions default to medium risk until explicitly classified.",
        )
