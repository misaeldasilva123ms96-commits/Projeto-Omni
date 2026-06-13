from __future__ import annotations

import inspect
import json
import sys
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.governance import (  # noqa: E402
    HumanApprovalGateRequest,
    evaluate_human_approval_gate,
)
from brain.runtime.governance import approval_gate  # noqa: E402
from brain.runtime.sandbox import (  # noqa: E402
    AgentWorkflowRequest,
    build_agent_workflow_evidence,
    evaluate_agent_workflow_request,
    render_agent_sandbox_report,
)
from brain.runtime.vault import build_vault_draft_proposal  # noqa: E402


def _safe_request(**overrides) -> HumanApprovalGateRequest:
    values = {
        "proposal_id": "draft-proposal-2026-06-13-safe",
        "proposal_type": "agent-sandbox-report",
        "requested_by": "codex",
        "reviewer_id": "reviewer-1",
        "reviewer_role": "maintainer",
        "requested_decision": "submit_for_review",
        "source_governance_decision": "requires_human_approval",
        "source_allowed_for_human_review": True,
        "source_write_policy_allowed": True,
        "source_write_policy_requires_approval": True,
        "source_report_allowed_for_vault_draft": True,
        "source_blocked_reason": None,
        "target_path": "vault/09_Sandbox_Reports/example.md",
        "note_type": "sandbox-report",
        "requested_status": "draft",
        "related_phase": "phase-14",
        "related_pr": "future",
        "risk_level": "medium",
        "metadata": {"source": "test"},
    }
    values.update(overrides)
    return HumanApprovalGateRequest(**values)


def _decision(**overrides):
    return evaluate_human_approval_gate(
        _safe_request(**overrides),
        created_at="2026-06-13T00:00:00+00:00",
    )


def test_safe_draft_proposal_is_allowed_for_review() -> None:
    decision = _decision()

    assert decision.allowed_for_review is True
    assert decision.blocked is False
    assert decision.requires_human_approval is True
    assert decision.governance_decision == "requires_human_approval"
    assert decision.reason == "Proposal may be presented for human review."


def test_blocked_source_conditions_block_gate() -> None:
    cases = (
        {"source_allowed_for_human_review": False},
        {"source_write_policy_allowed": False},
        {"source_write_policy_requires_approval": False},
        {"source_report_allowed_for_vault_draft": False},
        {"source_blocked_reason": "source blocked"},
    )

    for overrides in cases:
        decision = _decision(**overrides)

        assert decision.allowed_for_review is False
        assert decision.blocked is True
        assert decision.governance_decision == "blocked"


def test_allowed_requested_decisions_map_governance_decisions() -> None:
    expected = {
        "submit_for_review": "requires_human_approval",
        "request_changes": "requires_changes",
        "reject": "rejected",
        "hold": "hold",
    }

    for requested_decision, governance_decision in expected.items():
        decision = _decision(requested_decision=requested_decision)

        assert decision.blocked is False
        assert decision.allowed_for_review is True
        assert decision.governance_decision == governance_decision


def test_blocked_requested_decisions_are_blocked() -> None:
    for requested_decision in (
        "approve",
        "auto_approve",
        "write_to_vault",
        "promote_to_reviewed",
        "promote_to_approved",
        "merge_pr",
        "push_main",
        "bypass_governance",
    ):
        decision = _decision(requested_decision=requested_decision)

        assert decision.blocked is True
        assert decision.allowed_for_review is False
        assert decision.governance_decision == "blocked"


def test_status_rules_block_trusted_and_final_statuses() -> None:
    for requested_status in ("approved", "reviewed", "deprecated", "archived"):
        decision = _decision(requested_status=requested_status)

        assert decision.blocked is True
        assert decision.allowed_for_review is False
        assert decision.normalized_status == requested_status
        if requested_status in {"approved", "reviewed"}:
            assert decision.risk_level == "critical"
            assert "trusted" in decision.reason


def test_draft_status_is_allowed() -> None:
    decision = _decision(requested_status="draft")

    assert decision.allowed_for_review is True
    assert decision.normalized_status == "draft"


def test_allowed_proposal_types() -> None:
    for proposal_type in (
        "agent-sandbox-report",
        "sandbox-report",
        "runtime-report",
        "incident",
        "session-summary",
        "provider-evaluation",
        "agent-prompt",
    ):
        decision = _decision(proposal_type=proposal_type)

        assert decision.allowed_for_review is True


def test_blocked_proposal_types() -> None:
    for proposal_type in (
        "adr",
        "governance-policy",
        "security-policy",
        "architecture-approved",
        "contract",
        "secret",
        "credential",
    ):
        decision = _decision(proposal_type=proposal_type)

        assert decision.blocked is True
        assert decision.allowed_for_review is False


def test_allowed_target_paths() -> None:
    for target_path in (
        "vault/09_Sandbox_Reports/example.md",
        "vault/03_Runtime_Truth/example.md",
        "vault/06_Incidents/example.md",
        "vault/05_Agent_Prompts/example.md",
        "vault/10_Provider_Research/example.md",
    ):
        decision = _decision(target_path=target_path)

        assert decision.target_path_allowed is True
        assert decision.allowed_for_review is True


def test_blocked_target_paths() -> None:
    for target_path in (
        "docs/example.md",
        "vault/08_ADR/example.md",
        "../vault/09_Sandbox_Reports/example.md",
        "/tmp/example.md",
        "vault/09_Sandbox_Reports/example.txt",
        "vault/09_Sandbox_Reports/.env",
    ):
        decision = _decision(target_path=target_path)

        assert decision.target_path_allowed is False
        assert decision.blocked is True


def test_automation_flags_are_always_false() -> None:
    decision = _decision()

    assert decision.can_auto_approve is False
    assert decision.can_auto_write is False
    assert decision.can_change_status is False
    assert decision.can_promote_to_reviewed is False
    assert decision.can_promote_to_approved is False
    assert decision.can_merge is False
    assert decision.can_push_main is False
    assert decision.requires_human_approval is True


def test_secret_like_metadata_is_redacted_and_blocked() -> None:
    marker = "OPEN" + "AI" + "_API" + "_KEY"
    decision = _decision(metadata={"note": marker})

    assert decision.blocked is True
    assert decision.allowed_for_review is False
    assert decision.redacted is True
    assert decision.risk_level == "critical"
    assert marker not in json.dumps(decision.to_dict())
    assert "Credential-like content" in decision.reason


def test_secret_like_reviewer_id_is_redacted_and_blocked() -> None:
    marker = "Authorization: " + "Bearer"
    decision = _decision(reviewer_id=f"{marker} placeholder")

    assert decision.blocked is True
    assert decision.reviewer_id is not None
    assert marker not in decision.reviewer_id
    assert "[REDACTED]" in decision.reviewer_id


def test_secret_like_target_path_is_redacted_and_blocked() -> None:
    decision = _decision(target_path="vault/09_Sandbox_Reports/.env")

    assert decision.blocked is True
    assert decision.target_path_allowed is False
    assert decision.redacted is True
    assert ".env" not in json.dumps(decision.to_dict())


def test_decision_is_json_serializable() -> None:
    decision = _decision()
    encoded = json.dumps(decision.to_dict(), sort_keys=True)

    assert "approval_gate_id" in encoded
    assert decision.to_dict()["proposal_id"] == "draft-proposal-2026-06-13-safe"


def test_accepts_phase_13_draft_proposal_object() -> None:
    request = AgentWorkflowRequest(
        agent_id="codex",
        requested_action="analyze_task",
        workflow_mode="advisory_only",
        target_branch="governance/human-approval-gate",
        requested_by="human",
        related_phase="phase-14",
        related_pr="future",
    )
    policy_decision = evaluate_agent_workflow_request(request)
    evidence = build_agent_workflow_evidence(
        policy_decision,
        requested_by="human",
        related_phase="phase-14",
        related_pr="future",
        notes="safe notes",
        timestamp="2026-06-13T00:00:00+00:00",
    )
    report = render_agent_sandbox_report(evidence)
    proposal = build_vault_draft_proposal(
        report,
        requested_by="codex",
        related_phase="phase-14",
        write_mode="draft_only",
        created_at="2026-06-13T00:00:00+00:00",
    )
    gate = evaluate_human_approval_gate(
        proposal,
        reviewer_id="reviewer-1",
        reviewer_role="maintainer",
        created_at="2026-06-13T00:00:00+00:00",
    )

    assert proposal.allowed_for_human_review is True
    assert gate.allowed_for_review is True
    assert gate.can_auto_approve is False
    assert gate.can_auto_write is False
    assert gate.can_change_status is False
    assert gate.can_merge is False


def test_request_override_does_not_mutate_source() -> None:
    request = _safe_request()
    gate = evaluate_human_approval_gate(
        request,
        reviewer_id="reviewer-2",
        requested_decision="hold",
        created_at="2026-06-13T00:00:00+00:00",
    )

    assert request.reviewer_id == "reviewer-1"
    assert gate.reviewer_id == "reviewer-2"
    assert gate.governance_decision == "hold"


def test_approval_gate_source_does_not_use_file_mutation_apis() -> None:
    source = inspect.getsource(approval_gate)
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
