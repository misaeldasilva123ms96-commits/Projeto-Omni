"""Tests for the PR creation gate."""

from __future__ import annotations

import json
from pathlib import Path

from brain.runtime.sandbox.pr_creation_gate import evaluate_pr_creation_gate


def _push_executor(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "pushed": True,
        "success": True,
        "blocked": False,
        "requires_human_intervention": False,
        "workspace_root": "repo",
        "current_branch": "feature/phase27",
        "target_branch": "feature/phase27",
        "remote_name": "origin",
        "remote_branch": "feature/phase27",
        "pushed_ref": "feature/phase27:refs/heads/feature/phase27",
        "pushed_remote": "origin",
        "commit_sha": "abc123def456",
        "runtime_truth": {
            "event_type": "sandbox.push_executor.push",
            "secrets_detected": False,
            "push_executed": True,
            "force_push_executed": False,
            "main_pushed": False,
            "pr_created": False,
            "pr_merged": False,
            "merge_performed": False,
            "rebase_performed": False,
            "checkout_performed": False,
            "branch_created": False,
            "main_modified": False,
            "provider_called": False,
            "mcp_used": False,
            "agent_called": False,
            "vault_written": False,
        },
    }
    payload.update(overrides)
    return payload


def _push_gate(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "push_eligible": True,
        "push_ready_metadata_only": True,
        "blocked": False,
        "requires_human_intervention": False,
        "runtime_truth": {
            "event_type": "sandbox.push_gate.decision",
            "secrets_detected": False,
            "main_push_detected": False,
            "force_push_detected": False,
            "protected_branch_detected": False,
            "main_modified": False,
            "pr_created": False,
            "pr_merged": False,
            "network_used": False,
            "provider_called": False,
            "agent_called": False,
            "mcp_used": False,
            "vault_written": False,
        },
    }
    payload.update(overrides)
    return payload


def _request(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "push_executor_result": _push_executor(),
        "push_gate_result": _push_gate(),
        "pr_gate_mode": "evaluate_pr",
        "repository_full_name": "misaeldasilva123ms96-commits/Projeto-Omni",
        "source_branch": "feature/phase27",
        "head_branch": "feature/phase27",
        "base_branch": "main",
        "current_branch": "feature/phase27",
        "remote_name": "origin",
        "remote_branch": "feature/phase27",
        "pushed_ref": "feature/phase27:refs/heads/feature/phase27",
        "pushed_remote": "origin",
        "commit_sha": "abc123def456",
        "labels": ["sandbox", "phase-27"],
        "reviewers": ["misael"],
        "assignees": ["misael"],
    }
    payload.update(overrides)
    return payload


def test_modes_block_or_dry_run() -> None:
    assert evaluate_pr_creation_gate(_request(pr_gate_mode="disabled")).blocked is True
    assert evaluate_pr_creation_gate(_request(pr_gate_mode="blocked")).blocked is True
    assert evaluate_pr_creation_gate(_request(pr_gate_mode="unknown")).blocked is True

    dry_run = evaluate_pr_creation_gate(_request(pr_gate_mode="dry_run"))
    assert dry_run.dry_run is True
    assert dry_run.pr_eligible is False
    assert dry_run.can_create_pr is False
    assert dry_run.runtime_truth["pr_created"] is False


def test_evaluate_pr_marks_clean_evidence_eligible() -> None:
    result = evaluate_pr_creation_gate(_request())
    assert result.evaluated is True
    assert result.success is True
    assert result.pr_eligible is True
    assert result.pr_ready_metadata_only is True
    assert result.requires_pr_executor_phase is True
    assert result.push_was_executed is True
    assert result.push_evidence_clean is True
    assert result.branch_safe is True
    assert result.base_safe is True
    assert result.repository_safe is True
    assert result.pr_plan["allowed_in_future_pr_creation"] is True
    assert result.runtime_truth["event_type"] == "sandbox.pr_creation_gate.decision"
    assert result.runtime_truth["push_executed"] is False
    assert result.runtime_truth["command_executed"] is False
    assert result.runtime_truth["git_mutated"] is False


def test_phase26_integration_blocks_invalid_push_evidence() -> None:
    assert evaluate_pr_creation_gate(_request(push_executor_result=None)).blocked is True
    assert evaluate_pr_creation_gate(_request(push_executor_result=_push_executor(pushed=False))).blocked is True
    assert evaluate_pr_creation_gate(_request(push_executor_result=_push_executor(success=False))).blocked is True
    assert evaluate_pr_creation_gate(_request(push_executor_result=_push_executor(blocked=True))).blocked is True
    assert evaluate_pr_creation_gate(_request(push_executor_result=_push_executor(requires_human_intervention=True))).blocked is True
    assert evaluate_pr_creation_gate(_request(push_executor_result=_push_executor(pushed_ref=None), pushed_ref=None)).blocked is True
    assert evaluate_pr_creation_gate(_request(push_executor_result=_push_executor(pushed_remote=None), pushed_remote=None)).blocked is True
    assert evaluate_pr_creation_gate(_request(push_executor_result=_push_executor(commit_sha=None), commit_sha=None)).blocked is True

    for flag in (
        "secrets_detected",
        "force_push_executed",
        "main_pushed",
        "pr_created",
        "pr_merged",
        "merge_performed",
        "rebase_performed",
        "checkout_performed",
        "branch_created",
        "main_modified",
        "provider_called",
        "mcp_used",
        "agent_called",
        "vault_written",
    ):
        executor = _push_executor()
        truth = dict(executor["runtime_truth"])  # type: ignore[index]
        truth[flag] = True
        executor["runtime_truth"] = truth
        assert evaluate_pr_creation_gate(_request(push_executor_result=executor)).blocked is True


def test_phase25_integration_blocks_invalid_gate_evidence() -> None:
    assert evaluate_pr_creation_gate(_request(push_gate_result=_push_gate(push_eligible=False))).blocked is True
    assert evaluate_pr_creation_gate(_request(push_gate_result=_push_gate(blocked=True))).blocked is True
    assert evaluate_pr_creation_gate(_request(push_gate_result=_push_gate(requires_human_intervention=True))).blocked is True
    for flag in (
        "secrets_detected",
        "main_push_detected",
        "force_push_detected",
        "protected_branch_detected",
        "main_modified",
        "pr_created",
        "pr_merged",
        "network_used",
        "provider_called",
        "agent_called",
        "mcp_used",
        "vault_written",
    ):
        gate = _push_gate()
        truth = dict(gate["runtime_truth"])  # type: ignore[index]
        truth[flag] = True
        gate["runtime_truth"] = truth
        assert evaluate_pr_creation_gate(_request(push_gate_result=gate)).blocked is True


def test_branch_safety_rules() -> None:
    cases = [
        {"source_branch": "main"},
        {"head_branch": "main"},
        {"current_branch": "main"},
        {"remote_branch": "main"},
        {"source_branch": None},
        {"head_branch": None},
        {"base_branch": "develop"},
        {"source_branch": "main", "base_branch": "main"},
        {"head_branch": "main", "base_branch": "main"},
        {"source_branch": "release/1.0", "head_branch": "release/1.0", "remote_branch": "release/1.0"},
        {"source_branch": "prod/x", "head_branch": "prod/x", "remote_branch": "prod/x"},
        {"source_branch": "protected/x", "head_branch": "protected/x", "remote_branch": "protected/x"},
        {"metadata": {"direct_main_edit": True}},
        {"metadata": {"source_main": True}},
        {"metadata": {"base_not_main": True}},
    ]
    for override in cases:
        assert evaluate_pr_creation_gate(_request(**override)).blocked is True


def test_repository_safety_rules() -> None:
    assert evaluate_pr_creation_gate(_request(repository_full_name="misaeldasilva123ms96-commits/Projeto-Omni")).pr_eligible is True
    assert evaluate_pr_creation_gate(_request(repository_full_name=None)).blocked is True
    assert evaluate_pr_creation_gate(_request(repository_full_name="owner/repo;bad")).blocked is True
    assert evaluate_pr_creation_gate(_request(repository_full_name="owner/ghp_placeholder")).redacted is True
    assert evaluate_pr_creation_gate(_request(repository_full_name="owner/github_pat_placeholder")).redacted is True
    assert evaluate_pr_creation_gate(_request(repository_full_name="https://token@example.invalid/repo")).blocked is True
    assert evaluate_pr_creation_gate(_request(repository_full_name="missing-owner")).blocked is True
    assert evaluate_pr_creation_gate(_request(repository_full_name="other/fork")).requires_human_intervention is True


def test_pr_plan_title_body_and_metadata_are_safe() -> None:
    result = evaluate_pr_creation_gate(
        _request(
            pr_title_hint="sandbox: add PR creation gate",
            pr_body_hint="Summary only. No merge or auto-merge.",
            labels=["sandbox", "governance", "runtime-truth"],
            reviewers=["reviewer-one"],
            assignees=["assignee-one"],
        )
    )
    payload = result.to_dict()
    json.dumps(payload)
    assert result.pr_eligible is True
    assert result.proposed_pr_title == "sandbox: add PR creation gate"
    assert result.proposed_pr_draft is True
    assert result.required_pre_pr_checks
    assert result.pr_plan["draft"] is True
    assert result.pr_plan["risk_level"] == "low"


def test_pr_title_body_labels_reviewers_assignees_block_unsafe_content() -> None:
    cases = [
        {"pr_title_hint": "x" * 150},
        {"pr_title_hint": "OPENAI_API_KEY placeholder"},
        {"pr_title_hint": "touch .env"},
        {"pr_body_hint": "Authorization: Bearer placeholder"},
        {"labels": ["sandbox;bad"]},
        {"reviewers": ["person@example.invalid"]},
        {"assignees": ["https://example.invalid/user"]},
        {"labels": ["ghp_placeholder"]},
        {"reviewers": ["TOKEN_placeholder"]},
        {"assignees": ["SECRET_placeholder"]},
    ]
    long_title = evaluate_pr_creation_gate(_request(pr_title_hint="x" * 150))
    assert long_title.blocked is False
    assert len(long_title.proposed_pr_title or "") <= 120
    for override in cases[1:]:
        result = evaluate_pr_creation_gate(_request(**override))
        assert result.blocked is True
        if result.redacted:
            text = json.dumps(result.to_dict())
            assert "Authorization: Bearer" not in text
            assert "OPENAI_API_KEY" not in text
            assert ".env" not in text
            assert "ghp_" not in text
            assert "TOKEN" not in text
            assert "SECRET" not in text


def test_flags_and_runtime_truth_remain_metadata_only() -> None:
    result = evaluate_pr_creation_gate(_request())
    assert result.can_create_pr is False
    assert result.can_merge is False
    assert result.can_auto_merge is False
    assert result.can_push is False
    assert result.can_force_push is False
    assert result.can_push_main is False
    assert result.can_rebase is False
    assert result.can_create_branch is False
    assert result.can_checkout is False
    assert result.can_edit_code is False
    assert result.can_apply_patch is False
    for flag in (
        "pr_created",
        "pr_merged",
        "auto_merge_enabled",
        "push_executed",
        "force_push_executed",
        "main_pushed",
        "command_executed",
        "git_mutated",
        "commit_executed",
        "files_staged",
        "code_edited",
        "patch_applied",
        "files_written",
        "branch_created",
        "checkout_performed",
        "rebase_performed",
        "merge_performed",
        "network_used",
        "provider_called",
        "agent_called",
        "mcp_used",
        "vault_written",
        "main_modified",
    ):
        assert result.runtime_truth[flag] is False
    assert len(result.runtime_truth["child_runtime_truth_events"]) == 2


def test_redaction_blocks_secret_like_metadata() -> None:
    result = evaluate_pr_creation_gate(_request(metadata={"header": "Authorization: Bearer placeholder"}))
    assert result.blocked is True
    assert result.redacted is True
    assert "Authorization: Bearer" not in json.dumps(result.to_dict())

    branch = evaluate_pr_creation_gate(_request(source_branch="feature/SECRET-placeholder"))
    assert branch.blocked is True
    assert branch.redacted is True
    assert "SECRET" not in json.dumps(branch.to_dict())

    repo = evaluate_pr_creation_gate(_request(repository_full_name="owner/ghp_placeholder"))
    assert repo.blocked is True
    assert repo.redacted is True
    assert "ghp_" not in json.dumps(repo.to_dict())


def test_source_has_no_execution_or_integration_apis() -> None:
    source = Path("backend/python/brain/runtime/sandbox/pr_creation_gate.py").read_text(encoding="utf-8")
    forbidden = [
        "subprocess",
        "shell=True",
        "os.system",
        "eval(",
        "exec(",
        "requests.",
        "urllib",
        "socket",
        "websocket",
        "http.client",
        "pexpect",
        "open(",
        "write(",
        "unlink(",
        "rename(",
        "remove(",
        "rmtree(",
        "shutil.move",
    ]
    for pattern in forbidden:
        assert pattern not in source
