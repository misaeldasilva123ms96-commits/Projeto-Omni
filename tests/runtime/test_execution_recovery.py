from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYTHON_ROOT = PROJECT_ROOT / "backend" / "python"
MAIN_PY = PYTHON_ROOT / "main.py"
PACKAGE_JSON = PROJECT_ROOT / "package.json"
ENV_KEYS_TO_CLEAR = (
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "VITE_SUPABASE_URL",
    "VITE_SUPABASE_ANON_KEY",
    "VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GROQ_API_KEY",
    "GEMINI_API_KEY",
    "DEEPSEEK_API_KEY",
    "OLLAMA_URL",
    "OMNI_AVAILABLE_PROVIDERS",
    "BUN_INSTALL",
)

sys.path.insert(0, str(PYTHON_ROOT))

from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402


class ExecutionRecoveryTest(unittest.TestCase):
    def _prepare_isolated_runtime_env(self, session_id: str) -> tuple[dict[str, str], str]:
        previous_env = os.environ.copy()
        previous_cwd = os.getcwd()

        preserved = {
            key: os.environ[key]
            for key in ("PATH", "HOME", "LANG", "LC_ALL", "PYTHONPATH", "NODE_PATH")
            if key in os.environ and os.environ[key]
        }
        os.environ.clear()
        os.environ.update(preserved)
        os.environ.update(
            {
                "AI_SESSION_ID": session_id,
                "BASE_DIR": str(PROJECT_ROOT),
                "PYTHON_BASE_DIR": str(PYTHON_ROOT),
                "CI": "1",
            }
        )
        if "PYTHONPATH" not in os.environ:
            os.environ["PYTHONPATH"] = str(PYTHON_ROOT)
        for key in ENV_KEYS_TO_CLEAR:
            os.environ.pop(key, None)
        os.chdir(PROJECT_ROOT)
        return previous_env, previous_cwd

    def _restore_runtime_env(self, previous_env: dict[str, str], previous_cwd: str) -> None:
        os.chdir(previous_cwd)
        os.environ.clear()
        os.environ.update(previous_env)

    def _diagnostics(
        self,
        *,
        response: str,
        inspection: dict,
        orchestrator: BrainOrchestrator,
    ) -> str:
        path_parts = [part for part in os.environ.get("PATH", "").split(os.pathsep) if part]
        return json.dumps(
            {
                "cwd": os.getcwd(),
                "repo_root": str(PROJECT_ROOT),
                "main_py": str(MAIN_PY),
                "package_json": str(PACKAGE_JSON),
                "AI_SESSION_ID": os.environ.get("AI_SESSION_ID", ""),
                "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
                "CI": os.environ.get("CI", ""),
                "BUN_INSTALL": os.environ.get("BUN_INSTALL", ""),
                "NODE_PATH": os.environ.get("NODE_PATH", ""),
                "PATH_summary": {
                    "entries": len(path_parts),
                    "first_entries": path_parts[:5],
                },
                "response_first3000": str(response)[:3000],
                "inspection": inspection,
                "last_strategy_execution": getattr(orchestrator, "last_strategy_execution", None),
                "last_runtime_mode": getattr(orchestrator, "last_runtime_mode", None),
                "last_runtime_reason": getattr(orchestrator, "last_runtime_reason", None),
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    def test_tool_capable_prompt_uses_real_primary_execution_path(self) -> None:
        previous_env, previous_cwd = self._prepare_isolated_runtime_env(
            f"execution-recovery-{uuid4().hex[:8]}"
        )
        try:
            orchestrator = BrainOrchestrator(BrainPaths.from_entrypoint(MAIN_PY))
            with patch.object(BrainOrchestrator, "_answer_from_memory", return_value=""):
                response = orchestrator.run("analise o arquivo package.json")
            inspection = orchestrator.last_cognitive_runtime_inspection or {}
            diagnostics = self._diagnostics(
                response=response,
                inspection=inspection,
                orchestrator=orchestrator,
            )
            signals = inspection.get("signals", {})
            tool_execution = signals.get("tool_execution", {})
            strategy_execution = orchestrator.last_strategy_execution or {}

            self.assertTrue(PACKAGE_JSON.is_file(), diagnostics)
            self.assertTrue(response.strip(), diagnostics)
            self.assertNotEqual(inspection.get("runtime_mode"), "SAFE_FALLBACK", diagnostics)
            self.assertEqual(inspection.get("runtime_mode"), "FULL_COGNITIVE_RUNTIME", diagnostics)
            self.assertEqual(inspection.get("runtime_reason"), "node_execution_request", diagnostics)
            self.assertEqual(signals.get("execution_path_used"), "node_execution", diagnostics)
            self.assertFalse(signals.get("fallback_triggered", True), diagnostics)
            self.assertEqual(signals.get("transport_status"), "success", diagnostics)
            self.assertTrue(tool_execution.get("tool_requested"), diagnostics)
            self.assertTrue(tool_execution.get("tool_attempted"), diagnostics)
            self.assertTrue(tool_execution.get("tool_succeeded"), diagnostics)
            self.assertEqual(strategy_execution["execution_runtime_lane"], "true_action_execution", diagnostics)
            self.assertFalse(strategy_execution["compatibility_execution_active"], diagnostics)
            self.assertEqual(strategy_execution["execution_path_used"], "node_execution", diagnostics)
            # Accept tool chains that include read_file (CI uses chains like ["glob_search", "read_file"])
            # Try multiple paths to find tool_calls
            tool_calls = []
            td = strategy_execution.get("tool_diagnostics")
            if isinstance(td, dict):
                tool_calls = td.get("tool_calls") or []
            elif isinstance(td, list):
                # tool_diagnostics is a list directly
                tool_calls = td
            ep = strategy_execution.get("execution_provenance")
            if isinstance(ep, dict):
                tool_calls = tool_calls or ep.get("tool_calls") or []
            lse = strategy_execution.get("last_strategy_execution") or {}
            raw = lse.get("raw_result") or {}
            lse_td = raw.get("tool_diagnostics")
            if isinstance(lse_td, dict):
                tool_calls = tool_calls or lse_td.get("tool_calls") or []
            elif isinstance(lse_td, list):
                tool_calls = tool_calls or lse_td
            lse_ep = raw.get("execution_provenance")
            if isinstance(lse_ep, dict):
                tool_calls = tool_calls or lse_ep.get("tool_calls") or []
            read_file_in_chain = any(
                (isinstance(tc, dict) and tc.get("name") == "read_file") or (isinstance(tc, str) and tc == "read_file")
                for tc in (tool_calls if isinstance(tool_calls, list) else [])
            )
            self.assertTrue(
                read_file_in_chain,
                f"read_file must appear in tool chain; tool_calls={tool_calls}. Diagnostics: {diagnostics}",
            )
        finally:
            self._restore_runtime_env(previous_env, previous_cwd)

    def test_primary_local_tool_path_executes_real_read_file(self) -> None:
        os.environ["BASE_DIR"] = str(PROJECT_ROOT)
        os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
        orchestrator = BrainOrchestrator(
            BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
        )
        payload = orchestrator._execute_primary_local_tool_path(
            session_id="local-tool-recovery",
            runtime_message="leia o arquivo package.json",
            predicted_intent="inspect",
            selected_tools=["read_file"],
        )
        self.assertTrue(str(payload.get("response", "")).strip())
        self.assertEqual(payload.get("execution_runtime_lane"), "local_tool_execution")
        tool_execution = payload.get("tool_execution", {})
        self.assertTrue(tool_execution.get("tool_requested"))
        self.assertEqual(tool_execution.get("tool_selected"), "read_file")
        self.assertTrue(tool_execution.get("tool_attempted"))
        self.assertTrue(tool_execution.get("tool_succeeded"))


if __name__ == "__main__":
    unittest.main()
