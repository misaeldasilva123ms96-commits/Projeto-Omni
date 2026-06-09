from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYTHON_MAIN_PATH = PROJECT_ROOT / "backend" / "python" / "main.py"
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))


def _load_python_main_module():
    spec = importlib.util.spec_from_file_location("omni_python_main_test", PYTHON_MAIN_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load python main module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BridgePipelineTest(unittest.TestCase):
    def test_session_byok_bridge_extracts_private_overlay(self) -> None:
        from brain.runtime.session_helpers import extract_session_byok_bridge as _extract_session_byok_bridge

        state = _extract_session_byok_bridge(
            {
                "client_context": {
                    "provider_preference": " OpenAI ",
                    "session_provider_credentials": {
                        "openai": {
                            "api_key": "test-byok-key",
                            "model": "gpt-4o-mini",
                        }
                    },
                }
            }
        )
        preference = state["provider"]
        overlay = state["env_overlay"]

        self.assertEqual(preference, "openai")
        self.assertEqual(overlay["OPENAI_API_KEY"], "test-byok-key")
        self.assertEqual(overlay["OPENAI_MODEL"], "gpt-4o-mini")
        self.assertTrue(state["active"])
        self.assertIsNone(state["error_reason"])

    def test_session_byok_bridge_rejects_deepseek_and_control_chars(self) -> None:
        from brain.runtime.session_helpers import extract_session_byok_bridge as _extract_session_byok_bridge

        state = _extract_session_byok_bridge(
            {
                "provider_preference": "deepseek",
                "session_provider_credentials": {
                    "deepseek": {"api_key": "test-deepseek-key"},
                    "openai": {"api_key": "bad\u0000key"},
                },
            }
        )

        self.assertIsNone(state["provider"])
        self.assertEqual(state["env_overlay"], {})
        self.assertEqual(state["error_reason"], "byok_provider_not_allowed")

    def test_session_byok_requires_matching_provider_preference(self) -> None:
        from brain.runtime.session_helpers import extract_session_byok_bridge as _extract_session_byok_bridge

        missing_preference = _extract_session_byok_bridge(
            {"session_provider_credentials": {"openai": {"api_key": "test-byok-key"}}}
        )
        self.assertEqual(missing_preference["error_reason"], "byok_provider_preference_required")

        mismatch = _extract_session_byok_bridge(
            {
                "provider_preference": "openai",
                "session_provider_credentials": {"groq": {"api_key": "test-groq-key"}},
            }
        )
        self.assertEqual(mismatch["error_reason"], "byok_credentials_missing_for_provider")

    def test_session_byok_requires_cloud_api_key(self) -> None:
        from brain.runtime.session_helpers import extract_session_byok_bridge as _extract_session_byok_bridge

        state = _extract_session_byok_bridge(
            {
                "provider_preference": "openai",
                "session_provider_credentials": {"openai": {"model": "gpt-4o-mini"}},
            }
        )

        self.assertEqual(state["error_reason"], "byok_credentials_incomplete")

    def test_session_byok_overlay_is_private_node_env_only(self) -> None:
        from types import SimpleNamespace

        from brain.runtime.orchestrator import BrainOrchestrator

        orchestrator = BrainOrchestrator.__new__(BrainOrchestrator)
        orchestrator.js_runtime_adapter = SimpleNamespace(
            build_env=lambda: ({"BASE_DIR": "project"}, SimpleNamespace(runtime_name="node")),
            select_runtime=lambda: SimpleNamespace(runtime_name="node", node_available=True, executable="node"),
        )
        orchestrator._pending_policy_hint_json = None
        orchestrator._session_byok_active = True
        orchestrator._session_provider_preference = "openai"
        orchestrator._session_provider_env_overlay = {
            "OPENAI_API_KEY": "test-byok-key",
            "OPENAI_MODEL": "gpt-4o-mini",
        }

        env = orchestrator._build_node_subprocess_env()

        self.assertEqual(env["OPENAI_API_KEY"], "test-byok-key")
        self.assertEqual(env["OPENAI_MODEL"], "gpt-4o-mini")
        self.assertEqual(env["OMNI_BYOK_SESSION_MODE"], "true")
        self.assertEqual(env["OMNI_BYOK_PROVIDER"], "openai")
        self.assertEqual(env["OMNI_BYOK_FAIL_CLOSED"], "true")
        self.assertIn('"recommended_provider": "openai"', env["OMNI_POLICY_HINT_JSON"])

    def test_session_byok_overlay_does_not_leak_across_requests(self) -> None:
        from types import SimpleNamespace

        from brain.runtime.orchestrator import BrainOrchestrator

        orchestrator = BrainOrchestrator.__new__(BrainOrchestrator)
        orchestrator.js_runtime_adapter = SimpleNamespace(
            build_env=lambda: ({"BASE_DIR": "project", "OPENAI_API_KEY": "system-key"}, SimpleNamespace(runtime_name="node")),
            select_runtime=lambda: SimpleNamespace(runtime_name="node", node_available=True, executable="node"),
        )
        orchestrator._pending_policy_hint_json = None

        orchestrator._session_byok_active = True
        orchestrator._session_provider_preference = "openai"
        orchestrator._session_provider_env_overlay = {"OPENAI_API_KEY": "test-byok-key-a"}
        env_a = orchestrator._build_node_subprocess_env()

        orchestrator._session_byok_active = False
        orchestrator._session_provider_preference = None
        orchestrator._session_provider_env_overlay = {}
        orchestrator._pending_policy_hint_json = None
        env_b = orchestrator._build_node_subprocess_env()

        self.assertEqual(env_a["OPENAI_API_KEY"], "test-byok-key-a")
        self.assertEqual(env_b["OPENAI_API_KEY"], "system-key")
        self.assertNotIn("OMNI_BYOK_SESSION_MODE", env_b)

    def test_session_byok_overlay_only_selected_provider_and_does_not_mutate_environ(self) -> None:
        from types import SimpleNamespace

        from brain.runtime.orchestrator import BrainOrchestrator

        original_openai = os.environ.get("OPENAI_API_KEY")
        original_groq = os.environ.get("GROQ_API_KEY")
        orchestrator = BrainOrchestrator.__new__(BrainOrchestrator)
        orchestrator.js_runtime_adapter = SimpleNamespace(
            build_env=lambda: (
                {
                    "BASE_DIR": "project",
                    "GROQ_API_KEY": "test-system-groq-key",
                    "OPENROUTER_API_KEY": "test-system-openrouter-key",
                    "OPENAI_API_KEY": "test-system-openai-key",
                },
                SimpleNamespace(runtime_name="node"),
            ),
            select_runtime=lambda: SimpleNamespace(runtime_name="node", node_available=True, executable="node"),
        )
        orchestrator._pending_policy_hint_json = None
        orchestrator._session_byok_active = True
        orchestrator._session_provider_preference = "openai"
        orchestrator._session_provider_env_overlay = {
            "OPENAI_API_KEY": "sk-test-byok-session-openai",
            "OPENAI_MODEL": "byok-test-model",
        }

        env = orchestrator._build_node_subprocess_env()
        serialized = json.dumps(env, sort_keys=True)

        self.assertEqual(env["OPENAI_API_KEY"], "sk-test-byok-session-openai")
        self.assertEqual(env["OPENAI_MODEL"], "byok-test-model")
        self.assertEqual(env["GROQ_API_KEY"], "test-system-groq-key")
        self.assertEqual(env["OPENROUTER_API_KEY"], "test-system-openrouter-key")
        self.assertNotIn("sk-test-system-openai", serialized)
        self.assertEqual(os.environ.get("OPENAI_API_KEY"), original_openai)
        self.assertEqual(os.environ.get("GROQ_API_KEY"), original_groq)

    def test_session_byok_invalid_bridge_returns_public_safe_reason(self) -> None:
        from brain.runtime.session_helpers import extract_session_byok_bridge as _extract_session_byok_bridge

        state = _extract_session_byok_bridge(
            {
                "provider_preference": "openai",
                "session_provider_credentials": {
                    "groq": {
                        "api_key": "sk-test-byok-session-openai",
                        "model": "byok-test-model",
                    }
                },
            }
        )
        serialized = json.dumps(state, sort_keys=True)

        self.assertTrue(state["active"])
        self.assertEqual(state["provider"], "openai")
        self.assertEqual(state["env_overlay"], {})
        self.assertEqual(state["error_reason"], "byok_credentials_missing_for_provider")
        self.assertNotIn("sk-test-byok-session-openai", serialized)
        self.assertNotIn("byok-test-model", serialized)

    def test_runner_smoke_diagnostic_exposes_only_safe_fields(self) -> None:
        from types import SimpleNamespace

        import brain.runtime.orchestrator as orchestrator_module
        from brain.runtime.orchestrator import BrainOrchestrator

        captured_env = {}

        def fake_transport(*, diagnostics, payload, timeout_seconds):
            captured_env.update(diagnostics["subprocess_env"])
            return {
                "ok": True,
                "stage": "completed",
                "reason_code": "success",
                "returncode": 0,
                "stdout": "sk-test-secret Authorization raw response stack trace",
                "stderr": "traceback",
                "parsed": {
                    "response": "OK",
                    "metadata": {"engine_mode": "fusion_authority"},
                },
            }

        orchestrator = BrainOrchestrator.__new__(BrainOrchestrator)
        orchestrator.paths = SimpleNamespace(root=PROJECT_ROOT)
        orchestrator._resolve_node_command_context = lambda payload: {
            "js_runtime": {"runtime_name": "node"},
            "cwd": str(PROJECT_ROOT),
            "runner_exists": True,
            "adapter_exists": True,
            "fusion_brain_exists": True,
            "subprocess_env": {
                "BASE_DIR": str(PROJECT_ROOT),
                "OPENAI_API_KEY": "sk-test-secret",
                "GEMINI_API_KEY": "gemini-secret",
                "OLLAMA_URL": "http://local.invalid",
            },
        }

        with patch.object(orchestrator_module, "run_node_subprocess", side_effect=fake_transport):
            payload = orchestrator.build_runner_smoke_diagnostic(timeout_seconds=3)

        self.assertEqual(
            set(payload),
            {
                "status",
                "selected_runtime",
                "cwd_label",
                "runner_exists",
                "adapter_exists",
                "fusion_brain_exists",
                "contract_exists",
                "runner_exit_code",
                "stdout_json_valid",
                "result_degraded",
                "public_failure_class",
                "public_summary",
            },
        )
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["selected_runtime"], "node")
        self.assertTrue(payload["stdout_json_valid"])
        self.assertFalse(payload["result_degraded"])
        self.assertNotIn("OPENAI_API_KEY", captured_env)
        self.assertNotIn("GEMINI_API_KEY", captured_env)
        self.assertNotIn("OLLAMA_URL", captured_env)

        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("sk-test-secret", serialized)
        self.assertNotIn("gemini-secret", serialized)
        self.assertNotIn("Authorization", serialized)
        self.assertNotIn("raw response", serialized)
        self.assertNotIn("traceback", serialized)

    def test_sanitize_for_user_keeps_structured_error(self) -> None:
        module = _load_python_main_module()
        out = module.sanitize_for_user(
            {
                "response": "",
                "error": {
                    "failure_class": "NODE_BRIDGE_INVALID_JSON",
                    "message": "node stdout was malformed",
                },
            }
        )
        self.assertEqual(out["response"], module.USER_FALLBACK_RESPONSE)
        self.assertEqual(out["error"]["failure_class"], "NODE_BRIDGE_INVALID_JSON")

    def test_emit_public_json_writes_single_valid_json_object(self) -> None:
        module = _load_python_main_module()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = module.emit_public_json({"response": "ok", "stop_reason": "done"})
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["response"], "ok")
        self.assertEqual(payload["stop_reason"], "done")

    def test_main_adds_provider_diagnostics_from_inspection_signals(self) -> None:
        script = (
            "import importlib.util, json, sys\n"
            f"sys.path.insert(0, r'{PROJECT_ROOT / 'backend' / 'python'}')\n"
            f"spec = importlib.util.spec_from_file_location('omni_python_main_exec_diag', r'{PYTHON_MAIN_PATH}')\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(module)\n"
            "module.resolve_entry_message = lambda: ('ola', {})\n"
            "module.apply_bridge_env = lambda bridge: None\n"
            "module.get_available_providers = lambda: ['openai']\n"
            "class _OkOrchestrator:\n"
            "    def __init__(self, *a, **k):\n"
            "        self.last_cognitive_runtime_inspection = {\n"
            "            'runtime_mode': 'PROVIDER_FAILURE',\n"
            "            'signals': {\n"
            "                'provider_actual': 'openai',\n"
            "                'provider_failed': True,\n"
            "                'failure_class': 'provider_timeout',\n"
            "                'provider_diagnostics': [\n"
            "                    {\n"
            "                        'provider': 'openai',\n"
            "                        'configured': True,\n"
            "                        'available': True,\n"
            "                        'selected': True,\n"
            "                        'attempted': True,\n"
            "                        'succeeded': False,\n"
            "                        'failed': True,\n"
            "                        'failure_class': 'provider_timeout',\n"
            "                        'failure_reason': 'request timed out',\n"
            "                        'latency_ms': 321,\n"
            "                    }\n"
            "                ],\n"
            "            },\n"
            "        }\n"
            "    def run(self, *a, **k):\n"
            "        return {'response': 'provider failed'}\n"
            "module.BrainOrchestrator = _OkOrchestrator\n"
            "raise SystemExit(module.main())\n"
        )
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["provider_actual"], "openai")
        self.assertTrue(payload["provider_failed"])
        self.assertEqual(payload["failure_class"], "provider_timeout")
        diagnostics = payload["provider_diagnostics"]
        snapshot = payload["provider_diagnostics_snapshot"]
        self.assertIsInstance(diagnostics, list)
        self.assertIsInstance(snapshot, dict)
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual([item["provider"] for item in diagnostics], ["openai"])
        self.assertIsInstance(snapshot["providers"], list)
        self.assertEqual(
            snapshot["fallback_chain"],
            ["groq", "openrouter", "openai", "anthropic", "gemini", "ollama", "lmstudio", "local-heuristic"],
        )
        self.assertEqual(snapshot["active_provider"], "openai")
        self.assertIsInstance(snapshot["active_provider"], str)
        self.assertIsInstance(snapshot["fallback_triggered"], bool)
        self.assertIsNone(snapshot["fallback_reason"])
        self.assertEqual(diagnostics[0]["provider"], "openai")
        self.assertIn("configured", diagnostics[0])
        self.assertIn("available", diagnostics[0])
        self.assertIn("selected", diagnostics[0])
        self.assertIn("attempted", diagnostics[0])
        self.assertIn("succeeded", diagnostics[0])
        self.assertIn("failed", diagnostics[0])
        self.assertTrue(diagnostics[0]["failed"])
        openai = next(item for item in snapshot["providers"] if item["id"] == "openai")
        self.assertEqual(openai["provider"], "openai")
        self.assertTrue(openai["failed"])
        provider_ids = {item["id"] for item in snapshot["providers"]}
        self.assertEqual(provider_ids, {"groq", "openrouter", "openai", "anthropic", "gemini", "deepseek", "ollama", "lmstudio"})
        rows = {item["id"]: item for item in snapshot["providers"]}
        self.assertTrue(rows["deepseek"]["registered"])
        self.assertFalse(rows["deepseek"]["adapter_implemented"])
        self.assertFalse(rows["deepseek"]["executable"])
        self.assertEqual(rows["deepseek"]["execution_status"], "unsupported")
        self.assertIn(rows["ollama"]["execution_status"], {"local_config_gated", "active"})
        self.assertIn(rows["lmstudio"]["execution_status"], {"local_config_gated", "active"})
        serialized_diagnostics = json.dumps(diagnostics, sort_keys=True)
        serialized_snapshot = json.dumps(snapshot, sort_keys=True)
        for forbidden in (
            "sk-test",
            "matrix-key",
            "Authorization",
            "x-api-key",
            "raw request",
            "raw response",
            "stack trace",
            "traceback",
            "http://127.0.0.1",
        ):
            self.assertNotIn(forbidden, serialized_diagnostics)
            self.assertNotIn(forbidden, serialized_snapshot)

    def test_main_uses_attempted_provider_separately_from_actual_provider(self) -> None:
        script = (
            "import importlib.util, json, sys\n"
            f"sys.path.insert(0, r'{PROJECT_ROOT / 'backend' / 'python'}')\n"
            f"spec = importlib.util.spec_from_file_location('omni_python_main_provider_args', r'{PYTHON_MAIN_PATH}')\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(module)\n"
            "module.resolve_entry_message = lambda: ('ola', {})\n"
            "module.apply_bridge_env = lambda bridge: None\n"
            "module.sanitize_for_user = lambda raw: raw\n"
            "module.get_available_providers = lambda: ['openai', 'groq']\n"
            "module.emit_public_json = lambda payload: 0\n"
            "class _OkOrchestrator:\n"
            "    def __init__(self, *a, **k):\n"
            "        self.last_cognitive_runtime_inspection = {\n"
            "            'runtime_mode': 'PROVIDER_FAILURE',\n"
            "            'signals': {\n"
            "                'provider_actual': 'groq',\n"
            "                'provider_failed': True,\n"
            "                'failure_class': 'provider_timeout',\n"
            "            },\n"
            "        }\n"
            "    def run(self, *a, **k):\n"
            "        return {\n"
            "            'response': 'provider failed',\n"
            "            'provider_actual': 'groq',\n"
            "            'provider_attempted': 'openai',\n"
            "            'provider_failed': True,\n"
            "            'fallback_triggered': True,\n"
            "            'failure_class': 'provider_timeout',\n"
            "            'provider_diagnostics': None,\n"
            "        }\n"
            "captured = {}\n"
            "def _capture_provider_diag(**kwargs):\n"
            "    captured.update(kwargs)\n"
            "    return [\n"
            "        {\n"
            "            'provider': kwargs.get('attempted_provider') or '',\n"
            "            'selected': kwargs.get('selected_provider') == kwargs.get('attempted_provider'),\n"
            "            'attempted': True,\n"
            "            'failed': bool(kwargs.get('failure_class')),\n"
            "            'actual': kwargs.get('actual_provider') or '',\n"
            "        }\n"
            "    ]\n"
            "module.describe_provider_diagnostics_snapshot = _capture_provider_diag\n"
            "module.BrainOrchestrator = _OkOrchestrator\n"
            "module.main()\n"
            "print(json.dumps(captured))\n"
        )
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0)
        captured = json.loads(completed.stdout.strip().splitlines()[-1])
        self.assertEqual(captured["actual_provider"], "groq")
        self.assertEqual(captured["attempted_provider"], "openai")
        self.assertEqual(captured["failure_class"], "provider_timeout")
        self.assertTrue(captured["fallback_triggered"])
        self.assertEqual(captured["selected_provider"], "groq")

    def test_python_main_structured_error_on_orchestrator_failure(self) -> None:
        script = (
            "import importlib.util, json, sys\n"
            f"sys.path.insert(0, r'{PROJECT_ROOT / 'backend' / 'python'}')\n"
            f"spec = importlib.util.spec_from_file_location('omni_python_main_exec', r'{PYTHON_MAIN_PATH}')\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(module)\n"
            "module.resolve_entry_message = lambda: ('ola', {})\n"
            "module.apply_bridge_env = lambda bridge: None\n"
            "module.get_available_providers = lambda: ['openai']\n"
            "class _BrokenOrchestrator:\n"
            "    def __init__(self, *a, **k):\n"
            "        pass\n"
            "    def run(self, *a, **k):\n"
            "        raise RuntimeError('boom')\n"
            "module.BrainOrchestrator = _BrokenOrchestrator\n"
            "try:\n"
            "    raise SystemExit(module.main())\n"
            "except SystemExit:\n"
            "    raise\n"
            "except Exception:\n"
            "    import logging\n"
            "    logging.exception('Unhandled exception in main execution path')\n"
            "    module.emit_public_json({\n"
            "        'response': module.USER_FALLBACK_RESPONSE,\n"
            "        'stop_reason': 'python_main_exception',\n"
            "        'error': module.build_public_error(\n"
            "            failure_class='PYTHON_BRIDGE_NONZERO_EXIT',\n"
            "            message='Python main raised an unhandled exception before completing the public response.',\n"
            "        ),\n"
            "        'cognitive_runtime_inspection': {\n"
            "            'execution_tier': 'technical_fallback',\n"
            "            'layer': 'python_main',\n"
            "            'reason': 'unhandled_exception',\n"
            "        },\n"
            "    })\n"
            "    sys.exit(1)\n"
        )
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 1)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["stop_reason"], "python_main_exception")
        self.assertEqual(payload["error"]["failure_class"], "PYTHON_BRIDGE_NONZERO_EXIT")

    def test_python_main_sanitizer_marks_empty_string_as_shape_mismatch(self) -> None:
        module = _load_python_main_module()
        out = module.sanitize_for_user("")
        self.assertEqual(out["error"]["failure_class"], "FRONTEND_RESPONSE_SHAPE_MISMATCH")
        self.assertEqual(out["response"], module.USER_FALLBACK_RESPONSE)


if __name__ == "__main__":
    unittest.main()
