from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.language import OILError, OILResult, OutputComposer, compose_output  # noqa: E402
from brain.runtime.language.types import OILErrorDetails, OIL_VERSION  # noqa: E402


class OutputComposerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.composer = OutputComposer()

    def test_gate_30_4_1_oil_result_to_natural_language(self) -> None:
        res = OILResult(
            oil_version=OIL_VERSION,
            result_type="business_idea",
            status="success",
            data={"idea": "SaaS de automação documental com IA", "target_market": "pequenas empresas"},
        )
        text = self.composer.compose(res, user_language="pt-BR")
        self.assertIn("SaaS", text)
        self.assertIn("pequenas empresas", text)

    def test_gate_30_4_2_oil_error_safe_response(self) -> None:
        err = OILError(
            oil_version=OIL_VERSION,
            error=OILErrorDetails(
                code="AMBIGUOUS_INTENT",
                message="Não foi possível determinar a intenção principal com confiança suficiente.",
                recoverable=True,
            ),
        )
        pt = self.composer.compose(err, user_language="pt-BR")
        self.assertIn("Não consegui identificar", pt)
        en = self.composer.compose(err, user_language="en")
        self.assertIn("could not confidently", en.lower())

    def test_gate_30_4_2_portuguese_preservation(self) -> None:
        res = OILResult(
            oil_version=OIL_VERSION,
            result_type="summary",
            status="success",
            data={"summary": "Texto em português."},
        )
        out = self.composer.compose(res, user_language="pt-BR")
        self.assertIn("português", out)

    def test_gate_30_4_2_english_preservation(self) -> None:
        res = OILResult(
            oil_version=OIL_VERSION,
            result_type="summary",
            status="success",
            data={"summary": "Short English summary."},
        )
        out = self.composer.compose(res, user_language="en")
        self.assertIn("English", out)

    def test_gate_30_4_3_tone_adaptation_deterministic(self) -> None:
        res = OILResult(
            oil_version=OIL_VERSION,
            result_type="answer",
            status="success",
            data={"answer": "First sentence. Second sentence. Third sentence."},
        )
        concise = self.composer.compose(res, user_language="en", tone="concise")
        explanatory = self.composer.compose(res, user_language="en", tone="explanatory")
        structured = self.composer.compose(res, user_language="en", tone="structured")
        self.assertLessEqual(len(concise), len(explanatory))
        self.assertIn("Here is the result.", explanatory)
        self.assertTrue(structured.strip().startswith("-"))

    def test_legacy_dict_result(self) -> None:
        payload = {
            "oil_version": OIL_VERSION,
            "result_type": "plan",
            "status": "success",
            "data": {"steps": ["A", "B"]},
        }
        text = self.composer.compose(payload, user_language="pt-BR")
        self.assertIn("Plano", text)
        self.assertIn("1.", text)

    def test_plain_string_fallback(self) -> None:
        self.assertEqual(self.composer.compose("  hello  "), "hello")

    def test_compose_output_alias(self) -> None:
        self.assertEqual(compose_output("x"), "x")

    def test_malformed_dict_safe_fallback(self) -> None:
        out = self.composer.compose({"foo": "bar"}, user_language="pt-BR")
        self.assertTrue(len(out) > 0)

    def test_dict_error_shape(self) -> None:
        out = self.composer.compose(
            {
                "oil_version": OIL_VERSION,
                "status": "error",
                "error": {"code": "AMBIGUOUS_INTENT", "message": "x", "recoverable": True},
            },
            user_language="pt-BR",
        )
        self.assertIn("Não consegui identificar", out)


if __name__ == "__main__":
    unittest.main()
