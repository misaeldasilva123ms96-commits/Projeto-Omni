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


class RuntimeUpgradeIntegrationTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-runtime-upgrade"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"upgrade-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_build_runtime_upgrade_artifacts_happy_path(self) -> None:
        with self.temp_workspace() as workspace_root:
            os.environ["BASE_DIR"] = str(workspace_root)
            os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
            orchestrator = BrainOrchestrator(
                BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
            )
            routing = orchestrator.capability_router.classify_task("rode os testes e valide")
            artifacts = orchestrator._build_runtime_upgrade_artifacts(
                message="rode os testes e valide",
                session_id="upgrade-happy",
                run_id="",
                routing_decision=routing,
                strategy_payload={},
                selected_tools=["test_runner"],
                provider_path="openai",
            )
            self.assertEqual(artifacts["oil_summary"]["user_intent"], "execute_tool_like_action")
            self.assertEqual(artifacts["manifest_summary"]["chosen_strategy"], "TOOL_ASSISTED")
            self.assertFalse(artifacts["fallback_triggered"])

    def test_build_runtime_upgrade_artifacts_falls_back_safely(self) -> None:
        with self.temp_workspace() as workspace_root:
            os.environ["BASE_DIR"] = str(workspace_root)
            os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
            orchestrator = BrainOrchestrator(
                BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
            )
            routing = orchestrator.capability_router.classify_task("explique este fluxo")
            with patch("brain.runtime.orchestrator.translate_to_oil_projection", side_effect=RuntimeError("boom")):
                artifacts = orchestrator._build_runtime_upgrade_artifacts(
                    message="explique este fluxo",
                    session_id="upgrade-fallback",
                    run_id="run-upgrade",
                    routing_decision=routing,
                    strategy_payload={},
                    selected_tools=[],
                    provider_path="",
                )
            self.assertTrue(artifacts["fallback_triggered"])
            self.assertEqual(artifacts["fallback_reason"], "runtime_upgrade_build_failed")


if __name__ == "__main__":
    unittest.main()
