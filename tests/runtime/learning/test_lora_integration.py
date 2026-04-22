from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.control.capability_router import CapabilityRouter  # noqa: E402
from brain.runtime.learning import LoRADecisionEngine, LoRAInferenceEngine, LoRARouterAdapter  # noqa: E402


class LoRAIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.router = CapabilityRouter()
        self.inference = LoRAInferenceEngine(PROJECT_ROOT)
        self.adapter = LoRARouterAdapter(self.inference)
        self.engine = LoRADecisionEngine(self.inference, self.adapter)

    def test_inference_falls_back_when_adapter_missing(self) -> None:
        result = self.inference.generate_response("Teste", {})
        self.assertTrue(result.fallback)
        self.assertFalse(result.model_used)
        self.assertEqual(result.reason, "adapter_missing")

    def test_decision_engine_prefers_rule_when_model_not_needed(self) -> None:
        routing = self.router.classify_task("explique o manifest")
        result = self.engine.evaluate(
            message="explique o manifest",
            base_response="O manifest representa a execução de forma resumida e auditável.",
            oil_summary={"urgency": "medium"},
            routing_decision=routing,
            execution_manifest={"output_mode": "direct"},
        )
        self.assertEqual(result.decision_source, "rule")
        self.assertFalse(result.model_used)
        self.assertEqual(result.final_strategy, routing.strategy)

    def test_decision_engine_uses_model_signal_when_available(self) -> None:
        routing = self.router.classify_task("talvez refine a resposta do runtime")
        with patch.object(self.inference, "adapter_available", return_value=True), patch.object(
            self.inference,
            "generate_response",
            return_value=type(
                "InferenceResult",
                (),
                {
                    "model_used": True,
                    "fallback": False,
                    "confidence": 0.71,
                    "text": "Resposta refinada com mais clareza e contexto operacional.",
                    "reason": "adapter_inference",
                    "dataset_origin": "omni-training/data/sft/omni_sft_seed.jsonl",
                    "as_dict": lambda self: {
                        "model_used": True,
                        "fallback": False,
                        "confidence": 0.71,
                        "text": "Resposta refinada com mais clareza e contexto operacional.",
                        "reason": "adapter_inference",
                        "dataset_origin": "omni-training/data/sft/omni_sft_seed.jsonl",
                    },
                },
            )(),
        ):
            result = self.engine.evaluate(
                message="talvez refine a resposta do runtime",
                base_response="Resposta curta.",
                oil_summary={"urgency": "medium"},
                routing_decision=routing,
                execution_manifest={"output_mode": "hybrid"},
            )
        self.assertTrue(result.model_used)
        self.assertEqual(result.decision_source, "hybrid")
        self.assertIn("Resposta refinada", result.refined_response)


if __name__ == "__main__":
    unittest.main()

