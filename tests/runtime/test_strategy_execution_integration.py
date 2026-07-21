from __future__ import annotations

import os
import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402
from brain.runtime.observability.runtime_lane_classifier import (  # noqa: E402
    LANE_BRIDGE_EXECUTION_REQUEST,
    LANE_TRUE_ACTION_EXECUTION,
)
from brain.runtime.node_transport import NodeTransportResult  # noqa: E402


class StrategyExecutionIntegrationTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-strategy-execution"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"exec-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    @staticmethod
    def node_file_routing(orchestrator: BrainOrchestrator):
        routing = orchestrator.capability_router.classify_task("analise o arquivo package.json")
        return type(routing)(
            **{
                **routing.as_dict(),
                "preferred_mode": routing.preferred_mode,
                "strategy": "NODE_RUNTIME_DELEGATION",
                "requires_node_runtime": True,
                "decision_reason_codes": ["explicit_node_test_route"],
            }
        )

    def test_dispatch_strategy_execution_uses_manifest_driven_executor(self) -> None:
        with self.temp_workspace() as workspace_root:
            os.environ["BASE_DIR"] = str(workspace_root)
            os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
            orchestrator = BrainOrchestrator(BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py"))
            routing = orchestrator.capability_router.classify_task("explique este fluxo")
            artifacts = orchestrator._build_runtime_upgrade_artifacts(
                message="explique este fluxo",
                session_id="strategy-int",
                run_id="",
                routing_decision=routing,
                strategy_payload={},
                selected_tools=[],
                provider_path="openai",
            )
            payload = orchestrator._dispatch_strategy_execution(
                session_id="strategy-int",
                run_id="",
                routing_decision=routing,
                upgrade_artifacts=artifacts,
                selected_tools=[],
                direct_response="Resposta local",
                compat_execute=lambda: {"response": "compat"},
            )
            self.assertTrue(payload["manifest_driven_execution"])
            self.assertEqual(payload["executor_used"], "direct_response_executor")
            self.assertEqual(payload["status"], "success")
            self.assertEqual(payload["response_text"], "Resposta local")

    def test_run_promotes_true_action_execution_when_node_returns_actions(self) -> None:
        with self.temp_workspace() as workspace_root:
            os.environ["BASE_DIR"] = str(workspace_root)
            os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
            orchestrator = BrainOrchestrator(BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py"))
            transport_payload = NodeTransportResult(
                ok=True,
                stage="completed",
                reason_code="success",
                stdout='{"response":"ok"}',
                stderr="",
                returncode=0,
                details={},
                parsed={
                    "response": "ok",
                    "execution_request": {
                        "task_id": "task-runtime-actions",
                        "run_id": "run-runtime-actions",
                        "provider": {},
                        "intent": "file_analysis",
                        "actions": [
                            {
                                "tool": "read_file",
                                "tool_arguments": {"path": "package.json"},
                            }
                        ],
                    },
                    "metadata": {
                        "execution_provenance": {
                            "execution_mode": "node_execution_graph",
                        }
                    },
                },
            )
            step_results = [
                {
                    "ok": True,
                    "selected_tool": "read_file",
                    "result_payload": {
                        "file": {
                            "filePath": "package.json",
                            "content": '{"name":"omni"}',
                        }
                    },
                }
            ]
            with (
                patch.object(BrainOrchestrator, "_answer_from_memory", return_value=""),
                patch.object(
                    orchestrator.capability_router,
                    "classify_task",
                    return_value=self.node_file_routing(orchestrator),
                ),
                patch("brain.runtime.orchestrator.call_node_with_preflight", return_value=transport_payload),
                patch.object(BrainOrchestrator, "_execute_runtime_actions", return_value=step_results) as execute_actions,
            ):
                response = orchestrator.run("analise o arquivo package.json")
            execute_actions.assert_called_once()
            self.assertEqual(response, '{"name":"omni"}')
            self.assertEqual(orchestrator.last_strategy_execution["execution_runtime_lane"], LANE_TRUE_ACTION_EXECUTION)
            self.assertFalse(orchestrator.last_strategy_execution["compatibility_execution_active"])
            self.assertTrue(orchestrator.last_strategy_execution["true_action_execution_active"])
            self.assertEqual(orchestrator.last_strategy_execution["tool_execution"]["tool_selected"], "read_file")
            self.assertTrue(orchestrator.last_strategy_execution["tool_execution"]["tool_succeeded"])
            inspection = orchestrator.last_cognitive_runtime_inspection or {}
            self.assertEqual(inspection.get("signals", {}).get("semantic_runtime_lane"), LANE_TRUE_ACTION_EXECUTION)
            self.assertEqual(inspection.get("signals", {}).get("execution_runtime_lane"), LANE_TRUE_ACTION_EXECUTION)
            self.assertEqual(inspection.get("signals", {}).get("tool_execution", {}).get("tool_selected"), "read_file")

    def test_run_keeps_bridge_execution_request_distinct_from_true_action_execution(self) -> None:
        with self.temp_workspace() as workspace_root:
            os.environ["BASE_DIR"] = str(workspace_root)
            os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
            orchestrator = BrainOrchestrator(BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py"))
            transport_payload = NodeTransportResult(
                ok=True,
                stage="completed",
                reason_code="success",
                stdout='{"response":"[execução_python_requerida] análise preparada"}',
                stderr="",
                returncode=0,
                details={},
                parsed={
                    "response": "[execução_python_requerida] análise preparada",
                    "execution_request": {"actions": []},
                    "metadata": {
                        "execution_provenance": {
                            "execution_mode": "python_executor_bridge",
                        }
                    },
                },
            )
            with (
                patch.object(BrainOrchestrator, "_answer_from_memory", return_value=""),
                patch.object(
                    orchestrator.capability_router,
                    "classify_task",
                    return_value=self.node_file_routing(orchestrator),
                ),
                patch("brain.runtime.orchestrator.call_node_with_preflight", return_value=transport_payload),
                patch.object(BrainOrchestrator, "_execute_runtime_actions") as execute_actions,
            ):
                response = orchestrator.run("analise o arquivo package.json")
            execute_actions.assert_not_called()
            self.assertEqual(response, "[execução_python_requerida] análise preparada")
            self.assertEqual(orchestrator.last_strategy_execution["execution_runtime_lane"], LANE_BRIDGE_EXECUTION_REQUEST)
            self.assertFalse(orchestrator.last_strategy_execution["true_action_execution_active"])
            self.assertFalse(orchestrator.last_strategy_execution["compatibility_execution_active"])
            self.assertEqual(orchestrator.last_strategy_execution["execution_path_used"], "node_execution")
            self.assertTrue(str(orchestrator.last_strategy_execution["tool_execution"]["tool_selected"]).strip())
            self.assertFalse(orchestrator.last_strategy_execution["tool_execution"]["tool_attempted"])
            inspection = orchestrator.last_cognitive_runtime_inspection or {}
            self.assertEqual(inspection.get("signals", {}).get("semantic_runtime_lane"), LANE_BRIDGE_EXECUTION_REQUEST)
            self.assertEqual(inspection.get("signals", {}).get("execution_runtime_lane"), LANE_BRIDGE_EXECUTION_REQUEST)
            self.assertTrue(str(inspection.get("signals", {}).get("tool_execution", {}).get("tool_selected", "")).strip())

    def test_execute_primary_local_tool_path_records_denied_tool_diagnostic(self) -> None:
        with self.temp_workspace() as workspace_root:
            os.environ["BASE_DIR"] = str(workspace_root)
            os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
            orchestrator = BrainOrchestrator(BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py"))
            with patch.object(
                BrainOrchestrator,
                "_execute_runtime_actions",
                return_value=[
                    {
                        "ok": False,
                        "selected_tool": "git_commit",
                        "tool_execution": {
                            "tool_requested": True,
                            "tool_selected": "git_commit",
                            "tool_available": True,
                            "tool_attempted": True,
                            "tool_succeeded": False,
                            "tool_failed": False,
                            "tool_denied": True,
                            "tool_failure_class": "permission_denied",
                            "tool_failure_reason": "git_commit requires explicit approval.",
                            "tool_latency_ms": 5,
                        },
                        "error_payload": {
                            "kind": "permission_denied",
                            "message": "git_commit requires explicit approval.",
                        },
                    }
                ],
            ):
                payload = orchestrator._execute_primary_local_tool_path(
                    session_id="strategy-local-tool",
                    runtime_message="faça commit",
                    predicted_intent="execute",
                    selected_tools=["git_commit"],
                )
            self.assertIn("tool_execution", payload)
            self.assertTrue(payload["tool_execution"]["tool_denied"])
            self.assertEqual(payload["tool_execution"]["tool_failure_class"], "permission_denied")

    def test_explicit_file_read_uses_local_tool_execution_end_to_end(self) -> None:
        os.environ["OMNI_BASE_DIR"] = str(PROJECT_ROOT)
        os.environ["OMNI_PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
        os.environ["OMNI_WORKSPACE_ROOT"] = str(PROJECT_ROOT)
        os.environ["OMNI_RUNTIME_MODE"] = "live"
        orchestrator = BrainOrchestrator(BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py"))
        with patch.object(BrainOrchestrator, "_answer_from_memory", return_value=""):
            response = orchestrator.run("analise o arquivo package.json")
        diagnostics = str(orchestrator.last_strategy_execution)
        self.assertTrue(response.strip())
        self.assertEqual(orchestrator.last_cognitive_runtime_inspection["runtime_mode"], "LOCAL_TOOL_SUCCESS", diagnostics)
        self.assertEqual(orchestrator.last_cognitive_runtime_inspection["signals"]["execution_runtime_lane"], "local_tool_execution", diagnostics)
        self.assertEqual(orchestrator.last_strategy_execution["execution_runtime_lane"], "local_tool_execution", diagnostics)
        self.assertTrue(orchestrator.last_strategy_execution["tool_execution"]["tool_succeeded"], diagnostics)
        self.assertNotIn("[execução_python_requerida]", response)


if __name__ == "__main__":
    unittest.main()
