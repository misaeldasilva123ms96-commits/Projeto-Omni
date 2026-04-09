from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402


class MemoryContextIntegrationTest(unittest.TestCase):
    def build_orchestrator(self) -> BrainOrchestrator:
        os.environ["BASE_DIR"] = str(PROJECT_ROOT)
        os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
        return BrainOrchestrator(
            BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
        )

    def test_mutation_request_records_memory_and_budget_signals(self) -> None:
        session_id = "phase13-memory-context"
        os.environ["AI_SESSION_ID"] = session_id
        orchestrator = self.build_orchestrator()

        response = orchestrator.run("edite o codigo em varios arquivos do repositorio e aplique uma mudanca ampla")

        self.assertIsInstance(response, str)
        self.assertTrue(response.strip())

        audit_path = PROJECT_ROOT / ".logs" / "fusion-runtime" / "execution-audit.jsonl"
        lines = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]

        budget_events = [
            entry
            for entry in lines
            if entry.get("session_id") == session_id
            and entry.get("event_type") == "runtime.context.budget_selected"
        ]
        self.assertTrue(budget_events)
        self.assertEqual(budget_events[-1].get("budget_level"), "high")

        retrieval_events = [
            entry
            for entry in lines
            if entry.get("session_id") == session_id
            and entry.get("event_type") == "runtime.context.retrieval_plan"
        ]
        self.assertTrue(retrieval_events)
        self.assertIn("working_memory", retrieval_events[-1].get("load_order", []))

        working_events = [
            entry
            for entry in lines
            if entry.get("session_id") == session_id
            and entry.get("event_type") == "runtime.memory.working_updated"
        ]
        self.assertTrue(working_events)

        decision_events = [
            entry
            for entry in lines
            if entry.get("session_id") == session_id
            and entry.get("event_type") == "runtime.memory.decision_recorded"
        ]
        self.assertTrue(decision_events)

        evidence_events = [
            entry
            for entry in lines
            if entry.get("session_id") == session_id
            and entry.get("event_type") == "runtime.memory.evidence_recorded"
        ]
        self.assertTrue(evidence_events)

        working_path = PROJECT_ROOT / ".logs" / "fusion-runtime" / "working-memory.json"
        decision_path = PROJECT_ROOT / ".logs" / "fusion-runtime" / "decision-memory.json"
        evidence_path = PROJECT_ROOT / ".logs" / "fusion-runtime" / "evidence-memory.json"
        self.assertTrue(working_path.exists())
        self.assertTrue(decision_path.exists())
        self.assertTrue(evidence_path.exists())


if __name__ == "__main__":
    unittest.main()
