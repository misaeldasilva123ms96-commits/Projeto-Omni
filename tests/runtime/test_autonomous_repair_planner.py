from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.sandbox import (  # noqa: E402
    AutonomousRepairPlannerRequest,
    plan_autonomous_repair,
)
from brain.runtime.sandbox import repair_planner  # noqa: E402


def _request(**overrides) -> AutonomousRepairPlannerRequest:
    values = {
        "failure_summary": "pytest failed",
        "failure_classification": "tests_failed",
        "requested_by": "codex",
        "planner_mode": "plan_only",
        "related_phase": "phase-19",
        "related_pr": "future",
        "target_branch": "sandbox/autonomous-repair-planner",
        "base_branch": "main",
        "task_type": "runtime-validation",
        "files_changed": ["tests/runtime/test_example.py"],
        "allowed_files": ["tests/runtime/test_example.py"],
        "blocked_files": [],
        "max_files_to_touch": 5,
        "max_repair_steps": 10,
        "allow_code_edit": False,
        "allow_git_mutation": False,
        "allow_test_execution": False,
        "allow_provider_call": False,
        "allow_agent_call": False,
        "allow_network": False,
        "metadata": {"source": "test"},
    }
    values.update(overrides)
    return AutonomousRepairPlannerRequest(**values)


def _plan(**overrides):
    return plan_autonomous_repair(_request(**overrides))


def _loop_result(**overrides):
    payload = {
        "success": False,
        "failed": True,
        "blocked": False,
        "timed_out": False,
        "failure_summary": "validation failed",
        "failure_classification": "tests_failed",
        "command_results": [
            {
                "command": "python -m pytest tests/runtime/test_example.py",
                "exit_code": 1,
                "runtime_truth": {
                    "event_type": "sandbox.command.execution",
                    "governance_decision": "executed_failed",
                    "secrets_detected": False,
                },
            }
        ],
        "runtime_truth": {
            "event_type": "sandbox.test_runner.loop",
            "governance_decision": "validation_failed",
        },
    }
    payload.update(overrides)
    return payload


def test_modes_block_dry_run_and_plan_only() -> None:
    disabled = _plan(planner_mode="disabled")
    blocked = _plan(planner_mode="blocked")
    dry_run = _plan(planner_mode="dry_run")
    plan_only = _plan(planner_mode="plan_only")
    unknown = _plan(planner_mode="unknown")

    assert disabled.blocked is True
    assert blocked.blocked is True
    assert unknown.blocked is True
    assert dry_run.dry_run is True
    assert dry_run.planned is True
    assert plan_only.planned is True
    assert plan_only.repair_category == "test_repair"


def test_failure_alias_normalization() -> None:
    cases = {
        "test_failed": "tests_failed",
        "pytest_failed": "tests_failed",
        "npm_build_failed": "build_failed",
        "eslint_failed": "lint_failed",
        "tsc_failed": "typecheck_failed",
        "cargo_fmt_failed": "format_failed",
        "timeout": "command_timed_out",
        "unknown_value": "unknown_failure",
    }

    for raw, expected in cases.items():
        result = _plan(failure_classification=raw)

        assert result.normalized_failure_classification == expected


def test_repair_category_mapping() -> None:
    cases = {
        "tests_failed": "test_repair",
        "build_failed": "build_repair",
        "lint_failed": "lint_repair",
        "typecheck_failed": "type_repair",
        "format_failed": "formatting_repair",
        "command_not_found": "environment_or_tooling",
        "command_timed_out": "timeout_or_performance",
        "command_blocked": "policy_blocked",
        "unsafe_command": "policy_blocked",
        "secret_detected": "security_escalation",
        "unknown_failure": "investigation_required",
    }

    for classification, category in cases.items():
        result = _plan(failure_classification=classification)

        assert result.repair_category == category


def test_planning_outputs_for_common_failures() -> None:
    for classification in (
        "tests_failed",
        "build_failed",
        "lint_failed",
        "typecheck_failed",
        "format_failed",
    ):
        result = _plan(failure_classification=classification)

        assert result.planned is True
        assert result.proposed_steps
        assert result.validation_commands
        assert json.dumps(result.to_dict())


def test_successful_loop_returns_no_repair_needed() -> None:
    result = _plan(
        test_loop_result=_loop_result(
            success=True,
            failed=False,
            failure_summary=None,
            failure_classification=None,
        ),
        failure_summary=None,
        failure_classification=None,
    )

    assert result.success is True
    assert result.planned is False
    assert result.repair_category == "no_repair_needed"
    assert result.reason == "Validation passed; no repair plan is needed."


def test_limits_steps_and_suspected_files() -> None:
    result = _plan(
        files_changed=[
            "backend/python/a.py",
            "backend/python/b.py",
            "frontend/c.ts",
        ],
        allowed_files=[
            "backend/python/a.py",
            "backend/python/b.py",
            "frontend/c.ts",
        ],
        max_files_to_touch=2,
        max_repair_steps=2,
    )

    assert len(result.suspected_files) == 2
    assert len(result.proposed_steps) == 2


def test_validation_commands_are_safe_metadata() -> None:
    for classification in ("tests_failed", "build_failed", "lint_failed", "typecheck_failed", "format_failed"):
        result = _plan(failure_classification=classification)
        joined = " ".join(result.validation_commands)

        assert result.validation_commands
        assert "git add" not in joined
        assert "git commit" not in joined
        assert "git push" not in joined
        assert "git merge" not in joined
        assert "git rebase" not in joined
        assert "gh " not in joined
        assert "curl" not in joined
        assert "wget" not in joined


def test_phase_18_failed_blocked_timeout_inputs() -> None:
    failed = _plan(test_loop_result=_loop_result(), failure_classification=None)
    blocked = _plan(
        test_loop_result=_loop_result(blocked=True, failure_classification="unsafe_command"),
        failure_classification=None,
    )
    timed_out = _plan(
        test_loop_result=_loop_result(timed_out=True, failure_classification=None),
        failure_classification=None,
    )

    assert failed.repair_category == "test_repair"
    assert failed.runtime_truth["event_type"] == "sandbox.repair_planner.plan"
    assert blocked.repair_requires_human is True
    assert blocked.repair_category == "policy_blocked"
    assert timed_out.repair_category == "timeout_or_performance"


def test_escalation_triggers() -> None:
    assert _plan(failure_classification="secret_detected").repair_requires_human is True
    assert _plan(failure_classification="unsafe_command").repair_requires_human is True
    assert _plan(failure_classification="command_blocked").repair_requires_human is True
    assert _plan(files_changed=["docs/governance/policy.md"]).repair_requires_human is True
    assert _plan(files_changed=["vault/08_ADR/001.md"]).repair_requires_human is True
    assert _plan(metadata={"ci_threshold_changed": True}).repair_requires_human is True
    assert _plan(metadata={"skip_tests": True}).repair_requires_human is True
    assert _plan(metadata={"production_deploy": True}).repair_requires_human is True
    assert _plan(target_branch="main").repair_requires_human is True
    assert _plan(allowed_files=[]).repair_requires_human is True


def test_flags_are_locked_down() -> None:
    result = _plan()

    assert result.can_attempt_autonomous_repair is False
    assert result.repair_requires_new_phase is True
    assert result.can_edit_code is False
    assert result.can_mutate_git is False
    assert result.can_call_provider is False
    assert result.can_call_agent is False
    assert result.can_use_network is False
    assert result.can_open_pr is False
    assert result.can_merge is False
    assert result.runtime_truth["code_edited"] is False
    assert result.runtime_truth["files_written"] is False
    assert result.runtime_truth["git_mutated"] is False
    assert result.runtime_truth["pr_created"] is False
    assert result.runtime_truth["pr_merged"] is False
    assert result.runtime_truth["network_used"] is False
    assert result.runtime_truth["provider_called"] is False
    assert result.runtime_truth["agent_called"] is False
    assert result.runtime_truth["mcp_used"] is False
    assert result.runtime_truth["vault_written"] is False
    assert result.runtime_truth["main_modified"] is False


def test_capability_enablement_is_blocked() -> None:
    for flag in (
        "allow_code_edit",
        "allow_git_mutation",
        "allow_provider_call",
        "allow_agent_call",
        "allow_network",
    ):
        result = _plan(**{flag: True})

        assert result.blocked is True
        assert result.planned is False


def test_redaction_blocks_secret_like_inputs() -> None:
    marker = "OPEN" + "AI" + "_API" + "_KEY"
    bearer = "Authorization: " + "Bearer"
    summary = _plan(failure_summary=f"{marker}=placeholder")
    metadata = _plan(metadata={"header": f"{bearer} placeholder"})
    suspected = _plan(files_changed=[".env"])
    encoded = json.dumps(summary.to_dict()) + json.dumps(metadata.to_dict()) + json.dumps(suspected.to_dict())

    assert summary.blocked is True
    assert summary.normalized_failure_classification == "secret_detected"
    assert metadata.blocked is True
    assert suspected.blocked is True
    assert marker not in encoded
    assert bearer not in encoded


def test_source_has_no_unsafe_implementation() -> None:
    source = inspect.getsource(repair_planner)
    forbidden = (
        "sub" + "process",
        "shell=True",
        "os.system",
        "eval" + "(",
        "exec" + "(",
        "requests" + ".",
        "urllib",
        "socket",
        "websocket",
        "http.client",
        "pexpect",
        "MCP SDK",
        "provider call implementation",
        "real GitHub PR creation",
        "real PR merge implementation",
        "auto_merge",
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
