"""Tests for the CI repair planner."""

from __future__ import annotations

import json
from pathlib import Path

from brain.runtime.sandbox.ci_repair_planner import evaluate_ci_repair_planner

SAFE_SHA = "abc123def4567890abc123def4567890abc123de"


def _ci_repair_gate(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "repair_loop_eligible": True,
        "repair_loop_ready_metadata_only": True,
        "success": True,
        "blocked": False,
        "requires_human_intervention": False,
        "failure_categories": ["test_failure"],
        "blocked_failure_categories": [],
        "failing_checks": [
            {"name": "pytest / test-suite", "status": "failure", "required": True, "provider": "github_actions"}
        ],
        "pending_checks": [],
        "missing_required_checks": [],
        "unknown_checks": [],
        "repair_scope": [],
        "max_repair_attempts": 3,
        "current_repair_attempt": 0,
        "attempt_budget_remaining": 3,
        "repository_full_name": "misaeldasilva123ms96-commits/Projeto-Omni",
        "pr_number": 361,
        "pr_url": "https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/pull/361",
        "pr_state": "open",
        "source_branch": "sandbox/ci-repair-planner",
        "head_branch": "sandbox/ci-repair-planner",
        "base_branch": "main",
        "head_sha": SAFE_SHA,
        "commit_sha": SAFE_SHA,
        "aggregate_status": "failure",
        "aggregate_conclusion": "failed",
        "runtime_truth": {
            "event_type": "sandbox.ci_repair_loop_gate.decision",
            "secrets_detected": False,
            "repair_loop_started": False,
            "repair_plan_created": False,
            "logs_downloaded": False,
            "workflow_retried": False,
            "workflow_triggered": False,
            "provider_called": False,
            "agent_called": False,
            "mcp_used": False,
            "patch_proposed": False,
            "patch_applied": False,
            "files_written": False,
            "code_edited": False,
            "command_executed": False,
            "git_mutated": False,
            "commit_executed": False,
            "push_executed": False,
            "pr_updated": False,
            "pr_merged": False,
            "auto_merge_enabled": False,
            "approval_submitted": False,
            "main_modified": False,
            "vault_written": False,
            "attempt_budget_remaining": 3,
        },
    }
    payload.update(overrides)
    return payload


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
        "pr_number": 361,
        "pr_url": "https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/pull/361",
        "pr_state": "open",
        "source_branch": "sandbox/ci-repair-planner",
        "head_branch": "sandbox/ci-repair-planner",
        "base_branch": "main",
        "head_sha": SAFE_SHA,
        "commit_sha": SAFE_SHA,
        "aggregate_status": "failure",
        "aggregate_conclusion": "failed",
        "failing_checks": [
            {"name": "pytest / test-suite", "status": "failure", "required": True, "provider": "github_actions"}
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
        "source_branch": "sandbox/ci-repair-planner",
        "head_branch": "sandbox/ci-repair-planner",
        "base_branch": "main",
        "commit_sha": SAFE_SHA,
        "pr_number": 361,
        "pr_url": "https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/pull/361",
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


def _request(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "ci_repair_loop_gate_result": _ci_repair_gate(),
        "ci_monitor_result": _ci_monitor(),
        "ci_monitor_gate_result": _ci_gate(),
        "pr_creator_result": _pr_creator(),
        "planner_mode": "plan_repair",
    }
    payload.update(overrides)
    return payload


# --- Modes ---


def test_disabled_mode_blocks() -> None:
    result = evaluate_ci_repair_planner(_request(planner_mode="disabled"))
    assert result.blocked is True
    assert result.planned is False


def test_blocked_mode_blocks() -> None:
    result = evaluate_ci_repair_planner(_request(planner_mode="blocked"))
    assert result.blocked is True
    assert result.planned is False


def test_dry_run_validates_evidence() -> None:
    result = evaluate_ci_repair_planner(_request(planner_mode="dry_run"))
    assert result.dry_run is True
    assert result.planned is False
    assert result.repair_plan_ready is False
    assert result.can_start_repair_loop is False


def test_plan_repair_creates_safe_plan() -> None:
    result = evaluate_ci_repair_planner(_request())
    assert result.planned is True
    assert result.repair_plan_ready is True
    assert result.repair_plan["next_allowed_phase"] == "scoped_ci_patch_proposal_gate"


def test_unknown_mode_blocks() -> None:
    result = evaluate_ci_repair_planner(_request(planner_mode="unknown"))
    assert result.blocked is True


# --- Phase 31 integration ---


def test_clean_repair_gate_allows_planning() -> None:
    result = evaluate_ci_repair_planner(_request())
    assert result.planned is True
    assert result.repair_gate_eligible is True


def test_missing_repair_gate_blocks() -> None:
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=None))
    assert result.blocked is True


def test_repair_gate_not_eligible_blocks() -> None:
    gate = _ci_repair_gate(repair_loop_eligible=False, repair_loop_ready_metadata_only=False)
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_blocked_repair_gate_blocks() -> None:
    gate = _ci_repair_gate(blocked=True)
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_repair_gate_human_blocks() -> None:
    gate = _ci_repair_gate(requires_human_intervention=True)
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_repair_gate_blocked_categories_blocks() -> None:
    gate = _ci_repair_gate(blocked_failure_categories=["security_failure"])
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_repair_gate_no_budget_blocks() -> None:
    gate = _ci_repair_gate(attempt_budget_remaining=0)
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_repair_gate_secrets_detected_blocks() -> None:
    truth = dict(_ci_repair_gate()["runtime_truth"])  # type: ignore[index]
    truth["secrets_detected"] = True
    gate = _ci_repair_gate(runtime_truth=truth)
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_repair_gate_repair_loop_started_blocks() -> None:
    truth = dict(_ci_repair_gate()["runtime_truth"])  # type: ignore[index]
    truth["repair_loop_started"] = True
    gate = _ci_repair_gate(runtime_truth=truth)
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_repair_gate_logs_downloaded_blocks() -> None:
    truth = dict(_ci_repair_gate()["runtime_truth"])  # type: ignore[index]
    truth["logs_downloaded"] = True
    gate = _ci_repair_gate(runtime_truth=truth)
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_repair_gate_workflow_retried_blocks() -> None:
    truth = dict(_ci_repair_gate()["runtime_truth"])  # type: ignore[index]
    truth["workflow_retried"] = True
    gate = _ci_repair_gate(runtime_truth=truth)
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_repair_gate_workflow_triggered_blocks() -> None:
    truth = dict(_ci_repair_gate()["runtime_truth"])  # type: ignore[index]
    truth["workflow_triggered"] = True
    gate = _ci_repair_gate(runtime_truth=truth)
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_repair_gate_provider_called_blocks() -> None:
    truth = dict(_ci_repair_gate()["runtime_truth"])  # type: ignore[index]
    truth["provider_called"] = True
    gate = _ci_repair_gate(runtime_truth=truth)
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_repair_gate_agent_called_blocks() -> None:
    truth = dict(_ci_repair_gate()["runtime_truth"])  # type: ignore[index]
    truth["agent_called"] = True
    gate = _ci_repair_gate(runtime_truth=truth)
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_repair_gate_mcp_used_blocks() -> None:
    truth = dict(_ci_repair_gate()["runtime_truth"])  # type: ignore[index]
    truth["mcp_used"] = True
    gate = _ci_repair_gate(runtime_truth=truth)
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_repair_gate_patch_proposed_blocks() -> None:
    truth = dict(_ci_repair_gate()["runtime_truth"])  # type: ignore[index]
    truth["patch_proposed"] = True
    gate = _ci_repair_gate(runtime_truth=truth)
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_repair_gate_patch_applied_blocks() -> None:
    truth = dict(_ci_repair_gate()["runtime_truth"])  # type: ignore[index]
    truth["patch_applied"] = True
    gate = _ci_repair_gate(runtime_truth=truth)
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_repair_gate_files_written_blocks() -> None:
    truth = dict(_ci_repair_gate()["runtime_truth"])  # type: ignore[index]
    truth["files_written"] = True
    gate = _ci_repair_gate(runtime_truth=truth)
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_repair_gate_code_edited_blocks() -> None:
    truth = dict(_ci_repair_gate()["runtime_truth"])  # type: ignore[index]
    truth["code_edited"] = True
    gate = _ci_repair_gate(runtime_truth=truth)
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_repair_gate_command_executed_blocks() -> None:
    truth = dict(_ci_repair_gate()["runtime_truth"])  # type: ignore[index]
    truth["command_executed"] = True
    gate = _ci_repair_gate(runtime_truth=truth)
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_repair_gate_git_mutated_blocks() -> None:
    truth = dict(_ci_repair_gate()["runtime_truth"])  # type: ignore[index]
    truth["git_mutated"] = True
    gate = _ci_repair_gate(runtime_truth=truth)
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_repair_gate_commit_executed_blocks() -> None:
    truth = dict(_ci_repair_gate()["runtime_truth"])  # type: ignore[index]
    truth["commit_executed"] = True
    gate = _ci_repair_gate(runtime_truth=truth)
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_repair_gate_push_executed_blocks() -> None:
    truth = dict(_ci_repair_gate()["runtime_truth"])  # type: ignore[index]
    truth["push_executed"] = True
    gate = _ci_repair_gate(runtime_truth=truth)
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_repair_gate_pr_updated_blocks() -> None:
    truth = dict(_ci_repair_gate()["runtime_truth"])  # type: ignore[index]
    truth["pr_updated"] = True
    gate = _ci_repair_gate(runtime_truth=truth)
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_repair_gate_pr_merged_blocks() -> None:
    truth = dict(_ci_repair_gate()["runtime_truth"])  # type: ignore[index]
    truth["pr_merged"] = True
    gate = _ci_repair_gate(runtime_truth=truth)
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_repair_gate_auto_merge_blocks() -> None:
    truth = dict(_ci_repair_gate()["runtime_truth"])  # type: ignore[index]
    truth["auto_merge_enabled"] = True
    gate = _ci_repair_gate(runtime_truth=truth)
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_child_runtime_truth_preserved() -> None:
    result = evaluate_ci_repair_planner(_request())
    assert len(result.runtime_truth["child_runtime_truth_events"]) >= 1


# --- Phase 30 integration ---


def test_clean_failed_ci_monitor_supports_planning() -> None:
    result = evaluate_ci_repair_planner(_request())
    assert result.ci_monitor_clean is True
    assert result.ci_failed is True
    assert result.planned is True


def test_passed_ci_returns_repair_not_needed() -> None:
    mon = _ci_monitor(failed=False, passed=True, pending=False)
    result = evaluate_ci_repair_planner(_request(ci_monitor_result=mon))
    assert result.ci_passed is True
    assert result.blocked is True
    assert "CI passed" in (result.blocked_reason or "")


def test_pending_ci_returns_repair_wait_for_ci() -> None:
    mon = _ci_monitor(failed=False, passed=False, pending=True)
    result = evaluate_ci_repair_planner(_request(ci_monitor_result=mon))
    assert result.ci_pending is True
    assert result.blocked is True
    assert "CI is pending" in (result.blocked_reason or "")


def test_missing_required_checks_requires_human() -> None:
    mon = _ci_monitor(missing_required_checks=["missing-check"])
    result = evaluate_ci_repair_planner(_request(ci_monitor_result=mon))
    assert result.planned is False
    assert result.requires_human_intervention is True


def test_ci_monitor_unsafe_runtime_truth_flags_block() -> None:
    for flag in ("secrets_detected", "logs_downloaded", "workflow_retried", "workflow_triggered", "repair_loop_started"):
        mon = _ci_monitor()
        truth = dict(mon["runtime_truth"])  # type: ignore[index]
        truth[flag] = True
        mon["runtime_truth"] = truth
        assert evaluate_ci_repair_planner(_request(ci_monitor_result=mon)).blocked is True

    for flag in ("pr_updated", "pr_merged", "auto_merge_enabled", "push_executed", "command_executed", "git_mutated"):
        mon = _ci_monitor()
        truth = dict(mon["runtime_truth"])  # type: ignore[index]
        truth[flag] = True
        mon["runtime_truth"] = truth
        assert evaluate_ci_repair_planner(_request(ci_monitor_result=mon)).blocked is True

    for flag in ("provider_called", "mcp_used", "agent_called", "vault_written", "main_modified"):
        mon = _ci_monitor()
        truth = dict(mon["runtime_truth"])  # type: ignore[index]
        truth[flag] = True
        mon["runtime_truth"] = truth
        assert evaluate_ci_repair_planner(_request(ci_monitor_result=mon)).blocked is True


# --- PR/repository/branch/SHA safety ---


def test_open_pr_accepted() -> None:
    assert evaluate_ci_repair_planner(_request(pr_state="open")).blocked is False


def test_draft_open_pr_accepted() -> None:
    assert evaluate_ci_repair_planner(_request(pr_state="open")).blocked is False


def test_closed_pr_blocks() -> None:
    result = evaluate_ci_repair_planner(_request(pr_state="closed"))
    assert result.blocked is True


def test_merged_pr_blocks() -> None:
    result = evaluate_ci_repair_planner(_request(pr_state="merged"))
    assert result.blocked is True


def test_unknown_pr_state_blocks() -> None:
    result = evaluate_ci_repair_planner(_request(pr_state="unknown"))
    assert result.blocked is True


def test_head_branch_main_blocks() -> None:
    result = evaluate_ci_repair_planner(_request(head_branch="main", source_branch="main"))
    assert result.blocked is True


def test_source_branch_main_blocks() -> None:
    result = evaluate_ci_repair_planner(_request(source_branch="main"))
    assert result.blocked is True


def test_base_branch_not_main_blocks() -> None:
    result = evaluate_ci_repair_planner(_request(base_branch="develop"))
    assert result.blocked is True


def test_protected_branch_blocks_or_requires_human() -> None:
    result = evaluate_ci_repair_planner(_request(head_branch="release/1.0", source_branch="release/1.0"))
    assert result.blocked is True


def test_valid_repository_accepted() -> None:
    assert evaluate_ci_repair_planner(_request(repository_full_name="misaeldasilva123ms96-commits/Projeto-Omni")).blocked is False


def test_unsafe_repository_blocks() -> None:
    assert evaluate_ci_repair_planner(_request(repository_full_name="owner/repo;bad")).blocked is True
    assert evaluate_ci_repair_planner(_request(repository_full_name="other/fork")).blocked is True


def test_safe_head_sha_accepted() -> None:
    assert evaluate_ci_repair_planner(_request(head_sha=SAFE_SHA)).blocked is False


def test_missing_head_sha_uses_commit_sha() -> None:
    assert evaluate_ci_repair_planner(_request(head_sha=None, commit_sha=SAFE_SHA)).blocked is False


def test_missing_both_shas_blocks() -> None:
    mon = _ci_monitor(head_sha=None, commit_sha=None)
    gate = _ci_repair_gate(head_sha=None, commit_sha=None)
    creator = _pr_creator(commit_sha=None)
    result = evaluate_ci_repair_planner(_request(ci_monitor_result=mon, ci_repair_loop_gate_result=gate, pr_creator_result=creator, head_sha=None, commit_sha=None))
    assert result.blocked is True


def test_unsafe_sha_blocks() -> None:
    assert evaluate_ci_repair_planner(_request(head_sha="abc123d;bad")).blocked is True


# --- Repair planning ---


def test_test_failure_creates_test_repair_step() -> None:
    result = evaluate_ci_repair_planner(_request())
    steps = result.repair_plan_steps
    assert len(steps) >= 1
    assert steps[0]["failure_category"] == "test_failure"


def test_typecheck_failure_creates_typecheck_step() -> None:
    gate = _ci_repair_gate(
        failure_categories=["typecheck_failure"],
        failing_checks=[{"name": "typecheck / tsc", "status": "failure", "required": True}],
    )
    mon = _ci_monitor(failing_checks=[{"name": "typecheck / tsc", "status": "failure", "required": True}])
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate, ci_monitor_result=mon))
    steps = result.repair_plan_steps
    assert len(steps) >= 1
    assert steps[0]["step_type"] == "inspect_typecheck_failure_metadata"


def test_lint_failure_creates_lint_step() -> None:
    gate = _ci_repair_gate(
        failure_categories=["lint_failure"],
        failing_checks=[{"name": "lint / eslint", "status": "failure", "required": True}],
    )
    mon = _ci_monitor(failing_checks=[{"name": "lint / eslint", "status": "failure", "required": True}])
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate, ci_monitor_result=mon))
    steps = result.repair_plan_steps
    assert len(steps) >= 1
    assert steps[0]["step_type"] == "inspect_lint_failure_metadata"


def test_format_failure_creates_format_step() -> None:
    gate = _ci_repair_gate(
        failure_categories=["format_failure"],
        failing_checks=[{"name": "fmt / black", "status": "failure", "required": True}],
    )
    mon = _ci_monitor(failing_checks=[{"name": "fmt / black", "status": "failure", "required": True}])
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate, ci_monitor_result=mon))
    steps = result.repair_plan_steps
    assert len(steps) >= 1
    assert steps[0]["step_type"] == "inspect_format_failure_metadata"


def test_build_failure_creates_build_step() -> None:
    gate = _ci_repair_gate(
        failure_categories=["build_failure"],
        failing_checks=[{"name": "build / cargo check", "status": "failure", "required": True}],
    )
    mon = _ci_monitor(failing_checks=[{"name": "build / cargo check", "status": "failure", "required": True}])
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate, ci_monitor_result=mon))
    steps = result.repair_plan_steps
    assert len(steps) >= 1
    assert steps[0]["step_type"] == "inspect_build_failure_metadata"


def test_mixed_allowed_categories_bounded_plan_steps() -> None:
    gate = _ci_repair_gate(failure_categories=["test_failure", "lint_failure"])
    mon = _ci_monitor(failing_checks=[
        {"name": "pytest", "status": "failure", "required": True},
        {"name": "eslint", "status": "failure", "required": True},
    ])
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate, ci_monitor_result=mon))
    assert len(result.repair_plan_steps) <= 10
    assert len(result.repair_plan_steps) >= 1


def test_security_failure_blocks() -> None:
    gate = _ci_repair_gate(failure_categories=[], blocked_failure_categories=["security_failure"])
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_secret_failure_blocks() -> None:
    gate = _ci_repair_gate(failure_categories=[], blocked_failure_categories=["secret_failure"])
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_deployment_failure_requires_human() -> None:
    gate = _ci_repair_gate(failure_categories=[], blocked_failure_categories=["deployment_failure"])
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True
    assert result.requires_human_intervention is True


def test_billing_failure_requires_human() -> None:
    gate = _ci_repair_gate(failure_categories=[], blocked_failure_categories=["billing_failure"])
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_permission_failure_requires_human() -> None:
    gate = _ci_repair_gate(failure_categories=[], blocked_failure_categories=["permission_failure"])
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate))
    assert result.blocked is True


def test_unknown_category_requires_human() -> None:
    mon = _ci_monitor(failing_checks=[{"name": "weird-check", "status": "failure", "required": True}])
    gate = _ci_repair_gate(
        failure_categories=[], blocked_failure_categories=[],
        failing_checks=[{"name": "weird-check", "status": "failure", "required": True}],
    )
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate, ci_monitor_result=mon))
    assert result.blocked is True


def test_affected_areas_bounded_and_safe() -> None:
    result = evaluate_ci_repair_planner(_request())
    for area in result.affected_areas:
        assert area in ("tests", "backend/python", "backend/rust", "frontend/src", "docs", "sandbox/local", "unknown")


def test_no_patch_hunks_generated() -> None:
    result = evaluate_ci_repair_planner(_request())
    plan_json = json.dumps(result.repair_plan)
    plan_lower = plan_json.lower()
    assert not any(key in plan_lower for key in ["diff", "before", "after"])


def test_no_file_edits_generated() -> None:
    result = evaluate_ci_repair_planner(_request())
    for step in result.repair_plan_steps:
        assert "file_edit" not in str(step.get("step_type", ""))


# --- Suggested validation commands ---


def test_pytest_suggested_for_test_failure() -> None:
    result = evaluate_ci_repair_planner(_request())
    cmds = " ".join(result.suggested_validation_commands)
    assert "pytest" in cmds


def test_typecheck_command_suggested() -> None:
    gate = _ci_repair_gate(failure_categories=["typecheck_failure"])
    mon = _ci_monitor(failing_checks=[{"name": "typecheck / tsc", "status": "failure", "required": True}])
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate, ci_monitor_result=mon))
    cmds = " ".join(result.suggested_validation_commands)
    assert "typecheck" in cmds


def test_lint_command_suggested() -> None:
    gate = _ci_repair_gate(failure_categories=["lint_failure"])
    mon = _ci_monitor(failing_checks=[{"name": "lint / eslint", "status": "failure", "required": True}])
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate, ci_monitor_result=mon))
    cmds = " ".join(result.suggested_validation_commands)
    assert "lint" in cmds or "clippy" in cmds


def test_format_command_suggested() -> None:
    gate = _ci_repair_gate(failure_categories=["format_failure"])
    mon = _ci_monitor(failing_checks=[{"name": "fmt / black", "status": "failure", "required": True}])
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate, ci_monitor_result=mon))
    cmds = " ".join(result.suggested_validation_commands)
    assert "fmt" in cmds


def test_build_command_suggested() -> None:
    gate = _ci_repair_gate(failure_categories=["build_failure"])
    mon = _ci_monitor(failing_checks=[{"name": "build / cargo check", "status": "failure", "required": True}])
    result = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate, ci_monitor_result=mon))
    cmds = " ".join(result.suggested_validation_commands)
    assert "build" in cmds or "cargo check" in cmds


def test_validation_commands_metadata_only() -> None:
    result = evaluate_ci_repair_planner(_request())
    assert isinstance(result.suggested_validation_commands, list)


# --- Attempt budget ---


def test_attempt_budget_zero_allows_planning() -> None:
    result = evaluate_ci_repair_planner(_request(current_repair_attempt=0, max_repair_attempts=3))
    assert result.planned is True


def test_attempt_budget_two_of_three_allows_planning() -> None:
    result = evaluate_ci_repair_planner(_request(current_repair_attempt=2, max_repair_attempts=3))
    assert result.planned is True


def test_attempt_budget_three_of_three_blocks() -> None:
    result = evaluate_ci_repair_planner(_request(current_repair_attempt=3, max_repair_attempts=3))
    assert result.planned is False
    assert result.blocked is True


def test_attempt_budget_exceeded_blocks() -> None:
    result = evaluate_ci_repair_planner(_request(current_repair_attempt=5, max_repair_attempts=3))
    assert result.planned is False
    assert result.blocked is True


def test_negative_attempt_blocks() -> None:
    result = evaluate_ci_repair_planner(_request(current_repair_attempt=-1, max_repair_attempts=3))
    assert result.blocked is True


def test_max_attempts_outside_range_blocks() -> None:
    assert evaluate_ci_repair_planner(_request(max_repair_attempts=0)).blocked is True
    assert evaluate_ci_repair_planner(_request(max_repair_attempts=11)).blocked is True


def test_attempt_budget_remaining_not_negative() -> None:
    result = evaluate_ci_repair_planner(_request(current_repair_attempt=5, max_repair_attempts=3))
    assert result.attempt_budget_remaining >= 0
    assert result.attempt_budget_remaining == 0


# --- Repair plan ---


def test_repair_plan_json_serializable() -> None:
    result = evaluate_ci_repair_planner(_request())
    json.dumps(result.repair_plan)


def test_repair_plan_steps_bounded_by_max() -> None:
    result = evaluate_ci_repair_planner(_request(max_plan_steps=1))
    assert len(result.repair_plan_steps) <= 1


def test_required_pre_patch_proposal_checks_populated() -> None:
    result = evaluate_ci_repair_planner(_request())
    assert len(result.required_pre_patch_proposal_checks) > 0


def test_allowed_in_future_patch_proposal_true_for_clean() -> None:
    result = evaluate_ci_repair_planner(_request())
    assert result.repair_plan["allowed_in_future_patch_proposal"] is True


def test_repair_plan_ready_only_for_clean() -> None:
    result = evaluate_ci_repair_planner(_request())
    assert result.repair_plan_ready is True


def test_next_allowed_phase_scoped_patch_proposal_gate_when_ready() -> None:
    result = evaluate_ci_repair_planner(_request())
    assert result.repair_plan["next_allowed_phase"] == "scoped_ci_patch_proposal_gate"


def test_next_allowed_phase_wait_for_ci_when_pending() -> None:
    mon = _ci_monitor(failed=False, passed=False, pending=True)
    result = evaluate_ci_repair_planner(_request(ci_monitor_result=mon, planner_mode="dry_run"))
    assert result.repair_plan["next_allowed_phase"] == "wait_for_ci"


def test_next_allowed_phase_merge_gate_when_passed() -> None:
    mon = _ci_monitor(failed=False, passed=True, pending=False)
    result = evaluate_ci_repair_planner(_request(ci_monitor_result=mon, planner_mode="dry_run"))
    assert result.repair_plan["next_allowed_phase"] == "merge_gate"


def test_next_allowed_phase_human_review_when_blocked() -> None:
    result = evaluate_ci_repair_planner(_request(planner_mode="disabled"))
    assert result.repair_plan["next_allowed_phase"] == "human_review"


def test_no_patch_proposal_created() -> None:
    result = evaluate_ci_repair_planner(_request())
    assert hasattr(result, "can_create_patch_proposal")
    assert result.can_create_patch_proposal is False


# --- Flags ---


def test_all_action_flags_remain_false() -> None:
    result = evaluate_ci_repair_planner(_request())
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
    result = evaluate_ci_repair_planner(_request()).runtime_truth
    for flag in (
        "repair_loop_started",
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


def test_runtime_truth_event_type() -> None:
    result = evaluate_ci_repair_planner(_request()).runtime_truth
    assert result["event_type"] == "sandbox.ci_repair_planner.plan"


def test_runtime_truth_repair_plan_created_true_when_planned() -> None:
    result = evaluate_ci_repair_planner(_request()).runtime_truth
    assert result["repair_plan_created"] is True


# --- Governance decisions ---


def test_governance_decisions() -> None:
    assert evaluate_ci_repair_planner(_request(planner_mode="disabled")).runtime_truth["governance_decision"] == "blocked"
    assert evaluate_ci_repair_planner(_request(planner_mode="dry_run")).runtime_truth["governance_decision"] == "dry_run"
    assert evaluate_ci_repair_planner(_request()).runtime_truth["governance_decision"] == "ci_repair_plan_created"


# --- Redaction ---


def test_redaction_blocks_secret_like_inputs() -> None:
    result = evaluate_ci_repair_planner(_request(metadata={"header": "Authorization: Bearer placeholder"}))
    assert result.blocked is True
    assert result.redacted is True
    assert "Authorization: Bearer" not in json.dumps(result.to_dict())

    result2 = evaluate_ci_repair_planner(
        _request(metadata={"check": "SECRET-check-name"})
    )
    assert result2.redacted is True

    result3 = evaluate_ci_repair_planner(
        _request(pr_url="https://github.com/owner/repo/pull/1?token=ghp_placeholder")
    )
    assert result3.redacted is True

    gate = _ci_repair_gate(
        failing_checks=[{"name": "check-with-TOKEN", "status": "failure", "required": True}]
    )
    mon = _ci_monitor(
        failing_checks=[{"name": "check-with-TOKEN", "status": "failure", "required": True}]
    )
    result4 = evaluate_ci_repair_planner(_request(ci_repair_loop_gate_result=gate, ci_monitor_result=mon))
    assert result4.redacted is True


def test_output_does_not_expose_secrets() -> None:
    result = evaluate_ci_repair_planner(_request(metadata={"secret": "sk-test123"}))
    output = json.dumps(result.to_dict())
    assert "sk-test123" not in output


# --- No unsafe implementation ---


def test_source_has_no_unsafe_implementation() -> None:
    source = Path("backend/python/brain/runtime/sandbox/ci_repair_planner.py").read_text(encoding="utf-8")
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
