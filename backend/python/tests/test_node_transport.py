from __future__ import annotations

import sys
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.node_path_policy import NodePathPolicy, NodePathPolicyError, ValidatedNodeExecutionPlan  # noqa: E402
from brain.runtime.node_transport import call_node_with_preflight, run_node_subprocess  # noqa: E402


def _valid_plan() -> ValidatedNodeExecutionPlan:
    executable = Path(shutil.which("node") or "").resolve(strict=True)
    policy = NodePathPolicy.from_runtime(
        project_root=PROJECT_ROOT,
        python_root=PROJECT_ROOT / "backend/python",
        runner_path=PROJECT_ROOT / "js-runner/queryEngineRunner.js",
    )
    root = str(PROJECT_ROOT.resolve())
    return ValidatedNodeExecutionPlan.create(
        policy=policy,
        executable=executable,
        runtime_name="node",
        environment={
            "BASE_DIR": root,
            "OMNI_BASE_DIR": root,
            "NODE_RUNNER_BASE_DIR": root,
            "NODE_BIN": str(executable),
            "OMNI_JS_RUNTIME": "node",
            "OMNI_JS_RUNTIME_SELECTED": "node",
            "OMNI_JS_RUNTIME_BIN": str(executable),
            "OMNI_JS_RUNTIME_SOURCE": "test",
        },
    )


def test_arbitrary_diagnostics_dictionary_never_starts_subprocess() -> None:
    diagnostics = {
        "command": ["node", "outside.js"],
        "cwd": str(PROJECT_ROOT.parent),
        "subprocess_env": {"BASE_DIR": str(PROJECT_ROOT.parent)},
        "node_resolved": "node",
        "runner_exists": True,
        "cwd_exists": True,
        "missing_paths": [],
    }

    with patch("brain.runtime.node_transport.subprocess.run") as run:
        result = call_node_with_preflight(diagnostics=diagnostics, payload="{}", timeout_seconds=1)

    assert result.ok is False
    assert result.stage == "preflight"
    run.assert_not_called()


def test_valid_plan_keeps_payload_on_stdin_and_shell_disabled() -> None:
    completed = subprocess.CompletedProcess(args=[], returncode=0, stdout='{"response":"ok"}', stderr="")
    plan = _valid_plan()
    with patch("brain.runtime.node_transport.subprocess.run", return_value=completed) as run:
        result = run_node_subprocess(diagnostics=plan, payload="sensitive-payload", timeout_seconds=7)
    assert result["ok"] is True
    args, kwargs = run.call_args
    assert args[0] == list(plan.command)
    assert "sensitive-payload" not in args[0]
    assert kwargs["input"] == "sensitive-payload"
    assert kwargs["shell"] is False
    assert kwargs["timeout"] == 7


def test_tampered_command_cwd_or_control_environment_is_rejected_before_launch() -> None:
    plan = _valid_plan()
    mutations = (
        replace(plan, runner_path=PROJECT_ROOT / "package.json"),
        replace(plan, cwd=PROJECT_ROOT.parent),
        replace(plan, environment=tuple((key, "outside") if key == "BASE_DIR" else (key, value) for key, value in plan.environment)),
    )
    with patch("brain.runtime.node_transport.subprocess.run") as run:
        results = [call_node_with_preflight(diagnostics=item, payload="{}", timeout_seconds=1) for item in mutations]
    assert all(result.ok is False and result.stage == "preflight" for result in results)
    assert all(result.details["failure_class"] == "node_execution_plan_invalid" for result in results)
    run.assert_not_called()


def test_timeout_remains_a_safe_structured_failure() -> None:
    plan = _valid_plan()
    timeout = subprocess.TimeoutExpired(cmd=list(plan.command), timeout=1, output="", stderr="")
    with patch("brain.runtime.node_transport.subprocess.run", side_effect=timeout):
        result = run_node_subprocess(diagnostics=plan, payload="{}", timeout_seconds=1)
    assert result["ok"] is False
    assert result["reason_code"] == "NODE_BRIDGE_TIMEOUT"
    assert result["stage"] == "timeout"


def test_path_policy_failure_uses_safe_label_and_never_starts_subprocess() -> None:
    plan = _valid_plan()
    with (
        patch.object(NodePathPolicy, "from_runtime", side_effect=NodePathPolicyError("node_path_policy_symlink_rejected")),
        patch("brain.runtime.node_transport.subprocess.run") as run,
    ):
        result = call_node_with_preflight(diagnostics=plan, payload="{}", timeout_seconds=1)

    assert result.ok is False
    assert result.stage == "preflight"
    assert result.details["failure_class"] == "node_path_policy_symlink_rejected"
    assert "pathPolicy.js" not in str(result.details)
    run.assert_not_called()
