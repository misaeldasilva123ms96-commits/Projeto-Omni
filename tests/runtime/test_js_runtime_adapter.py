from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.js_runtime_adapter import JSRuntimeAdapter  # noqa: E402
from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402
from config.secrets_manager import build_controlled_os_environ_base  # noqa: E402


class JSRuntimeAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = PROJECT_ROOT
        self.adapter = JSRuntimeAdapter(self.root)
        self.env_backup = {
            key: os.environ.get(key)
            for key in (
                "OMINI_JS_RUNTIME_BIN",
                "OMNI_JS_RUNTIME_BIN",
                "BUN_BIN",
                "OMNI_NODE_BIN",
                "OMINI_NODE_BIN",
                "NODE_BIN",
                "BASE_DIR",
                "PYTHON_BASE_DIR",
            )
        }
        os.environ["BASE_DIR"] = str(PROJECT_ROOT)
        os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")

    def tearDown(self) -> None:
        for key, value in self.env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_bun_available_still_defaults_to_node(self) -> None:
        with patch("brain.runtime.js_runtime_adapter.shutil.which", side_effect=lambda name: "C:/bun.exe" if name == "bun" else "C:/node.exe"):
            selection = self.adapter.select_runtime()

        self.assertEqual(selection.runtime_name, "node")
        self.assertEqual(selection.source, "node_default")
        self.assertTrue(selection.bun_available)
        self.assertFalse(selection.fallback_used)

    def test_bun_unavailable_uses_node_default(self) -> None:
        with patch("brain.runtime.js_runtime_adapter.shutil.which", side_effect=lambda name: None if name == "bun" else "C:/node.exe"):
            selection = self.adapter.select_runtime()

        self.assertEqual(selection.runtime_name, "node")
        self.assertEqual(selection.source, "node_default")
        self.assertFalse(selection.fallback_used)

    def test_canonical_node_bin_takes_precedence_over_legacy_alias(self) -> None:
        os.environ["OMNI_NODE_BIN"] = "canonical-missing-node"
        os.environ["NODE_BIN"] = "legacy-node"

        with patch("brain.runtime.js_runtime_adapter.shutil.which", return_value=None):
            selection = self.adapter.select_runtime()
            env, _ = self.adapter.build_env()

        self.assertEqual(selection.executable, "canonical-missing-node")
        self.assertEqual(selection.source, "node_missing")
        self.assertFalse(selection.node_available)
        self.assertEqual(env["NODE_BIN"], "canonical-missing-node")

    def test_canonical_omni_runtime_bin_takes_precedence_over_legacy_alias(self) -> None:
        os.environ["OMINI_JS_RUNTIME_BIN"] = "node"
        os.environ["OMNI_JS_RUNTIME_BIN"] = "bun"
        with patch("brain.runtime.js_runtime_adapter.shutil.which", side_effect=lambda name: f"C:/{name}.exe"):
            selection = self.adapter.select_runtime()

        self.assertEqual(selection.runtime_name, "bun")
        self.assertEqual(selection.source, "explicit_env")

    def test_legacy_omini_runtime_bin_alias_is_preserved(self) -> None:
        os.environ.pop("OMINI_JS_RUNTIME_BIN", None)
        os.environ.pop("OMNI_JS_RUNTIME_BIN", None)
        os.environ["OMINI_JS_RUNTIME_BIN"] = "node"
        with patch("brain.runtime.js_runtime_adapter.shutil.which", side_effect=lambda name: f"C:/{name}.exe"):
            selection = self.adapter.select_runtime()

        self.assertEqual(selection.runtime_name, "node")
        self.assertEqual(selection.source, "explicit_env")

    def test_bun_is_explicit_opt_in(self) -> None:
        os.environ["OMINI_JS_RUNTIME_BIN"] = "bun"
        with patch("brain.runtime.js_runtime_adapter.shutil.which", side_effect=lambda name: "C:/bun.exe" if name == "bun" else "C:/node.exe"):
            selection = self.adapter.select_runtime()

        self.assertEqual(selection.runtime_name, "bun")
        self.assertEqual(selection.source, "explicit_env")
        self.assertTrue(selection.preferred)

    def test_python_can_invoke_runtime_layer_successfully_via_selected_runtime(self) -> None:
        script = self.root / "js-runner" / "healthcheck.js"
        command, selection = self.adapter.build_command(script_path=script)
        env, _ = self.adapter.build_env()
        completed = subprocess.run(
            command,
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=30,
            env=env,
        )

        self.assertEqual(completed.returncode, 0)
        self.assertEqual(selection.runtime_name, env["OMINI_JS_RUNTIME"])
        self.assertEqual(selection.runtime_name, env["OMNI_JS_RUNTIME"])

    @unittest.skipUnless(os.name == "nt", "Windows-only Node subprocess environment guard")
    def test_controlled_env_synthesizes_windows_runtime_root_when_env_is_isolated(self) -> None:
        with patch.dict(os.environ, {"PATH": os.environ.get("PATH", "")}, clear=True):
            env = build_controlled_os_environ_base()

        self.assertIn("SystemRoot", env)
        self.assertIn("WINDIR", env)
        self.assertTrue(Path(env["SystemRoot"]).exists())

    def test_js_runtime_output_remains_compatible_with_python_expectations(self) -> None:
        orchestrator = BrainOrchestrator(
            BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
        )
        diagnostics = orchestrator._resolve_node_command_context(payload=json.dumps({"message": "oi", "history": [], "capabilities": [], "memory": {}, "session": {}}))

        self.assertIn("js_runtime", diagnostics)
        self.assertEqual(diagnostics["command"][1], str((PROJECT_ROOT / "js-runner" / "queryEngineRunner.js").resolve()))
        self.assertEqual(len(diagnostics["command"]), 2)

    def test_query_engine_runner_accepts_stdin_payload(self) -> None:
        script = self.root / "js-runner" / "queryEngineRunner.js"
        command, _ = self.adapter.build_command(script_path=script)
        env, _ = self.adapter.build_env()
        payload = json.dumps(
            {
                "message": "ola",
                "memory": {},
                "history": [],
                "summary": "",
                "capabilities": [],
                "session": {"session_id": "stdin-runtime-test"},
            },
            ensure_ascii=False,
        )
        completed = subprocess.run(
            command,
            input=payload,
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=30,
            env=env,
        )

        self.assertEqual(completed.returncode, 0)
        parsed = json.loads(completed.stdout)
        self.assertIsInstance(parsed.get("response"), str)
        self.assertTrue(parsed["response"].strip())

    def test_frontend_vite_workflow_remains_untouched(self) -> None:
        frontend_package = json.loads((PROJECT_ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
        scripts = frontend_package.get("scripts", {})

        self.assertEqual(scripts.get("dev"), "vite")
        self.assertEqual(scripts.get("build"), "vite build")


if __name__ == "__main__":
    unittest.main()
