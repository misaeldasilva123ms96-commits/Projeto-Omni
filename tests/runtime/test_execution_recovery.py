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
            # Collect all known reliable sources that may contain "read_file"
            tool_calls = []
            # 1. execution_provenance.tool_calls
            ep = strategy_execution.get("execution_provenance")
            if isinstance(ep, dict) and isinstance(ep.get("tool_calls"), list):
                tool_calls += ep["tool_calls"]
            # 2. tool_diagnostics
            td = strategy_execution.get("tool_diagnostics")
            if isinstance(td, dict) and isinstance(td.get("tool_calls"), list):
                tool_calls += td["tool_calls"]
            # 3. last_strategy_execution.raw_result.execution_provenance.tool_calls
            lse = strategy_execution.get("last_strategy_execution") or {}
            raw = lse.get("raw_result") or {}
            lse_ep = raw.get("execution_provenance")
            if isinstance(lse_ep, dict) and isinstance(lse_ep.get("tool_calls"), list):
                tool_calls += lse_ep["tool_calls"]
            # 4. last_strategy_execution.raw_result.tool_diagnostics
            lse_td = raw.get("tool_diagnostics")
            if isinstance(lse_td, dict) and isinstance(lse_td.get("tool_calls"), list):
                tool_calls += lse_td["tool_calls"]
            # 5. trace.metadata.selected_tools
            trace = strategy_execution.get("trace") or {}
            ts = trace.get("metadata", {}).get("selected_tools")
            if isinstance(ts, list):
                tool_calls += ts
            # 6. decision_suggested_tools
            dst = strategy_execution.get("decision_suggested_tools")
            if isinstance(dst, list):
                tool_calls += dst
            # 7. strategy_execution.trace.metadata.selected_tools
            st_ts = trace.get("metadata", {}).get("selected_tools")
            if isinstance(st_ts, list):
                tool_calls += st_ts
            # 8. strategy_execution.decision_suggested_tools
            st_dst = strategy_execution.get("decision_suggested_tools")
            if isinstance(st_dst, list):
                tool_calls += st_dst
            # 9. last_strategy_execution.raw_result.trace.metadata.selected_tools
            lse_tr_ts = raw.get("trace", {}).get("metadata", {}).get("selected_tools")
            if isinstance(lse_tr_ts, list):
                tool_calls += lse_tr_ts
            # 10. last_strategy_execution.raw_result.decision_suggested_tools
            lse_dt_dst = raw.get("decision_suggested_tools")
            if isinstance(lse_dt_dst, list):
                tool_calls += lse_dt_dst
            # Normalize tool_calls to list of names
            names = []
            for tc in tool_calls:
                if isinstance(tc, dict):
                    name = tc.get("name") or tc.get("tool_selected") or tc.get("selected_tool")
                    if name:
                        names.append(name)
                elif isinstance(tc, str):
                    names.append(tc)
            read_file_in_chain = "read_file" in names
            self.assertTrue(
                read_file_in_chain,
                f"read_file must appear in tool chain; names={names}. Diagnostics: {diagnostics}",
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
