from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.language.oil_translator import oil_summary, translate_to_oil_projection  # noqa: E402


class OilTranslatorTest(unittest.TestCase):
    def test_translate_to_projection_builds_expected_shape(self) -> None:
        oil_request, projection = translate_to_oil_projection(
            "faça um plano em json sobre o repositorio hoje",
            session_id="oil-translator-test",
            metadata={"source_component": "test"},
        )
        self.assertEqual(oil_request.intent, "plan")
        self.assertEqual(projection.user_intent, "plan")
        self.assertEqual(projection.desired_output, "json")
        self.assertEqual(projection.urgency, "high")
        self.assertEqual(projection.execution_bias, "deep")
        self.assertIn("oil_version", projection.metadata)

    def test_oil_summary_is_safe_and_compact(self) -> None:
        _, projection = translate_to_oil_projection("explique isso em bullets")
        summary = oil_summary(projection)
        self.assertEqual(summary["user_intent"], projection.user_intent)
        self.assertIn("desired_output", summary)
        self.assertIn("entity_keys", summary)
        self.assertIn("constraint_keys", summary)


if __name__ == "__main__":
    unittest.main()
