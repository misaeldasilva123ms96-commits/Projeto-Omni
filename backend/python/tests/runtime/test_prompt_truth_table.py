from __future__ import annotations

import os
import shutil
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.node_transport import NodeTransportResult  # noqa: E402
from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402
from brain.runtime.observability.runtime_lane_classifier import (  # noqa: E402
    LANE_BRIDGE_EXECUTION_REQUEST,
    LANE_LOCAL_DIRECT_RESPONSE,
    LANE_MATCHER_SHORTCUT,
    LANE_SAFE_DEGRADED_FALLBACK,
    LANE_TRUE_ACTION_EXECUTION,
)


def _ok_result(parsed: dict) -> NodeTransportResult:
    return NodeTransportResult(
        ok=True, stage="completed", reason_code="success",
        stdout="", stderr="", returncode=0, parsed=parsed, details={},
    )


MATCHER_NODE_RESPONSE = _ok_result({
    "response": "Olá! Como posso ajudar?",
    "cognitive_runtime_hint": {"lane": "matcher_shortcut", "detail": "regex_greeting"},
})

LOCAL_DIRECT_NODE_RESPONSE = _ok_result({
    "response": "Sim, posso ajudar com isso.",
    "cognitive_runtime_hint": {"lane": "local_direct_response", "detail": "no_tool_local"},
})

BRIDGE_NODE_RESPONSE = _ok_result({
    "response": "Vou processar sua solicitação.",
    "execution_request": {
        "task_id": "bridge-task",
        "run_id": "bridge-run",
        "provider": {},
        "intent": "code_analysis",
    },
    "cognitive_runtime_hint": {"lane": "node_execution_graph", "detail": "python_executor_bridge"},
})

TRUE_ACTION_NODE_RESPONSE = _ok_result({
    "response": "Analisando o arquivo...",
    "execution_request": {
        "task_id": "action-task",
        "run_id": "action-run",
        "provider": {},
        "intent": "file_analysis",
        "actions": [{"tool": "read_file", "tool_arguments": {"path": "package.json"}}],
    },
    "cognitive_runtime_hint": {"lane": "node_execution_graph", "detail": "python_executor_bridge"},
})

FALLBACK_TRANSPORT = NodeTransportResult(
    ok=False, stage="completed", reason_code="NODE_BRIDGE_NONZERO_EXIT",
    stdout="", stderr="", returncode=-1, parsed=None, details={"returncode": -1},
)


@contextmanager
def _orchestrator():
    base = PROJECT_ROOT / ".logs" / "test-prompt-truth"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"truth-{uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=True)
    os.environ["BASE_DIR"] = str(path)
    os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
    orchestrator = BrainOrchestrator(BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py"))
    try:
        yield orchestrator
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _allow_synthetic_execution(orchestrator: BrainOrchestrator):
    evaluate_control_layer = orchestrator._evaluate_control_layer

    def allow(**kwargs):
        result = evaluate_control_layer(**kwargs)
        result["allowed"] = True
        return result

    return patch.object(orchestrator, "_evaluate_control_layer", side_effect=allow)


def test_prompt_greeting_triggers_matcher_shortcut_lane() -> None:
    with _orchestrator() as orchestrator:
        with (
            patch.object(BrainOrchestrator, "_answer_from_memory", return_value=""),
            patch("brain.runtime.orchestrator.call_node_with_preflight", return_value=MATCHER_NODE_RESPONSE),
            patch.object(BrainOrchestrator, "_resolve_node_command_context", return_value={
                "node_resolved": True, "runner_exists": True, "cwd_exists": True,
                "missing_paths": [], "command": ["node", "runner.js"],
                "subprocess_env": {}, "cwd": str(PROJECT_ROOT),
                "runner_path": "runner.js", "adapter_path": "adapter.js",
                "fusion_brain_path": "brain.js", "command_preview": "node runner.js",
                "node_bin": "node", "typescript_direct_execution_detected": False,
                "typescript_candidates_exist": False, "compiled_runner_artifact_exists": True,
                "env_preview": "PATH=...",
            }),
        ):
            response = orchestrator.run("Olá!")
    inspection = orchestrator.last_cognitive_runtime_inspection or {}
    signals = inspection.get("signals", {})
    assert signals.get("semantic_runtime_lane") == LANE_MATCHER_SHORTCUT, (
        f"Expected {LANE_MATCHER_SHORTCUT}, got {signals.get('semantic_runtime_lane')}"
    )


def test_prompt_local_direct_triggers_local_direct_response_lane() -> None:
    with _orchestrator() as orchestrator:
        with (
            patch.object(BrainOrchestrator, "_answer_from_memory", return_value=""),
            patch("brain.runtime.orchestrator.call_node_with_preflight", return_value=LOCAL_DIRECT_NODE_RESPONSE),
            patch.object(BrainOrchestrator, "_resolve_node_command_context", return_value={
                "node_resolved": True, "runner_exists": True, "cwd_exists": True,
                "missing_paths": [], "command": ["node", "runner.js"],
                "subprocess_env": {}, "cwd": str(PROJECT_ROOT),
                "runner_path": "runner.js", "adapter_path": "adapter.js",
                "fusion_brain_path": "brain.js", "command_preview": "node runner.js",
                "node_bin": "node", "typescript_direct_execution_detected": False,
                "typescript_candidates_exist": False, "compiled_runner_artifact_exists": True,
                "env_preview": "PATH=...",
            }),
        ):
            response = orchestrator.run("você pode me ajudar?")
    inspection = orchestrator.last_cognitive_runtime_inspection or {}
    signals = inspection.get("signals", {})
    assert signals.get("semantic_runtime_lane") == LANE_LOCAL_DIRECT_RESPONSE, (
        f"Expected {LANE_LOCAL_DIRECT_RESPONSE}, got {signals.get('semantic_runtime_lane')}"
    )


def test_prompt_bridge_execution_triggers_bridge_execution_request_lane() -> None:
    with _orchestrator() as orchestrator:
        with (
            patch.object(BrainOrchestrator, "_answer_from_memory", return_value=""),
            _allow_synthetic_execution(orchestrator),
            patch("brain.runtime.orchestrator.call_node_with_preflight", return_value=BRIDGE_NODE_RESPONSE),
            patch.object(BrainOrchestrator, "_resolve_node_command_context", return_value={
                "node_resolved": True, "runner_exists": True, "cwd_exists": True,
                "missing_paths": [], "command": ["node", "runner.js"],
                "subprocess_env": {}, "cwd": str(PROJECT_ROOT),
                "runner_path": "runner.js", "adapter_path": "adapter.js",
                "fusion_brain_path": "brain.js", "command_preview": "node runner.js",
                "node_bin": "node", "typescript_direct_execution_detected": False,
                "typescript_candidates_exist": False, "compiled_runner_artifact_exists": True,
                "env_preview": "PATH=...",
            }),
        ):
            response = orchestrator.run("implemente este fluxo via node runtime")
    inspection = orchestrator.last_cognitive_runtime_inspection or {}
    signals = inspection.get("signals", {})
    assert signals.get("semantic_runtime_lane") == LANE_BRIDGE_EXECUTION_REQUEST, (
        f"Expected {LANE_BRIDGE_EXECUTION_REQUEST}, got {signals.get('semantic_runtime_lane')}"
    )


def test_prompt_true_action_triggers_true_action_execution_lane() -> None:
    step_results = [
        {"ok": True, "selected_tool": "read_file", "result_payload": {"file": {"filePath": "package.json", "content": "{}"}}}
    ]
    with _orchestrator() as orchestrator:
        with (
            patch.object(BrainOrchestrator, "_answer_from_memory", return_value=""),
            _allow_synthetic_execution(orchestrator),
            patch("brain.runtime.orchestrator.call_node_with_preflight", return_value=TRUE_ACTION_NODE_RESPONSE),
            patch.object(BrainOrchestrator, "_execute_runtime_actions", return_value=step_results),
            patch.object(BrainOrchestrator, "_resolve_node_command_context", return_value={
                "node_resolved": True, "runner_exists": True, "cwd_exists": True,
                "missing_paths": [], "command": ["node", "runner.js"],
                "subprocess_env": {}, "cwd": str(PROJECT_ROOT),
                "runner_path": "runner.js", "adapter_path": "adapter.js",
                "fusion_brain_path": "brain.js", "command_preview": "node runner.js",
                "node_bin": "node", "typescript_direct_execution_detected": False,
                "typescript_candidates_exist": False, "compiled_runner_artifact_exists": True,
                "env_preview": "PATH=...",
            }),
        ):
            response = orchestrator.run("implemente via node runtime uma inspeção de package.json")
    inspection = orchestrator.last_cognitive_runtime_inspection or {}
    signals = inspection.get("signals", {})
    assert signals.get("semantic_runtime_lane") == LANE_TRUE_ACTION_EXECUTION, (
        f"Expected {LANE_TRUE_ACTION_EXECUTION}, got {signals.get('semantic_runtime_lane')}"
    )
    assert orchestrator.last_runtime_mode == LANE_TRUE_ACTION_EXECUTION, (
        f"Expected last_runtime_mode={LANE_TRUE_ACTION_EXECUTION}, got {orchestrator.last_runtime_mode}"
    )


def test_prompt_fallback_triggers_safe_degraded_fallback_lane() -> None:
    with _orchestrator() as orchestrator:
        with (
            patch.object(BrainOrchestrator, "_answer_from_memory", return_value=""),
            patch("brain.runtime.orchestrator.call_node_with_preflight", return_value=FALLBACK_TRANSPORT),
            patch.object(BrainOrchestrator, "_resolve_node_command_context", return_value={
                "node_resolved": True, "runner_exists": True, "cwd_exists": True,
                "missing_paths": [], "command": ["node", "runner.js"],
                "subprocess_env": {}, "cwd": str(PROJECT_ROOT),
                "runner_path": "runner.js", "adapter_path": "adapter.js",
                "fusion_brain_path": "brain.js", "command_preview": "node runner.js",
                "node_bin": "node", "typescript_direct_execution_detected": False,
                "typescript_candidates_exist": False, "compiled_runner_artifact_exists": True,
                "env_preview": "PATH=...",
            }),
        ):
            response = orchestrator.run("comando invalido")
    inspection = orchestrator.last_cognitive_runtime_inspection or {}
    signals = inspection.get("signals", {})
    assert signals.get("semantic_runtime_lane") == LANE_SAFE_DEGRADED_FALLBACK, (
        f"Expected {LANE_SAFE_DEGRADED_FALLBACK}, got {signals.get('semantic_runtime_lane')}"
    )
