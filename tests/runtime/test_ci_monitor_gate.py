"""Tests for the CI monitor gate."""

from __future__ import annotations

import json
from pathlib import Path

from brain.runtime.sandbox.ci_monitor_gate import evaluate_ci_monitor_gate


SAFE_SHA = "abc123def4567890abc123def4567890abc123de"


def _pr_creator(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "pr_created": True,
        "success": True,
        "blocked": False,
        "requires_human_intervention": False,
        "repository_full_name": "misaeldasilva123ms96-commits/Projeto-Omni",
        "source_branch": "feature/phase29",
        "head_branch": "feature/phase29",
        "base_branch": "main",
        "commit_sha": SAFE_SHA,
        "pr_number": 358,
        "pr_url": "https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/pull/358",
        "pr_state": "open",
        "final_draft": True,
        "runtime_truth": {
            "event_type": "sandbox.pr_creator.create",
            "secrets_detected": False,
            "pr_created": True,
            "pr_merged": False,
            "auto_merge_enabled": False,
            "approval_submitted": False,
            "push_executed": False,
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


def _pr_gate(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "pr_eligible": True,
        "blocked": False,
        "requires_human_intervention": False,
        "runtime_truth": {
            "event_type": "sandbox.pr_creation_gate.decision",
            "secrets_detected": False,
            "pr_created": False,
            "pr_merged": False,
            "auto_merge_enabled": False,
            "push_executed": False,
            "main_modified": False,
            "provider_called": False,
            "agent_called": False,
            "mcp_used": False,
            "vault_written": False,
        },
    }
    payload.update(overrides)
    return payload


def _push_executor(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "pushed": True,
        "success": True,
        "runtime_truth": {
            "event_type": "sandbox.push_executor.push",
            "secrets_detected": False,
            "force_push_executed": False,
            "main_pushed": False,
            "pr_merged": False,
            "auto_merge_enabled": False,
            "merge_performed": False,
            "rebase_performed": False,
            "checkout_performed": False,
            "branch_created": False,
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
        "pr_creator_result": _pr_creator(),
        "pr_creation_gate_result": _pr_gate(),
        "push_executor_result": _push_executor(),
        "ci_monitor_gate_mode": "evaluate_ci_monitor",
        "expected_workflows": ["CI", "Omni Security CI"],
        "expected_required_checks": ["build-and-test-js-python (24.x, 3.11)"],
    }
    payload.update(overrides)
    return payload


def test_modes_block_or_dry_run() -> None:
    assert evaluate_ci_monitor_gate(_request(ci_monitor_gate_mode="disabled")).blocked is True
    assert evaluate_ci_monitor_gate(_request(ci_monitor_gate_mode="blocked")).blocked is True
    assert evaluate_ci_monitor_gate(_request(ci_monitor_gate_mode="unknown")).blocked is True

    dry_run = evaluate_ci_monitor_gate(_request(ci_monitor_gate_mode="dry_run"))
    assert dry_run.dry_run is True
    assert dry_run.ci_monitor_eligible is False
    assert dry_run.can_monitor_ci is False
    assert dry_run.runtime_truth["ci_monitored"] is False


def test_evaluate_ci_monitor_marks_clean_evidence_eligible() -> None:
    result = evaluate_ci_monitor_gate(_request())
    assert result.evaluated is True
    assert result.success is True
    assert result.ci_monitor_eligible is True
    assert result.ci_monitor_ready_metadata_only is True
    assert result.requires_ci_monitor_executor_phase is True
    assert result.pr_was_created is True
    assert result.pr_evidence_clean is True
    assert result.repository_safe is True
    assert result.pr_safe is True
    assert result.branch_safe is True
    assert result.base_safe is True
    assert result.head_sha_safe is True
    assert result.ci_monitor_plan["allowed_in_future_ci_monitoring"] is True
    assert result.ci_monitor_plan["polling_strategy"] == "bounded_polling"
    assert result.runtime_truth["event_type"] == "sandbox.ci_monitor_gate.decision"
    assert result.runtime_truth["governance_decision"] == "ci_monitor_eligible"


def test_phase28_integration_blocks_invalid_creator_evidence() -> None:
    assert evaluate_ci_monitor_gate(_request(pr_creator_result=None)).blocked is True
    assert evaluate_ci_monitor_gate(_request(pr_creator_result=_pr_creator(pr_created=False))).blocked is True
    assert evaluate_ci_monitor_gate(_request(pr_creator_result=_pr_creator(success=False))).blocked is True
    assert evaluate_ci_monitor_gate(_request(pr_creator_result=_pr_creator(pr_number=None))).blocked is True
    assert evaluate_ci_monitor_gate(_request(pr_creator_result=_pr_creator(pr_url=None))).blocked is True
    assert evaluate_ci_monitor_gate(_request(pr_creator_result=_pr_creator(blocked=True))).blocked is True
    assert evaluate_ci_monitor_gate(_request(pr_creator_result=_pr_creator(requires_human_intervention=True))).blocked is True

    for flag in (
        "secrets_detected",
        "pr_merged",
        "auto_merge_enabled",
        "approval_submitted",
        "push_executed",
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
        creator = _pr_creator()
        truth = dict(creator["runtime_truth"])  # type: ignore[index]
        truth[flag] = True
        creator["runtime_truth"] = truth
        assert evaluate_ci_monitor_gate(_request(pr_creator_result=creator)).blocked is True


def test_phase27_and_phase26_integration_blocks_unsafe_evidence() -> None:
    assert evaluate_ci_monitor_gate(_request(pr_creation_gate_result=_pr_gate(pr_eligible=False))).blocked is True
    assert evaluate_ci_monitor_gate(_request(pr_creation_gate_result=_pr_gate(blocked=True))).blocked is True
    assert evaluate_ci_monitor_gate(_request(pr_creation_gate_result=_pr_gate(requires_human_intervention=True))).blocked is True
    for flag in ("secrets_detected", "pr_created", "pr_merged", "auto_merge_enabled", "push_executed", "main_modified"):
        gate = _pr_gate()
        truth = dict(gate["runtime_truth"])  # type: ignore[index]
        truth[flag] = True
        gate["runtime_truth"] = truth
        assert evaluate_ci_monitor_gate(_request(pr_creation_gate_result=gate)).blocked is True

    assert evaluate_ci_monitor_gate(_request(push_executor_result=_push_executor(pushed=False))).blocked is True
    assert evaluate_ci_monitor_gate(_request(push_executor_result=_push_executor(success=False))).blocked is True
    for flag in ("force_push_executed", "main_pushed", "merge_performed", "rebase_performed", "branch_created"):
        push = _push_executor()
        truth = dict(push["runtime_truth"])  # type: ignore[index]
        truth[flag] = True
        push["runtime_truth"] = truth
        assert evaluate_ci_monitor_gate(_request(push_executor_result=push)).blocked is True


def test_pr_state_branch_repository_and_sha_safety() -> None:
    assert evaluate_ci_monitor_gate(_request(pr_creator_result=_pr_creator(pr_state="closed"))).blocked is True
    assert evaluate_ci_monitor_gate(_request(pr_creator_result=_pr_creator(pr_state="merged"))).blocked is True
    assert evaluate_ci_monitor_gate(_request(pr_creator_result=_pr_creator(pr_state="unknown"))).blocked is True
    assert evaluate_ci_monitor_gate(_request(metadata={"locked": True})).requires_human_intervention is True
    assert evaluate_ci_monitor_gate(_request(metadata={"repository_archived": True})).requires_human_intervention is True

    cases = [
        {"head_branch": "main"},
        {"source_branch": "main"},
        {"base_branch": "develop"},
        {"head_branch": "release/1.0", "source_branch": "release/1.0"},
        {"metadata": {"direct_main_edit": True}},
        {"metadata": {"source_main": True}},
    ]
    for override in cases:
        creator = _pr_creator(**{key: value for key, value in override.items() if key in {"head_branch", "source_branch", "base_branch"}})
        result = evaluate_ci_monitor_gate(_request(pr_creator_result=creator, **override))
        assert result.blocked is True
    assert evaluate_ci_monitor_gate(_request(pr_creator_result=_pr_creator(head_branch=None), head_branch=None)).blocked is True
    assert evaluate_ci_monitor_gate(_request(pr_creator_result=_pr_creator(source_branch=None), source_branch=None)).blocked is True

    assert evaluate_ci_monitor_gate(_request(pr_creator_result=_pr_creator(repository_full_name=None), repository_full_name=None)).blocked is True
    assert evaluate_ci_monitor_gate(_request(repository_full_name="owner/repo;bad")).blocked is True
    assert evaluate_ci_monitor_gate(_request(repository_full_name="owner/ghp_placeholder")).redacted is True
    assert evaluate_ci_monitor_gate(_request(repository_full_name="owner/github_pat_placeholder")).redacted is True
    assert evaluate_ci_monitor_gate(_request(repository_full_name="https://token@example.invalid/repo")).blocked is True
    assert evaluate_ci_monitor_gate(_request(repository_full_name="missing-owner")).blocked is True
    assert evaluate_ci_monitor_gate(_request(repository_full_name="other/fork")).blocked is True

    assert evaluate_ci_monitor_gate(_request(head_sha="abc123d")).ci_monitor_eligible is True
    assert evaluate_ci_monitor_gate(_request(head_sha=None, commit_sha=None, pr_creator_result=_pr_creator(commit_sha=None))).blocked is True
    assert evaluate_ci_monitor_gate(_request(head_sha="abc123d;bad")).blocked is True
    assert evaluate_ci_monitor_gate(_request(head_sha="OPENAI_API_KEY")).redacted is True


def test_ci_provider_workflow_plan_and_flags() -> None:
    assert evaluate_ci_monitor_gate(_request(expected_ci_providers=["github_actions"])).ci_monitor_eligible is True
    assert evaluate_ci_monitor_gate(_request(expected_ci_providers=["github_actions"])).ci_monitor_eligible is True
    assert evaluate_ci_monitor_gate(_request(expected_ci_providers=["jenkins"])).blocked is True
    assert evaluate_ci_monitor_gate(_request(expected_ci_providers=["github_actions;bad"])).blocked is True
    assert evaluate_ci_monitor_gate(_request(expected_workflows=["CI"])).ci_monitor_eligible is True
    assert evaluate_ci_monitor_gate(_request(expected_workflows=["OPENAI_API_KEY placeholder"])).redacted is True
    assert evaluate_ci_monitor_gate(_request(expected_workflows=["production deploy"])).blocked is True

    result = evaluate_ci_monitor_gate(_request())
    json.dumps(result.ci_monitor_plan)
    assert result.required_pre_ci_monitor_checks
    for flag in (
        "can_monitor_ci",
        "can_call_github_api",

        "can_download_logs",
        "can_retry_workflows",
        "can_start_repair_loop",
        "can_update_pr",
        "can_merge",
        "can_auto_merge",
        "can_push",
        "can_force_push",
        "can_push_main",
        "can_rebase",
        "can_create_branch",
        "can_checkout",
        "can_edit_code",
        "can_apply_patch",
    ):
        assert getattr(result, flag) is False
    for flag in (
        "ci_monitored",
        "ci_status_fetched",
        "workflow_runs_fetched",
        "check_runs_fetched",
        "logs_downloaded",
        "workflow_retried",
        "repair_loop_started",
        "pr_created",
        "pr_updated",
        "pr_merged",
        "auto_merge_enabled",
        "push_executed",
        "command_executed",
        "git_mutated",
        "network_used",
    ):
        assert result.runtime_truth[flag] is False


def test_redaction_blocks_secret_like_inputs() -> None:
    result = evaluate_ci_monitor_gate(_request(metadata={"header": "Authorization: Bearer placeholder"}))
    assert result.blocked is True
    assert result.redacted is True
    assert "Authorization: Bearer" not in json.dumps(result.to_dict())

    branch = evaluate_ci_monitor_gate(_request(head_branch="feature/SECRET-placeholder"))
    assert branch.blocked is True
    assert "SECRET" not in json.dumps(branch.to_dict())

    repo = evaluate_ci_monitor_gate(_request(repository_full_name="owner/ghp_placeholder"))
    assert repo.blocked is True
    assert "ghp_" not in json.dumps(repo.to_dict())


def test_source_has_no_unsafe_implementation() -> None:
    source = Path("backend/python/brain/runtime/sandbox/ci_monitor_gate.py").read_text(encoding="utf-8")
    forbidden = [
        "subprocess",
        "shell=True",
        "os.system",
        "eval(",
        "exec(",
        " gh ",
        "requests.",
        "urllib",
        "socket",
        "http.client",
        "download_logs(",
        "retry_workflow(",
        "repair_loop(",
        "git push",
        "git add",
        "git commit",
        "git merge",
        "git rebase",
        "git checkout",
        "git switch",
        "git branch",
        "create_pull_request",
        "update_pull_request",
        "merge_pull_request",
        "auto_merge(",
        "approve(",
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
