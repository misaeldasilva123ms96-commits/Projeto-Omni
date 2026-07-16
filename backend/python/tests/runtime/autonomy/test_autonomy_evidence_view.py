"""Tests for read-only autonomy evidence retrieval."""

from __future__ import annotations

import shutil
import tempfile
import unittest
import os
from pathlib import Path

from brain.memory import runtime_integration
from brain.memory.memory_facade import MemoryFacade
from brain.memory.memory_models import GovernanceEventRecord
from brain.runtime.autonomy import AutonomyContext, AutonomyController, DecisionType
from brain.runtime.autonomy.runtime_wiring import evaluate_and_attach, reset_controller_for_testing
from brain.runtime.autonomy.evidence_view import build_autonomy_evidence_payload


class AutonomyEvidenceViewTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="omni-autonomy-evidence-"))
        self._jsonl_path = self._tmp / "audit.jsonl"
        self._sqlite_path = self._tmp / "memory.sqlite"

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _facade(self, *, enable_sqlite: bool = False) -> MemoryFacade:
        facade = MemoryFacade(
            enable_sqlite=enable_sqlite,
            jsonl_path=self._jsonl_path,
            sqlite_path=self._sqlite_path,
        )
        facade.initialize()
        return facade

    def test_retrieves_safe_autonomy_metadata_only_from_jsonl_default(self) -> None:
        facade = self._facade()
        facade.record_governance_event(
            GovernanceEventRecord(
                event_id="ev-1",
                event_type="autonomy_decision_evidence",
                source="runtime_wiring",
                session_id="s1",
                status="RETRY",
                reason="fingerprint=abc | retry after timeout",
                metadata={
                    "fingerprint_id": "abc",
                    "progress_score": 1,
                    "stagnation_score": 2,
                    "recommended_decision_hint": "RETRY",
                    "strategies_attempted": ["retry"],
                    "advisory": True,
                    "risk_level": "low",
                    "raw_prompt": "should-not-render",
                    "api_key": "should-not-render",
                    "stdout": "should-not-render",
                },
            )
        )

        payload = build_autonomy_evidence_payload(facade=facade, session_id="s1")

        self.assertTrue(payload["read_only"])
        self.assertEqual(payload["mode"], "advisory-only")
        self.assertEqual(payload["source"], "memory_facade_governance_events")
        self.assertEqual(payload["summary"]["total"], 1)
        item = payload["items"][0]
        self.assertEqual(item["decision"], "RETRY")
        self.assertEqual(item["fingerprint_id"], "abc")
        as_text = str(payload)
        self.assertNotIn("should-not-render", as_text)
        self.assertNotIn("raw_prompt", as_text)
        self.assertNotIn("api_key", as_text)
        self.assertNotIn("stdout", as_text)

    def test_corrupt_jsonl_degrades_to_safe_empty_state(self) -> None:
        self._jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        self._jsonl_path.write_text("{not-json}\n", encoding="utf-8")
        facade = self._facade()

        payload = build_autonomy_evidence_payload(facade=facade)

        self.assertEqual(payload["items"], [])
        self.assertEqual(payload["summary"]["total"], 0)
        self.assertTrue(payload["read_only"])

    def test_sqlite_opt_in_does_not_disable_jsonl_evidence_view(self) -> None:
        facade = self._facade(enable_sqlite=True)
        self.assertTrue(facade.sqlite_enabled)
        facade.record_governance_event(
            GovernanceEventRecord(
                event_id="ev-sqlite",
                event_type="autonomy_decision",
                source="autonomy_controller",
                session_id="s2",
                status="CONTINUE",
                reason="safe metadata",
                metadata={"advisory": "true", "risk_level": "low"},
            )
        )

        payload = build_autonomy_evidence_payload(facade=facade, session_id="s2")

        self.assertEqual(payload["summary"]["total"], 1)
        self.assertEqual(payload["items"][0]["decision"], "CONTINUE")

    def test_escalation_summary_is_visibility_only(self) -> None:
        facade = self._facade()
        facade.record_governance_event(
            GovernanceEventRecord(
                event_id="ev-escalate",
                event_type="autonomy_decision_evidence",
                source="runtime_wiring",
                session_id="s3",
                status="ESCALATE_TO_MISAEL",
                reason="stagnation threshold reached",
                metadata={"advisory": True, "risk_level": "high"},
            )
        )

        payload = build_autonomy_evidence_payload(facade=facade, session_id="s3")

        self.assertEqual(payload["summary"]["escalation_count"], 1)
        self.assertEqual(payload["items"][0]["decision"], "ESCALATE_TO_MISAEL")
        self.assertNotIn("execute", payload["items"][0])
        self.assertNotIn("action", payload["items"][0])


class ControllerReceiptReliabilityTest(unittest.TestCase):
    def test_decide_with_report_records_single_receipt(self) -> None:
        controller = AutonomyController()

        decision, receipt, escalation = controller.decide_with_report(
            AutonomyContext(secret_detected=True)
        )

        self.assertEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)
        self.assertIsNotNone(escalation)
        self.assertEqual(controller.receipt_log.count(), 1)
        self.assertEqual(receipt.decision_id, decision.decision_id)


class EndToEndAdvisoryEvidenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="omni-autonomy-e2e-"))
        self._old_env = {
            "OMNI_JSONL_MEMORY_PATH": os.environ.get("OMNI_JSONL_MEMORY_PATH"),
            "OMNI_ENABLE_SQLITE_MEMORY": os.environ.get("OMNI_ENABLE_SQLITE_MEMORY"),
        }
        os.environ["OMNI_JSONL_MEMORY_PATH"] = str(self._tmp / "audit.jsonl")
        os.environ["OMNI_ENABLE_SQLITE_MEMORY"] = "false"
        runtime_integration.reset_for_testing()
        reset_controller_for_testing()

    def tearDown(self) -> None:
        runtime_integration.reset_for_testing()
        reset_controller_for_testing()
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_evaluate_persists_safe_evidence_without_execution(self) -> None:
        inspection = {
            "signals": {
                "runtime_mode": "provider_failure",
                "failure_class": "provider_timeout",
                "provider_failed": True,
                "provider_actual": "openai",
                "raw_response": "should-not-render",
                "api_key": "should-not-render",
            },
            "runtime_mode": "provider_failure",
        }

        evaluate_and_attach(inspection, "session-e2e", "safe response")

        autonomy = inspection["autonomy_evaluation"]
        self.assertEqual(autonomy["decision"], DecisionType.RETRY.value)
        self.assertTrue(autonomy["advisory"])
        evidence = inspection["autonomy_evidence"]
        self.assertTrue(evidence["read_only"])
        self.assertEqual(evidence["mode"], "advisory-only")
        self.assertGreaterEqual(evidence["summary"]["total"], 1)
        as_text = str(evidence)
        self.assertNotIn("should-not-render", as_text)
        for execution_key in (
            "execute",
            "patch",
            "commit",
            "push",
            "pull_request",
            "merge",
            "switch_provider",
            "self_repair",
        ):
            self.assertNotIn(execution_key, evidence["items"][0])


if __name__ == "__main__":
    unittest.main()
