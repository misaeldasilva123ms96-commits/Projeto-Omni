"""Tests for the controlled push gate."""

from __future__ import annotations

import json
from pathlib import Path

from brain.runtime.sandbox.push_gate import evaluate_push_gate


def _executor(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "committed": True,
        "success": True,
        "blocked": False,
        "requires_human_intervention": False,
        "commit_sha": "abc123def456",
        "pre_commit_head": "aaa111",
        "post_commit_head": "abc123def456",
        "current_branch": "feature/phase25",
        "target_branch": "feature/phase25",
        "workspace_root": "repo",
        "files_staged": ["tests/example_test.py"],
        "requires_push_phase": True,
        "can_push": False,
        "runtime_truth": {
            "event_type": "sandbox.commit_executor.commit",
            "secrets_detected": False,
            "pushed": False,
            "pr_created": False,
            "pr_merged": False,
            "merge_performed": False,
            "rebase_performed": False,
            "checkout_performed": False,
            "branch_created": False,
            "main_modified": False,
            "network_used": False,
            "provider_called": False,
            "mcp_used": False,
            "agent_called": False,
            "vault_written": False,
        },
    }
    payload.update(overrides)
    return payload


def _commit_gate(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "commit_eligible": True,
        "blocked": False,
        "requires_human_intervention": False,
        "runtime_truth": {
            "event_type": "sandbox.commit_gate.decision",
            "secrets_detected": False,
            "main_modified": False,
            "git_mutated": False,
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
        "commit_executor_result": _executor(),
        "commit_gate_result": _commit_gate(),
        "push_gate_mode": "evaluate_push",
        "current_branch": "feature/phase25",
        "target_branch": "feature/phase25",
        "remote_name": "origin",
        "remote_branch": "feature/phase25",
        "proposed_push_ref": "feature/phase25",
    }
    payload.update(overrides)
    return payload


def test_modes_block_or_dry_run() -> None:
    assert evaluate_push_gate(_request(push_gate_mode="disabled")).blocked is True
    assert evaluate_push_gate(_request(push_gate_mode="blocked")).blocked is True
    assert evaluate_push_gate(_request(push_gate_mode="unknown")).blocked is True

    dry_run = evaluate_push_gate(_request(push_gate_mode="dry_run"))
    assert dry_run.dry_run is True
    assert dry_run.push_eligible is False
    assert dry_run.can_execute_push is False


def test_evaluate_push_marks_clean_evidence_eligible() -> None:
    result = evaluate_push_gate(_request())
    assert result.evaluated is True
    assert result.success is True
    assert result.push_eligible is True
    assert result.push_ready_metadata_only is True
    assert result.commit_was_executed is True
    assert result.commit_evidence_clean is True
    assert result.branch_safe is True
    assert result.remote_safe is True
    assert result.push_plan["allowed_in_future_push_execution"] is True
    assert result.runtime_truth["event_type"] == "sandbox.push_gate.decision"
    assert result.runtime_truth["push_executed"] is False
    assert result.runtime_truth["command_executed"] is False
    assert result.runtime_truth["git_mutated"] is False
    assert result.runtime_truth["commit_executed"] is False


def test_phase24_integration_blocks_invalid_executor_evidence() -> None:
    assert evaluate_push_gate(_request(commit_executor_result=None)).blocked is True
    assert evaluate_push_gate(_request(commit_executor_result=_executor(committed=False))).blocked is True
    assert evaluate_push_gate(_request(commit_executor_result=_executor(success=False))).blocked is True
    assert evaluate_push_gate(_request(commit_executor_result=_executor(blocked=True))).blocked is True
    assert evaluate_push_gate(_request(commit_executor_result=_executor(requires_human_intervention=True))).blocked is True
    assert evaluate_push_gate(_request(commit_executor_result=_executor(commit_sha=None))).blocked is True


def test_phase24_runtime_truth_unsafe_flags_block() -> None:
    for flag in (
        "secrets_detected",
        "pushed",
        "pr_created",
        "pr_merged",
        "merge_performed",
        "rebase_performed",
        "checkout_performed",
        "branch_created",
        "main_modified",
        "network_used",
        "provider_called",
        "mcp_used",
        "agent_called",
        "vault_written",
    ):
        executor = _executor()
        truth = dict(executor["runtime_truth"])  # type: ignore[index]
        truth[flag] = True
        executor["runtime_truth"] = truth
        result = evaluate_push_gate(_request(commit_executor_result=executor))
        assert result.blocked is True
        assert result.requires_human_intervention is True


def test_phase23_integration_blocks_unsafe_gate_evidence() -> None:
    assert evaluate_push_gate(_request(commit_gate_result=_commit_gate(commit_eligible=False))).blocked is True
    assert evaluate_push_gate(_request(commit_gate_result=_commit_gate(blocked=True))).blocked is True
    assert evaluate_push_gate(_request(commit_gate_result=_commit_gate(requires_human_intervention=True))).blocked is True
    for flag in (
        "secrets_detected",
        "main_modified",
        "git_mutated",
        "pr_created",
        "pr_merged",
        "network_used",
        "provider_called",
        "agent_called",
        "mcp_used",
        "vault_written",
    ):
        gate = _commit_gate()
        truth = dict(gate["runtime_truth"])  # type: ignore[index]
        truth[flag] = True
        gate["runtime_truth"] = truth
        assert evaluate_push_gate(_request(commit_gate_result=gate)).blocked is True


def test_child_runtime_truth_is_preserved() -> None:
    result = evaluate_push_gate(_request())
    child_events = result.runtime_truth["child_runtime_truth_events"]
    assert isinstance(child_events, list)
    assert len(child_events) == 2


def test_branch_safety_blocks_risky_targets() -> None:
    cases = [
        {"current_branch": "main"},
        {"current_branch": None},
        {"current_branch": "main", "base_branch": "main"},
        {"target_branch": "main"},
        {"remote_branch": "main"},
        {"base_branch": "develop"},
        {"current_branch": "release/1.0", "remote_branch": "release/1.0", "proposed_push_ref": "release/1.0"},
        {"current_branch": "prod/x", "remote_branch": "prod/x", "proposed_push_ref": "prod/x"},
        {"remote_branch": "protected/x", "proposed_push_ref": "protected/x"},
        {"proposed_push_ref": "refs/heads/main"},
        {"metadata": {"direct_main_edit": True}},
        {"metadata": {"push_main": True}},
        {"metadata": {"force_push": True}},
    ]
    for override in cases:
        result = evaluate_push_gate(_request(**override))
        assert result.blocked is True


def test_remote_safety_rules() -> None:
    assert evaluate_push_gate(_request(remote_name="origin")).push_eligible is True
    assert evaluate_push_gate(_request(remote_name="")).blocked is True
    assert evaluate_push_gate(_request(remote_name="origin;bad")).blocked is True
    assert evaluate_push_gate(_request(remote_branch="release/1.0", proposed_push_ref="release/1.0")).blocked is True
    assert evaluate_push_gate(_request(proposed_push_ref="+feature/phase25")).blocked is True
    assert evaluate_push_gate(_request(proposed_push_ref="feature/phase25 --force")).blocked is True
    assert evaluate_push_gate(_request(proposed_push_ref="-f")).blocked is True
    assert evaluate_push_gate(_request(proposed_push_ref="HEAD:feature/phase25")).blocked is True
    token_remote = evaluate_push_gate(_request(remote_name="https://ghp_placeholder@example.invalid/repo.git"))
    assert token_remote.blocked is True
    assert token_remote.redacted is True


def test_file_safety() -> None:
    for path in (
        "tests/example_test.py",
        "backend/python/module.py",
        "backend/rust/src/lib.rs",
        "frontend/src/App.tsx",
        "docs/example.md",
        "sandbox/local/runbook.md",
        "vault/templates/example.md",
    ):
        executor = _executor(files_staged=[path])
        assert evaluate_push_gate(_request(commit_executor_result=executor)).files_blocked == []

    for path in (
        ".env",
        "vault/08_ADR/example.md",
        "docs/governance/policy.md",
        "docs/security/threat-model.md",
        ".github/workflows/ci.yml",
        "../escape.py",
        "C:/outside/repo.py",
        ".git/config",
    ):
        executor = _executor(files_staged=[path])
        result = evaluate_push_gate(_request(commit_executor_result=executor))
        assert result.blocked is True
        assert result.requires_human_intervention is True


def test_push_plan_and_flags_are_metadata_only() -> None:
    result = evaluate_push_gate(_request())
    json.dumps(result.to_dict())
    assert result.required_pre_push_checks
    assert result.push_plan["risk_level"] == "low"
    assert result.can_execute_push is False
    assert result.can_force_push is False
    assert result.can_push_main is False
    assert result.can_open_pr is False
    assert result.can_merge is False
    assert result.can_rebase is False
    assert result.can_create_branch is False
    assert result.can_checkout is False
    assert result.can_edit_code is False
    assert result.can_apply_patch is False


def test_redaction_blocks_secret_like_metadata() -> None:
    auth = evaluate_push_gate(_request(metadata={"header": "Authorization: Bearer placeholder"}))
    assert auth.blocked is True
    assert auth.redacted is True
    assert "Authorization: Bearer" not in json.dumps(auth.to_dict())

    branch = evaluate_push_gate(_request(current_branch="feature/SECRET-placeholder"))
    assert branch.blocked is True
    assert branch.redacted is True
    assert "SECRET" not in json.dumps(branch.to_dict())

    ref = evaluate_push_gate(_request(proposed_push_ref="feature/ghp_placeholder"))
    assert ref.blocked is True
    assert ref.redacted is True
    assert "ghp_" not in json.dumps(ref.to_dict())

    env_file = _executor(files_staged=[".env"])
    result = evaluate_push_gate(_request(commit_executor_result=env_file))
    assert result.blocked is True
    assert result.redacted is True
    assert ".env" not in json.dumps(result.to_dict())


def test_source_has_no_execution_or_mutation_apis() -> None:
    source = Path("backend/python/brain/runtime/sandbox/push_gate.py").read_text(encoding="utf-8")
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
