from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.governance import (  # noqa: E402
    AutonomyPolicyRequest,
    evaluate_autonomy_policy,
)
from brain.runtime.governance import autonomy_policy  # noqa: E402


def _request(**overrides) -> AutonomyPolicyRequest:
    values = {
        "requested_level": "L1_ADVISORY",
        "requested_action": "analyze_task",
        "requested_by": "codex",
        "task_type": "governed-change",
        "target_branch": "governance/autonomy-operating-model",
        "base_branch": "main",
        "risk_level": None,
        "files_changed": ["docs/governance/autonomy-operating-model.md"],
        "checks_green": False,
        "secrets_detected": False,
        "ci_threshold_changed": False,
        "tests_skipped": False,
        "security_policy_changed": False,
        "governance_policy_changed": False,
        "production_targeted": False,
        "billing_or_cost_impact": False,
        "destructive_action_requested": False,
        "requires_human_decision": False,
        "related_phase": "phase-15",
        "related_pr": "future",
        "metadata": {"source": "test"},
    }
    values.update(overrides)
    return AutonomyPolicyRequest(**values)


def _decision(**overrides):
    return evaluate_autonomy_policy(_request(**overrides))


def test_default_level_is_l1_advisory() -> None:
    decision = evaluate_autonomy_policy({})

    assert decision.autonomy_level == "L1_ADVISORY"
    assert decision.requested_action == "analyze_task"
    assert decision.allowed is True


def test_advisory_action_allowed_at_l1() -> None:
    decision = _decision(requested_action="analyze_task")

    assert decision.allowed is True
    assert decision.can_analyze is True
    assert decision.can_push_main is False


def test_unknown_action_is_blocked() -> None:
    decision = _decision(requested_action="unknown_action")

    assert decision.blocked is True
    assert decision.requires_human_intervention is True
    assert decision.risk_level == "high"


def test_unknown_level_is_blocked() -> None:
    decision = _decision(requested_level="L99_UNKNOWN")

    assert decision.blocked is True
    assert decision.requires_human_intervention is True
    assert decision.risk_level == "high"


def test_decision_object_is_json_serializable() -> None:
    decision = _decision()
    encoded = json.dumps(decision.to_dict(), sort_keys=True)

    assert "autonomy_level" in encoded
    assert decision.to_dict()["main_branch_protected"] is True


def test_l0_blocks_edits() -> None:
    decision = _decision(
        requested_level="L0_READ_ONLY",
        requested_action="request_branch_edit",
    )

    assert decision.blocked is True
    assert decision.can_edit_branch is False


def test_l1_allows_analyze_task() -> None:
    assert _decision(requested_level="L1_ADVISORY", requested_action="analyze_task").allowed


def test_l1_allows_create_plan() -> None:
    decision = _decision(requested_level="L1_ADVISORY", requested_action="create_plan")

    assert decision.allowed is True
    assert decision.can_plan is True


def test_l1_blocks_request_branch_edit() -> None:
    decision = _decision(
        requested_level="L1_ADVISORY",
        requested_action="request_branch_edit",
    )

    assert decision.blocked is True
    assert decision.can_edit_branch is False


def test_l2_allows_request_branch_edit_as_policy_decision() -> None:
    decision = _decision(
        requested_level="L2_BRANCH_EDIT_PROPOSAL",
        requested_action="request_branch_edit",
    )

    assert decision.allowed is True
    assert decision.can_edit_branch is True
    assert decision.runtime_truth_required is True


def test_l3_allows_test_commit_push_for_non_main_branch() -> None:
    cases = {
        "request_test_run": "can_run_tests",
        "request_commit": "can_commit",
        "request_push_branch": "can_push_branch",
    }

    for action, flag in cases.items():
        decision = _decision(
            requested_level="L3_TEST_COMMIT_PUSH_BRANCH",
            requested_action=action,
            target_branch="governance/autonomy-operating-model",
        )

        assert decision.allowed is True
        assert getattr(decision, flag) is True
        assert decision.can_push_main is False


def test_l4_allows_pr_open_and_ci_repair_but_blocks_merge() -> None:
    for action, flag in {
        "request_pr_open": "can_open_pr",
        "request_ci_repair": "can_repair_ci",
    }.items():
        decision = _decision(
            requested_level="L4_PR_OPEN_AND_CI_REPAIR",
            requested_action=action,
            target_branch="governance/autonomy-operating-model",
        )

        assert decision.allowed is True
        assert getattr(decision, flag) is True

    merge_decision = _decision(
        requested_level="L4_PR_OPEN_AND_CI_REPAIR",
        requested_action="request_pr_merge",
        checks_green=True,
    )

    assert merge_decision.blocked is True
    assert merge_decision.can_merge_pr is False


def test_l5_allows_pr_merge_only_when_all_gates_pass() -> None:
    decision = _decision(
        requested_level="L5_CONDITIONAL_AUTO_MERGE",
        requested_action="request_pr_merge",
        target_branch="governance/autonomy-operating-model",
        base_branch="main",
        checks_green=True,
    )

    assert decision.allowed is True
    assert decision.can_merge_pr is True
    assert decision.runtime_truth_required is True
    assert decision.report_required is True


def test_l6_allows_sandbox_execution_as_policy_decision() -> None:
    decision = _decision(
        requested_level="L6_SUPERVISED_SANDBOX_EXECUTION",
        requested_action="request_sandbox_execution",
        checks_green=True,
    )

    assert decision.allowed is True
    assert decision.can_execute_sandbox is True


def test_l7_allows_full_autonomous_resolution_when_safe() -> None:
    decision = _decision(
        requested_level="L7_FULL_AUTONOMOUS_RESOLUTION",
        requested_action="request_full_autonomous_resolution",
        checks_green=True,
    )

    assert decision.allowed is True
    assert decision.human_exception_required is False
    assert decision.runtime_truth_required is True
    assert decision.report_required is True


def test_main_branch_protection() -> None:
    assert _decision().can_push_main is False
    assert _decision(requested_action="push_main").blocked is True

    push_main = _decision(
        requested_level="L3_TEST_COMMIT_PUSH_BRANCH",
        requested_action="request_push_branch",
        target_branch="main",
    )
    edit_main = _decision(
        requested_level="L2_BRANCH_EDIT_PROPOSAL",
        requested_action="request_branch_edit",
        target_branch="main",
    )
    failing_merge = _decision(
        requested_level="L5_CONDITIONAL_AUTO_MERGE",
        requested_action="request_pr_merge",
        checks_green=False,
    )

    assert push_main.blocked is True
    assert edit_main.blocked is True
    assert _decision(requested_action="merge_with_failing_checks").blocked is True
    assert failing_merge.blocked is True
    assert failing_merge.can_merge_pr is False


def test_exception_triggers_block_autonomy() -> None:
    triggers = (
        "secrets_detected",
        "ci_threshold_changed",
        "tests_skipped",
        "security_policy_changed",
        "governance_policy_changed",
        "production_targeted",
        "billing_or_cost_impact",
        "destructive_action_requested",
        "requires_human_decision",
    )

    for trigger in triggers:
        decision = _decision(
            requested_level="L7_FULL_AUTONOMOUS_RESOLUTION",
            requested_action="request_full_autonomous_resolution",
            checks_green=True,
            **{trigger: True},
        )

        assert decision.blocked is True
        assert decision.requires_human_intervention is True
        assert decision.human_exception_required is True


def test_always_blocked_actions() -> None:
    for action in (
        "bypass_ci",
        "lower_ci_threshold",
        "skip_tests",
        "disable_security_scan",
        "read_secrets",
        "expose_secrets",
        "delete_production_data",
        "deploy_production",
        "change_billing",
        "approve_security_policy",
        "edit_governance_policy_directly",
        "approve_vault_note",
        "promote_to_reviewed",
        "promote_to_approved",
        "force_merge",
    ):
        decision = _decision(
            requested_level="L7_FULL_AUTONOMOUS_RESOLUTION",
            requested_action=action,
        )

        assert decision.blocked is True
        assert decision.allowed is False
        assert decision.risk_level == "critical"


def test_policy_flags_remain_safe() -> None:
    decision = _decision(
        requested_level="L7_FULL_AUTONOMOUS_RESOLUTION",
        requested_action="request_vault_draft",
        checks_green=True,
    )

    assert decision.can_bypass_ci is False
    assert decision.can_lower_security is False
    assert decision.can_call_provider is False
    assert decision.can_use_mcp is False
    assert decision.can_push_main is False
    assert decision.can_write_vault_draft is True
    assert decision.runtime_truth_required is True
    assert decision.report_required is True


def test_secret_like_metadata_is_redacted_and_blocked() -> None:
    marker = "OPEN" + "AI" + "_API" + "_KEY"
    decision = _decision(metadata={"credential": marker})
    encoded = json.dumps(decision.to_dict())

    assert decision.blocked is True
    assert decision.risk_level == "critical"
    assert marker not in encoded
    assert "Credential-like content" in decision.reason


def test_secret_like_requested_by_is_redacted_and_blocked() -> None:
    marker = "Authorization: " + "Bearer"
    decision = _decision(requested_by=f"{marker} placeholder")
    encoded = json.dumps(decision.to_dict())

    assert decision.blocked is True
    assert marker not in encoded
    assert "Credential-like content" in decision.reason


def test_autonomy_policy_source_does_not_use_execution_or_mutation_apis() -> None:
    source = inspect.getsource(autonomy_policy)
    forbidden = (
        "subprocess",
        "os.system",
        "shell=True",
        "eval" + "(",
        "exec" + "(",
        "requests" + ".",
        "urllib",
        "socket",
        "websocket",
        "http.client",
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
