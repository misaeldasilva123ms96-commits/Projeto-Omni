"""Tests for the scoped CI patch proposal gate."""

from __future__ import annotations

import json
from pathlib import Path

from brain.runtime.sandbox.scoped_ci_patch_proposal_gate import (
    evaluate_scoped_ci_patch_proposal_gate,
)

SAFE_SHA = "abc123def4567890abc123def4567890abc123de"


def _repair_planner(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "planned": True,
        "blocked": False,
        "dry_run": False,
        "success": True,
        "repair_plan_ready": True,
        "failure_categories": ["test_failure"],
        "blocked_failure_categories": [],
        "attempt_budget_remaining": 3,
        "repository_full_name": "misaeldasilva123ms96-commits/Projeto-Omni",
        "pr_number": 362,
        "pr_url": "https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/pull/362",
        "pr_state": "open",
        "source_branch": "sandbox/scoped-ci-patch-proposal-gate",
        "head_branch": "sandbox/scoped-ci-patch-proposal-gate",
        "base_branch": "main",
        "head_sha": SAFE_SHA,
        "commit_sha": SAFE_SHA,
        "aggregate_status": "failure",
        "aggregate_conclusion": "failed",
        "repair_plan": {"plan_id": "ci-repair-plan-pr-362-1"},
        "repair_plan_steps": [
            {
                "step_id": "phase32-step-1",
                "step_type": "propose_scoped_test_fix",
                "failure_category": "test_failure",
                "source_check_name": "pytest / test-suite",
                "target_area": "tests",
                "action_intent": "Fix test",
                "risk_level": "medium",
                "requires_human": False,
                "allowed_for_future_patch_proposal": True,
                "suggested_validation_commands": ["python -m pytest"],
            }
        ],
        "affected_areas": ["tests"],
        "suggested_validation_commands": ["python -m pytest"],
        "required_pre_patch_proposal_checks": ["ci_monitor_succeeded"],
        "max_files_to_change": 5,
        "max_hunks_total": 20,
        "runtime_truth": {
            "event_type": "sandbox.ci_repair_planner.plan",
            "secrets_detected": False,
            "patch_proposed": False,
            "patch_applied": False,
            "files_written": False,
            "code_edited": False,
            "repair_loop_started": False,
            "logs_downloaded": False,
            "workflow_retried": False,
            "workflow_triggered": False,
            "provider_called": False,
            "agent_called": False,
            "mcp_used": False,
            "command_executed": False,
            "git_mutated": False,
            "commit_executed": False,
            "push_executed": False,
            "pr_updated": False,
            "pr_merged": False,
            "auto_merge_enabled": False,
            "main_modified": False,
            "vault_written": False,
        },
    }
    payload.update(overrides)
    return payload


def _repair_gate(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "repair_loop_eligible": True,
        "repair_loop_ready_metadata_only": True,
        "success": True,
        "blocked": False,
        "requires_human_intervention": False,
        "failure_categories": ["test_failure"],
        "blocked_failure_categories": [],
        "attempt_budget_remaining": 3,
        "repository_full_name": "misaeldasilva123ms96-commits/Projeto-Omni",
        "pr_number": 362,
        "pr_state": "open",
        "head_branch": "sandbox/scoped-ci-patch-proposal-gate",
        "base_branch": "main",
        "head_sha": SAFE_SHA,
        "runtime_truth": {
            "event_type": "sandbox.ci_repair_loop_gate.decision",
            "secrets_detected": False,
            "repair_loop_started": False,
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
            "main_modified": False,
            "vault_written": False,
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
        "pr_number": 362,
        "pr_state": "open",
        "head_branch": "sandbox/scoped-ci-patch-proposal-gate",
        "base_branch": "main",
        "head_sha": SAFE_SHA,
        "aggregate_status": "failure",
        "aggregate_conclusion": "failed",
        "failing_checks": [
            {"name": "pytest / test-suite", "status": "failure", "required": True}
        ],
        "pending_checks": [],
        "missing_required_checks": [],
        "unknown_checks": [],
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
            "mcp_used": False,
            "agent_called": False,
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
        "source_branch": "sandbox/scoped-ci-patch-proposal-gate",
        "head_branch": "sandbox/scoped-ci-patch-proposal-gate",
        "base_branch": "main",
        "commit_sha": SAFE_SHA,
        "pr_number": 362,
        "pr_url": "https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/pull/362",
        "pr_state": "open",
        "runtime_truth": {
            "event_type": "sandbox.pr_creator.create",
            "secrets_detected": False,
            "pr_merged": False,
            "auto_merge_enabled": False,
            "push_executed": False,
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
        "ci_repair_planner_result": _repair_planner(),
        "ci_repair_loop_gate_result": _repair_gate(),
        "ci_monitor_result": _ci_monitor(),
        "ci_monitor_gate_result": _ci_gate(),
        "pr_creator_result": _pr_creator(),
        "patch_proposal_gate_mode": "evaluate_patch_proposal",
    }
    payload.update(overrides)
    return payload


# --- Modes ---


def test_disabled_mode_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(patch_proposal_gate_mode="disabled")
    )
    assert result.blocked is True
    assert result.patch_proposal_eligible is False
    assert result.patch_proposal_ready_metadata_only is False


def test_blocked_mode_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(patch_proposal_gate_mode="blocked")
    )
    assert result.blocked is True
    assert result.patch_proposal_eligible is False


def test_dry_run_validates_but_not_eligible() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(patch_proposal_gate_mode="dry_run")
    )
    assert result.dry_run is True
    assert result.blocked is False
    assert result.patch_proposal_eligible is False
    assert result.patch_proposal_ready_metadata_only is False
    assert result.evaluated is True


def test_evaluate_patch_proposal_eligible_happy() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.patch_proposal_eligible is True
    assert result.patch_proposal_ready_metadata_only is True
    assert result.evaluated is True
    assert result.success is True
    assert result.blocked is False
    assert result.dry_run is False


def test_unknown_mode_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(patch_proposal_gate_mode="unknown")
    )
    assert result.blocked is True
    assert result.patch_proposal_eligible is False


# --- Phase 32 integration ---


def test_clean_repair_planner_allows_eligibility() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.repair_planner_clean is True
    assert result.repair_plan_ready is True
    assert result.patch_proposal_eligible is True


def test_missing_repair_planner_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=None)
    )
    assert result.blocked is True
    assert result.repair_planner_clean is False
    assert result.repair_plan_ready is False


def test_repair_plan_ready_false_blocks() -> None:
    planner = _repair_planner(repair_plan_ready=False)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True
    assert result.repair_plan_ready is False


def test_planned_false_blocks() -> None:
    planner = _repair_planner(planned=False)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True
    assert result.repair_planner_clean is False


def test_success_false_blocks() -> None:
    planner = _repair_planner(success=False)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True
    assert result.repair_planner_clean is False


def test_blocked_repair_planner_blocks() -> None:
    planner = _repair_planner(blocked=True)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True
    assert result.repair_planner_clean is False


def test_repair_planner_human_blocks() -> None:
    planner = _repair_planner(requires_human_intervention=True)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True
    assert result.repair_planner_clean is False


def test_repair_planner_blocked_categories_blocks() -> None:
    planner = _repair_planner(blocked_failure_categories=["security_failure"])
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True
    assert result.repair_planner_clean is False


def test_repair_planner_no_attempt_budget_blocks() -> None:
    planner = _repair_planner(attempt_budget_remaining=0)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True
    assert result.repair_planner_clean is False


def test_repair_planner_negative_attempt_budget_blocks() -> None:
    planner = _repair_planner(attempt_budget_remaining=-1)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_repair_planner_secrets_detected_blocks() -> None:
    truth = dict(_repair_planner()["runtime_truth"])  # type: ignore[index]
    truth["secrets_detected"] = True
    planner = _repair_planner(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_repair_planner_patch_proposed_blocks() -> None:
    truth = dict(_repair_planner()["runtime_truth"])  # type: ignore[index]
    truth["patch_proposed"] = True
    planner = _repair_planner(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_repair_planner_patch_applied_blocks() -> None:
    truth = dict(_repair_planner()["runtime_truth"])  # type: ignore[index]
    truth["patch_applied"] = True
    planner = _repair_planner(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_repair_planner_files_written_blocks() -> None:
    truth = dict(_repair_planner()["runtime_truth"])  # type: ignore[index]
    truth["files_written"] = True
    planner = _repair_planner(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_repair_planner_code_edited_blocks() -> None:
    truth = dict(_repair_planner()["runtime_truth"])  # type: ignore[index]
    truth["code_edited"] = True
    planner = _repair_planner(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_repair_planner_repair_loop_started_blocks() -> None:
    truth = dict(_repair_planner()["runtime_truth"])  # type: ignore[index]
    truth["repair_loop_started"] = True
    planner = _repair_planner(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_repair_planner_logs_downloaded_blocks() -> None:
    truth = dict(_repair_planner()["runtime_truth"])  # type: ignore[index]
    truth["logs_downloaded"] = True
    planner = _repair_planner(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_repair_planner_workflow_retried_blocks() -> None:
    truth = dict(_repair_planner()["runtime_truth"])  # type: ignore[index]
    truth["workflow_retried"] = True
    planner = _repair_planner(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_repair_planner_workflow_triggered_blocks() -> None:
    truth = dict(_repair_planner()["runtime_truth"])  # type: ignore[index]
    truth["workflow_triggered"] = True
    planner = _repair_planner(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_repair_planner_provider_called_blocks() -> None:
    truth = dict(_repair_planner()["runtime_truth"])  # type: ignore[index]
    truth["provider_called"] = True
    planner = _repair_planner(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_repair_planner_agent_called_blocks() -> None:
    truth = dict(_repair_planner()["runtime_truth"])  # type: ignore[index]
    truth["agent_called"] = True
    planner = _repair_planner(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_repair_planner_mcp_used_blocks() -> None:
    truth = dict(_repair_planner()["runtime_truth"])  # type: ignore[index]
    truth["mcp_used"] = True
    planner = _repair_planner(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_repair_planner_command_executed_blocks() -> None:
    truth = dict(_repair_planner()["runtime_truth"])  # type: ignore[index]
    truth["command_executed"] = True
    planner = _repair_planner(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_repair_planner_git_mutated_blocks() -> None:
    truth = dict(_repair_planner()["runtime_truth"])  # type: ignore[index]
    truth["git_mutated"] = True
    planner = _repair_planner(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_repair_planner_commit_executed_blocks() -> None:
    truth = dict(_repair_planner()["runtime_truth"])  # type: ignore[index]
    truth["commit_executed"] = True
    planner = _repair_planner(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_repair_planner_push_executed_blocks() -> None:
    truth = dict(_repair_planner()["runtime_truth"])  # type: ignore[index]
    truth["push_executed"] = True
    planner = _repair_planner(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_repair_planner_pr_updated_blocks() -> None:
    truth = dict(_repair_planner()["runtime_truth"])  # type: ignore[index]
    truth["pr_updated"] = True
    planner = _repair_planner(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_repair_planner_pr_merged_blocks() -> None:
    truth = dict(_repair_planner()["runtime_truth"])  # type: ignore[index]
    truth["pr_merged"] = True
    planner = _repair_planner(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_repair_planner_auto_merge_enabled_blocks() -> None:
    truth = dict(_repair_planner()["runtime_truth"])  # type: ignore[index]
    truth["auto_merge_enabled"] = True
    planner = _repair_planner(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_repair_planner_main_modified_blocks() -> None:
    truth = dict(_repair_planner()["runtime_truth"])  # type: ignore[index]
    truth["main_modified"] = True
    planner = _repair_planner(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_repair_planner_vault_written_blocks() -> None:
    truth = dict(_repair_planner()["runtime_truth"])  # type: ignore[index]
    truth["vault_written"] = True
    planner = _repair_planner(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_child_runtime_truth_events_preserved_from_repair_planner() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    events = result.runtime_truth["child_runtime_truth_events"]
    assert isinstance(events, list)
    assert len(events) >= 1
    planner_event = next(
        (e for e in events if e.get("event_type") == "sandbox.ci_repair_planner.plan"),
        None,
    )
    assert planner_event is not None


# --- Phase 31 integration ---


def test_clean_repair_gate_supports_eligibility() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.patch_proposal_eligible is True


def test_missing_repair_gate_does_not_block() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_loop_gate_result=None)
    )
    assert result.blocked is False
    assert result.patch_proposal_eligible is True


def test_repair_gate_ineligible_blocks() -> None:
    gate = _repair_gate(
        repair_loop_eligible=False, repair_loop_ready_metadata_only=False
    )
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_loop_gate_result=gate)
    )
    assert result.blocked is True


def test_repair_gate_blocked_blocks() -> None:
    gate = _repair_gate(blocked=True)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_loop_gate_result=gate)
    )
    assert result.blocked is True


def test_repair_gate_human_blocks() -> None:
    gate = _repair_gate(requires_human_intervention=True)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_loop_gate_result=gate)
    )
    assert result.blocked is True


def test_repair_gate_blocked_categories_blocks() -> None:
    gate = _repair_gate(blocked_failure_categories=["security_failure"])
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_loop_gate_result=gate)
    )
    assert result.blocked is True


def test_repair_gate_no_budget_blocks() -> None:
    gate = _repair_gate(attempt_budget_remaining=0)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_loop_gate_result=gate)
    )
    assert result.blocked is True


def test_repair_gate_secrets_detected_blocks() -> None:
    truth = dict(_repair_gate()["runtime_truth"])  # type: ignore[index]
    truth["secrets_detected"] = True
    gate = _repair_gate(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_loop_gate_result=gate)
    )
    assert result.blocked is True


def test_repair_gate_repair_loop_started_blocks() -> None:
    truth = dict(_repair_gate()["runtime_truth"])  # type: ignore[index]
    truth["repair_loop_started"] = True
    gate = _repair_gate(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_loop_gate_result=gate)
    )
    assert result.blocked is True


# --- PR / branch / repository / SHA safety ---


def test_open_pr_accepted() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.blocked is False
    assert result.patch_proposal_eligible is True


def test_draft_open_pr_accepted() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(pr_state="open")
    )
    assert result.blocked is False


def test_closed_pr_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request(pr_state="closed"))
    assert result.blocked is True


def test_merged_pr_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request(pr_state="merged"))
    assert result.blocked is True


def test_head_branch_main_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(head_branch="main")
    )
    assert result.blocked is True


def test_base_branch_not_main_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(base_branch="develop")
    )
    assert result.blocked is True


def test_valid_repository_accepted() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.blocked is False


def test_non_matching_repository_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(repository_full_name="other/fork")
    )
    assert result.blocked is True


def test_repository_with_shell_chars_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(repository_full_name="owner/repo;bad")
    )
    assert result.blocked is True


def test_safe_head_sha_accepted() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.blocked is False


def test_missing_head_sha_uses_commit_sha() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(head_sha=None, commit_sha=SAFE_SHA)
    )
    assert result.blocked is False


def test_missing_both_head_sha_and_commit_sha_blocks() -> None:
    planner = _repair_planner(head_sha=None, commit_sha=None)
    gate = _repair_gate(head_sha=None, commit_sha=None)
    mon = _ci_monitor(head_sha=None, commit_sha=None)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(
            ci_repair_planner_result=planner,
            ci_repair_loop_gate_result=gate,
            ci_monitor_result=mon,
            head_sha=None,
            commit_sha=None,
        )
    )
    assert result.blocked is True


def test_unsafe_sha_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(head_sha="abc123d;bad")
    )
    assert result.blocked is True


# --- Repair step validation ---


def test_propose_scoped_test_fix_supports_eligibility() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.patch_proposal_eligible is True
    steps = result.repair_plan_steps
    assert len(steps) >= 1
    assert steps[0]["step_type"] == "propose_scoped_test_fix"


def test_propose_scoped_typecheck_fix_supports_eligibility() -> None:
    steps = [
        {
            "step_id": "step-tc",
            "step_type": "propose_scoped_typecheck_fix",
            "failure_category": "typecheck_failure",
            "source_check_name": "typecheck / tsc",
            "target_area": "backend/python",
            "action_intent": "Fix typecheck",
            "risk_level": "medium",
            "requires_human": False,
            "allowed_for_future_patch_proposal": True,
            "suggested_validation_commands": ["npm run typecheck"],
        }
    ]
    planner = _repair_planner(
        failure_categories=["typecheck_failure"],
        repair_plan_steps=steps,
        affected_areas=["backend/python"],
        suggested_validation_commands=["npm run typecheck"],
    )
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.patch_proposal_eligible is True
    assert result.repair_plan_steps[0]["step_type"] == "propose_scoped_typecheck_fix"


def test_propose_scoped_lint_fix_supports_eligibility() -> None:
    steps = [
        {
            "step_id": "step-lint",
            "step_type": "propose_scoped_lint_fix",
            "failure_category": "lint_failure",
            "source_check_name": "lint / eslint",
            "target_area": "frontend/src",
            "action_intent": "Fix lint",
            "risk_level": "medium",
            "requires_human": False,
            "allowed_for_future_patch_proposal": True,
            "suggested_validation_commands": ["npm run lint"],
        }
    ]
    planner = _repair_planner(
        failure_categories=["lint_failure"],
        repair_plan_steps=steps,
        affected_areas=["frontend/src"],
        suggested_validation_commands=["npm run lint"],
    )
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.patch_proposal_eligible is True
    assert result.repair_plan_steps[0]["step_type"] == "propose_scoped_lint_fix"


def test_propose_scoped_format_fix_supports_eligibility() -> None:
    steps = [
        {
            "step_id": "step-fmt",
            "step_type": "propose_scoped_format_fix",
            "failure_category": "format_failure",
            "source_check_name": "fmt / black",
            "target_area": "backend/python",
            "action_intent": "Fix format",
            "risk_level": "low",
            "requires_human": False,
            "allowed_for_future_patch_proposal": True,
            "suggested_validation_commands": ["cargo fmt --check"],
        }
    ]
    planner = _repair_planner(
        failure_categories=["format_failure"],
        repair_plan_steps=steps,
        affected_areas=["backend/python"],
        suggested_validation_commands=["cargo fmt --check"],
    )
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.patch_proposal_eligible is True
    assert result.repair_plan_steps[0]["step_type"] == "propose_scoped_format_fix"


def test_propose_scoped_build_fix_supports_eligibility() -> None:
    steps = [
        {
            "step_id": "step-build",
            "step_type": "propose_scoped_build_fix",
            "failure_category": "build_failure",
            "source_check_name": "build / cargo check",
            "target_area": "backend/rust",
            "action_intent": "Fix build",
            "risk_level": "medium",
            "requires_human": False,
            "allowed_for_future_patch_proposal": True,
            "suggested_validation_commands": ["cargo check"],
        }
    ]
    planner = _repair_planner(
        failure_categories=["build_failure"],
        repair_plan_steps=steps,
        affected_areas=["backend/rust"],
        suggested_validation_commands=["cargo check"],
    )
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.patch_proposal_eligible is True
    assert result.repair_plan_steps[0]["step_type"] == "propose_scoped_build_fix"


def test_inspect_steps_as_metadata_context_only() -> None:
    steps = [
        {
            "step_id": "step-inspect",
            "step_type": "inspect_test_failure_metadata",
            "failure_category": "test_failure",
            "source_check_name": "pytest / test-suite",
            "target_area": "tests",
            "action_intent": "Inspect test failure",
            "risk_level": "low",
            "requires_human": False,
        }
    ]
    planner = _repair_planner(
        repair_plan_steps=steps,
    )
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.safe_repair_steps[0]["step_type"] == "inspect_test_failure_metadata"
    assert result.blocked is True
    assert "No propose-scoped-* repair steps found" in (result.blocked_reason or "")


def test_request_human_review_alone_blocks_eligibility() -> None:
    steps = [
        {
            "step_id": "step-human",
            "step_type": "request_human_review",
            "failure_category": "test_failure",
            "source_check_name": "pytest / test-suite",
            "target_area": "tests",
            "action_intent": "Human review needed",
            "risk_level": "medium",
            "requires_human": True,
        }
    ]
    planner = _repair_planner(
        repair_plan_steps=steps,
    )
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True
    assert "No propose-scoped-* repair steps found" in (result.blocked_reason or "")


def test_unknown_step_type_requires_human() -> None:
    steps = [
        {
            "step_id": "step-unknown",
            "step_type": "some_unknown_step",
            "failure_category": "test_failure",
            "source_check_name": "pytest / test-suite",
            "target_area": "tests",
            "action_intent": "Unknown action",
            "risk_level": "medium",
            "requires_human": False,
        },
        {
            "step_id": "phase32-step-1",
            "step_type": "propose_scoped_test_fix",
            "failure_category": "test_failure",
            "source_check_name": "pytest / test-suite",
            "target_area": "tests",
            "action_intent": "Fix test",
            "risk_level": "medium",
            "requires_human": False,
            "suggested_validation_commands": ["python -m pytest"],
        },
    ]
    planner = _repair_planner(repair_plan_steps=steps)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True
    assert "unknown step types" in (result.blocked_reason or "")


def test_high_risk_step_requires_human() -> None:
    steps = [
        {
            "step_id": "phase32-step-1",
            "step_type": "propose_scoped_test_fix",
            "failure_category": "test_failure",
            "source_check_name": "pytest / test-suite",
            "target_area": "tests",
            "action_intent": "Fix test",
            "risk_level": "high",
            "requires_human": True,
            "suggested_validation_commands": ["python -m pytest"],
        }
    ]
    planner = _repair_planner(repair_plan_steps=steps)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True
    assert "high-risk" in (result.blocked_reason or "")


def test_step_targeting_sensitive_area_blocks() -> None:
    steps = [
        {
            "step_id": "phase32-step-1",
            "step_type": "propose_scoped_test_fix",
            "failure_category": "test_failure",
            "source_check_name": "pytest / test-suite",
            "target_area": ".env",
            "action_intent": "Fix env",
            "risk_level": "medium",
            "requires_human": False,
            "suggested_validation_commands": ["python -m pytest"],
        }
    ]
    planner = _repair_planner(
        repair_plan_steps=steps,
        target_area=".env",
    )
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True
    assert "sensitive" in (result.blocked_reason or "")


# --- Candidate target areas ---


def test_tests_target_area_accepted() -> None:
    planner = _repair_planner(affected_areas=["tests"])
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert "tests" in result.candidate_target_areas
    assert len(result.blocked_target_areas) == 0
    assert result.patch_proposal_eligible is True


def test_backend_python_target_area_accepted() -> None:
    planner = _repair_planner(affected_areas=["backend/python"])
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert "backend/python" in result.candidate_target_areas
    assert result.patch_proposal_eligible is True


def test_backend_rust_target_area_accepted() -> None:
    planner = _repair_planner(affected_areas=["backend/rust"])
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert "backend/rust" in result.candidate_target_areas
    assert "backend/rust/src" in result.candidate_file_roots
    assert result.patch_proposal_eligible is True


def test_frontend_src_target_area_accepted() -> None:
    planner = _repair_planner(affected_areas=["frontend/src"])
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert "frontend/src" in result.candidate_target_areas
    assert result.patch_proposal_eligible is True


def test_docs_target_area_accepted() -> None:
    planner = _repair_planner(affected_areas=["docs"])
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert "docs" in result.candidate_target_areas
    assert result.patch_proposal_eligible is True


def test_sandbox_local_target_area_accepted() -> None:
    planner = _repair_planner(affected_areas=["sandbox/local"])
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert "sandbox/local" in result.candidate_target_areas
    assert result.patch_proposal_eligible is True


def test_github_workflows_target_area_blocked() -> None:
    planner = _repair_planner(affected_areas=[".github/workflows"])
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert ".github/workflows" in result.blocked_target_areas
    assert result.blocked is True


def test_docs_governance_target_area_blocked() -> None:
    planner = _repair_planner(affected_areas=["docs/governance"])
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert "docs/governance" in result.blocked_target_areas
    assert result.blocked is True


def test_env_target_area_blocked() -> None:
    planner = _repair_planner(affected_areas=[".env"])
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert ".env" in result.blocked_target_areas
    assert result.blocked is True


def test_unknown_target_area_requires_human() -> None:
    planner = _repair_planner(affected_areas=["some/random/path"])
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert "some/random/path" in result.blocked_target_areas
    assert result.blocked is True


# --- Suggested validation commands ---


def test_safe_pytest_command_accepted() -> None:
    planner = _repair_planner(
        suggested_validation_commands=["python -m pytest"]
    )
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert "python -m pytest" in result.suggested_validation_commands
    assert result.patch_proposal_eligible is True


def test_safe_cargo_test_accepted() -> None:
    planner = _repair_planner(
        failure_categories=["build_failure"],
        repair_plan_steps=[
            {
                "step_id": "step-build",
                "step_type": "propose_scoped_build_fix",
                "failure_category": "build_failure",
                "source_check_name": "build / cargo check",
                "target_area": "backend/rust",
                "action_intent": "Fix build",
                "risk_level": "medium",
                "requires_human": False,
                "suggested_validation_commands": ["cargo test"],
            }
        ],
        affected_areas=["backend/rust"],
        suggested_validation_commands=["cargo test"],
    )
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert "cargo test" in result.suggested_validation_commands


def test_safe_git_diff_check_accepted() -> None:
    planner = _repair_planner(
        suggested_validation_commands=["git diff --check"]
    )
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert "git diff --check" in result.suggested_validation_commands


def test_git_add_blocked() -> None:
    planner = _repair_planner(
        suggested_validation_commands=["git add ."]
    )
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert "git add ." in result.unsafe_repair_steps or "git add ." in str(
        result.blocked_reason
    )
    assert result.blocked is True


def test_git_commit_blocked() -> None:
    planner = _repair_planner(
        suggested_validation_commands=["git commit -m fix"]
    )
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_git_push_blocked() -> None:
    planner = _repair_planner(
        suggested_validation_commands=["git push origin main"]
    )
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_gh_blocked() -> None:
    planner = _repair_planner(
        suggested_validation_commands=["gh pr create"]
    )
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_curl_blocked() -> None:
    planner = _repair_planner(
        suggested_validation_commands=["curl http://example.com"]
    )
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


# --- Failure categories ---


def test_test_failure_allowed() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.patch_proposal_eligible is True
    assert "test_failure" in result.failure_categories


def test_typecheck_failure_allowed() -> None:
    planner = _repair_planner(failure_categories=["typecheck_failure"])
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert "typecheck_failure" in result.failure_categories


def test_lint_failure_allowed() -> None:
    planner = _repair_planner(failure_categories=["lint_failure"])
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert "lint_failure" in result.failure_categories


def test_format_failure_allowed() -> None:
    planner = _repair_planner(failure_categories=["format_failure"])
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert "format_failure" in result.failure_categories


def test_build_failure_allowed() -> None:
    planner = _repair_planner(failure_categories=["build_failure"])
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert "build_failure" in result.failure_categories


def test_security_failure_blocks() -> None:
    planner = _repair_planner(blocked_failure_categories=["security_failure"])
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True
    assert result.blocked_failure_categories == ["security_failure"]


def test_secret_failure_blocks() -> None:
    planner = _repair_planner(blocked_failure_categories=["secret_failure"])
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_mixed_allowed_and_blocked_categories_blocks() -> None:
    planner = _repair_planner(
        failure_categories=["test_failure", "security_failure"],
        blocked_failure_categories=["security_failure"],
    )
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


# --- Scope limits ---


def test_default_max_files_and_hunks_populated() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.max_patch_proposal_files == 5
    assert result.max_patch_proposal_hunks == 20
    assert result.max_hunks_per_file == 8


def test_malformed_max_patch_proposal_files_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(max_patch_proposal_files=0)
    )
    assert result.blocked is True


def test_malformed_max_patch_proposal_hunks_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(max_patch_proposal_hunks=0)
    )
    assert result.blocked is True


def test_malformed_max_hunks_per_file_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(max_hunks_per_file=0)
    )
    assert result.blocked is True


def test_planner_files_exceed_max_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(max_files_to_change=10, max_patch_proposal_files=5)
    )
    assert result.blocked is True


def test_planner_hunks_exceed_max_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(max_hunks_total=30, max_patch_proposal_hunks=20)
    )
    assert result.blocked is True


# --- Attempt budget ---


def test_current_repair_attempt_zero_allows_eligibility() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(current_repair_attempt=0, max_repair_attempts=3)
    )
    assert result.patch_proposal_eligible is True


def test_current_repair_attempt_three_of_three_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(current_repair_attempt=3, max_repair_attempts=3)
    )
    assert result.patch_proposal_eligible is False
    assert result.blocked is True
    assert result.attempt_budget_remaining == 0


def test_negative_attempt_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(current_repair_attempt=-1, max_repair_attempts=3)
    )
    assert result.blocked is True


def test_max_attempts_out_of_range_blocks() -> None:
    assert evaluate_scoped_ci_patch_proposal_gate(
        _request(max_repair_attempts=0)
    ).blocked is True
    assert evaluate_scoped_ci_patch_proposal_gate(
        _request(max_repair_attempts=11)
    ).blocked is True


# --- Scoped patch proposal plan ---


def test_scoped_patch_proposal_plan_json_serializable() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    json.dumps(result.scoped_patch_proposal_plan)


def test_required_pre_patch_proposal_checks_populated() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert len(result.required_pre_patch_proposal_checks) > 0
    assert "ci_monitor_succeeded" in result.required_pre_patch_proposal_checks


def test_next_allowed_phase_scoped_ci_patch_proposal_when_eligible() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert (
        result.scoped_patch_proposal_plan["next_allowed_phase"]
        == "scoped_ci_patch_proposal"
    )


def test_next_allowed_phase_merge_gate_when_passed() -> None:
    mon = _ci_monitor(failed=False, passed=True, pending=False)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_monitor_result=mon, patch_proposal_gate_mode="dry_run")
    )
    assert (
        result.scoped_patch_proposal_plan["next_allowed_phase"] == "merge_gate"
    )


def test_next_allowed_phase_human_review_when_blocked() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(patch_proposal_gate_mode="disabled")
    )
    assert (
        result.scoped_patch_proposal_plan["next_allowed_phase"] == "human_review"
    )


def test_next_allowed_phase_wait_for_ci_when_pending() -> None:
    mon = _ci_monitor(failed=False, passed=False, pending=True)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_monitor_result=mon, patch_proposal_gate_mode="dry_run")
    )
    assert (
        result.scoped_patch_proposal_plan["next_allowed_phase"] == "wait_for_ci"
    )


def test_scoped_patch_proposal_plan_allowed_in_future_true() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert (
        result.scoped_patch_proposal_plan[
            "allowed_in_future_scoped_patch_proposal"
        ]
        is True
    )


# --- Flags ---


def test_can_create_patch_proposal_false_always() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.can_create_patch_proposal is False


def test_can_generate_patch_hunks_false_always() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.can_generate_patch_hunks is False


def test_can_apply_patch_false_always() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.can_apply_patch is False


def test_can_write_files_false_always() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.can_write_files is False


def test_can_download_logs_false_always() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.can_download_logs is False


def test_can_retry_workflows_false_always() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.can_retry_workflows is False


def test_can_trigger_workflows_false_always() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.can_trigger_workflows is False


def test_can_call_provider_false_always() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.can_call_provider is False


def test_can_call_agent_false_always() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.can_call_agent is False


def test_can_commit_false_always() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.can_commit is False


def test_can_push_false_always() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.can_push is False


def test_can_update_pr_false_always() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.can_update_pr is False


def test_can_merge_false_always() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.can_merge is False


def test_can_auto_merge_false_always() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.can_auto_merge is False


def test_can_mutate_git_false_always() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.can_mutate_git is False


def test_can_execute_commands_false_always() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.can_execute_commands is False


def test_runtime_truth_event_type_correct() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request()).runtime_truth
    assert (
        result["event_type"]
        == "sandbox.scoped_ci_patch_proposal_gate.decision"
    )


def test_runtime_truth_all_action_flags_false() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request()).runtime_truth
    for flag in (
        "patch_proposal_created",
        "patch_hunks_generated",
        "patch_applied",
        "files_written",
        "code_edited",
        "logs_downloaded",
        "workflow_retried",
        "workflow_triggered",
        "repair_loop_started",
        "provider_called",
        "agent_called",
        "mcp_used",
        "command_executed",
        "git_mutated",
        "commit_executed",
        "push_executed",
        "pr_updated",
        "pr_merged",
        "auto_merge_enabled",
        "approval_submitted",
        "main_modified",
        "vault_written",
    ):
        assert result[flag] is False, f"{flag} should be False"


# --- Redaction ---


def test_check_name_with_secret_redacted_and_blocked() -> None:
    steps = [
        {
            "step_id": "step-1",
            "step_type": "propose_scoped_test_fix",
            "failure_category": "test_failure",
            "source_check_name": "check-with-SECRET",
            "target_area": "tests",
            "action_intent": "Fix test with SECRET",
            "risk_level": "medium",
            "requires_human": False,
            "suggested_validation_commands": ["python -m pytest"],
        }
    ]
    planner = _repair_planner(repair_plan_steps=steps)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.redacted is True
    assert result.blocked is True
    assert result.repair_plan_steps == []


def test_pr_url_with_ghp_placeholder_redacted_and_blocked() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(
            pr_url="https://github.com/owner/repo/pull/1?token=ghp_placeholder"
        )
    )
    assert result.redacted is True
    assert result.blocked is True
    output = json.dumps(result.to_dict())
    assert "ghp_placeholder" not in output


def test_failing_check_with_token_redacted() -> None:
    gate = _repair_gate(
        failing_checks=[{"name": "check-with-TOKEN", "status": "failure", "required": True}]
    )
    mon = _ci_monitor(
        failing_checks=[{"name": "check-with-TOKEN", "status": "failure", "required": True}]
    )
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_loop_gate_result=gate, ci_monitor_result=mon)
    )
    assert result.redacted is True
    assert result.blocked is True


def test_redaction_does_not_expose_secrets_in_output() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(metadata={"secret": "sk-test123"})
    )
    output = json.dumps(result.to_dict())
    assert "sk-test123" not in output


# --- Governance decisions ---


def test_governance_decision_blocked() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(patch_proposal_gate_mode="disabled")
    )
    assert result.runtime_truth["governance_decision"] == "blocked"


def test_governance_decision_dry_run() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(patch_proposal_gate_mode="dry_run")
    )
    assert result.runtime_truth["governance_decision"] == "dry_run"


def test_governance_decision_eligible() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert (
        result.runtime_truth["governance_decision"]
        == "scoped_ci_patch_proposal_eligible"
    )


def test_governance_decision_patch_proposal_not_needed_ci_passed() -> None:
    mon = _ci_monitor(failed=False, passed=True)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_monitor_result=mon, patch_proposal_gate_mode="evaluate_patch_proposal")
    )
    assert result.runtime_truth["governance_decision"] == "blocked"
    assert result.ci_passed is True


# --- Phase 30 CI monitor integration ---


def test_ci_failed_allows_eligibility() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.ci_failed is True
    assert result.patch_proposal_eligible is True


def test_ci_passed_blocks() -> None:
    mon = _ci_monitor(failed=False, passed=True, pending=False)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_monitor_result=mon)
    )
    assert result.ci_passed is True
    assert result.blocked is True


def test_ci_pending_blocks() -> None:
    mon = _ci_monitor(failed=False, passed=False, pending=True)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_monitor_result=mon)
    )
    assert result.ci_pending is True
    assert result.blocked is True


def test_ci_monitor_not_monitored_blocks() -> None:
    mon = _ci_monitor(monitored=False)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_monitor_result=mon)
    )
    assert result.blocked is True


def test_ci_monitor_not_successful_blocks() -> None:
    mon = _ci_monitor(success=False)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_monitor_result=mon)
    )
    assert result.blocked is True


def test_ci_monitor_blocked_blocks() -> None:
    mon = _ci_monitor(blocked=True)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_monitor_result=mon)
    )
    assert result.blocked is True


def test_ci_monitor_human_blocks() -> None:
    mon = _ci_monitor(requires_human_intervention=True)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_monitor_result=mon)
    )
    assert result.blocked is True


# --- Request-level allow flags ---


def test_allow_patch_proposal_eligibility_false_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(allow_patch_proposal_eligibility=False)
    )
    assert result.patch_proposal_eligible is False
    assert result.blocked is False


def test_allow_action_flags_any_true_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(allow_patch_proposal_creation=True)
    )
    assert result.blocked is True
    result2 = evaluate_scoped_ci_patch_proposal_gate(
        _request(allow_commit=True)
    )
    assert result2.blocked is True


# --- Edge cases ---


def test_empty_repair_planner_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result={})
    )
    assert result.blocked is True
    assert result.repair_planner_clean is False


def test_no_main_head_sha_fallback_preserved() -> None:
    plan = _repair_planner(head_sha=SAFE_SHA, commit_sha=SAFE_SHA)
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=plan)
    )
    assert result.head_sha == SAFE_SHA
    assert result.commit_sha == SAFE_SHA


def test_reason_eligible() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert (
        result.reason
        == "Scoped CI patch proposal gate marked patch proposal eligible."
    )


def test_reason_blocked() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(patch_proposal_gate_mode="blocked")
    )
    assert (
        result.reason
        == "Scoped CI patch proposal gate blocked this request."
    )


def test_reason_dry_run() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(patch_proposal_gate_mode="dry_run")
    )
    assert "dry-run" in result.reason


def test_requires_scoped_patch_proposal_phase_true_when_eligible() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.requires_scoped_patch_proposal_phase is True


def test_requires_patch_application_gate_phase_false() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.requires_patch_application_gate_phase is False


def test_patch_proposal_scope_matches_candidate_areas() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.patch_proposal_scope == result.candidate_target_areas


# --- CI inconclusive ---


def test_ci_inconclusive_with_no_status() -> None:
    mon = _ci_monitor(
        failed=False,
        passed=False,
        pending=False,
        aggregate_conclusion="inconclusive",
    )
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_monitor_result=mon)
    )
    assert result.ci_inconclusive is True
    assert result.blocked is True


# --- Unsafe commands detection via unsafe_repair_steps ---


def test_unsafe_validation_commands_in_unsafe_steps() -> None:
    planner = _repair_planner(
        suggested_validation_commands=["git push"]
    )
    result = evaluate_scoped_ci_patch_proposal_gate(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


# --- Evidence version ---


def test_evidence_version_present() -> None:
    result = evaluate_scoped_ci_patch_proposal_gate(_request())
    assert result.evidence_version == "1.0"
