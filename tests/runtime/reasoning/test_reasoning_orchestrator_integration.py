from __future__ import annotations

import json
import os
import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402


class ReasoningOrchestratorIntegrationTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-reasoning-integration"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"reasoning-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_run_emits_reasoning_trace_and_persists_reasoning_payload(self) -> None:
        with self.temp_workspace() as workspace_root:
            with unittest.mock.patch.dict(
                os.environ,
                {
                    "BASE_DIR": str(workspace_root),
                    "PYTHON_BASE_DIR": str(PROJECT_ROOT / "backend" / "python"),
                    "AI_SESSION_ID": "sess-r31-int",
                    "OMINI_RUNTIME_MODE": "live",
                },
                clear=False,
            ):
                orchestrator = BrainOrchestrator(
                    BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
                )
                orchestrator._answer_from_memory = lambda *_args, **_kwargs: "Resposta de memória."
                response = orchestrator.run("Analise a arquitetura e proponha próximos passos.")
                self.assertEqual(response, "Resposta de memória.")

                audit_path = orchestrator.paths.root / ".logs" / "fusion-runtime" / "execution-audit.jsonl"
                self.assertTrue(audit_path.exists())
                lines = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]
                reasoning_events = [item for item in lines if item.get("event_type") == "runtime.reasoning.trace"]
                self.assertGreaterEqual(len(reasoning_events), 1)
                latest_reasoning = reasoning_events[-1]
                self.assertIn("trace", latest_reasoning)
                self.assertIn("handoff", latest_reasoning)
                memory_events = [item for item in lines if item.get("event_type") == "runtime.memory_intelligence.trace"]
                self.assertGreaterEqual(len(memory_events), 1)
                self.assertIn("selected_count", memory_events[-1])
                planning_events = [item for item in lines if item.get("event_type") == "runtime.planning_intelligence.trace"]
                self.assertGreaterEqual(len(planning_events), 1)
                pe = planning_events[-1]
                self.assertIn("planning_trace", pe)
                self.assertIn("execution_plan", pe)
                self.assertGreaterEqual(int(pe["planning_trace"].get("step_count", 0)), 1)
                strategy_events = [item for item in lines if item.get("event_type") == "runtime.strategy_adaptation.trace"]
                self.assertGreaterEqual(len(strategy_events), 1)
                se = strategy_events[-1]
                self.assertIn("strategy_trace", se)
                self.assertIn("selected_strategy", se)
                self.assertIn("fallback_strategy", se)

                session_path = orchestrator.session_store.path_for("sess-r31-int")
                payload = json.loads(session_path.read_text(encoding="utf-8"))
                self.assertIn("reasoning", payload)
                self.assertIn("execution_handoff", payload["reasoning"])
                self.assertIn("memory_intelligence", payload)
                self.assertIn("selected_count", payload["memory_intelligence"])
                self.assertIn("planning_intelligence", payload)
                self.assertIn("execution_plan", payload["planning_intelligence"])
                self.assertIn("planning_trace", payload["planning_intelligence"])
                learning_events = [item for item in lines if item.get("event_type") == "runtime.learning_intelligence.trace"]
                self.assertGreaterEqual(len(learning_events), 1)
                le = learning_events[-1]
                self.assertIn("learning_trace", le)
                self.assertIn("learning_record", le)
                self.assertIn("runtime_learning", payload)
                self.assertIn("learning_record", payload["runtime_learning"])
                self.assertIn("strategy_adaptation", payload)
                self.assertIn("selected_strategy", payload["strategy_adaptation"])
                perf_events = [item for item in lines if item.get("event_type") == "runtime.performance_optimization.trace"]
                self.assertGreaterEqual(len(perf_events), 1)
                self.assertIn("trace", perf_events[-1])
                self.assertIn("performance_optimization", payload)
                self.assertIn("trace", payload["performance_optimization"])


if __name__ == "__main__":
    unittest.main()
