from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.control.capability_router import CapabilityRouter  # noqa: E402
from brain.runtime.execution import StrategyDispatcher, StrategyExecutionContext, StrategyExecutionRequest  # noqa: E402
from brain.runtime.execution.manifest import build_execution_manifest  # noqa: E402
from brain.runtime.language.reasoning_contract import normalize_input_to_oil_request  # noqa: E402


class StrategyDispatcherTest(unittest.TestCase):
    def setUp(self) -> None:
        self.router = CapabilityRouter()
        self.dispatcher = StrategyDispatcher()

    def _request(self, message: str, *, direct_response: str = "", max_reasoning_steps: int = 3, node_runtime_available: bool = True) -> StrategyExecutionRequest:
        routing = self.router.classify_task(message, {"requires_node_runtime": "node runtime" in message.lower()})
        oil_request = normalize_input_to_oil_request(message, session_id="dispatch", run_id="", metadata={"source_component": "test"})
        manifest_result = build_execution_manifest(
            oil_request=oil_request,
            routing_decision=routing,
            selected_tools=["test_runner"] if routing.requires_tools else [],
            provider_path="openai",
        )
        self.assertIsNotNone(manifest_result.manifest)
        return StrategyExecutionRequest(
            selected_strategy=routing.strategy,
            manifest_id=manifest_result.manifest.manifest_id,
            manifest=manifest_result.manifest.as_dict(),
            oil_summary={"urgency": "medium", "desired_output": "analysis"},
            routing_decision=routing.as_dict(),
            ranked_decision={},
            tool_metadata=[],
            fallback_allowed=True,
            fallback_response="fallback",
            node_fallback_response="node fallback",
            context=StrategyExecutionContext(
                session_id="dispatch",
                run_id="",
                task_id="",
                current_runtime_mode="live",
                current_runtime_reason="test",
                direct_memory_hit=bool(direct_response),
                node_runtime_available=node_runtime_available,
                max_reasoning_steps=max_reasoning_steps,
            ),
            metadata={"direct_response": direct_response},
        )

    def test_direct_response_executor_prefers_precomputed_answer(self) -> None:
        request = self._request("explique o routing", direct_response="Resposta de memória")
        result = self.dispatcher.dispatch(request, compat_execute=lambda: {"response": "compat"})
        self.assertEqual(result.status, "success")
        self.assertEqual(result.response_text, "Resposta de memória")
        self.assertEqual(result.executor_used, "direct_response_executor")

    def test_node_runtime_executor_falls_back_when_node_unavailable(self) -> None:
        request = self._request("implemente algo com node runtime", node_runtime_available=False)
        request.selected_strategy = "NODE_RUNTIME_DELEGATION"
        result = self.dispatcher.dispatch(request, compat_execute=lambda: {"response": "node"})
        self.assertEqual(result.status, "fallback")
        self.assertTrue(result.fallback_applied)
        self.assertEqual(result.response_text, "node fallback")

    def test_multi_step_reasoning_downgrades_when_depth_exceeded(self) -> None:
        request = self._request("analise o repositorio", max_reasoning_steps=1)
        request.selected_strategy = "MULTI_STEP_REASONING"
        request.manifest["step_plan"] = [
            {"step_id": "s1", "kind": "reason", "description": "step 1"},
            {"step_id": "s2", "kind": "reason", "description": "step 2"},
        ]
        result = self.dispatcher.dispatch(request, compat_execute=lambda: {"response": "analysis"})
        self.assertEqual(result.status, "fallback")
        self.assertTrue(result.governance_downgrade_applied)
        self.assertTrue(result.downgraded)


if __name__ == "__main__":
    unittest.main()

