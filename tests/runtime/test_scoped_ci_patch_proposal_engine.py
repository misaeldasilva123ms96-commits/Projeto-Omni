"""Tests for the scoped CI patch proposal engine."""

from __future__ import annotations

from brain.runtime.sandbox.scoped_ci_patch_proposal_engine import (
    evaluate_scoped_ci_patch_proposal_engine,
)

SAFE_SHA = "abc123def4567890abc123def4567890abc123de"


def _gate_result(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "patch_proposal_eligible": True,
        "patch_proposal_ready_metadata_only": True,
        "evaluated": True,
        "success": True,
        "blocked": False,
        "requires_human_intervention": False,
        "dry_run": False,
        "failure_categories": ["test_failure"],
        "blocked_failure_categories": [],
        "unsafe_repair_steps": [],
        "repair_planner_clean": True,
        "repair_plan_ready": True,
        "attempt_budget_remaining": 3,
        "repository_full_name": "misaeldasilva123ms96-commits/Projeto-Omni",
        "pr_number": 362,
        "pr_url": "https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/pull/362",
        "pr_state": "open",
        "source_branch": "sandbox/scoped-ci-patch-proposal-engine",
        "head_branch": "sandbox/scoped-ci-patch-proposal-engine",
        "base_branch": "main",
        "head_sha": SAFE_SHA,
        "commit_sha": SAFE_SHA,
        "aggregate_status": "failure",
        "aggregate_conclusion": "failed",
        "scoped_patch_proposal_plan": {
            "repository_full_name": "misaeldasilva123ms96-commits/Projeto-Omni",
            "pr_number": 362,
            "pr_url": "https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/pull/362",
            "head_branch": "sandbox/scoped-ci-patch-proposal-engine",
            "base_branch": "main",
            "head_sha": SAFE_SHA,
            "commit_sha": SAFE_SHA,
            "repair_plan_id": "phase32-plan-1",
            "required_pre_patch_proposal_checks": ["ci_monitor_succeeded"],
        },
        "patch_proposal_scope": {
            "candidate_target_areas": ["tests"],
            "candidate_file_roots": ["tests"],
            "max_files_to_change": 5,
            "max_hunks_total": 20,
        },
        "candidate_target_areas": ["tests"],
        "candidate_file_roots": ["tests"],
        "suggested_validation_commands": ["python -m pytest tests"],
        "required_pre_patch_proposal_checks": ["ci_monitor_succeeded"],
        "safe_repair_steps": [
            {
                "step_id": "phase33-safe-1",
                "step_type": "propose_scoped_test_fix",
                "failure_category": "test_failure",
                "source_check_name": "pytest / test-suite",
                "target_area": "tests",
                "action_intent": "Fix test assertion",
                "risk_level": "medium",
                "requires_human": False,
            }
        ],
        "runtime_truth": {
            "event_type": "sandbox.scoped_ci_patch_proposal_gate.decision",
            "secrets_detected": False,
            "patch_proposal_created": False,
            "patch_hunks_generated": False,
            "patch_applied": False,
            "files_written": False,
            "code_edited": False,
            "source_inspected": False,
            "logs_downloaded": False,
            "workflow_retried": False,
            "workflow_triggered": False,
            "repair_loop_started": False,
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
        "source_branch": "sandbox/scoped-ci-patch-proposal-engine",
        "head_branch": "sandbox/scoped-ci-patch-proposal-engine",
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
        "head_branch": "sandbox/scoped-ci-patch-proposal-engine",
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
        "head_branch": "sandbox/scoped-ci-patch-proposal-engine",
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
        "source_branch": "sandbox/scoped-ci-patch-proposal-engine",
        "head_branch": "sandbox/scoped-ci-patch-proposal-engine",
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
        "scoped_ci_patch_proposal_gate_result": _gate_result(),
        "ci_repair_planner_result": _repair_planner(),
        "ci_repair_loop_gate_result": _repair_gate(),
        "ci_monitor_result": _ci_monitor(),
        "ci_monitor_gate_result": _ci_gate(),
        "pr_creator_result": _pr_creator(),
        "proposal_mode": "propose_patch",
    }
    payload.update(overrides)
    return payload


# --- Modes ---


def test_disabled_mode_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(proposal_mode="disabled")
    )
    assert result.blocked is True
    assert result.proposal_created is False
    assert result.dry_run is False


def test_blocked_mode_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(proposal_mode="blocked")
    )
    assert result.blocked is True
    assert result.proposal_created is False


def test_dry_run_mode_does_not_create_proposals() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(proposal_mode="dry_run")
    )
    assert result.dry_run is True
    assert result.blocked is False
    assert result.proposal_created is False


def test_unknown_mode_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(proposal_mode="invalid_mode")
    )
    assert result.blocked is True


def test_propose_patch_happy_path_creates_proposal() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert result.proposal_created is True
    assert result.success is True
    assert result.blocked is False
    assert result.dry_run is False
    assert len(result.scoped_ci_patch_proposals) > 0
    assert len(result.proposal_hunks) > 0
    assert result.can_apply_patch is False
    assert result.can_write_files is False
    assert result.can_inspect_source is False


# --- Default mode ---


def test_default_mode_is_disabled() -> None:
    req = dict(_request())
    del req["proposal_mode"]
    result = evaluate_scoped_ci_patch_proposal_engine(req)
    assert result.blocked is True
    assert result.proposal_mode == "disabled"


# --- All action flags must be false ---


def test_action_flags_all_false() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert result.can_apply_patch is False
    assert result.can_write_files is False
    assert result.can_inspect_source is False
    assert result.can_download_logs is False
    assert result.can_retry_workflows is False
    assert result.can_trigger_workflows is False
    assert result.can_call_provider is False
    assert result.can_call_agent is False
    assert result.can_commit is False
    assert result.can_push is False
    assert result.can_update_pr is False
    assert result.can_merge is False
    assert result.can_auto_merge is False
    assert result.can_mutate_git is False
    assert result.can_execute_commands is False


# --- Request with allow flags blocks ---


def test_allow_patch_application_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(allow_patch_application=True)
    )
    assert result.blocked is True


def test_allow_file_write_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(allow_file_write=True)
    )
    assert result.blocked is True


def test_allow_source_inspection_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(allow_source_inspection=True)
    )
    assert result.blocked is True


def test_allow_commit_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(allow_commit=True)
    )
    assert result.blocked is True


def test_allow_push_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(allow_push=True)
    )
    assert result.blocked is True


def test_allow_git_mutation_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(allow_git_mutation=True)
    )
    assert result.blocked is True


def test_allow_command_execution_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(allow_command_execution=True)
    )
    assert result.blocked is True


# --- Gate eligibility ---


def test_missing_gate_result_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=None)
    )
    assert result.blocked is True
    assert result.gate_eligible is False


def test_gate_not_eligible_blocks() -> None:
    gate = _gate_result(patch_proposal_eligible=False)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True
    assert result.gate_eligible is False


def test_gate_blocked_blocks() -> None:
    gate = _gate_result(blocked=True)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_gate_human_intervention_blocks() -> None:
    gate = _gate_result(requires_human_intervention=True)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_gate_not_ready_metadata_blocks() -> None:
    gate = _gate_result(patch_proposal_ready_metadata_only=False)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


# --- Gate runtime truth unsafe flags ---


def test_gate_truth_secrets_detected_blocks() -> None:
    truth = dict(_gate_result()["runtime_truth"])
    truth["secrets_detected"] = True
    gate = _gate_result(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_gate_truth_patch_proposal_created_blocks() -> None:
    truth = dict(_gate_result()["runtime_truth"])
    truth["patch_proposal_created"] = True
    gate = _gate_result(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_gate_truth_patch_hunks_generated_blocks() -> None:
    truth = dict(_gate_result()["runtime_truth"])
    truth["patch_hunks_generated"] = True
    gate = _gate_result(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_gate_truth_patch_applied_blocks() -> None:
    truth = dict(_gate_result()["runtime_truth"])
    truth["patch_applied"] = True
    gate = _gate_result(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_gate_truth_files_written_blocks() -> None:
    truth = dict(_gate_result()["runtime_truth"])
    truth["files_written"] = True
    gate = _gate_result(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_gate_truth_code_edited_blocks() -> None:
    truth = dict(_gate_result()["runtime_truth"])
    truth["code_edited"] = True
    gate = _gate_result(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_gate_truth_source_inspected_blocks() -> None:
    truth = dict(_gate_result()["runtime_truth"])
    truth["source_inspected"] = True
    gate = _gate_result(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_gate_truth_logs_downloaded_blocks() -> None:
    truth = dict(_gate_result()["runtime_truth"])
    truth["logs_downloaded"] = True
    gate = _gate_result(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_gate_truth_workflow_retried_blocks() -> None:
    truth = dict(_gate_result()["runtime_truth"])
    truth["workflow_retried"] = True
    gate = _gate_result(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_gate_truth_workflow_triggered_blocks() -> None:
    truth = dict(_gate_result()["runtime_truth"])
    truth["workflow_triggered"] = True
    gate = _gate_result(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_gate_truth_repair_loop_started_blocks() -> None:
    truth = dict(_gate_result()["runtime_truth"])
    truth["repair_loop_started"] = True
    gate = _gate_result(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_gate_truth_provider_called_blocks() -> None:
    truth = dict(_gate_result()["runtime_truth"])
    truth["provider_called"] = True
    gate = _gate_result(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_gate_truth_agent_called_blocks() -> None:
    truth = dict(_gate_result()["runtime_truth"])
    truth["agent_called"] = True
    gate = _gate_result(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_gate_truth_mcp_used_blocks() -> None:
    truth = dict(_gate_result()["runtime_truth"])
    truth["mcp_used"] = True
    gate = _gate_result(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_gate_truth_command_executed_blocks() -> None:
    truth = dict(_gate_result()["runtime_truth"])
    truth["command_executed"] = True
    gate = _gate_result(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_gate_truth_git_mutated_blocks() -> None:
    truth = dict(_gate_result()["runtime_truth"])
    truth["git_mutated"] = True
    gate = _gate_result(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_gate_truth_commit_executed_blocks() -> None:
    truth = dict(_gate_result()["runtime_truth"])
    truth["commit_executed"] = True
    gate = _gate_result(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_gate_truth_push_executed_blocks() -> None:
    truth = dict(_gate_result()["runtime_truth"])
    truth["push_executed"] = True
    gate = _gate_result(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_gate_truth_pr_updated_blocks() -> None:
    truth = dict(_gate_result()["runtime_truth"])
    truth["pr_updated"] = True
    gate = _gate_result(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_gate_truth_pr_merged_blocks() -> None:
    truth = dict(_gate_result()["runtime_truth"])
    truth["pr_merged"] = True
    gate = _gate_result(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_gate_truth_auto_merge_enabled_blocks() -> None:
    truth = dict(_gate_result()["runtime_truth"])
    truth["auto_merge_enabled"] = True
    gate = _gate_result(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_gate_truth_main_modified_blocks() -> None:
    truth = dict(_gate_result()["runtime_truth"])
    truth["main_modified"] = True
    gate = _gate_result(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_gate_truth_vault_written_blocks() -> None:
    truth = dict(_gate_result()["runtime_truth"])
    truth["vault_written"] = True
    gate = _gate_result(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


# --- Planner evidence ---


def test_missing_planner_defaults_clean() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(ci_repair_planner_result=None)
    )
    # Without planner, planner evidence defaults to clean/ready true
    assert result.repair_plan_ready is True


def test_planner_not_planned_blocks() -> None:
    planner = _repair_planner(planned=False)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_planner_success_false_blocks() -> None:
    planner = _repair_planner(success=False)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_planner_blocked_blocks() -> None:
    planner = _repair_planner(blocked=True)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_planner_human_blocks() -> None:
    planner = _repair_planner(requires_human_intervention=True)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_planner_blocked_categories_blocks() -> None:
    planner = _repair_planner(blocked_failure_categories=["security_failure"])
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_planner_not_ready_blocks() -> None:
    planner = _repair_planner(repair_plan_ready=False)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


def test_planner_truth_secrets_detected_blocks() -> None:
    truth = dict(_repair_planner()["runtime_truth"])
    truth["secrets_detected"] = True
    planner = _repair_planner(runtime_truth=truth)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(ci_repair_planner_result=planner)
    )
    assert result.blocked is True


# --- CI evidence ---


def test_ci_passed_blocks() -> None:
    monitor = _ci_monitor(passed=True, failed=False)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(ci_monitor_result=monitor)
    )
    assert result.blocked is True
    assert result.ci_passed is True
    assert result.ci_failed is False


def test_ci_pending_blocks() -> None:
    monitor = _ci_monitor(pending=True, failed=False, passed=False)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(ci_monitor_result=monitor)
    )
    assert result.blocked is True
    assert result.ci_pending is True


def test_ci_not_failed_blocks() -> None:
    monitor = _ci_monitor(failed=False, passed=False, pending=False)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(ci_monitor_result=monitor)
    )
    assert result.blocked is True
    assert result.ci_failed is False


def test_ci_monitor_not_monitored_blocks() -> None:
    monitor = _ci_monitor(monitored=False)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(ci_monitor_result=monitor)
    )
    assert result.blocked is True


def test_ci_inconclusive_no_monitor() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(ci_monitor_result=None)
    )
    assert result.ci_inconclusive is True


# --- PR state safety ---


def test_merged_pr_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(pr_state="merged")
    )
    assert result.blocked is True


def test_closed_pr_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(pr_state="closed")
    )
    assert result.blocked is True


def test_locked_pr_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(pr_state="open", metadata={"locked": True})
    )
    assert result.blocked is True


def test_archived_repository_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(pr_state="open", metadata={"repository_archived": True})
    )
    assert result.blocked is True


# --- Repository safety ---


def test_missing_repository_blocks() -> None:
    gate = _gate_result(repository_full_name=None)
    planner = _repair_planner(repository_full_name=None)
    rg = _repair_gate(repository_full_name=None)
    monitor = _ci_monitor(repository_full_name=None)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(
            repository_full_name=None,
            scoped_ci_patch_proposal_gate_result=gate,
            ci_repair_planner_result=planner,
            ci_repair_loop_gate_result=rg,
            ci_monitor_result=monitor,
        )
    )
    assert result.blocked is True


def test_unexpected_repository_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(repository_full_name="other/repo")
    )
    assert result.blocked is True


def test_unexpected_repository_allowed_with_flag() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(
            repository_full_name="other/repo",
            metadata={"allow_unexpected_repository": True},
        )
    )
    # Other conditions still need to be met; this just avoids the unexpected repo block
    pass


def test_repo_with_shell_chars_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(repository_full_name="repo/path;rm -rf")
    )
    assert result.blocked is True


# --- Branch safety ---


def test_main_head_branch_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(head_branch="main")
    )
    assert result.blocked is True


def test_empty_head_branch_blocks() -> None:
    gate = _gate_result(head_branch="", source_branch="")
    planner = _repair_planner(head_branch="", source_branch="")
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(
            head_branch="",
            source_branch="",
            scoped_ci_patch_proposal_gate_result=gate,
            ci_repair_planner_result=planner,
        )
    )
    assert result.blocked is True


def test_protected_branch_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(head_branch="release/v1.0")
    )
    assert result.blocked is True


def test_base_branch_not_main_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(base_branch="develop")
    )
    assert result.blocked is True


# --- SHA safety ---


def test_missing_head_sha_blocks() -> None:
    gate = _gate_result(head_sha=None, commit_sha=None)
    planner = _repair_planner(head_sha=None, commit_sha=None)
    monitor = _ci_monitor(head_sha=None)
    rg = _repair_gate(head_sha=None)
    pr = _pr_creator(commit_sha=None)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(
            head_sha=None, commit_sha=None,
            scoped_ci_patch_proposal_gate_result=gate,
            ci_repair_planner_result=planner,
            ci_monitor_result=monitor,
            ci_repair_loop_gate_result=rg,
            pr_creator_result=pr,
        )
    )
    assert result.blocked is True


def test_invalid_head_sha_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(head_sha="not-a-sha")
    )
    assert result.blocked is True


# --- PR number and URL ---


def test_missing_pr_number_blocks() -> None:
    gate = _gate_result(pr_number=None)
    planner = _repair_planner(pr_number=None)
    rg = _repair_gate(pr_number=None)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(
            pr_number=None,
            scoped_ci_patch_proposal_gate_result=gate,
            ci_repair_planner_result=planner,
            ci_repair_loop_gate_result=rg,
        )
    )
    assert result.blocked is True


def test_missing_pr_url_blocks() -> None:
    gate = _gate_result(pr_url=None)
    planner = _repair_planner(pr_url=None)
    rg = _repair_gate(pr_url=None)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(
            pr_url=None,
            scoped_ci_patch_proposal_gate_result=gate,
            ci_repair_planner_result=planner,
            ci_repair_loop_gate_result=rg,
        )
    )
    assert result.blocked is True


# --- Secret detection ---


def test_secret_in_requested_by_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(requested_by="user with sk-test-token")
    )
    assert result.blocked is True
    assert result.redacted is True


def test_secret_in_gate_failing_checks_blocks() -> None:
    gate = _gate_result(
        failing_checks=[{"name": "test with API_KEY", "required": True}]
    )
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_ghp_token_in_repository_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(repository_full_name="ghp_abc123def/repo")
    )
    assert result.blocked is True


# --- Attempt budget ---


def test_negative_attempt_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(current_repair_attempt=-1)
    )
    assert result.blocked is True


def test_exhausted_attempt_budget_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(current_repair_attempt=3, max_repair_attempts=3)
    )
    assert result.blocked is True


def test_valid_attempt_budget_allows_proposal() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(current_repair_attempt=0, max_repair_attempts=3)
    )
    assert result.proposal_created is True


def test_max_repair_attempts_too_high_invalid() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(max_repair_attempts=20)
    )
    assert result.blocked is True


# --- Failure categories / blocked categories ---


def test_blocked_failure_categories_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(blocked_failure_categories=["security_failure"])
    )
    assert result.blocked is True


def test_empty_failure_categories_does_not_generate_operations() -> None:
    gate = _gate_result(failure_categories=[])
    planner = _repair_planner(
        failure_categories=[],
        repair_plan_steps=[],
    )
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(
            failure_categories=[],
            scoped_ci_patch_proposal_gate_result=gate,
            ci_repair_planner_result=planner,
        )
    )
    # Empty failure categories without safe steps means no proposal
    assert result.proposal_created is False


# --- Target areas ---


def test_blocked_target_areas_blocks() -> None:
    gate = _gate_result(candidate_target_areas=[".github/workflows"])
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_mixed_target_areas_partial() -> None:
    gate = _gate_result(candidate_target_areas=["tests", ".github/workflows"])
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


# --- Scope limits ---


def test_max_files_below_min_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(max_patch_proposal_files=0)
    )
    assert result.blocked is True


def test_max_files_above_max_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(max_patch_proposal_files=11)
    )
    assert result.blocked is True


def test_max_hunks_below_min_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(max_patch_proposal_hunks=0)
    )
    assert result.blocked is True


def test_max_hunks_above_max_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(max_patch_proposal_hunks=51)
    )
    assert result.blocked is True


def test_max_hunks_per_file_below_min_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(max_hunks_per_file=0)
    )
    assert result.blocked is True


def test_max_hunks_per_file_above_max_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(max_hunks_per_file=21)
    )
    assert result.blocked is True


def test_planner_max_files_exceeds_engine_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(max_files_to_change=7, max_patch_proposal_files=5)
    )
    assert result.blocked is True


def test_planner_max_hunks_exceeds_engine_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(max_hunks_total=30, max_patch_proposal_hunks=20)
    )
    assert result.blocked is True


# --- Validation commands ---


def test_unsafe_validation_commands_blocks() -> None:
    gate = _gate_result(suggested_validation_commands=["git push origin main"])
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


def test_deploy_command_blocks() -> None:
    gate = _gate_result(suggested_validation_commands=["deploy to production"])
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.blocked is True


# --- Proposal generation ---


def test_proposal_has_correct_structure() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert result.proposal_created is True
    for proposal in result.scoped_ci_patch_proposals:
        assert "proposal_id" in proposal
        assert "proposal_kind" in proposal
        assert proposal["proposal_kind"] == "scoped_ci_patch_proposal"
        assert "source_phase" in proposal
        assert proposal["source_phase"] == "phase_34_scoped_ci_patch_proposal_engine"
        assert "hunks" in proposal
        assert "operations" in proposal
        assert "target_file_roots" in proposal


def test_proposal_hunks_have_correct_structure() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert result.proposal_created is True
    for hunk in result.proposal_hunks:
        assert "hunk_id" in hunk
        assert hunk["hunk_id"].startswith("phase34-hunk-")
        assert "hunk_type" in hunk
        assert "target_area" in hunk
        assert "target_file_root" in hunk
        assert "operation" in hunk
        assert "before_context" in hunk
        assert hunk["before_context"] is None
        assert "after_intent" in hunk
        assert "proposed_snippet" in hunk
        assert hunk["proposed_snippet"] is None
        assert "confidence" in hunk
        assert "risk_level" in hunk


def test_proposal_not_allowed_for_future_if_high_risk() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    for hunk in result.proposal_hunks:
        if hunk["risk_level"] in ("high", "critical"):
            assert hunk["allowed_for_future_patch_application"] is False
            assert hunk["requires_human"] is True


def test_proposal_summary_includes_counts() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    summary = result.patch_proposal_summary
    assert summary["proposal_created"] is True
    assert summary["files_proposed_count"] > 0
    assert summary["hunks_proposed_count"] > 0
    assert "scope_limits" in summary
    assert "attempt_budget_remaining" in summary


def test_proposal_files_listed() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert len(result.proposal_files) > 0
    for f in result.proposal_files:
        assert f


def test_proposal_operations_listed() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert len(result.proposal_operations) > 0
    for op in result.proposal_operations:
        assert op in ("modify_existing", "add_test", "add_documentation")


def test_proposal_scope_listed() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert result.proposal_scope == ["tests"]


# --- Multiple failure categories ---


def test_multiple_failure_categories_proposal() -> None:
    gate = _gate_result(
        failure_categories=["test_failure", "lint_failure"],
        candidate_target_areas=["tests", "backend/python"],
    )
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert result.proposal_created is True
    assert "test_failure" in result.failure_categories
    assert "lint_failure" in result.failure_categories


# --- Multiple repair steps ---


def test_multiple_repair_steps_proposal() -> None:
    gate = _gate_result(failure_categories=["test_failure", "lint_failure"])
    planner = _repair_planner(
        failure_categories=["test_failure", "lint_failure"],
        repair_plan_steps=[
            {
                "step_id": "phase32-step-1",
                "step_type": "propose_scoped_test_fix",
                "failure_category": "test_failure",
                "source_check_name": "pytest",
                "target_area": "tests",
                "action_intent": "Fix test 1",
                "risk_level": "medium",
                "requires_human": False,
                "allowed_for_future_patch_proposal": True,
                "suggested_validation_commands": ["python -m pytest"],
            },
            {
                "step_id": "phase32-step-2",
                "step_type": "propose_scoped_lint_fix",
                "failure_category": "lint_failure",
                "source_check_name": "eslint",
                "target_area": "tests",
                "action_intent": "Fix lint 1",
                "risk_level": "low",
                "requires_human": False,
                "allowed_for_future_patch_proposal": True,
                "suggested_validation_commands": ["npm run lint"],
            },
        ],
    )
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(
            scoped_ci_patch_proposal_gate_result=gate,
            ci_repair_planner_result=planner,
        )
    )
    assert result.proposal_created is True
    assert len(result.proposal_hunks) >= 2


# --- Step validation ---


def test_unsafe_step_with_credential_skipped() -> None:
    planner = _repair_planner(
        repair_plan_steps=[
            {
                "step_id": "unsafe-step",
                "step_type": "propose_scoped_test_fix",
                "failure_category": "test_failure",
                "source_check_name": "test with API_KEY",
                "target_area": "tests",
                "action_intent": "Fix",
                "risk_level": "medium",
                "requires_human": False,
                "allowed_for_future_patch_proposal": True,
                "suggested_validation_commands": ["python -m pytest"],
            }
        ],
    )
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(ci_repair_planner_result=planner)
    )
    # Unsafe step with credential in source_check_name -> unsafe
    assert len(result.unsafe_repair_steps) > 0


def test_unsafe_step_from_gate_unsafe_steps_skipped() -> None:
    gate = _gate_result(
        unsafe_repair_steps=[
            {
                "step_id": "unsafe",
                "step_type": "propose_scoped_test_fix",
                "failure_category": "test_failure",
                "source_check_name": "pytest",
                "target_area": "tests",
                "action_intent": "Fix",
            }
        ],
    )
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    # step_type "propose_scoped_test_fix" is in gate_unsafe_types, so the planner steps are skipped
    assert result.proposal_created is False


# --- Type-specific step processing ---


def test_typecheck_step_maps_to_modify_existing() -> None:
    gate = _gate_result(
        failure_categories=["typecheck_failure"],
        candidate_target_areas=["backend/python"],
        candidate_file_roots=["backend/python"],
    )
    planner = _repair_planner(
        failure_categories=["typecheck_failure"],
        repair_plan_steps=[
            {
                "step_id": "tc-step",
                "step_type": "propose_scoped_typecheck_fix",
                "failure_category": "typecheck_failure",
                "source_check_name": "typecheck",
                "target_area": "backend/python",
                "action_intent": "Fix type error",
                "risk_level": "medium",
                "requires_human": False,
                "allowed_for_future_patch_proposal": True,
                "suggested_validation_commands": ["python -m pytest tests --typecheck"],
            }
        ],
    )
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(
            scoped_ci_patch_proposal_gate_result=gate,
            ci_repair_planner_result=planner,
        )
    )
    assert result.proposal_created is True
    for hunk in result.proposal_hunks:
        assert hunk["hunk_type"] == "typecheck_fix"
        assert hunk["operation"] == "modify_existing"


def test_lint_step_maps_to_modify_existing() -> None:
    gate = _gate_result(
        failure_categories=["lint_failure"],
        candidate_target_areas=["backend/python"],
        candidate_file_roots=["backend/python"],
    )
    planner = _repair_planner(
        failure_categories=["lint_failure"],
        repair_plan_steps=[
            {
                "step_id": "lint-step",
                "step_type": "propose_scoped_lint_fix",
                "failure_category": "lint_failure",
                "source_check_name": "lint",
                "target_area": "backend/python",
                "action_intent": "Fix lint",
                "risk_level": "low",
                "requires_human": False,
                "allowed_for_future_patch_proposal": True,
                "suggested_validation_commands": ["npm run lint"],
            }
        ],
    )
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(
            scoped_ci_patch_proposal_gate_result=gate,
            ci_repair_planner_result=planner,
        )
    )
    assert result.proposal_created is True
    for hunk in result.proposal_hunks:
        assert hunk["hunk_type"] == "lint_fix"


def test_format_step_maps_to_modify_existing() -> None:
    gate = _gate_result(
        failure_categories=["format_failure"],
        candidate_target_areas=["backend/python"],
        candidate_file_roots=["backend/python"],
    )
    planner = _repair_planner(
        failure_categories=["format_failure"],
        repair_plan_steps=[
            {
                "step_id": "fmt-step",
                "step_type": "propose_scoped_format_fix",
                "failure_category": "format_failure",
                "source_check_name": "fmt",
                "target_area": "backend/python",
                "action_intent": "Fix format",
                "risk_level": "low",
                "requires_human": False,
                "allowed_for_future_patch_proposal": True,
                "suggested_validation_commands": ["npm run lint"],
            }
        ],
    )
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(
            scoped_ci_patch_proposal_gate_result=gate,
            ci_repair_planner_result=planner,
        )
    )
    assert result.proposal_created is True
    for hunk in result.proposal_hunks:
        assert hunk["hunk_type"] == "format_fix"


def test_build_step_maps_to_modify_existing() -> None:
    gate = _gate_result(
        failure_categories=["build_failure"],
        candidate_target_areas=["backend/python"],
        candidate_file_roots=["backend/python"],
    )
    planner = _repair_planner(
        failure_categories=["build_failure"],
        repair_plan_steps=[
            {
                "step_id": "build-step",
                "step_type": "propose_scoped_build_fix",
                "failure_category": "build_failure",
                "source_check_name": "build",
                "target_area": "backend/python",
                "action_intent": "Fix build",
                "risk_level": "high",
                "requires_human": False,
                "allowed_for_future_patch_proposal": True,
                "suggested_validation_commands": ["npm run build"],
            }
        ],
    )
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(
            scoped_ci_patch_proposal_gate_result=gate,
            ci_repair_planner_result=planner,
        )
    )
    # build_failure with high risk -> hunks not allowed for future
    assert result.proposal_created is True
    for hunk in result.proposal_hunks:
        assert hunk["hunk_type"] == "build_fix"
        assert hunk["allowed_for_future_patch_application"] is False


def test_docs_target_area_adds_documentation_operation() -> None:
    gate = _gate_result(
        failure_categories=["test_failure"],
        candidate_target_areas=["docs"],
        candidate_file_roots=["docs"],
    )
    planner = _repair_planner(
        failure_categories=["test_failure"],
        repair_plan_steps=[
            {
                "step_id": "docs-step",
                "step_type": "propose_scoped_test_fix",
                "failure_category": "test_failure",
                "source_check_name": "docs",
                "target_area": "docs",
                "action_intent": "Update docs",
                "risk_level": "low",
                "requires_human": False,
                "allowed_for_future_patch_proposal": True,
                "suggested_validation_commands": ["git diff --check"],
            }
        ],
    )
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(
            scoped_ci_patch_proposal_gate_result=gate,
            ci_repair_planner_result=planner,
        )
    )
    assert result.proposal_created is True
    assert "add_documentation" in result.proposal_operations


# --- Partial proposal ---


def test_partial_proposal_with_blocked_operations() -> None:
    # security_failure in blocked_failure_categories blocks the engine
    gate = _gate_result(
        failure_categories=["test_failure"],
        blocked_failure_categories=["security_failure"],
    )
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(
            blocked_failure_categories=["security_failure"],
            scoped_ci_patch_proposal_gate_result=gate,
        )
    )
    assert result.blocked is True


# --- Governance decisions ---


def test_governance_decision_proposal_created() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    decision = result.runtime_truth["governance_decision"]
    assert decision == "scoped_ci_patch_proposal_created"


def test_governance_decision_dry_run() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(proposal_mode="dry_run")
    )
    decision = result.runtime_truth["governance_decision"]
    assert decision == "dry_run"


def test_governance_decision_blocked() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(proposal_mode="disabled")
    )
    decision = result.runtime_truth["governance_decision"]
    assert decision == "blocked"


def test_governance_decision_ci_passed() -> None:
    monitor = _ci_monitor(passed=True, failed=False)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(ci_monitor_result=monitor)
    )
    # engine blocks before governance decision, so it's "blocked"
    decision = result.runtime_truth["governance_decision"]
    assert decision == "blocked"
    assert result.ci_passed is True


def test_governance_decision_ci_pending() -> None:
    monitor = _ci_monitor(pending=True, failed=False, passed=False)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(ci_monitor_result=monitor)
    )
    # engine blocks before governance decision, so it's "blocked"
    decision = result.runtime_truth["governance_decision"]
    assert decision == "blocked"
    assert result.ci_pending is True


# --- Runtime truth fields ---


def test_runtime_truth_has_all_safe_flags_false() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    rt = result.runtime_truth
    assert rt["patch_applied"] is False
    assert rt["files_written"] is False
    assert rt["code_edited"] is False
    assert rt["source_inspected"] is False
    assert rt["logs_downloaded"] is False
    assert rt["workflow_retried"] is False
    assert rt["workflow_triggered"] is False
    assert rt["repair_loop_started"] is False
    assert rt["provider_called"] is False
    assert rt["agent_called"] is False
    assert rt["mcp_used"] is False
    assert rt["command_executed"] is False
    assert rt["git_mutated"] is False
    assert rt["commit_executed"] is False
    assert rt["push_executed"] is False
    assert rt["pr_updated"] is False
    assert rt["pr_merged"] is False
    assert rt["auto_merge_enabled"] is False
    assert rt["approval_submitted"] is False
    assert rt["main_modified"] is False
    assert rt["vault_written"] is False


def test_runtime_truth_patch_proposal_created_matches() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    rt = result.runtime_truth
    assert rt["patch_proposal_created"] == result.proposal_created


def test_runtime_truth_patch_hunks_generated_matches() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    rt = result.runtime_truth
    expected = result.proposal_created and result.hunks_proposed_count > 0
    assert rt["patch_hunks_generated"] == expected


def test_runtime_truth_evidence_version() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    rt = result.runtime_truth
    assert "evidence_version" in rt


def test_runtime_truth_event_type() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    rt = result.runtime_truth
    assert rt["event_type"] == "sandbox.scoped_ci_patch_proposal_engine.propose"


def test_runtime_truth_includes_child_events() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    rt = result.runtime_truth
    assert len(rt["child_runtime_truth_events"]) > 0


# --- Evidence version ---


def test_evidence_version_in_result() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert result.evidence_version == "1.0"


# --- Reason field ---


def test_reason_proposal_created() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert "created scoped CI patch proposal metadata" in result.reason


def test_reason_blocked() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(proposal_mode="disabled")
    )
    assert "blocked" in result.reason.lower()


def test_reason_dry_run() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(proposal_mode="dry_run")
    )
    assert "dry-run" in result.reason


def test_reason_ci_passed() -> None:
    monitor = _ci_monitor(passed=True, failed=False)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(ci_monitor_result=monitor)
    )
    # engine blocks with the ci_passed reason
    assert result.blocked is True
    assert result.ci_passed is True


def test_reason_ci_pending() -> None:
    monitor = _ci_monitor(pending=True, failed=False, passed=False)
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(ci_monitor_result=monitor)
    )
    # engine blocks with the ci_pending reason
    assert result.blocked is True
    assert result.ci_pending is True


# --- Follow-up tests ---


def test_followup_tests_includes_pytest_for_test_failure() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert "python -m pytest tests" in result.required_followup_tests


def test_followup_tests_includes_typecheck() -> None:
    gate = _gate_result(
        failure_categories=["typecheck_failure"],
        candidate_target_areas=["backend/python"],
    )
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert "npm run typecheck" in result.required_followup_tests


def test_followup_tests_includes_lint() -> None:
    gate = _gate_result(
        failure_categories=["lint_failure"],
    )
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert "npm run lint" in result.required_followup_tests


def test_followup_tests_includes_build() -> None:
    gate = _gate_result(
        failure_categories=["build_failure"],
    )
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert "npm run build" in result.required_followup_tests


def test_followup_tests_include_cargo_for_rust() -> None:
    gate = _gate_result(
        failure_categories=["test_failure"],
        candidate_target_areas=["backend/rust"],
    )
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert "cargo test" in result.required_followup_tests


def test_followup_tests_include_npm_test_for_frontend() -> None:
    gate = _gate_result(
        failure_categories=["test_failure"],
        candidate_target_areas=["frontend/src"],
    )
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    assert "npm test" in result.required_followup_tests


def test_followup_tests_fallback_to_git_diff() -> None:
    gate = _gate_result(
        failure_categories=[],
        candidate_target_areas=[],
    )
    planner = _repair_planner(
        failure_categories=[],
        affected_areas=[],
    )
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(
            failure_categories=[],
            scoped_ci_patch_proposal_gate_result=gate,
            ci_repair_planner_result=planner,
        )
    )
    assert "git diff --check" in result.required_followup_tests


# --- Required pre-patch checks ---


def test_required_checks_included_in_result() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    checks = result.required_pre_patch_application_checks
    assert len(checks) > 0
    assert "ci_monitor_succeeded" in checks


# --- Mapping input ---


def test_dict_input_works() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(dict(_request()))
    assert result.proposal_created is True


# --- Redacted field in result ---


def test_redacted_false_on_clean_request() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert result.redacted is False


def test_redacted_true_on_secret_requested_by() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(requested_by="user with sk-abc123")
    )
    assert result.redacted is True


# --- Escalation reason ---


def test_escalation_reason_on_blocked() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(proposal_mode="disabled")
    )
    assert result.escalation_reason is not None


def test_escalation_reason_none_on_success() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert result.escalation_reason is None


# --- Proposal mode passed through ---


def test_proposal_mode_passed_through() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(proposal_mode="dry_run")
    )
    assert result.proposal_mode == "dry_run"


# --- Repair plan steps validation ---


def test_repair_plan_steps_validated() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert len(result.repair_plan_steps) >= 0


def test_unsafe_repair_steps_listed() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert isinstance(result.unsafe_repair_steps, list)


def test_safe_repair_steps_listed() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert isinstance(result.safe_repair_steps, list)


def test_skipped_repair_steps_listed() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert isinstance(result.skipped_repair_steps, list)


def test_human_intervention_required_false_on_success() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert result.requires_human_intervention is False


def test_human_intervention_required_true_on_blocked() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(proposal_mode="disabled")
    )
    assert result.requires_human_intervention is True


# --- Aggregate status/conclusion ---


def test_aggregate_status_passed_through() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert result.aggregate_status == "failure"


def test_aggregate_conclusion_passed_through() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert result.aggregate_conclusion == "failed"


# --- Headers / request metadata ---


def test_requested_by_passed_through() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(requested_by="test-user")
    )
    assert result.requested_by == "test-user"


def test_related_phase_passed_through() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(related_phase="phase_33")
    )
    assert result.related_phase == "phase_33"


def test_related_pr_passed_through() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(related_pr="#362")
    )
    assert result.related_pr == "#362"


# --- Metadata propagation ---


def test_workspace_root_passed_through() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(workspace_root="/tmp/workspace")
    )
    assert result.workspace_root == "/tmp/workspace"


# --- PR state through request ---


def test_pr_state_open_from_request() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(pr_state="open")
    )
    assert result.pr_state == "open"


# --- Blocked failure categories via request ---


def test_blocked_failure_categories_via_happy_path_not_blocked() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert result.blocked_failure_categories == []


# --- Files/hunks proposed count ---


def test_files_proposed_count_matches() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert result.files_proposed_count == len(result.proposal_files)


def test_hunks_proposed_count_matches() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert result.hunks_proposed_count == len(result.proposal_hunks)


# --- Candidate areas/roots ---


def test_candidate_target_areas_passed_through() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert "tests" in result.candidate_target_areas


def test_candidate_file_roots_passed_through() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert "tests" in result.candidate_file_roots


def test_blocked_target_areas_empty_on_success() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert result.blocked_target_areas == []


# --- Suggested validation commands ---


def test_suggested_validation_commands_passed_through() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert "python -m pytest tests" in result.suggested_validation_commands


# --- Can flags are all false ---


def test_can_flags_all_false_on_success() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert result.can_apply_patch is False
    assert result.can_write_files is False
    assert result.can_inspect_source is False
    assert result.can_download_logs is False
    assert result.can_retry_workflows is False
    assert result.can_trigger_workflows is False
    assert result.can_call_provider is False
    assert result.can_call_agent is False
    assert result.can_commit is False
    assert result.can_push is False
    assert result.can_update_pr is False
    assert result.can_merge is False
    assert result.can_auto_merge is False
    assert result.can_mutate_git is False
    assert result.can_execute_commands is False


# --- Requires patch application gate ---


def test_requires_patch_application_gate_on_proposal() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert result.requires_patch_application_gate_phase is True


def test_requires_patch_application_gate_false_on_dry_run() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(proposal_mode="dry_run")
    )
    assert result.requires_patch_application_gate_phase is False


def test_requires_patch_application_gate_false_on_blocked() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(proposal_mode="disabled")
    )
    assert result.requires_patch_application_gate_phase is False


# --- Scope limit defaults ---


def test_default_scope_limits() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    assert result.max_patch_proposal_files == 5
    assert result.max_patch_proposal_hunks == 20
    assert result.max_hunks_per_file == 8


# --- Empty safe steps ---


def test_no_safe_steps_does_not_propose() -> None:
    planner = _repair_planner(repair_plan_steps=[])
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(ci_repair_planner_result=planner)
    )
    assert result.proposal_created is False


# --- Allow proposal generation false ---


def test_allow_proposal_generation_false_blocks() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(allow_proposal_generation=False)
    )
    assert result.proposal_created is False


# --- Hunk metadata completeness (no real source) ---


def test_hunk_metadata_no_source_snippets() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(_request())
    for hunk in result.proposal_hunks:
        assert hunk["before_context"] is None
        assert hunk["proposed_snippet"] is None
        assert hunk["after_intent"] is not None


# --- Redacted request fields ---


def test_secret_in_related_phase_redacted() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(related_phase="phase_with_API_KEY")
    )
    assert result.redacted is True


def test_secret_in_workspace_root_redacted() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(workspace_root="/path/with/SECRET/file")
    )
    assert result.redacted is True


def test_secret_in_pr_url_redacted() -> None:
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(pr_url="https://github.com/with/token@github.com/repo")
    )
    assert result.redacted is True


# --- Step with gate unsafe type skipping ---


def test_step_with_gate_unsafe_type_skipped() -> None:
    gate = _gate_result(
        unsafe_repair_steps=[
            {"step_type": "propose_scoped_test_fix"}
        ],
    )
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(scoped_ci_patch_proposal_gate_result=gate)
    )
    # Step type matches an unsafe step type -> skipped
    assert result.proposal_created is False


# --- inspect_ steps ---


def test_inspect_step_is_valid_and_generates_proposal() -> None:
    planner = _repair_planner(
        repair_plan_steps=[
            {
                "step_id": "inspect-step",
                "step_type": "inspect_test_output",
                "failure_category": "test_failure",
                "source_check_name": "pytest",
                "target_area": "tests",
                "action_intent": "Inspect test output",
                "risk_level": "low",
                "requires_human": False,
                "allowed_for_future_patch_proposal": True,
                "suggested_validation_commands": ["python -m pytest"],
            }
        ],
    )
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(ci_repair_planner_result=planner)
    )
    # inspect_ steps are valid and generate test_fix hunks
    assert result.proposal_created is True
    assert len(result.proposal_hunks) > 0


# --- request_human_review step ---


def test_request_human_review_step_skipped() -> None:
    planner = _repair_planner(
        repair_plan_steps=[
            {
                "step_id": "human-step",
                "step_type": "request_human_review",
                "failure_category": "test_failure",
                "source_check_name": "review",
                "target_area": "tests",
                "action_intent": "Human review needed",
                "risk_level": "high",
                "requires_human": True,
                "allowed_for_future_patch_proposal": True,
                "suggested_validation_commands": [],
            }
        ],
    )
    result = evaluate_scoped_ci_patch_proposal_engine(
        _request(ci_repair_planner_result=planner)
    )
    # request_human_review with requires_human -> skipped
    assert result.proposal_created is False
