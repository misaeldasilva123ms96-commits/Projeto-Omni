from __future__ import annotations

import os
import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()

