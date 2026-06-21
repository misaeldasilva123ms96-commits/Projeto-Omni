from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.sandbox import (  # noqa: E402
    SandboxCommandRunnerRequest,
    run_sandbox_command,
)
from brain.runtime.sandbox import command_runner  # noqa: E402


@pytest.fixture
def workspace_temp_dir():
    with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as value:
        yield Path(value)


def _request(**overrides) -> SandboxCommandRunnerRequest:
    values = {
        "command": "python --version",
        "requested_by": "codex",
        "runner_mode": "sandbox_readonly",
        "command_mode": "sandbox_allowed",
        "working_directory": str(PROJECT_ROOT),
        "timeout_seconds": 60,
        "max_stdout_bytes": 20000,
        "max_stderr_bytes": 20000,
        "target_branch": "sandbox/command-runner",
        "base_branch": "main",
        "related_phase": "phase-17",
        "related_pr": "future",
        "purpose": "validate safe command runner",
        "metadata": {"source": "test"},
    }
    values.update(overrides)
    return SandboxCommandRunnerRequest(**values)


def _run(**overrides):
    return run_sandbox_command(_request(**overrides))


def test_disabled_and_blocked_modes_block_without_execution(monkeypatch) -> None:
    calls: list[object] = []
    monkeypatch.setattr(command_runner.subprocess, "run", lambda *args, **kwargs: calls.append(args))

    disabled = _run(runner_mode="disabled")
    blocked = _run(runner_mode="blocked")

    assert disabled.blocked is True
    assert blocked.blocked is True
    assert disabled.executed is False
    assert blocked.executed is False
    assert calls == []


def test_dry_run_mode_classifies_without_execution(monkeypatch) -> None:
    calls: list[object] = []
    monkeypatch.setattr(command_runner.subprocess, "run", lambda *args, **kwargs: calls.append(args))

    result = _run(runner_mode="dry_run")

    assert result.dry_run is True
    assert result.executed is False
    assert result.blocked is False
    assert result.runtime_truth["governance_decision"] == "dry_run"
    assert calls == []


def test_sandbox_readonly_executes_python_version() -> None:
    result = _run(command="python --version")

    assert result.executed is True
    assert result.blocked is False
    assert result.exit_code == 0
    assert result.argv == ["python", "--version"]
    assert result.runtime_truth["event_type"] == "sandbox.command.execution"
    assert result.runtime_truth["command_executed"] is True
    assert result.runtime_truth["network_used"] is False
    assert result.runtime_truth["provider_called"] is False
    assert result.runtime_truth["mcp_used"] is False
    assert result.runtime_truth["vault_written"] is False
    assert result.runtime_truth["git_mutated"] is False
    assert result.runtime_truth["main_modified"] is False


def test_git_status_and_diff_check_execute_safely() -> None:
    status = _run(command="git status")
    diff_check = _run(command="git diff --check")

    assert status.executed is True
    assert status.exit_code == 0
    assert diff_check.executed is True
    assert diff_check.timed_out is False


def test_json_tool_and_compileall_execute_on_safe_temp_paths(workspace_temp_dir) -> None:
    payload = workspace_temp_dir / "safe.json"
    package = workspace_temp_dir / "pkg"
    module = package / "mod.py"
    payload.write_text('{"ok": true}\n', encoding="utf-8")
    package.mkdir()
    module.write_text("VALUE = 1\n", encoding="utf-8")

    json_result = _run(
        command=f'python -m json.tool "{payload.as_posix()}"',
        working_directory=str(workspace_temp_dir),
    )
    compile_result = _run(
        command=f'python -m compileall "{package.as_posix()}"',
        working_directory=str(workspace_temp_dir),
    )

    assert json_result.executed is True
    assert json_result.exit_code == 0
    assert '"ok": true' in json_result.stdout
    assert compile_result.executed is True
    assert compile_result.exit_code == 0


def test_optional_pytest_execution_on_safe_temp_test(monkeypatch, workspace_temp_dir) -> None:
    test_file = workspace_temp_dir / "test_tiny.py"
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_run(*args, **kwargs):
        captured["argv"] = args[0]
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=b"1 passed", stderr=b"")

    monkeypatch.setattr(command_runner.subprocess, "run", fake_run)

    result = _run(
        command=f'python -m pytest "{test_file.as_posix()}"',
        working_directory=str(workspace_temp_dir),
        timeout_seconds=30,
    )

    assert result.executed is True
    assert result.exit_code == 0
    assert captured["argv"] == ["python", "-m", "pytest", test_file.as_posix()]


def test_runner_calls_gate_before_execution(monkeypatch) -> None:
    original = command_runner.evaluate_command_gate
    called = {"gate": False}

    def wrapped(request):
        called["gate"] = True
        return original(request)

    monkeypatch.setattr(command_runner, "evaluate_command_gate", wrapped)

    result = _run(command="python --version")

    assert called["gate"] is True
    assert result.executed is True


def test_gate_blocked_and_policy_only_command_mode_do_not_execute(monkeypatch) -> None:
    calls: list[object] = []
    monkeypatch.setattr(command_runner.subprocess, "run", lambda *args, **kwargs: calls.append(args))

    blocked = _run(command="curl https://example.invalid")
    policy_only = _run(command_mode="dry_run_policy_only")

    assert blocked.executed is False
    assert policy_only.executed is False
    assert blocked.blocked is True
    assert policy_only.blocked is True
    assert calls == []


def test_future_branch_git_write_commands_do_not_execute(monkeypatch) -> None:
    calls: list[object] = []
    monkeypatch.setattr(command_runner.subprocess, "run", lambda *args, **kwargs: calls.append(args))

    for command in (
        "git add docs/example.md",
        'git commit -m "safe message"',
        "git push origin feature/test",
        "git checkout -b feature/test",
        "git switch -c feature/test",
        "git merge main",
        "git rebase main",
        "gh pr merge 1",
    ):
        result = _run(command=command)

        assert result.blocked is True, command
        assert result.executed is False, command

    assert calls == []


def test_blocked_execution_commands_do_not_execute(monkeypatch) -> None:
    calls: list[object] = []
    monkeypatch.setattr(command_runner.subprocess, "run", lambda *args, **kwargs: calls.append(args))

    for command in (
        "curl https://example.invalid",
        "wget https://example.invalid",
        "ssh example.invalid",
        "rm -rf build",
        "Remove-Item -Recurse build",
        "cat .env",
        "printenv",
        "env",
    ):
        result = _run(command=command)

        assert result.blocked is True, command
        assert result.executed is False, command

    assert calls == []


def test_shell_injection_patterns_are_blocked(monkeypatch) -> None:
    calls: list[object] = []
    monkeypatch.setattr(command_runner.subprocess, "run", lambda *args, **kwargs: calls.append(args))

    for command in (
        "git status && echo bad",
        "python --version; echo bad",
        "git status | cat",
        "python --version > out.txt",
        "python --version $(echo bad)",
        "python --version `echo bad`",
    ):
        result = _run(command=command)

        assert result.blocked is True, command
        assert result.executed is False, command

    assert calls == []


def test_working_directory_boundaries(workspace_temp_dir) -> None:
    safe_repo = _run(working_directory=str(PROJECT_ROOT))
    safe_temp = _run(working_directory=str(workspace_temp_dir))
    traversal = _run(working_directory=str(PROJECT_ROOT / ".."))
    git_internal = _run(working_directory=str(PROJECT_ROOT / ".git"))
    env_path = _run(working_directory=str(PROJECT_ROOT / ".env"))
    temp_root = _run(working_directory=os.path.abspath(os.getenv("TMPDIR") or "/tmp"))

    assert safe_repo.executed is True
    assert safe_temp.executed is True
    assert traversal.blocked is True
    assert git_internal.blocked is True
    assert env_path.blocked is True
    assert temp_root.blocked is True


def test_token_meter_path_and_branch_output_are_not_credentials(monkeypatch) -> None:
    with tempfile.TemporaryDirectory(prefix="token-meter-", dir=PROJECT_ROOT) as value:
        working_directory = Path(value)

        def fake_run(*args, **kwargs):
            return subprocess.CompletedProcess(
                args=args[0],
                returncode=0,
                stdout=b"On branch ui/omni-token-meter\nnothing to commit\n",
                stderr=b"",
            )

        monkeypatch.setattr(command_runner.subprocess, "run", fake_run)
        result = _run(command="git status", working_directory=str(working_directory))

    assert result.executed is True
    assert result.blocked is False
    assert result.redacted is False
    assert result.runtime_truth["secrets_detected"] is False
    assert "ui/omni-token-meter" in result.stdout


def test_token_assignment_remains_blocked() -> None:
    result = _run(command="python --version --access_token=placeholder")

    assert result.blocked is True
    assert result.executed is False
    assert result.runtime_truth["secrets_detected"] is True
    assert "placeholder" not in json.dumps(result.to_dict())


def test_path_arguments_block_traversal_and_secret_paths(workspace_temp_dir) -> None:
    safe_json = workspace_temp_dir / "safe.json"
    safe_json.write_text('{"ok": true}\n', encoding="utf-8")

    no_path = _run(command="python -m pytest -q", working_directory=str(workspace_temp_dir))
    traversal = _run(
        command="python -m json.tool ../safe.json",
        working_directory=str(workspace_temp_dir),
    )
    env_arg = _run(
        command="python -m json.tool .env",
        working_directory=str(workspace_temp_dir),
    )
    safe = _run(
        command=f'python -m json.tool "{safe_json.as_posix()}"',
        working_directory=str(workspace_temp_dir),
    )

    assert no_path.blocked is True
    assert traversal.blocked is True
    assert env_arg.blocked is True
    assert safe.executed is True


def test_secret_like_environment_is_removed_and_output_is_redacted(monkeypatch) -> None:
    marker = "OPEN" + "AI" + "_API" + "_KEY"
    monkeypatch.setenv(marker, "placeholder")
    captured_env: dict[str, str] = {}

    def fake_run(*args, **kwargs):
        captured_env.update(kwargs["env"])
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=f"{marker}=placeholder".encode("utf-8"),
            stderr=b"Authorization: Bearer placeholder",
        )

    monkeypatch.setattr(command_runner.subprocess, "run", fake_run)

    result = _run(command="python --version")
    encoded = json.dumps(result.to_dict())

    assert marker not in captured_env
    assert marker not in encoded
    assert "Authorization: Bearer" not in encoded
    assert result.redacted is True
    assert result.runtime_truth["secrets_detected"] is True
    assert result.runtime_truth["human_intervention_required"] is True


def test_timeout_is_clamped_and_reported(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs["timeout"], output=b"", stderr=b"")

    monkeypatch.setattr(command_runner.subprocess, "run", fake_run)

    below = _run(timeout_seconds=0)
    above = _run(timeout_seconds=999)

    assert below.timeout_seconds == 1
    assert below.timed_out is True
    assert below.runtime_truth["governance_decision"] == "timed_out"
    assert above.timeout_seconds == 300


def test_output_capture_truncation_and_json_serialization(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=1,
            stdout=b"abcdef",
            stderr=b"ghijkl",
        )

    monkeypatch.setattr(command_runner.subprocess, "run", fake_run)

    result = _run(command="python --version", max_stdout_bytes=3, max_stderr_bytes=2)
    encoded = json.dumps(result.to_dict(), sort_keys=True)

    assert result.stdout == "abc"
    assert result.stderr == "gh"
    assert result.stdout_truncated is True
    assert result.stderr_truncated is True
    assert result.runtime_truth["governance_decision"] == "executed_failed"
    assert "sandbox.command.execution" in encoded


def test_unknown_runner_mode_and_unknown_command_block(monkeypatch) -> None:
    calls: list[object] = []
    monkeypatch.setattr(command_runner.subprocess, "run", lambda *args, **kwargs: calls.append(args))

    unknown_mode = _run(runner_mode="unknown")
    unknown_command = _run(command="python custom_script.py")

    assert unknown_mode.blocked is True
    assert unknown_command.blocked is True
    assert calls == []


def test_command_runner_source_uses_only_approved_execution_boundary() -> None:
    source = inspect.getsource(command_runner)
    forbidden = (
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
        "MCP",
        "provider",
        "auto_merge",
        "open" + "(",
        "write" + "(",
        "unlink" + "(",
        "rename" + "(",
        "rmtree" + "(",
        "shutil" + ".move",
    )

    assert "subprocess.run" in source
    assert "shell=False" in source
    for pattern in forbidden:
        assert pattern not in source
