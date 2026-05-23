from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.language import (  # noqa: E402
    OIL_VERSION,
    OILError,
    OILRequest,
    OILResult,
)


class OilSchemaTest(unittest.TestCase):
    def test_request_serialization_round_trip(self) -> None:
        raw = {
            "oil_version": "1.0",
            "intent": "generate_business_idea",
            "entities": {"domain": "digital"},
            "constraints": {"budget": "low"},
            "context": {
                "user_language": "pt-BR",
                "session_id": "abc123",
                "memory_refs": [],
            },
            "requested_output": "idea",
            "execution": {
                "priority": "normal",
                "complexity": "light",
                "mode": "interactive",
            },
        }
        model = OILRequest.deserialize(raw)
        out = model.serialize()
        again = OILRequest.deserialize(out)
        self.assertEqual(again.serialize(), out)
        self.assertEqual(out["oil_version"], OIL_VERSION)
        self.assertEqual(out["intent"], "generate_business_idea")
        self.assertEqual(out["entities"]["domain"], "digital")
        self.assertEqual(out["execution"]["mode"], "interactive")

    def test_result_serialization_round_trip(self) -> None:
        raw = {
            "oil_version": "1.0",
            "result_type": "business_idea",
            "status": "success",
            "data": {
                "idea": "AI powered document automation SaaS",
                "target_market": "small businesses",
            },
            "confidence": 0.92,
            "trace": {
                "planner": "idea_generator",
                "specialists": ["startup_advisor"],
                "memory_used": False,
            },
        }
        model = OILResult.deserialize(raw)
        out = model.serialize()
        again = OILResult.deserialize(out)
        self.assertEqual(again.serialize(), out)
        self.assertEqual(out["confidence"], 0.92)
        self.assertFalse(out["trace"]["memory_used"])

    def test_error_serialization_round_trip(self) -> None:
        raw = {
            "oil_version": "1.0",
            "status": "error",
            "error": {
                "code": "AMBIGUOUS_INTENT",
                "message": "Unable to determine intent with sufficient confidence",
                "recoverable": True,
            },
        }
        model = OILError.deserialize(raw)
        out = model.serialize()
        again = OILError.deserialize(out)
        self.assertEqual(again.serialize(), out)
        self.assertEqual(out["error"]["code"], "AMBIGUOUS_INTENT")
        self.assertTrue(out["error"]["recoverable"])

    def test_version_constant_present(self) -> None:
        self.assertEqual(OIL_VERSION, "1.0")
        req = OILRequest.deserialize({"oil_version": OIL_VERSION, "intent": "ping"})
        self.assertEqual(req.oil_version, "1.0")

    def test_optional_fields_and_extensibility(self) -> None:
        minimal = {"oil_version": "1.0", "intent": "noop"}
        m = OILRequest.deserialize(minimal)
        self.assertEqual(m.entities, {})
        self.assertEqual(m.constraints, {})
        self.assertEqual(m.requested_output, None)
        extended = {
            "oil_version": "1.0",
            "intent": "x",
            "future_field": {"k": 1},
        }
        mx = OILRequest.deserialize(extended)
        self.assertIn("future_field", mx.extensions)
        self.assertEqual(mx.extensions["future_field"], {"k": 1})

    def test_malformed_payloads_rejected(self) -> None:
        with self.assertRaises(ValueError):
            OILRequest.deserialize({"intent": "only_intent"})
        with self.assertRaises(ValueError):
            OILRequest.deserialize({"oil_version": "1.0"})
        with self.assertRaises(ValueError):
            OILResult.deserialize({"oil_version": "1.0", "result_type": "t", "status": "s", "data": []})
        with self.assertRaises(ValueError):
            OILError.deserialize({"oil_version": "1.0", "error": "not_a_dict"})
        with self.assertRaises(ValueError):
            OILError.deserialize(
                {"oil_version": "1.0", "error": {"code": "", "message": "m"}}
            )

    def test_json_transport(self) -> None:
        req = OILRequest.deserialize({"oil_version": "1.0", "intent": "ping"})
        wire = json.dumps(req.serialize())
        back = OILRequest.deserialize(json.loads(wire))
        self.assertEqual(back.intent, "ping")


if __name__ == "__main__":
    unittest.main()
