from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.node_path_policy import NodePathPolicyError  # noqa: E402
from brain.runtime.js_runtime_adapter import JSRuntimeAdapter  # noqa: E402
from brain.runtime.node_runner import (  # noqa: E402
    build_node_subprocess_env,
    classify_node_subprocess_failure,
    resolve_node_command_context,
)
from brain.runtime.orchestrator import BrainPaths  # noqa: E402


class _Adapter:
    root = PROJECT_ROOT

    def build_env(self):
        return ({"NODE_OPTIONS": "--require external.js", "NODE_PATH": "/external"}, SimpleNamespace(runtime_name="node", executable="node", source="test"))

    def select_runtime(self):
        return SimpleNamespace(runtime_name="node", executable="node", node_available=True)


def test_inherited_node_startup_controls_are_removed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NODE_OPTIONS", "--require external.js")
    monkeypatch.setenv("NODE_PATH", "/external")

    env = build_node_subprocess_env(_Adapter())

    assert "NODE_OPTIONS" not in env
    assert "NODE_PATH" not in env


@pytest.mark.parametrize("key", ["NODE_RUNNER_BASE_DIR", "RUNNER_ADAPTER_PATH", "OMNI_JS_RUNTIME_BIN", "NODE_OPTIONS"])
def test_reserved_provider_overlay_is_rejected(key: str) -> None:
    with pytest.raises(NodePathPolicyError, match="node_reserved_env_override"):
        build_node_subprocess_env(_Adapter(), session_provider_env_overlay={key: "attacker"})


def test_only_recognized_provider_credentials_survive_overlay() -> None:
    env = build_node_subprocess_env(
        _Adapter(),
        session_byok_active=True,
        session_provider_preference="openai",
        session_provider_env_overlay={"OPENAI_API_KEY": "test-key", "OPENAI_MODEL": "test-model"},
    )
    assert env["OPENAI_API_KEY"] == "test-key"
    assert env["OPENAI_MODEL"] == "test-model"
    assert env["OMNI_BYOK_PROVIDER"] == "openai"
    with pytest.raises(NodePathPolicyError, match="node_reserved_env_override"):
        build_node_subprocess_env(_Adapter(), session_provider_env_overlay={"ATTACKER_PROVIDER": "value"})


def test_trusted_root_controls_are_written_after_overlay() -> None:
    env = build_node_subprocess_env(_Adapter(), session_provider_env_overlay={"OPENAI_API_KEY": "test-key"})
    expected = str(PROJECT_ROOT.resolve())
    assert env["BASE_DIR"] == expected
    assert env["OMNI_BASE_DIR"] == expected
    assert env["NODE_RUNNER_BASE_DIR"] == expected
    assert env["OMNI_JS_RUNTIME"] == "node"


def test_preflight_returns_authenticated_plan_with_exact_two_argument_command() -> None:
    paths = BrainPaths.from_entrypoint(PROJECT_ROOT / "backend/python/main.py")
    plan = resolve_node_command_context(paths, JSRuntimeAdapter(PROJECT_ROOT), "payload-is-stdin-only")
    assert len(plan.command) == 2
    assert plan.command[1] == str((PROJECT_ROOT / "js-runner/queryEngineRunner.js").resolve())
    assert "payload-is-stdin-only" not in plan.command
    plan.verify()


def test_failure_diagnostics_keep_secret_redaction_and_safe_labels() -> None:
    paths = BrainPaths.from_entrypoint(PROJECT_ROOT / "backend/python/main.py")
    plan = resolve_node_command_context(paths, JSRuntimeAdapter(PROJECT_ROOT), "{}")
    reason, details = classify_node_subprocess_failure(
        diagnostics=plan,
        exception=RuntimeError("Bearer abcdefghijklmnopqrstuvwxyz"),
    )
    serialized = str(details)
    assert reason == "subprocess_exception"
    assert "abcdefghijklmnopqrstuvwxyz" not in serialized
    assert str(PROJECT_ROOT.resolve()) not in serialized
