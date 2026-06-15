"""Tests for the CI repair loop gate."""

from __future__ import annotations

import json
from pathlib import Path

from brain.runtime.sandbox.ci_repair_loop_gate import evaluate_ci_repair_loop_gate

SAFE_SHA = "abc123def4567890abc123def4567890abc123de"


def _ci_monitor(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "monitored": True,
        "blocked": False,
        "dry_run": False,
        "success": True,
        "failed": True,
        "passed": False,
        "pending": False,
        "requires_human_intervention": False,
        "repository_full_name": "misaeldasilva123ms96-commits/Projeto-Omni",
        "pr_number": 360,
        "pr_url": "https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/pull/360",
        "pr_state": "open",
        "source_branch": "sandbox/ci-repair-loop-gate",
        "head_branch": "sandbox/ci-repair-loop-gate",
        "base_branch": "main",
        "head_sha": SAFE_SHA,
        "commit_sha": SAFE_SHA,
        "aggregate_status": "failure",
        "aggregate_conclusion": "failed",
        "failing_checks": [
            {"name": "build-and-test-js-python", "status": "failure", "required": True, "provider": "github_actions"}
        ],
        "pending_checks": [],
        "missing_required_checks": [],
        "unknown_checks": [],
        "successful_checks": [],
        "skipped_or_neutral_checks": [],
        "runtime_truth": {
            "event_type": "sandbox.ci_monitor.monitor",
            "secrets_detected": False,
            "logs_downloaded": False,
            "workflow_retried": False,
            "workflow_triggered": False,
            "repair_loop_started": False,
            "pr_updated": False,
            "pr_merged": False,
            "auto_merge_enabled": False,
            "push_executed": False,
            "command_executed": False,
            "git_mutated": False,
            "provider_called": False,
            "mcp_used": False,
            "agent_called": False,
            "vault_written": False,
            "main_modified": False,
        },
    }
    payload.update(overrides)
    return payload


def _ci_gate(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "ci_monitor_eligible": True,
        "blocked": False,
        "requires_human_intervention": False,
        "runtime_truth": {
            "event_type": "sandbox.ci_monitor_gate.decision",
            "secrets_detected": False,
            "ci_monitored": False,
            "logs_downloaded": False,
            "workflow_retried": False,
            "repair_loop_started": False,
            "pr_updated": False,
            "pr_merged": False,
            "auto_merge_enabled": False,
            "push_executed": False,
            "command_executed": False,
            "git_mutated": False,
            "provider_called": False,
            "agent_called": False,
            "mcp_used": False,
            "vault_written": False,
            "main_modified": False,
        },
    }
    payload.update(overrides)
    return payload


def _pr_creator(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "pr_created": True,
        "success": True,
        "blocked": False,
        "requires_human_intervention": False,
        "repository_full_name": "misaeldasilva123ms96-commits/Projeto-Omni",
        "source_branch": "sandbox/ci-repair-loop-gate",
        "head_branch": "sandbox/ci-repair-loop-gate",
        "base_branch": "main",
        "commit_sha": SAFE_SHA,
        "pr_number": 360,
        "pr_url": "https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/pull/360",
        "pr_state": "open",
        "runtime_truth": {
            "event_type": "sandbox.pr_creator.create",
            "secrets_detected": False,
            "pr_merged": False,
            "auto_merge_enabled": False,
            "approval_submitted": False,
            "push_executed": False,
            "merge_performed": False,
            "rebase_performed": False,
            "checkout_performed": False,
            "branch_created": False,
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
            "mcp_used": False,
        },
    }
    payload.update(overrides)
    return payload


def _request(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "ci_monitor_result": _ci_monitor(),
        "ci_monitor_gate_result": _ci_gate(),
        "pr_creator_result": _pr_creator(),
        "pr_creation_gate_result": _pr_gate(),
        "repair_gate_mode": "evaluate_repair",
    }
    payload.update(overrides)
    return payload


# --- Modes ---


def test_modes_block_or_dry_run() -> None:
    assert evaluate_ci_repair_loop_gate(_request(repair_gate_mode="disabled")).blocked is True
    assert evaluate_ci_repair_loop_gate(_request(repair_gate_mode="blocked")).blocked is True
    assert evaluate_ci_repair_loop_gate(_request(repair_gate_mode="unknown")).blocked is True

    dry_run = evaluate_ci_repair_loop_gate(_request(repair_gate_mode="dry_run"))
    assert dry_run.dry_run is True
    assert dry_run.repair_loop_eligible is False
    assert dry_run.can_start_repair_loop is False
    assert dry_run.runtime_truth["repair_loop_started"] is False


def test_evaluate_repair_marks_clean_failed_ci_eligible() -> None:
    result = evaluate_ci_repair_loop_gate(_request())
    assert result.evaluated is True
    assert result.success is True
    assert result.repair_loop_eligible is True
    assert result.repair_loop_ready_metadata_only is True
    assert result.ci_monitor_clean is True
    assert result.ci_failed is True
    assert result.requires_repair_planner_phase is True
    assert result.runtime_truth["event_type"] == "sandbox.ci_repair_loop_gate.decision"
    assert result.runtime_truth["governance_decision"] == "repair_loop_eligible"


# --- Phase 30 integration ---


def test_phase30_integration_blocks_invalid_ci_monitor_evidence() -> None:
    assert evaluate_ci_repair_loop_gate(_request(ci_monitor_result=None)).blocked is True
    assert evaluate_ci_repair_loop_gate(_request(ci_monitor_result=_ci_monitor(monitored=False))).blocked is True
    assert evaluate_ci_repair_loop_gate(_request(ci_monitor_result=_ci_monitor(success=False))).blocked is True
    assert evaluate_ci_repair_loop_gate(_request(ci_monitor_result=_ci_monitor(blocked=True))).blocked is True
    assert evaluate_ci_repair_loop_gate(_request(ci_monitor_result=_ci_monitor(requires_human_intervention=True))).blocked is True


def test_phase30_passed_ci_returns_repair_not_needed() -> None:
    result = evaluate_ci_repair_loop_gate(_request(ci_monitor_result=_ci_monitor(failed=False, passed=True)))
    assert result.ci_passed is True
    assert result.repair_loop_eligible is False
    assert result.runtime_truth["governance_decision"] == "repair_not_needed"


def test_phase30_pending_ci_returns_wait_for_ci() -> None:
    result = evaluate_ci_repair_loop_gate(_request(ci_monitor_result=_ci_monitor(failed=False, passed=False, pending=True)))
    assert result.ci_pending is True
    assert result.repair_loop_eligible is False
    assert result.runtime_truth["governance_decision"] == "repair_wait_for_ci"


def test_phase30_missing_required_checks_requires_human() -> None:
    mon = _ci_monitor(missing_required_checks=["missing-check"])
    result = evaluate_ci_repair_loop_gate(_request(ci_monitor_result=mon))
    assert result.repair_loop_eligible is False
    assert result.requires_human_intervention is True


def test_phase30_runtime_truth_unsafe_flags_block() -> None:
    for flag in ("secrets_detected", "logs_downloaded", "workflow_retried", "workflow_triggered", "repair_loop_started"):
        mon = _ci_monitor()
        truth = dict(mon["runtime_truth"])  # type: ignore[index]
        truth[flag] = True
        mon["runtime_truth"] = truth
        assert evaluate_ci_repair_loop_gate(_request(ci_monitor_result=mon)).blocked is True

    for flag in ("pr_updated", "pr_merged", "auto_merge_enabled", "push_executed", "command_executed", "git_mutated"):
        mon = _ci_monitor()
        truth = dict(mon["runtime_truth"])  # type: ignore[index]
        truth[flag] = True
        mon["runtime_truth"] = truth
        assert evaluate_ci_repair_loop_gate(_request(ci_monitor_result=mon)).blocked is True

    for flag in ("provider_called", "mcp_used", "agent_called", "vault_written", "main_modified"):
        mon = _ci_monitor()
        truth = dict(mon["runtime_truth"])  # type: ignore[index]
        truth[flag] = True
        mon["runtime_truth"] = truth
        assert evaluate_ci_repair_loop_gate(_request(ci_monitor_result=mon)).blocked is True


# --- Phase 29 integration ---


def test_phase29_integration_blocks_unsafe_evidence() -> None:
    assert evaluate_ci_repair_loop_gate(_request(ci_monitor_gate_result=None)).blocked is False
    assert evaluate_ci_repair_loop_gate(_request(ci_monitor_gate_result=_ci_gate(ci_monitor_eligible=False))).blocked is True
    assert evaluate_ci_repair_loop_gate(_request(ci_monitor_gate_result=_ci_gate(blocked=True))).blocked is True
    assert evaluate_ci_repair_loop_gate(_request(ci_monitor_gate_result=_ci_gate(requires_human_intervention=True))).blocked is True

    for flag in ("secrets_detected", "ci_monitored", "logs_downloaded", "workflow_retried", "repair_loop_started"):
        gate = _ci_gate()
        truth = dict(gate["runtime_truth"])  # type: ignore[index]
        truth[flag] = True
        gate["runtime_truth"] = truth
        assert evaluate_ci_repair_loop_gate(_request(ci_monitor_gate_result=gate)).blocked is True

    for flag in ("pr_updated", "pr_merged", "auto_merge_enabled", "push_executed", "command_executed", "git_mutated"):
        gate = _ci_gate()
        truth = dict(gate["runtime_truth"])  # type: ignore[index]
        truth[flag] = True
        gate["runtime_truth"] = truth
        assert evaluate_ci_repair_loop_gate(_request(ci_monitor_gate_result=gate)).blocked is True

    for flag in ("provider_called", "agent_called", "mcp_used", "vault_written", "main_modified"):
        gate = _ci_gate()
        truth = dict(gate["runtime_truth"])  # type: ignore[index]
        truth[flag] = True
        gate["runtime_truth"] = truth
        assert evaluate_ci_repair_loop_gate(_request(ci_monitor_gate_result=gate)).blocked is True


# --- PR/repository/branch/SHA safety ---


def test_pr_state_and_branch_safety() -> None:
    assert evaluate_ci_repair_loop_gate(_request(pr_state="open")).blocked is False
    assert evaluate_ci_repair_loop_gate(_request(pr_state="closed")).blocked is True
    assert evaluate_ci_repair_loop_gate(_request(pr_state="merged")).blocked is True
    assert evaluate_ci_repair_loop_gate(_request(pr_state="unknown")).blocked is True
    assert evaluate_ci_repair_loop_gate(_request(metadata={"locked": True})).requires_human_intervention is True
    assert evaluate_ci_repair_loop_gate(_request(metadata={"repository_archived": True})).requires_human_intervention is True

    assert evaluate_ci_repair_loop_gate(_request(head_branch="main")).blocked is True
    assert evaluate_ci_repair_loop_gate(_request(source_branch="main")).blocked is True
    assert evaluate_ci_repair_loop_gate(_request(base_branch="develop")).blocked is True
    assert evaluate_ci_repair_loop_gate(_request(head_branch="release/1.0", source_branch="release/1.0")).blocked is True
    mon = _ci_monitor(head_branch=None, source_branch=None)
    assert evaluate_ci_repair_loop_gate(_request(ci_monitor_result=mon, head_branch=None, source_branch=None, pr_creator_result=_pr_creator(head_branch=None, source_branch=None))).blocked is True

    assert evaluate_ci_repair_loop_gate(_request(repository_full_name="misaeldasilva123ms96-commits/Projeto-Omni")).blocked is False
    assert evaluate_ci_repair_loop_gate(_request(repository_full_name="owner/repo;bad")).blocked is True
    assert evaluate_ci_repair_loop_gate(_request(repository_full_name="owner/ghp_placeholder")).redacted is True
    assert evaluate_ci_repair_loop_gate(_request(repository_full_name="other/fork")).blocked is True

    assert evaluate_ci_repair_loop_gate(_request(head_sha=SAFE_SHA)).blocked is False
    assert evaluate_ci_repair_loop_gate(_request(head_sha=None, commit_sha=SAFE_SHA)).blocked is False
    mon = _ci_monitor(head_sha=None, commit_sha=None)
    assert evaluate_ci_repair_loop_gate(_request(ci_monitor_result=mon, head_sha=None, commit_sha=None, pr_creator_result=_pr_creator(commit_sha=None))).blocked is True
    assert evaluate_ci_repair_loop_gate(_request(head_sha="abc123d;bad")).blocked is True
    assert evaluate_ci_repair_loop_gate(_request(head_sha="OPENAI_API_KEY")).redacted is True


# --- Failure categorization ---


def test_failure_categorization() -> None:
    test_check = _ci_monitor(failing_checks=[{"name": "pytest / test-suite", "status": "failure", "required": True}])
    result = evaluate_ci_repair_loop_gate(_request(ci_monitor_result=test_check))
    assert "test_failure" in result.failure_categories
    assert result.repair_loop_eligible is True

    typecheck = _ci_monitor(failing_checks=[{"name": "typecheck / tsc", "status": "failure", "required": True}])
    assert "typecheck_failure" in evaluate_ci_repair_loop_gate(_request(ci_monitor_result=typecheck)).failure_categories

    flint = _ci_monitor(failing_checks=[{"name": "lint / eslint", "status": "failure", "required": True}])
    assert "lint_failure" in evaluate_ci_repair_loop_gate(_request(ci_monitor_result=flint)).failure_categories

    fmt = _ci_monitor(failing_checks=[{"name": "fmt / black", "status": "failure", "required": True}])
    assert "format_failure" in evaluate_ci_repair_loop_gate(_request(ci_monitor_result=fmt)).failure_categories

    build = _ci_monitor(failing_checks=[{"name": "build / cargo check", "status": "failure", "required": True}])
    assert "build_failure" in evaluate_ci_repair_loop_gate(_request(ci_monitor_result=build)).failure_categories


def test_blocked_failure_categories() -> None:
    codeql = _ci_monitor(failing_checks=[{"name": "CodeQL security", "status": "failure", "required": True}])
    result = evaluate_ci_repair_loop_gate(_request(ci_monitor_result=codeql))
    assert "security_failure" in result.blocked_failure_categories
    assert result.repair_loop_eligible is False

    deploy = _ci_monitor(failing_checks=[{"name": "deploy production", "status": "failure", "required": True}])
    result2 = evaluate_ci_repair_loop_gate(_request(ci_monitor_result=deploy))
    assert "deployment_failure" in result2.blocked_failure_categories
    assert result2.repair_loop_eligible is False

    billing = _ci_monitor(failing_checks=[{"name": "billing check", "status": "failure", "required": True}])
    result3 = evaluate_ci_repair_loop_gate(_request(ci_monitor_result=billing))
    assert "billing_failure" in result3.blocked_failure_categories
    assert result3.repair_loop_eligible is False

    perm = _ci_monitor(failing_checks=[{"name": "permission test", "status": "failure", "required": True}])
    result4 = evaluate_ci_repair_loop_gate(_request(ci_monitor_result=perm))
    assert "permission_failure" in result4.blocked_failure_categories
    assert result4.repair_loop_eligible is False

    unknown = _ci_monitor(failing_checks=[{"name": "weird-check-name", "status": "failure", "required": True}])
    result5 = evaluate_ci_repair_loop_gate(_request(ci_monitor_result=unknown))
    assert "unknown_infrastructure_failure" in result5.blocked_failure_categories
    assert result5.repair_loop_eligible is False


def test_mixed_allowed_and_blocked_categories() -> None:
    mixed = _ci_monitor(
        failing_checks=[
            {"name": "pytest", "status": "failure", "required": True},
            {"name": "CodeQL security", "status": "failure", "required": True},
        ]
    )
    result = evaluate_ci_repair_loop_gate(_request(ci_monitor_result=mixed))
    assert "test_failure" in result.failure_categories
    assert "security_failure" in result.blocked_failure_categories
    assert result.repair_loop_eligible is False


# --- Attempt budget ---


def test_attempt_budget() -> None:
    assert evaluate_ci_repair_loop_gate(_request(current_repair_attempt=0, max_repair_attempts=3)).repair_loop_eligible is True
    assert evaluate_ci_repair_loop_gate(_request(current_repair_attempt=2, max_repair_attempts=3)).repair_loop_eligible is True
    assert evaluate_ci_repair_loop_gate(_request(current_repair_attempt=3, max_repair_attempts=3)).repair_loop_eligible is False
    assert evaluate_ci_repair_loop_gate(_request(current_repair_attempt=5, max_repair_attempts=3)).repair_loop_eligible is False
    assert evaluate_ci_repair_loop_gate(_request(current_repair_attempt=-1, max_repair_attempts=3)).repair_loop_eligible is False
    assert evaluate_ci_repair_loop_gate(_request(current_repair_attempt=0, max_repair_attempts=0)).repair_loop_eligible is False
    assert evaluate_ci_repair_loop_gate(_request(current_repair_attempt=0, max_repair_attempts=11)).repair_loop_eligible is False


def test_attempt_budget_remaining_not_negative() -> None:
    result = evaluate_ci_repair_loop_gate(_request(current_repair_attempt=5, max_repair_attempts=3))
    assert result.attempt_budget_remaining >= 0
    assert result.attempt_budget_remaining == 0


# --- Repair plan ---


def test_repair_plan_is_metadata_only() -> None:
    result = evaluate_ci_repair_loop_gate(_request())
    json.dumps(result.repair_plan)
    assert result.repair_plan["plan_id"] == "ci-repair-loop-plan-1"
    assert result.repair_plan["allowed_in_future_repair_loop"] is True
    assert result.repair_plan["next_allowed_phase"] == "ci_repair_planner"
    assert result.required_pre_repair_checks


def test_repair_plan_next_allowed_phases() -> None:
    pending = evaluate_ci_repair_loop_gate(
        _request(ci_monitor_result=_ci_monitor(failed=False, passed=False, pending=True))
    )
    assert pending.repair_plan["next_allowed_phase"] == "wait_for_ci"

    passed = evaluate_ci_repair_loop_gate(
        _request(ci_monitor_result=_ci_monitor(failed=False, passed=True, pending=False))
    )
    assert passed.repair_plan["next_allowed_phase"] == "merge_gate"

    blocked = evaluate_ci_repair_loop_gate(_request(repair_gate_mode="disabled"))
    assert blocked.repair_plan["next_allowed_phase"] == "human_review"


# --- Flags ---


def test_all_action_flags_remain_false() -> None:
    result = evaluate_ci_repair_loop_gate(_request())
    for flag in (
        "can_start_repair_loop",
        "can_download_logs",
        "can_retry_workflows",
        "can_trigger_workflows",
        "can_call_provider",
        "can_call_agent",
        "can_create_patch_proposal",
        "can_apply_patch",
        "can_write_files",
        "can_commit",
        "can_push",
        "can_update_pr",
        "can_merge",
        "can_auto_merge",
        "can_mutate_git",
        "can_execute_commands",
    ):
        assert getattr(result, flag) is False


def test_runtime_truth_action_flags_false() -> None:
    result = evaluate_ci_repair_loop_gate(_request()).runtime_truth
    for flag in (
        "repair_loop_started",
        "repair_plan_created",
        "logs_downloaded",
        "workflow_retried",
        "workflow_triggered",
        "provider_called",
        "agent_called",
        "mcp_used",
        "patch_proposed",
        "patch_applied",
        "files_written",
        "code_edited",
        "command_executed",
        "git_mutated",
        "commit_executed",
        "push_executed",
        "pr_updated",
        "pr_merged",
        "auto_merge_enabled",
        "main_modified",
        "vault_written",
    ):
        assert result[flag] is False


# --- Repair scope ---


def test_repair_scope_metadata_only() -> None:
    result = evaluate_ci_repair_loop_gate(_request())
    for entry in result.repair_scope:
        assert "affected_provider" in entry
        assert "failing_check_name" in entry
        assert "failure_category" in entry
        assert "blocking" in entry
        assert "safe_to_plan_repair" in entry
        assert "suggested_next_phase" in entry


# --- Governance decision ---


def test_governance_decisions() -> None:
    assert evaluate_ci_repair_loop_gate(_request(repair_gate_mode="disabled")).runtime_truth["governance_decision"] == "blocked"
    assert evaluate_ci_repair_loop_gate(_request(repair_gate_mode="dry_run")).runtime_truth["governance_decision"] == "dry_run"

    passed = evaluate_ci_repair_loop_gate(
        _request(ci_monitor_result=_ci_monitor(failed=False, passed=True))
    )
    assert passed.runtime_truth["governance_decision"] == "repair_not_needed"

    pending = evaluate_ci_repair_loop_gate(
        _request(ci_monitor_result=_ci_monitor(failed=False, passed=False, pending=True))
    )
    assert pending.runtime_truth["governance_decision"] == "repair_wait_for_ci"

    eligible = evaluate_ci_repair_loop_gate(_request())
    assert eligible.runtime_truth["governance_decision"] == "repair_loop_eligible"

    exhausted = evaluate_ci_repair_loop_gate(_request(current_repair_attempt=3, max_repair_attempts=3))
    assert exhausted.runtime_truth["governance_decision"] == "repair_budget_exceeded"


# --- Redaction ---


def test_redaction_blocks_secret_like_inputs() -> None:
    result = evaluate_ci_repair_loop_gate(_request(metadata={"header": "Authorization: Bearer placeholder"}))
    assert result.blocked is True
    assert result.redacted is True
    assert "Authorization: Bearer" not in json.dumps(result.to_dict())

    branch = evaluate_ci_repair_loop_gate(_request(head_branch="feature/SECRET-placeholder"))
    assert branch.blocked is True
    assert "SECRET" not in json.dumps(branch.to_dict())

    repo = evaluate_ci_repair_loop_gate(_request(repository_full_name="owner/ghp_placeholder"))
    assert repo.blocked is True
    assert "ghp_" not in json.dumps(repo.to_dict())

    scope_result = evaluate_ci_repair_loop_gate(
        _request(ci_monitor_result=_ci_monitor(failing_checks=[{"name": "ghp_placeholder", "status": "failure", "required": True}]))
    )
    assert scope_result.blocked is True


# --- No unsafe implementation ---


def test_source_has_no_unsafe_implementation() -> None:
    source = Path("backend/python/brain/runtime/sandbox/ci_repair_loop_gate.py").read_text(encoding="utf-8")
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
        "trigger_workflow(",
        "repair_loop(",
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
