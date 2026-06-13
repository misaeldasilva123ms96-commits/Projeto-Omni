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
from brain.runtime.vault import build_vault_draft_proposal  # noqa: E402
from brain.runtime.vault import draft_proposals  # noqa: E402


def _report(*, action: str = "analyze_task", workflow_mode: str = "advisory_only"):
    request = AgentWorkflowRequest(
        agent_id="codex",
        requested_action=action,
        workflow_mode=workflow_mode,
        target_branch="vault/draft-proposal-pipeline",
        requested_by="human",
        related_phase="phase-13",
        related_pr="future",
    )
    decision = evaluate_agent_workflow_request(request)
    evidence = build_agent_workflow_evidence(
        decision,
        requested_by="human",
        related_phase="phase-13",
        related_pr="future",
        notes="safe notes",
        timestamp="2026-06-13T00:00:00+00:00",
    )
    return render_agent_sandbox_report(evidence)


def _proposal(**kwargs):
    return build_vault_draft_proposal(
        _report(),
        requested_by="codex",
        related_phase="phase-13",
        related_pr="future",
        write_mode="draft_only",
        created_at="2026-06-13T00:00:00+00:00",
        **kwargs,
    )


def test_draft_only_mode_creates_allowed_proposal_from_safe_report() -> None:
    proposal = _proposal()

    assert proposal.write_policy_allowed is True
    assert proposal.write_policy_blocked is False
    assert proposal.write_policy_requires_approval is True
    assert proposal.report_allowed_for_vault_draft is True
    assert proposal.allowed_for_human_review is True
    assert proposal.blocked_reason is None


def test_disabled_mode_blocks_proposal() -> None:
    proposal = build_vault_draft_proposal(
        _report(),
        requested_by="codex",
        write_mode="disabled",
        created_at="2026-06-13T00:00:00+00:00",
    )

    assert proposal.write_policy_allowed is False
    assert proposal.write_policy_blocked is True
    assert proposal.allowed_for_human_review is False
    assert "disabled" in (proposal.blocked_reason or "").lower()


def test_proposal_metadata_and_json_serialization() -> None:
    proposal = _proposal()
    encoded = json.dumps(proposal.to_dict(), sort_keys=True)

    assert proposal.markdown
    assert proposal.markdown_sha256
    assert proposal.suggested_filename.endswith(".md")
    assert proposal.suggested_vault_path.startswith("vault/09_Sandbox_Reports/")
    assert proposal.evidence_version == "1.0"
    assert proposal.proposal_id == "draft-proposal-2026-06-13-" + proposal.markdown_sha256[:12]
    assert "markdown_sha256" in encoded


def test_requested_status_draft_is_allowed_in_draft_only() -> None:
    proposal = _proposal(requested_status="draft")

    assert proposal.write_policy_allowed is True
    assert proposal.normalized_status == "draft"


def test_trusted_and_final_statuses_are_blocked() -> None:
    for status in ("approved", "reviewed", "deprecated", "archived"):
        proposal = _proposal(requested_status=status)

        assert proposal.write_policy_allowed is False
        assert proposal.allowed_for_human_review is False
        assert proposal.write_policy_blocked is True


def test_sensitive_note_types_are_blocked() -> None:
    for note_type in ("adr", "governance-policy", "security-policy", "secret"):
        proposal = _proposal(note_type=note_type)

        assert proposal.write_policy_allowed is False
        assert proposal.allowed_for_human_review is False
        assert proposal.write_policy_risk_level == "critical"


def test_unsafe_target_paths_are_blocked() -> None:
    unsafe_paths = (
        "docs/report.md",
        "vault/08_ADR/adr.md",
        "../vault/09_Sandbox_Reports/report.md",
        "vault/09_Sandbox_Reports/report.txt",
        "C:/Users/Misael/vault/09_Sandbox_Reports/report.md",
    )

    for target_path in unsafe_paths:
        proposal = _proposal(target_path=target_path)

        assert proposal.write_policy_allowed is False
        assert proposal.allowed_for_human_review is False
        assert proposal.write_policy_risk_level == "critical"


def test_report_not_allowed_for_vault_draft_blocks_proposal() -> None:
    report = replace(_report(), allowed_for_vault_draft=False, blocked_reason="unsafe report")
    proposal = build_vault_draft_proposal(
        report,
        requested_by="codex",
        write_mode="draft_only",
        created_at="2026-06-13T00:00:00+00:00",
    )

    assert proposal.report_allowed_for_vault_draft is False
    assert proposal.allowed_for_human_review is False
    assert "unsafe report" in (proposal.blocked_reason or "")


def test_unsafe_report_flags_block_proposal_when_represented() -> None:
    unsafe_markers = (
        "Agent executed: `true`",
        "Command executed: `true`",
        "Network used: `true`",
        "Vault written: `true`",
        "Git mutated: `true`",
    )

    for marker in unsafe_markers:
        report = replace(
            _report(),
            markdown=f"# Unsafe\n\n{marker}",
            allowed_for_vault_draft=False,
            blocked_reason=marker,
        )
        proposal = build_vault_draft_proposal(
            report,
            requested_by="codex",
            write_mode="draft_only",
            created_at="2026-06-13T00:00:00+00:00",
        )

        assert proposal.allowed_for_human_review is False
        assert proposal.blocked_reason


def test_redacts_and_blocks_key_like_markdown() -> None:
    marker = "OPEN" + "AI" + "_API" + "_KEY"
    report = replace(_report(), markdown=f"# Report\n\n{marker}=placeholder")
    proposal = build_vault_draft_proposal(
        report,
        requested_by="codex",
        write_mode="draft_only",
        created_at="2026-06-13T00:00:00+00:00",
    )

    assert marker not in proposal.markdown
    assert "[REDACTED]" in proposal.markdown
    assert proposal.redacted is True
    assert proposal.allowed_for_human_review is False


def test_redacts_and_blocks_authorization_bearer_markdown() -> None:
    marker = "Authorization: " + "Bearer"
    report = replace(_report(), markdown=f"# Report\n\n{marker} placeholder")
    proposal = build_vault_draft_proposal(
        report,
        requested_by="codex",
        write_mode="draft_only",
        created_at="2026-06-13T00:00:00+00:00",
    )

    assert marker not in proposal.markdown
    assert "[REDACTED]" in proposal.markdown
    assert proposal.allowed_for_human_review is False


def test_redacts_title_and_path_metadata() -> None:
    marker = "TO" + "KEN"
    report = replace(
        _report(),
        title=f"Report {marker}",
        suggested_filename=f"report-{marker}.md",
        suggested_vault_path=f"vault/09_Sandbox_Reports/report-{marker}.md",
    )
    proposal = build_vault_draft_proposal(
        report,
        requested_by="codex",
        write_mode="draft_only",
        created_at="2026-06-13T00:00:00+00:00",
    )

    assert marker not in proposal.title
    assert marker.lower() not in proposal.suggested_filename
    assert marker not in proposal.suggested_vault_path
    assert proposal.redacted is True


def test_markdown_hash_changes_when_markdown_changes() -> None:
    first = _proposal()
    changed_report = replace(_report(), markdown=_report().markdown + "\nextra")
    second = build_vault_draft_proposal(
        changed_report,
        requested_by="codex",
        write_mode="draft_only",
        created_at="2026-06-13T00:00:00+00:00",
    )

    assert first.markdown_sha256 != second.markdown_sha256


def test_markdown_hash_is_stable_for_same_markdown() -> None:
    first = _proposal()
    second = _proposal()

    assert first.markdown_sha256 == second.markdown_sha256
    assert first.proposal_id == second.proposal_id


def test_phase_10_11_12_13_integration_has_no_mutation_flags() -> None:
    report = _report(action="request_pr_open", workflow_mode="pr_proposal_only")
    proposal = build_vault_draft_proposal(
        report,
        requested_by="codex",
        related_phase="phase-13",
        write_mode="draft_only",
        created_at="2026-06-13T00:00:00+00:00",
    )

    assert proposal.allowed_for_human_review is True
    assert "Agent executed: `false`" in proposal.markdown
    assert "Command executed: `false`" in proposal.markdown
    assert "Network used: `false`" in proposal.markdown
    assert "Provider called: `false`" in proposal.markdown
    assert "MCP used: `false`" in proposal.markdown
    assert "Vault written: `false`" in proposal.markdown
    assert "Git mutated: `false`" in proposal.markdown


def test_pipeline_source_does_not_use_file_mutation_apis() -> None:
    source = inspect.getsource(draft_proposals)
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
