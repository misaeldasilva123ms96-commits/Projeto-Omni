from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.control.capability_router import CapabilityRouter  # noqa: E402
from brain.runtime.execution.manifest import build_execution_manifest  # noqa: E402
from brain.runtime.language.reasoning_contract import normalize_input_to_oil_request  # noqa: E402


class ExecutionManifestTest(unittest.TestCase):
    def test_manifest_builder_serializes_safe_shape(self) -> None:
        router = CapabilityRouter()
        routing = router.classify_task("rode os testes e valide")
        oil_request = normalize_input_to_oil_request(
            "rode os testes e valide",
            session_id="manifest-test",
            run_id="",
            metadata={"source_component": "test"},
        )
        result = build_execution_manifest(
            oil_request=oil_request,
            routing_decision=routing,
            selected_tools=["test_runner"],
            provider_path="openai",
        )
        self.assertFalse(result.fallback_triggered)
        self.assertIsNotNone(result.manifest)
        manifest = result.manifest.as_dict()
        self.assertEqual(manifest["intent"], oil_request.intent)
        self.assertEqual(manifest["provider_path"], "openai")
        self.assertEqual(manifest["selected_tools"], ["test_runner"])
        self.assertTrue(manifest["step_plan"])
        self.assertIn("summary_rationale", manifest)

    def test_unknown_tool_is_recorded_but_not_authorized(self) -> None:
        router = CapabilityRouter()
        routing = replace(router.classify_task("execute uma ferramenta"), requires_tools=True)
        oil_request = normalize_input_to_oil_request(
            "execute uma ferramenta",
            session_id="manifest-unknown-test",
            run_id="",
            metadata={"source_component": "test"},
        )
        result = build_execution_manifest(
            oil_request=oil_request,
            routing_decision=routing,
            selected_tools=["model_invented_tool"],
        )
        manifest = result.manifest.as_dict()
        self.assertEqual(manifest["selected_tools"], ["model_invented_tool"])
        self.assertEqual(manifest["metadata"]["authorized_selected_tools"], [])
        self.assertEqual(manifest["metadata"]["denied_unknown_tools"], ["model_invented_tool"])
        self.assertIn("unknown_tool_denied:model_invented_tool", manifest["safety_notes"])
        self.assertNotIn("use tool model_invented_tool", [step["description"] for step in manifest["step_plan"]])


if __name__ == "__main__":
    unittest.main()
