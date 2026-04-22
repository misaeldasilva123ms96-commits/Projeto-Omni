from __future__ import annotations

import io
import os
import shutil
import sys
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.control.capability_router import CapabilityRouter  # noqa: E402
from brain.runtime.learning import (  # noqa: E402
    DecisionAmbiguityDetector,
    DecisionCandidateBuilder,
    DecisionRankingEngine,
    LoRAInferenceEngine,
)
from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402


class DecisionRankingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.router = CapabilityRouter()
        self.detector = DecisionAmbiguityDetector()
        self.builder = DecisionCandidateBuilder()
        self.inference = LoRAInferenceEngine(PROJECT_ROOT)
        self.engine = DecisionRankingEngine(self.inference)

    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-phase3-ranking"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"phase3-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_ambiguity_detection_flags_safe_direct_vs_reasoning_case(self) -> None:
        routing = self.router.classify_task("explique a arquitetura e proponha um plano curto")
        routing = type(routing)(
            **{
                **routing.as_dict(),
                "preferred_mode": routing.preferred_mode,
                "confidence": 0.62,
            }
        )
        assessment = self.detector.detect(
            routing_decision=routing,
            oil_summary={"desired_output": "plan", "urgency": "medium"},
            execution_manifest={"output_mode": "hybrid"},
        )
        self.assertTrue(assessment.is_ambiguous)
        self.assertIn("MULTI_STEP_REASONING", assessment.candidate_strategies)
        self.assertTrue(assessment.safe_to_rank)

    def test_candidate_builder_returns_multiple_candidates(self) -> None:
        routing = self.router.classify_task("explique a arquitetura e proponha um plano curto")
        routing = type(routing)(
            **{
                **routing.as_dict(),
                "preferred_mode": routing.preferred_mode,
                "confidence": 0.62,
            }
        )
        assessment = self.detector.detect(
            routing_decision=routing,
            oil_summary={"desired_output": "plan", "urgency": "medium"},
            execution_manifest={"output_mode": "hybrid"},
        )
        candidates = self.builder.build(
            ambiguity_assessment=assessment,
            routing_decision=routing,
            oil_summary={"desired_output": "plan", "urgency": "medium"},
            execution_manifest={"output_mode": "hybrid", "selected_tools": []},
        )
        self.assertGreaterEqual(len(candidates), 2)
        self.assertEqual(candidates[0].source, "rule")

    def test_ranking_engine_prefers_rule_on_unsafe_high_risk(self) -> None:
        routing = self.router.classify_task("explique a arquitetura")
        routing = type(routing)(
            **{
                **routing.as_dict(),
                "preferred_mode": routing.preferred_mode,
                "strategy": "MULTI_STEP_REASONING",
                "confidence": 0.61,
                "risk_level": "high",
            }
        )
        assessment = self.detector.detect(
            routing_decision=routing,
            oil_summary={"desired_output": "analysis", "urgency": "medium"},
            execution_manifest={"output_mode": "hybrid"},
        )
        candidates = self.builder.build(
            ambiguity_assessment=assessment,
            routing_decision=routing,
            oil_summary={"desired_output": "analysis", "urgency": "medium"},
            execution_manifest={"output_mode": "hybrid"},
        )
        result = self.engine.rank(
            ambiguity_assessment=assessment,
            candidates=candidates,
            routing_decision=routing,
            oil_summary={"desired_output": "analysis", "urgency": "medium"},
            execution_manifest={"output_mode": "hybrid"},
        )
        self.assertEqual(result.selected_strategy, routing.strategy)
        self.assertFalse(result.model_used)

    def test_ranking_engine_uses_model_signal_when_available(self) -> None:
        routing = self.router.classify_task("talvez explique e planeje a resposta")
        routing = type(routing)(
            **{
                **routing.as_dict(),
                "preferred_mode": routing.preferred_mode,
                "confidence": 0.61,
            }
        )
        assessment = self.detector.detect(
            routing_decision=routing,
            oil_summary={"desired_output": "plan", "urgency": "medium"},
            execution_manifest={"output_mode": "hybrid"},
        )
        candidates = self.builder.build(
            ambiguity_assessment=assessment,
            routing_decision=routing,
            oil_summary={"desired_output": "plan", "urgency": "medium"},
            execution_manifest={"output_mode": "hybrid"},
        )
        with patch.object(self.inference, "adapter_available", return_value=True), patch.object(
            self.inference,
            "generate_response",
            return_value=type(
                "InferenceResult",
                (),
                {
                    "model_used": True,
                    "fallback": False,
                    "confidence": 0.69,
                    "text": "MULTI_STEP_REASONING",
                },
            )(),
        ):
            result = self.engine.rank(
                ambiguity_assessment=assessment,
                candidates=candidates,
                routing_decision=routing,
                oil_summary={"desired_output": "plan", "urgency": "medium"},
                execution_manifest={"output_mode": "hybrid"},
            )
        self.assertTrue(result.model_used)
        self.assertIn(result.decision_source, {"hybrid_ranked", "rule_ranked"})

    def test_orchestrator_applies_ranking_bundle_safely(self) -> None:
        with self.temp_workspace() as workspace_root:
            os.environ["BASE_DIR"] = str(workspace_root)
            os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
            orchestrator = BrainOrchestrator(
                BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
            )
            routing = orchestrator.capability_router.classify_task("explique a arquitetura e proponha um plano curto")
            routing = type(routing)(
                **{
                    **routing.as_dict(),
                    "preferred_mode": routing.preferred_mode,
                    "confidence": 0.62,
                }
            )
            artifacts = orchestrator._build_runtime_upgrade_artifacts(
                message="explique a arquitetura e proponha um plano curto",
                session_id="phase3",
                run_id="",
                routing_decision=routing,
                strategy_payload={},
                selected_tools=[],
                provider_path="",
            )
            bundle = orchestrator._apply_decision_ranking(
                session_id="phase3",
                message="explique a arquitetura e proponha um plano curto",
                routing_decision=routing,
                upgrade_artifacts=artifacts,
                strategy_payload={},
                selected_tools=[],
                provider_path="",
            )
            self.assertIn("decision_ranking", bundle)
            self.assertIn("routing_decision", bundle)
            self.assertIn("upgrade_artifacts", bundle)


if __name__ == "__main__":
    unittest.main()
