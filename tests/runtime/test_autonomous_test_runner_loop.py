from __future__ import annotations

import inspect
import json
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

import pytest

from brain.runtime.sandbox import (  # noqa: E402
    AutonomousTestRunnerLoopRequest,
    SandboxCommandRunnerResult,
    run_autonomous_test_loop,
)
from brain.runtime.sandbox import test_runner_loop  # noqa: E402


@pytest.fixture
def workspace_temp_dir():
    with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as value:
        yield Path(value)


def _request(**overrides) -> AutonomousTestRunnerLoopRequest:
    values = {
        "commands": ["python --version"],
        "requested_by": "codex",
        "loop_mode": "sandbox_readonly",
        "runner_mode": "sandbox_readonly",
        "command_mode": "sandbox_allowed",
        "working_directory": str(PROJECT_ROOT),
        "target_branch": "sandbox/autonomous-test-runner-loop",
        "base_branch": "main",
        "related_phase": "phase-18",
        "related_pr": "future",
        "purpose": "validate autonomous test runner loop",
        "stop_on_first_failure": True,
        "max_commands": 10,
        "timeout_seconds_per_command": 60,
        "total_timeout_seconds": 600,
        "max_stdout_bytes_per_command": 20000,
        "max_stderr_bytes_per_command": 20000,
        "allow_failure_analysis": True,
        "allow_repair_plan": True,
        "allow_code_edit": False,
        "allow_git_mutation": False,
        "allow_network": False,
        "metadata": {"source": "test"},
    }
    values.update(overrides)
    return AutonomousTestRunnerLoopRequest(**values)


def _run(**overrides):
    return run_autonomous_test_loop(_request(**overrides))


def _runner_result(
    *,
    command: str = "python --version",
    executed: bool = True,
    blocked: bool = False,
    dry_run: bool = False,
    timed_out: bool = False,
    exit_code: int | None = 0,
    stdout: str = "",
    stderr: str = "",
    reason: str = "fake result",
    blocked_reason: str | None = None,
    redacted: bool = False,
) -> SandboxCommandRunnerResult:
    return SandboxCommandRunnerResult(
        executed=executed,
        blocked=blocked,
        dry_run=dry_run,
        timed_out=timed_out,
        exit_code=exit_code,
        command=command,
        normalized_command=command,
        argv=command.split(),
        runner_mode="dry_run" if dry_run else "sandbox_readonly",
        command_mode="sandbox_allowed",
        category="read_safe",
        risk_level="low",
        reason=reason,
        blocked_reason=blocked_reason,
        escalation_reason=blocked_reason,
        working_directory=str(PROJECT_ROOT),
        timeout_seconds=60,
        stdout=stdout,
        stderr=stderr,
        stdout_truncated=False,
        stderr_truncated=False,
        stdout_bytes=len(stdout.encode("utf-8")),
        stderr_bytes=len(stderr.encode("utf-8")),
        started_at="2026-01-01T00:00:00Z",
        finished_at="2026-01-01T00:00:00Z",
        duration_ms=1,
        requested_by="codex",
        related_phase="phase-18",
        related_pr="future",
        gate_allowed=not blocked,
        gate_blocked=blocked,
        gate_requires_runtime_truth=not blocked,
        gate_requires_sandbox=not blocked,
        runtime_truth={
            "event_type": "sandbox.command.execution",
            "governance_decision": "blocked" if blocked else "executed_success",
            "secrets_detected": redacted,
            "command_executed": executed,
            "network_used": False,
            "provider_called": False,
            "mcp_used": False,
            "vault_written": False,
            "git_mutated": False,
            "main_modified": False,
        },
        evidence_version="1.0",
        redacted=redacted,
    )


def test_disabled_blocked_and_unknown_modes_block_without_runner(monkeypatch) -> None:
    calls: list[object] = []
    monkeypatch.setattr(test_runner_loop, "run_sandbox_command", lambda request: calls.append(request))

    disabled = _run(loop_mode="disabled")
    blocked = _run(loop_mode="blocked")
    unknown = _run(loop_mode="unknown")

    assert disabled.blocked is True
    assert blocked.blocked is True
    assert unknown.blocked is True
    assert disabled.executed is False
    assert calls == []


def test_dry_run_loop_plans_commands_without_execution(monkeypatch) -> None:
    calls = []

    def fake_runner(request):
        calls.append(request)
        return _runner_result(command=request.command, executed=False, dry_run=True, exit_code=None)

    monkeypatch.setattr(test_runner_loop, "run_sandbox_command", fake_runner)

    result = _run(loop_mode="dry_run", commands=["python --version", "git status"])

    assert result.dry_run is True
    assert result.executed is False
    assert result.commands_planned == ["python --version", "git status"]
    assert [call.runner_mode for call in calls] == ["dry_run", "dry_run"]
    assert result.runtime_truth["governance_decision"] == "dry_run"


def test_sandbox_readonly_executes_safe_command_through_runner() -> None:
    result = _run(commands=["python --version"])

    assert result.executed is True
    assert result.success is True
    assert result.failed is False
    assert result.runtime_truth["event_type"] == "sandbox.test_runner.loop"
    assert result.runtime_truth["child_runtime_truth_events"][0]["event_type"] == (
        "sandbox.command.execution"
    )


def test_loop_calls_runner_for_each_command(monkeypatch) -> None:
    calls = []

    def fake_runner(request):
        calls.append(request.command)
        return _runner_result(command=request.command)

    monkeypatch.setattr(test_runner_loop, "run_sandbox_command", fake_runner)

    result = _run(commands=["python --version", "git status"])

    assert calls == ["python --version", "git status"]
    assert result.success is True


def test_blocked_timeout_nonzero_and_success_results(monkeypatch) -> None:
    def blocked_runner(request):
        return _runner_result(
            command=request.command,
            executed=False,
            blocked=True,
            exit_code=None,
            blocked_reason="blocked by runner",
        )

    monkeypatch.setattr(test_runner_loop, "run_sandbox_command", blocked_runner)
    blocked = _run(commands=["python --version"])

    def timeout_runner(request):
        return _runner_result(
            command=request.command,
            timed_out=True,
            exit_code=None,
            reason="timeout",
        )

    monkeypatch.setattr(test_runner_loop, "run_sandbox_command", timeout_runner)
    timed_out = _run(commands=["python --version"])

    def failing_runner(request):
        return _runner_result(command=request.command, exit_code=1, stderr="failed")

    monkeypatch.setattr(test_runner_loop, "run_sandbox_command", failing_runner)
    failed = _run(commands=["python -m pytest tests/runtime/test_example.py"])

    assert blocked.failure_classification == "command_blocked"
    assert blocked.recommended_next_action == "blocked_by_policy"
    assert timed_out.timed_out is True
    assert timed_out.failure_classification == "command_timed_out"
    assert failed.failure_classification == "tests_failed"
    assert failed.runtime_truth["governance_decision"] == "validation_failed"


def test_allowed_real_validations(workspace_temp_dir) -> None:
    json_file = workspace_temp_dir / "safe.json"
    package = workspace_temp_dir / "pkg"
    module = package / "mod.py"
    json_file.write_text('{"ok": true}\n', encoding="utf-8")
    package.mkdir()
    module.write_text("VALUE = 1\n", encoding="utf-8")

    result = _run(
        commands=[
            f'python -m json.tool "{json_file.as_posix()}"',
            f'python -m compileall "{package.as_posix()}"',
            "git status",
            "git diff --check",
        ],
        working_directory=str(workspace_temp_dir),
        stop_on_first_failure=False,
    )

    assert result.success is True
    assert result.commands_executed == 4
    assert result.recommended_next_action == "no_action_needed"


def test_optional_pytest_can_pass_through_loop(monkeypatch, workspace_temp_dir) -> None:
    test_file = workspace_temp_dir / "test_tiny.py"
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    captured = []

    def fake_runner(request):
        captured.append(request.command)
        return _runner_result(command=request.command, stdout="1 passed")

    monkeypatch.setattr(test_runner_loop, "run_sandbox_command", fake_runner)
    result = _run(
        commands=[f'python -m pytest "{test_file.as_posix()}"'],
        working_directory=str(workspace_temp_dir),
    )

    assert result.success is True
    assert captured == [f'python -m pytest "{test_file.as_posix()}"']


def test_blocked_command_families_stop_before_runner(monkeypatch) -> None:
    calls: list[object] = []
    monkeypatch.setattr(test_runner_loop, "run_sandbox_command", lambda request: calls.append(request))

    for command in (
        "git add docs/example.md",
        "git commit -m safe",
        "git push origin feature/test",
        "git checkout -b feature/test",
        "git merge main",
        "git rebase main",
        "gh pr merge 1",
        "curl https://example.invalid",
        "wget https://example.invalid",
        "ssh example.invalid",
        "rm -rf build",
        "cat .env",
        "printenv",
        "env",
    ):
        result = _run(commands=[command])

        assert result.blocked is True, command
        assert result.executed is False, command

    assert calls == []


def test_stop_on_first_failure_and_continue_modes(monkeypatch) -> None:
    def fake_runner(request):
        if "pytest" in request.command:
            return _runner_result(command=request.command, exit_code=1)
        return _runner_result(command=request.command)

    monkeypatch.setattr(test_runner_loop, "run_sandbox_command", fake_runner)

    stop = _run(commands=["python -m pytest tests/x.py", "python --version"])
    keep_going = _run(
        commands=["python -m pytest tests/x.py", "python --version"],
        stop_on_first_failure=False,
    )

    assert stop.partial is True
    assert len(stop.command_results) == 1
    assert keep_going.partial is False
    assert len(keep_going.command_results) == 2


def test_max_commands_and_json_serialization(monkeypatch) -> None:
    monkeypatch.setattr(
        test_runner_loop,
        "run_sandbox_command",
        lambda request: _runner_result(command=request.command),
    )

    result = _run(commands=["python --version"] * 12, max_commands=2)
    encoded = json.dumps(result.to_dict(), sort_keys=True)

    assert len(result.commands_planned) == 2
    assert result.partial is True
    assert "sandbox.test_runner.loop" in encoded


def test_failure_classification_and_recommended_actions(monkeypatch) -> None:
    cases = {
        "npm run build": ("build_failed", "create_repair_plan"),
        "npm run lint": ("lint_failed", "create_repair_plan"),
        "npm run typecheck": ("typecheck_failed", "create_repair_plan"),
        "cargo fmt --check": ("format_failed", "create_repair_plan"),
    }

    def fake_runner(request):
        return _runner_result(command=request.command, exit_code=1, stderr="failure")

    monkeypatch.setattr(test_runner_loop, "run_sandbox_command", fake_runner)

    for command, expected in cases.items():
        result = _run(commands=[command])

        assert (result.failure_classification, result.recommended_next_action) == expected


def test_secret_redaction_in_command_and_metadata(monkeypatch) -> None:
    calls: list[object] = []
    marker = "OPEN" + "AI" + "_API" + "_KEY"
    bearer = "Authorization: " + "Bearer"
    monkeypatch.setattr(test_runner_loop, "run_sandbox_command", lambda request: calls.append(request))

    command_secret = _run(commands=[f"python --version --{marker}=placeholder"])
    metadata_secret = _run(metadata={"header": f"{bearer} placeholder"})
    encoded = json.dumps(command_secret.to_dict()) + json.dumps(metadata_secret.to_dict())

    assert command_secret.failure_classification == "secret_detected"
    assert command_secret.recommended_next_action == "escalate_to_human"
    assert metadata_secret.blocked is True
    assert marker not in encoded
    assert bearer not in encoded
    assert calls == []


def test_flags_remain_locked_down() -> None:
    result = _run(commands=["python --version"])

    assert result.can_edit_code is False
    assert result.can_mutate_git is False
    assert result.can_open_pr is False
    assert result.can_merge is False
    assert result.can_attempt_repair is False
    assert result.repair_requires_new_phase is True
    assert result.runtime_truth["network_used"] is False
    assert result.runtime_truth["provider_called"] is False
    assert result.runtime_truth["mcp_used"] is False
    assert result.runtime_truth["vault_written"] is False
    assert result.runtime_truth["git_mutated"] is False
    assert result.runtime_truth["main_modified"] is False
    assert result.runtime_truth["code_edited"] is False
    assert result.runtime_truth["pr_created"] is False
    assert result.runtime_truth["pr_merged"] is False


def test_source_has_no_direct_execution_or_external_integration() -> None:
    source = inspect.getsource(test_runner_loop)
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

    assert "run_sandbox_command" in source
    for pattern in forbidden:
        assert pattern not in source
