from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.reasoning import ReasoningEngine  # noqa: E402


class ReasoningEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ReasoningEngine()

    def test_reasoning_pipeline_returns_structured_handoff(self) -> None:
        outcome = self.engine.reason(
            raw_input="Analise o impacto de mudar o run registry.",
            session_id="sess-r31",
            run_id="run-r31",
            source_component="tests.reasoning",
        )
        self.assertIn(outcome.mode, {"fast", "deep", "critical"})
        self.assertEqual(outcome.execution_handoff.get("proceed"), True)
        self.assertIn("plan_steps", outcome.execution_handoff)
        self.assertEqual(outcome.execution_handoff["plan_steps"][0], "interpret")
        self.assertEqual(outcome.execution_handoff["plan_steps"][-1], "handoff_to_execution")
        self.assertEqual(outcome.oil_result.result_type, "reasoning_handoff")
        self.assertEqual(outcome.oil_result.status, "ready")

    def test_reasoning_mode_selection_fast_deep_critical(self) -> None:
        fast = self.engine.reason(
            raw_input="resuma isso",
            session_id="sess-fast",
            run_id="run-fast",
            source_component="tests.reasoning",
        )
        deep = self.engine.reason(
            raw_input="Faça uma análise de arquitetura com trade-off e estratégia de refactor.",
            session_id="sess-deep",
            run_id="run-deep",
            source_component="tests.reasoning",
        )
        critical = self.engine.reason(
            raw_input="Verifique risco de production secret e delete em massa.",
            session_id="sess-critical",
            run_id="run-critical",
            source_component="tests.reasoning",
        )
        self.assertEqual(fast.mode, "fast")
        self.assertEqual(deep.mode, "deep")
        self.assertEqual(critical.mode, "critical")

    def test_trace_contains_validation_and_handoff_decision(self) -> None:
        outcome = self.engine.reason(
            raw_input="Planeje uma resposta segura",
            session_id="sess-trace",
            run_id="run-trace",
            source_component="tests.reasoning",
        )
        trace = outcome.trace.as_dict()
        self.assertIn("validation_result", trace)
        self.assertIn(trace["validation_result"], {"valid", "invalid"})
        self.assertIn("handoff_decision", trace)
        self.assertIn(trace["handoff_decision"], {"proceed", "blocked"})
        self.assertEqual(trace["mode"], outcome.mode)


if __name__ == "__main__":
    unittest.main()
