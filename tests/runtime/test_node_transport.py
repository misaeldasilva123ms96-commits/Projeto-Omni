from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.node_transport import run_node_subprocess  # noqa: E402


def _diagnostics() -> dict[str, object]:
    return {
        "command": ["node", "runner.js"],
        "cwd": str(PROJECT_ROOT),
        "subprocess_env": {"BASE_DIR": str(PROJECT_ROOT)},
        "runner_path": "runner.js",
        "adapter_path": "adapter.js",
        "fusion_brain_path": "fusionBrain.js",
        "command_preview": ["node", "runner.js", "<payload:10 chars>"],
        "node_bin": "node",
        "node_resolved": "node",
        "typescript_direct_execution_detected": False,
        "typescript_candidates_exist": [],
        "compiled_runner_artifact_exists": True,
        "missing_paths": [],
        "env_preview": {"BASE_DIR": str(PROJECT_ROOT)},
        "runner_exists": True,
        "cwd_exists": True,
    }


class NodeTransportTest(unittest.TestCase):
    def test_transport_failure_is_separate_from_semantic_success(self) -> None:
        with patch("brain.runtime.node_transport.subprocess.run", side_effect=FileNotFoundError(2, "too large", None, 206, None)):
            result = run_node_subprocess(
                diagnostics=_diagnostics(),
                payload="{}",
                timeout_seconds=1,
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["stage"], "exception")
        self.assertEqual(result["reason_code"], "NODE_BRIDGE_NONZERO_EXIT")
        self.assertIsNone(result["parsed"])

    def test_transport_success_returns_parsed_payload_without_semantic_interpretation(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["node", "runner.js"],
            returncode=0,
            stdout='{"response":"Olá!","metadata":{"execution_provenance":{"execution_mode":"matcher_shortcut"}}}',
            stderr="",
        )
        with patch("brain.runtime.node_transport.subprocess.run", return_value=completed):
            result = run_node_subprocess(
                diagnostics=_diagnostics(),
                payload="{}",
                timeout_seconds=1,
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["reason_code"], "success")
        self.assertEqual(result["parsed"]["response"], "Olá!")
        self.assertEqual(result["parsed"]["metadata"]["execution_provenance"]["execution_mode"], "matcher_shortcut")

    def test_transport_empty_stdout_is_structured_failure(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["node", "runner.js"],
            returncode=0,
            stdout="",
            stderr="",
        )
        with patch("brain.runtime.node_transport.subprocess.run", return_value=completed):
            result = run_node_subprocess(
                diagnostics=_diagnostics(),
                payload="{}",
                timeout_seconds=1,
            )
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "NODE_BRIDGE_EMPTY_STDOUT")

    def test_transport_invalid_json_is_structured_failure(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["node", "runner.js"],
            returncode=0,
            stdout="{not-json",
            stderr="",
        )
        with patch("brain.runtime.node_transport.subprocess.run", return_value=completed):
            result = run_node_subprocess(
                diagnostics=_diagnostics(),
                payload="{}",
                timeout_seconds=1,
            )
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "NODE_BRIDGE_INVALID_JSON")


if __name__ == "__main__":
    unittest.main()
