from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.control.capability_router import CapabilityRouter  # noqa: E402
from brain.runtime.execution.manifest import build_execution_manifest  # noqa: E402
from brain.runtime.language.reasoning_contract import normalize_input_to_oil_request  # noqa: E402
from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402
from brain.runtime.reasoning.reasoning_engine import ReasoningEngine  # noqa: E402


DATASET_PATH = PROJECT_ROOT / "tests" / "cognitive" / "decision_dataset.yaml"


class DecisionQualityDatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.router = CapabilityRouter()
        cls.reasoner = ReasoningEngine()
        cls.workspace_root = Path(tempfile.mkdtemp(prefix="omni-phase9-", dir=str(PROJECT_ROOT / ".logs")))
        cls._old_base_dir = os.environ.get("BASE_DIR")
        cls._old_python_base_dir = os.environ.get("PYTHON_BASE_DIR")
        os.environ["BASE_DIR"] = str(cls.workspace_root)
        os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
        cls.orchestrator = BrainOrchestrator(
            BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
        )

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._old_base_dir is None:
            os.environ.pop("BASE_DIR", None)
        else:
            os.environ["BASE_DIR"] = cls._old_base_dir
        if cls._old_python_base_dir is None:
            os.environ.pop("PYTHON_BASE_DIR", None)
        else:
            os.environ["PYTHON_BASE_DIR"] = cls._old_python_base_dir
        shutil.rmtree(cls.workspace_root, ignore_errors=True)

    def _load_cases(self) -> list[dict[str, object]]:
        return json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    def test_curated_dataset_decisions_match_expected_routes(self) -> None:
        for case in self._load_cases():
            with self.subTest(case=case["name"]):
                metadata = dict(case.get("metadata") or {})
                expected = dict(case["expected"])
                message = str(case["input"])

                routing = self.router.classify_task(message, metadata=metadata)
                self.assertEqual(routing.strategy, expected["strategy"])
                self.assertEqual(routing.must_execute, bool(expected.get("must_execute", False)))
                if "requires_node_runtime" in expected:
                    self.assertEqual(routing.requires_node_runtime, bool(expected["requires_node_runtime"]))
                self.assertTrue(routing.reasoning)
                self.assertTrue(routing.decision_reason_codes)

                reasoning = self.reasoner.reason(
                    raw_input=message,
                    session_id="decision-dataset",
                    run_id="",
                    source_component="test.cognitive",
                )
                handoff = dict(reasoning.execution_handoff)
                suggested_capabilities = list(handoff.get("suggested_capabilities", []))

                expected_tool = str(expected.get("tool") or "").strip()
                if expected_tool:
                    self.assertIn(expected_tool, suggested_capabilities)
                elif routing.strategy == "DIRECT_RESPONSE" and not bool(expected.get("must_execute", False)):
                    self.assertEqual(suggested_capabilities, [])

                manifest_result = build_execution_manifest(
                    oil_request=reasoning.oil_request,
                    routing_decision=routing,
                    strategy_payload={},
                    selected_tools=suggested_capabilities,
                    provider_path="",
                )
                manifest_payload = manifest_result.manifest.as_dict() if manifest_result.manifest is not None else {}
                primary_execution_type = self.orchestrator._select_primary_execution_type(
                    routing_decision=routing,
                    upgrade_artifacts={
                        "manifest": manifest_payload,
                        "oil_summary": {"intent": reasoning.oil_request.intent},
                    },
                    selected_tools=suggested_capabilities,
                    direct_response="",
                )
                self.assertEqual(primary_execution_type, expected["primary_execution_type"])
                if bool(expected.get("must_execute", False)):
                    self.assertNotEqual(primary_execution_type, "COMPATIBILITY_EXECUTION")


if __name__ == "__main__":
    unittest.main()
