from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.governance import AutonomyPolicyRequest, evaluate_autonomy_policy  # noqa: E402
from brain.runtime.sandbox import CommandGateRequest, evaluate_command_gate  # noqa: E402
from brain.runtime.sandbox import command_gate  # noqa: E402


def _request(**overrides) -> CommandGateRequest:
    values = {
        "command": "git status",
        "requested_by": "codex",
        "command_mode": "dry_run_policy_only",
        "autonomy_level": "L3_TEST_COMMIT_PUSH_BRANCH",
        "target_branch": "sandbox/safe-command-execution-gate",
        "base_branch": "main",
        "working_directory": None,
        "related_phase": "phase-16",
        "related_pr": "future",
        "purpose": "validate safe command policy",
        "timeout_seconds": 60,
        "requires_network": False,
        "writes_files": False,
        "mutates_git": False,
        "reads_secrets": False,
        "production_targeted": False,
        "destructive_intent": False,
        "metadata": {"source": "test"},
    }
    values.update(overrides)
    return CommandGateRequest(**values)


def _decision(**overrides):
    return evaluate_command_gate(_request(**overrides))


def test_disabled_mode_blocks_git_status() -> None:
    decision = _decision(command_mode="disabled")

    assert decision.blocked is True
    assert decision.allowed is False
    assert decision.reason == "Command execution gate is disabled by default."
    assert decision.command_execution_allowed is False


def test_dry_run_policy_only_classifies_git_status_without_execution() -> None:
    decision = _decision(command="git status", command_mode="dry_run_policy_only")

    assert decision.allowed is True
    assert decision.category == "read_safe"
    assert decision.safe_for_future_execution is True
    assert decision.command_execution_allowed is False


def test_sandbox_allowed_marks_git_status_safe_for_future_execution() -> None:
    decision = _decision(command="git status", command_mode="sandbox_allowed")

    assert decision.allowed is True
    assert decision.safe_for_future_execution is True
    assert decision.requires_runtime_truth is True
    assert decision.requires_sandbox is True


def test_blocked_and_unknown_modes_block() -> None:
    blocked = _decision(command_mode="blocked")
    unknown = _decision(command_mode="unknown")

    assert blocked.blocked is True
    assert unknown.blocked is True
    assert unknown.requires_human_intervention is True


def test_safe_read_commands() -> None:
    commands = (
        "git status",
        "git diff",
        "git diff --check",
        "python -m pytest tests/runtime/test_example.py",
        "npm test",
        "npm run build",
        "cargo test",
        "python -m json.tool sandbox/local/allowlist.commands.json",
    )

    for command in commands:
        decision = _decision(command=command, command_mode="dry_run_policy_only")

        assert decision.allowed is True, command
        assert decision.category == "read_safe"
        assert decision.command_execution_allowed is False


def test_git_branch_write_future_eligibility_in_sandbox_mode() -> None:
    commands = (
        "git checkout -b feature/test",
        "git switch -c feature/test",
        "git add docs/example.md",
        'git commit -m "safe message"',
        "git push origin feature/test",
        "git push -u origin feature/test",
    )

    for command in commands:
        decision = _decision(command=command, command_mode="sandbox_allowed")

        assert decision.allowed is True, command
        assert decision.category == "git_write_branch"
        assert decision.safe_for_future_execution is True
        assert decision.command_execution_allowed is False
        assert decision.git_mutation_allowed is False


def test_git_branch_write_not_future_eligible_in_dry_run_mode() -> None:
    decision = _decision(command="git push origin feature/test", command_mode="dry_run_policy_only")

    assert decision.blocked is True
    assert decision.category == "git_write_branch"
    assert decision.safe_for_future_execution is False


def test_main_and_force_push_are_blocked() -> None:
    for command in (
        "git push origin main",
        "git push --force",
        "git push -f",
    ):
        decision = _decision(command=command, command_mode="sandbox_allowed")

        assert decision.blocked is True
        assert decision.risk_level == "critical"
        assert decision.git_push_allowed is False


def test_blocked_commands() -> None:
    commands = (
        "rm -rf build",
        "Remove-Item -Recurse build",
        "curl https://example.invalid",
        "wget https://example.invalid",
        "Invoke-WebRequest https://example.invalid",
        "ssh example.invalid",
        "scp file example.invalid:/tmp",
        "sudo apt update",
        "chmod 777 script.sh",
        "gh pr merge 1",
        "git merge main",
        "git rebase main",
        "docker run --privileged image",
    )

    for command in commands:
        decision = _decision(command=command, command_mode="sandbox_allowed")

        assert decision.blocked is True, command
        assert decision.requires_human_intervention is True
        assert decision.safe_for_future_execution is False


def test_secret_commands_are_blocked_and_redacted() -> None:
    for command in ("cat .env", "Get-Content .env"):
        decision = _decision(command=command, command_mode="sandbox_allowed")
        encoded = json.dumps(decision.to_dict())

        assert decision.blocked is True
        assert decision.redacted is True
        assert ".env" not in encoded


def test_environment_dump_and_secret_markers_are_blocked() -> None:
    marker = "OPEN" + "AI" + "_API" + "_KEY"
    bearer = "Authorization: " + "Bearer"
    commands = (
        "printenv",
        f"python -m pytest --{marker}=placeholder",
        f"npm test --header '{bearer} placeholder'",
    )

    for command in commands:
        decision = _decision(command=command, command_mode="sandbox_allowed")
        encoded = json.dumps(decision.to_dict())

        assert decision.blocked is True
        assert decision.requires_human_intervention is True
        if command != "printenv":
            assert decision.redacted is True
        assert marker not in encoded
        assert bearer not in encoded


def test_exception_triggers_block() -> None:
    triggers = (
        "requires_network",
        "reads_secrets",
        "production_targeted",
        "destructive_intent",
    )

    for trigger in triggers:
        decision = _decision(
            command="git status",
            command_mode="sandbox_allowed",
            **{trigger: True},
        )

        assert decision.blocked is True
        assert decision.requires_human_intervention is True


def test_target_branch_main_blocks_git_mutation_and_unknown_requires_human() -> None:
    main_decision = _decision(
        command="git push origin feature/test",
        command_mode="sandbox_allowed",
        target_branch="main",
    )
    unknown = _decision(command="python custom_script.py", command_mode="sandbox_allowed")

    assert main_decision.blocked is True
    assert main_decision.main_branch_protected is True
    assert unknown.blocked is True
    assert unknown.requires_human_intervention is True
    assert unknown.risk_level == "high"


def test_safe_flags_are_locked_down() -> None:
    decision = _decision(command="git status", command_mode="sandbox_allowed")

    assert decision.main_branch_protected is True
    assert decision.command_execution_allowed is False
    assert decision.network_allowed is False
    assert decision.secrets_access_allowed is False
    assert decision.production_allowed is False
    assert decision.destructive_allowed is False
    assert decision.requires_runtime_truth is True
    assert decision.requires_sandbox is True


def test_decision_is_json_serializable_and_has_expected_keys() -> None:
    decision = _decision(command="git status", command_mode="sandbox_allowed")
    payload = decision.to_dict()
    encoded = json.dumps(payload, sort_keys=True)

    assert "safe_for_future_execution" in encoded
    assert payload["evidence_version"] == "1.0"
    assert payload["command_execution_allowed"] is False


def test_phase_15_autonomy_test_run_integrates_with_command_gate() -> None:
    autonomy = evaluate_autonomy_policy(
        AutonomyPolicyRequest(
            requested_level="L3_TEST_COMMIT_PUSH_BRANCH",
            requested_action="request_test_run",
            target_branch="sandbox/safe-command-execution-gate",
        )
    )
    command = _decision(
        command="pytest tests/runtime/test_example.py",
        command_mode="sandbox_allowed",
    )

    assert autonomy.allowed is True
    assert command.allowed is True
    assert command.safe_for_future_execution is True


def test_phase_15_exception_and_main_protection_align_with_command_gate() -> None:
    autonomy = evaluate_autonomy_policy(
        AutonomyPolicyRequest(
            requested_level="L7_FULL_AUTONOMOUS_RESOLUTION",
            requested_action="request_full_autonomous_resolution",
            checks_green=True,
            requires_human_decision=True,
        )
    )
    main_push = _decision(command="git push origin main", command_mode="sandbox_allowed")

    assert autonomy.blocked is True
    assert main_push.blocked is True
    assert main_push.main_branch_protected is True


def test_command_gate_source_does_not_use_execution_or_mutation_apis() -> None:
    source = inspect.getsource(command_gate)
    forbidden = (
        "sub" + "process",
        "os" + ".system",
        "shell" + "=True",
        "eval" + "(",
        "exec" + "(",
        "pex" + "pect",
        "requests" + ".",
        "url" + "lib",
        "sock" + "et",
        "web" + "sock" + "et",
        "http" + ".client",
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
