from __future__ import annotations

import inspect
import json
import sys
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.sandbox import (  # noqa: E402
    AgentWorkflowRequest,
    build_agent_workflow_evidence,
    evaluate_agent_workflow_request,
    render_agent_sandbox_report,
)
from brain.runtime.sandbox import agent_reports  # noqa: E402


def _evidence(
    action: str,
    *,
    workflow_mode: str = "advisory_only",
    target_branch: str | None = None,
):
    request = AgentWorkflowRequest(
        agent_id="codex",
        requested_action=action,
        workflow_mode=workflow_mode,
        target_branch=target_branch,
        requested_by="human",
        related_phase="phase-12",
        related_pr="future",
    )
    decision = evaluate_agent_workflow_request(request)
    return build_agent_workflow_evidence(
        decision,
        requested_by="human",
        related_phase="phase-12",
        related_pr="future",
        notes="safe notes",
        timestamp="2026-06-13T00:00:00+00:00",
    )


def test_renders_report_from_allowed_advisory_evidence() -> None:
    report = render_agent_sandbox_report(_evidence("analyze_task"))

    assert report.governance_decision == "requires_approval"
    assert report.allowed_for_vault_draft is True
    assert "analyze_task" in report.markdown
    assert "advisory_only" in report.markdown


def test_renders_report_from_blocked_evidence() -> None:
    report = render_agent_sandbox_report(_evidence("merge_main"))

    assert report.governance_decision == "blocked"
    assert "blocked" in report.markdown


def test_renders_report_from_requires_approval_evidence() -> None:
    report = render_agent_sandbox_report(
        _evidence(
            "request_test_run",
            workflow_mode="supervised_sandbox",
            target_branch="sandbox/agent-report-renderer",
        )
    )

    assert report.governance_decision == "requires_approval"
    assert "supervised_sandbox" in report.markdown


def test_renders_report_from_pr_proposal_evidence() -> None:
    report = render_agent_sandbox_report(
        _evidence(
            "request_pr_open",
            workflow_mode="pr_proposal_only",
            target_branch="sandbox/agent-report-renderer",
        )
    )

    assert report.governance_decision == "requires_approval"
    assert "request_pr_open" in report.markdown
    assert "PR open allowed: `true`" in report.markdown


def test_markdown_contains_required_sections_and_safety_statements() -> None:
    report = render_agent_sandbox_report(_evidence("analyze_task"))
    markdown = report.markdown

    assert markdown.startswith("---")
    assert "status: draft" in markdown
    assert "Agent id: `codex`" in markdown
    assert "Requested action: `analyze_task`" in markdown
    assert "Workflow mode: `advisory_only`" in markdown
    assert "Governance decision: `requires_approval`" in markdown
    assert "Risk level: `low`" in markdown
    assert "Reason:" in markdown
    assert "No agent was executed." in markdown
    assert "No command was executed." in markdown
    assert "No network request, provider call, MCP operation" in markdown
    assert "vault write, Git mutation" in markdown


def test_output_metadata_is_json_serializable() -> None:
    report = render_agent_sandbox_report(_evidence("analyze_task"))
    payload = report.to_dict()
    encoded = json.dumps(payload, sort_keys=True)

    assert payload["markdown"]
    assert payload["title"] == "Agent Sandbox Report"
    assert payload["suggested_filename"].endswith(".md")
    assert payload["suggested_vault_path"].startswith("vault/09_Sandbox_Reports/")
    assert payload["report_type"] == "agent-sandbox-report"
    assert payload["evidence_version"] == "1.0"
    assert "agent-sandbox-report" in encoded


def test_suggested_vault_path_is_metadata_only() -> None:
    report = render_agent_sandbox_report(_evidence("analyze_task"))

    assert isinstance(report.suggested_vault_path, str)
    assert report.suggested_vault_path.endswith(report.suggested_filename)


def test_filename_is_safe_lowercase_and_blocks_path_traversal() -> None:
    marker = "OPEN" + "AI" + "_API" + "_KEY"
    evidence = _evidence("../Analyze Task/../")
    report = render_agent_sandbox_report(
        evidence,
        title=f"Unsafe {marker}",
        suggested_vault_dir="/absolute/path",
    )

    assert report.suggested_filename == report.suggested_filename.lower()
    assert ".." not in report.suggested_filename
    assert "/" not in report.suggested_filename
    assert "\\" not in report.suggested_filename
    assert not report.suggested_filename.startswith("/")
    assert marker not in report.suggested_filename
    assert report.suggested_vault_path.startswith("vault/09_Sandbox_Reports/")


def test_unsafe_runtime_flags_block_vault_draft() -> None:
    base = _evidence("analyze_task")
    unsafe_variants = (
        replace(base, agent_executed=True),
        replace(base, command_executed=True),
        replace(base, network_used=True),
        replace(base, provider_called=True),
        replace(base, mcp_used=True),
        replace(base, vault_written=True),
        replace(base, git_mutated=True),
        replace(base, main_modified=True),
        replace(base, main_branch_protected=False),
    )

    for evidence in unsafe_variants:
        report = render_agent_sandbox_report(evidence)

        assert report.allowed_for_vault_draft is False
        assert report.blocked_reason


def test_unsafe_policy_flags_block_vault_draft() -> None:
    base = _evidence("analyze_task")
    unsafe_variants = (
        replace(base, command_execution_allowed=True),
        replace(base, network_allowed=True),
        replace(base, provider_call_allowed=True),
        replace(base, vault_write_allowed=True),
        replace(base, mcp_write_allowed=True),
        replace(base, git_merge_allowed=True),
    )

    for evidence in unsafe_variants:
        report = render_agent_sandbox_report(evidence)

        assert report.allowed_for_vault_draft is False
        assert report.blocked_reason


def test_redacts_notes_with_key_like_placeholder() -> None:
    marker = "OPEN" + "AI" + "_API" + "_KEY"
    evidence = replace(_evidence("analyze_task"), notes=f"{marker}=placeholder")
    report = render_agent_sandbox_report(evidence)

    assert marker not in report.markdown
    assert "[REDACTED]" in report.markdown


def test_redacts_notes_with_authorization_bearer_placeholder() -> None:
    marker = "Authorization: " + "Bearer"
    evidence = replace(_evidence("analyze_task"), notes=f"{marker} placeholder")
    report = render_agent_sandbox_report(evidence)

    assert marker not in report.markdown
    assert "[REDACTED]" in report.markdown


def test_redacts_title_with_secret_like_marker() -> None:
    marker = "TO" + "KEN"
    report = render_agent_sandbox_report(
        _evidence("analyze_task"),
        title=f"Agent report {marker}",
    )

    assert marker not in report.title
    assert marker not in report.markdown
    assert "[REDACTED]" in report.title


def test_integration_with_phase_10_and_phase_11() -> None:
    evidence = _evidence(
        "request_test_run",
        workflow_mode="supervised_sandbox",
        target_branch="sandbox/agent-report-renderer",
    )
    report = render_agent_sandbox_report(evidence)

    assert report.governance_decision == "requires_approval"
    assert evidence.agent_executed is False
    assert evidence.command_executed is False
    assert evidence.network_used is False
    assert evidence.provider_called is False
    assert evidence.mcp_used is False
    assert evidence.vault_written is False
    assert evidence.git_mutated is False


def test_renderer_source_does_not_use_file_mutation_apis() -> None:
    source = inspect.getsource(agent_reports)
    forbidden = (
        "open" + "(",
        "write" + "(",
        "unlink" + "(",
        "rename" + "(",
        "remove" + "(",
        "rmtree" + "(",
        "shutil" + ".move",
    )

    for pattern in forbidden:
        assert pattern not in source
