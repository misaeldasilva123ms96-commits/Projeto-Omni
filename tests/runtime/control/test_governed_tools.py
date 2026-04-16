"""Phase 30.13 — governed tool registry, strict mode, and orchestrator wiring."""

from __future__ import annotations

import io
import json
import os
import shutil
import sys
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.control.cli import main as control_cli_main  # noqa: E402
from brain.runtime.control.governed_tools import (  # noqa: E402
    GOVERNED_TOOLS_STRICT_BLOCK_KIND,
    GovernedToolSpec,
    evaluate_tool_governance,
    get_governed_tool_metadata,
    is_governed_tool,
    is_strict_governed_tools_mode,
    list_governed_tools,
    register_governed_tool,
    reset_governed_tool_registry_for_tests,
    sync_governed_tools_from_trusted_executor_surface,
)
from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths, TRUSTED_EXECUTION_KNOWN_TOOLS  # noqa: E402


class GovernedToolsTest(unittest.TestCase):
    def setUp(self) -> None:
        # Restore default governed surface so test order does not leave an empty registry.
        sync_governed_tools_from_trusted_executor_surface(TRUSTED_EXECUTION_KNOWN_TOOLS, force=True)

    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-governed-tools"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"gov-tools-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def tearDown(self) -> None:
        os.environ.pop("OMINI_GOVERNED_TOOLS_STRICT", None)

    def test_decorator_registers_read_file_metadata(self) -> None:
        meta = get_governed_tool_metadata("read_file")
        self.assertIsNotNone(meta)
        self.assertIn(meta.policy_name, {"trusted_read", "trusted_execution_surface"})
        self.assertIn(meta.category, {"filesystem", "auto_registered"})

    def test_registry_helpers_coherent_after_surface_sync(self) -> None:
        reset_governed_tool_registry_for_tests()
        sync_governed_tools_from_trusted_executor_surface(TRUSTED_EXECUTION_KNOWN_TOOLS, force=True)
        names = {s.tool_name for s in list_governed_tools()}
        self.assertIn("read_file", names)
        self.assertIn("grep_search", names)
        self.assertNotIn("directory_tree", names)
        self.assertTrue(is_governed_tool("read_file"))
        self.assertFalse(is_governed_tool("directory_tree"))

    def test_non_strict_allows_ungoverned_trusted_legacy_tool(self) -> None:
        reset_governed_tool_registry_for_tests()
        sync_governed_tools_from_trusted_executor_surface(TRUSTED_EXECUTION_KNOWN_TOOLS, force=True)
        audit = evaluate_tool_governance(
            selected_tool="directory_tree",
            trusted_known_tools=set(TRUSTED_EXECUTION_KNOWN_TOOLS),
            strict_mode=False,
        )
        self.assertTrue(audit.allowed)
        self.assertFalse(audit.governed)
        self.assertTrue(audit.legacy_ungoverned_trusted)

    def test_strict_blocks_ungoverned_tool(self) -> None:
        reset_governed_tool_registry_for_tests()
        register_governed_tool(
            GovernedToolSpec(tool_name="read_file", policy_name="p", category="c", extensions={}),
            overwrite=True,
        )
        audit = evaluate_tool_governance(
            selected_tool="grep_search",
            trusted_known_tools=set(TRUSTED_EXECUTION_KNOWN_TOOLS),
            strict_mode=True,
        )
        self.assertFalse(audit.allowed)
        self.assertFalse(audit.governed)

    def test_strict_allows_empty_and_none_sentinel(self) -> None:
        reset_governed_tool_registry_for_tests()
        for name in ("", "none"):
            audit = evaluate_tool_governance(
                selected_tool=name,
                trusted_known_tools=set(TRUSTED_EXECUTION_KNOWN_TOOLS),
                strict_mode=True,
            )
            self.assertTrue(audit.allowed)

    def test_orchestrator_blocks_before_orchestration_in_strict_mode(self) -> None:
        with self.temp_workspace() as workspace_root:
            os.environ["BASE_DIR"] = str(workspace_root)
            os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
            orch = BrainOrchestrator(BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py"))
            reset_governed_tool_registry_for_tests()
            register_governed_tool(
                GovernedToolSpec(tool_name="read_file", policy_name="p", category="c", extensions={}),
                overwrite=True,
            )
            os.environ["OMINI_GOVERNED_TOOLS_STRICT"] = "true"
            out = orch._execute_single_action_core(
                action={"step_id": "s1", "selected_tool": "grep_search", "policy_decision": {}},
                step_results=[],
                semantic_retrieval=None,
                session_id="s",
                task_id="t",
                run_id="r",
                learning_guidance=None,
                operational_plan=None,
            )
            self.assertFalse(out.get("ok"))
            self.assertEqual(out.get("error_payload", {}).get("kind"), GOVERNED_TOOLS_STRICT_BLOCK_KIND)
            self.assertIsNone(out.get("orchestration"))

    def test_cli_list_governed_tools_json(self) -> None:
        reset_governed_tool_registry_for_tests()
        sync_governed_tools_from_trusted_executor_surface(TRUSTED_EXECUTION_KNOWN_TOOLS, force=True)
        stream = io.StringIO()
        with patch.object(sys, "argv", ["control-cli", "--root", str(PROJECT_ROOT), "list_governed_tools"]):
            with redirect_stdout(stream):
                code = control_cli_main()
        self.assertEqual(code, 0)
        payload = json.loads(stream.getvalue())
        self.assertEqual(payload["status"], "ok")
        self.assertIsInstance(payload.get("governed_tools"), list)
        self.assertGreaterEqual(len(payload["governed_tools"]), 1)

    def test_strict_mode_env_toggle(self) -> None:
        os.environ.pop("OMINI_GOVERNED_TOOLS_STRICT", None)
        self.assertFalse(is_strict_governed_tools_mode())
        os.environ["OMINI_GOVERNED_TOOLS_STRICT"] = "true"
        self.assertTrue(is_strict_governed_tools_mode())


if __name__ == "__main__":
    unittest.main()
