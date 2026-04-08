from __future__ import annotations

import os
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.checkpoint_store import CheckpointStore  # noqa: E402
from brain.runtime.milestone_manager import MilestoneManager  # noqa: E402
from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402
from brain.runtime.patch_set_manager import apply_patch_set, build_patch_set  # noqa: E402


class RuntimeHardeningTest(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["BASE_DIR"] = str(PROJECT_ROOT)
        os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
        os.environ["AI_SESSION_ID"] = f"fase3-{uuid4().hex[:8]}"

    def tearDown(self) -> None:
        for key in ["NODE_BIN", "OMINI_RUNTIME_MODE", "OMINI_FORCE_SPECIALIST_FAILURE", "AI_SESSION_ID"]:
            os.environ.pop(key, None)

    def build_orchestrator(self) -> BrainOrchestrator:
        return BrainOrchestrator(
            BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
        )

    def test_node_unavailable_triggers_explicit_fallback(self) -> None:
        os.environ["NODE_BIN"] = "definitely-missing-node-binary"
        orchestrator = self.build_orchestrator()
        response = orchestrator.run("analise package.json")
        self.assertIn("Modo fallback ativo", response)
        self.assertEqual(orchestrator.last_runtime_mode, "fallback")

    def test_mock_runtime_mode_is_explicit(self) -> None:
        os.environ["OMINI_RUNTIME_MODE"] = "mock"
        orchestrator = self.build_orchestrator()
        response = orchestrator.run("qualquer coisa")
        self.assertIn("Modo mock ativo", response)
        self.assertEqual(orchestrator.last_runtime_mode, "mock")

    def test_checkpoint_store_save_failure_does_not_raise(self) -> None:
        store = CheckpointStore(PROJECT_ROOT)
        with patch("pathlib.Path.write_text", side_effect=PermissionError("denied")):
            saved_path = store.save("fase3-checkpoint", {"status": "blocked"})
        self.assertTrue(str(saved_path).endswith("fase3-checkpoint.json"))

    def test_patch_set_manager_apply_failure_returns_descriptive_error(self) -> None:
        temp_root = PROJECT_ROOT / ".phase9-temp" / f"fase3-io-{uuid4().hex[:8]}"
        shutil.rmtree(temp_root, ignore_errors=True)
        (temp_root / "pkg").mkdir(parents=True, exist_ok=True)
        (temp_root / "pkg" / "mod.py").write_text("VALUE = 1\n", encoding="utf-8")
        try:
            patch_set = build_patch_set(
                workspace_root=temp_root,
                file_updates=[{"file_path": "pkg/mod.py", "new_content": "VALUE = 2\n"}],
            )
            with patch("brain.runtime.patch_set_manager.apply_patch", side_effect=OSError("disk full")):
                result = apply_patch_set(workspace_root=temp_root, patch_set=patch_set)
            self.assertFalse(result["ok"])
            self.assertIn("patch_set_apply_failed", result["error"])
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)

    def test_milestone_manager_ignores_malformed_state_entries(self) -> None:
        manager = MilestoneManager({"milestone_tree": {"milestones": ["bad", {"milestone_id": "m1", "title": "ok"}]}})
        state = manager.initialize_state()
        self.assertEqual(len(state["milestones"]), 1)


if __name__ == "__main__":
    unittest.main()
