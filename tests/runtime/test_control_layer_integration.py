from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402


class ControlLayerIntegrationTest(unittest.TestCase):
    def build_orchestrator(self) -> BrainOrchestrator:
        os.environ["BASE_DIR"] = str(PROJECT_ROOT)
        os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
        return BrainOrchestrator(
            BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
        )

    def test_mutation_like_request_without_evidence_is_blocked_safely(self) -> None:
        session_id = "phase11-control-block"
        os.environ["AI_SESSION_ID"] = session_id
        orchestrator = self.build_orchestrator()

        response = orchestrator.run("edite o codigo e aplique uma mudanca ampla")

        self.assertIsInstance(response, str)
        self.assertTrue(response.strip())
        self.assertIn("Execucao bloqueada pela camada de controle", response)

        audit_path = PROJECT_ROOT / ".logs" / "fusion-runtime" / "execution-audit.jsonl"
        self.assertTrue(audit_path.exists())
        lines = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        matching = [
            entry
            for entry in lines
            if entry.get("session_id") == session_id
            and entry.get("event_type") in {"runtime.control.policy_block", "runtime.control.evidence_gate_block"}
        ]
        self.assertTrue(matching)


if __name__ == "__main__":
    unittest.main()
