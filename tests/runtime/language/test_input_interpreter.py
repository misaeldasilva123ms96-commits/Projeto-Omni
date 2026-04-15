from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.language import OIL_VERSION, InputInterpreter  # noqa: E402


class InputInterpreterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.interpreter = InputInterpreter()

    def test_plain_question_becomes_valid_oil_request(self) -> None:
        req = self.interpreter.interpret("Como funciona o RunRegistry?", session_id="s1", user_language="pt-BR")
        payload = req.serialize()
        self.assertEqual(payload["oil_version"], OIL_VERSION)
        self.assertTrue(payload["intent"])
        self.assertIn("context", payload)
        self.assertEqual(payload["context"]["session_id"], "s1")
        self.assertEqual(payload["context"]["user_language"], "pt-BR")
        self.assertIn("extensions", payload)
        self.assertIn("confidence", payload["extensions"])

    def test_business_idea_intent(self) -> None:
        req = self.interpreter.interpret("Crie uma ideia de negócio digital com baixo orçamento.", user_language="pt-BR")
        self.assertEqual(req.intent, "generate_business_idea")
        self.assertEqual(req.serialize().get("requested_output"), "idea")
        self.assertEqual(req.constraints.get("budget"), "low")

    def test_summarize_intent(self) -> None:
        req = self.interpreter.interpret("Resuma esse texto em 5 tópicos.", user_language="pt-BR")
        self.assertEqual(req.intent, "summarize")
        self.assertEqual(req.serialize().get("requested_output"), "bullets")

    def test_ambiguous_input_safe_fallback(self) -> None:
        req = self.interpreter.interpret("...", session_id="s2")
        self.assertIn(req.intent, {"ambiguous_request", "ask_question"})
        conf = float(req.extensions.get("confidence", -1.0))
        self.assertGreaterEqual(conf, 0.0)
        self.assertLessEqual(conf, 1.0)

    def test_portuguese_language_preserved_when_provided(self) -> None:
        req = self.interpreter.interpret("Explique isso.", user_language="pt-BR")
        self.assertEqual(req.context.user_language, "pt-BR")

    def test_constraints_extracted_budget_format_length(self) -> None:
        req = self.interpreter.interpret("Resuma em JSON e no máximo 120 palavras com baixo orçamento.")
        self.assertEqual(req.constraints.get("budget"), "low")
        self.assertEqual(req.constraints.get("format"), "json")
        self.assertEqual(req.constraints.get("max_words"), 120)

    def test_requested_output_inferred_consistently(self) -> None:
        req1 = self.interpreter.interpret("Compare A vs B em tabela.")
        self.assertEqual(req1.intent, "compare")
        self.assertEqual(req1.serialize().get("requested_output"), "table")

        req2 = self.interpreter.interpret("Faça um plano passo a passo.")
        self.assertEqual(req2.intent, "plan")
        self.assertEqual(req2.serialize().get("requested_output"), "plan")

    def test_confidence_exists_and_bounded(self) -> None:
        req = self.interpreter.interpret("Summarize this.")
        conf = float(req.extensions.get("confidence", -1.0))
        self.assertGreaterEqual(conf, 0.0)
        self.assertLessEqual(conf, 1.0)

    def test_empty_input_handled_safely(self) -> None:
        req = self.interpreter.interpret("   ")
        self.assertEqual(req.intent, "ambiguous_request")
        self.assertEqual(float(req.extensions.get("confidence", 1.0)), 0.0)
        self.assertEqual(req.extensions.get("reason"), "empty_input")


if __name__ == "__main__":
    unittest.main()

