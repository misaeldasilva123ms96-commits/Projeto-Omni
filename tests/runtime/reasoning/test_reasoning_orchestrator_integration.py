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

                session_path = orchestrator.session_store.path_for("sess-r31-int")
                payload = json.loads(session_path.read_text(encoding="utf-8"))
                self.assertIn("reasoning", payload)
                self.assertIn("execution_handoff", payload["reasoning"])


if __name__ == "__main__":
    unittest.main()
