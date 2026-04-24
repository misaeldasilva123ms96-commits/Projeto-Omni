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
        self.assertEqual(payload["provider_diagnostics"][0]["provider"], "openai")
        self.assertTrue(payload["provider_diagnostics"][0]["failed"])

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
