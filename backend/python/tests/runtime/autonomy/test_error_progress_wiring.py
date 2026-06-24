"""Integration tests for the Smart Error Progress Tracker wiring.

Verifies that the tracker integrates cleanly into runtime_wiring,
does not break existing behavior, and produces safe output.
"""

from __future__ import annotations

import unittest
from typing import Any

from brain.runtime.autonomy import (
    DISABLED_DECISIONS,
    AutonomySessionTracker,
    DecisionType,
    SmartErrorProgressTracker,
)
from brain.runtime.autonomy.runtime_wiring import (
    _get_smart_tracker,
    build_autonomy_context,
    evaluate_autonomy,
    evaluate_and_attach,
    reset_controller_for_testing,
)


SAFE_FALLBACK = "Nao consegui processar isso ainda, mas estou aprendendo."


def _make_inspection(
    *,
    runtime_mode: str = "",
    failure_class: str = "",
    failure_reason: str = "",
    fallback_triggered: bool = False,
    provider_failed: bool = False,
    provider_actual: str = "",
    tool_category: str = "",
) -> dict[str, Any]:
    signals: dict[str, Any] = {}
    if runtime_mode:
        signals["runtime_mode"] = runtime_mode
    if failure_class:
        signals["failure_class"] = failure_class
    if failure_reason:
        signals["failure_reason"] = failure_reason
    if fallback_triggered:
        signals["fallback_triggered"] = True
    if provider_failed:
        signals["provider_failed"] = True
    if provider_actual:
        signals["provider_actual"] = provider_actual
    if tool_category:
        signals["tool_category"] = tool_category
    return {"signals": signals, "runtime_mode": runtime_mode}


class SmartTrackerWiredTest(unittest.TestCase):
    def setUp(self) -> None:
        reset_controller_for_testing()

    def test_smart_tracker_accessible(self) -> None:
        tracker = _get_smart_tracker()
        self.assertIsInstance(tracker, SmartErrorProgressTracker)

    def test_evaluate_smart_tracker_output_in_metadata(self) -> None:
        inspection = _make_inspection(failure_class="timeout")
        result = evaluate_autonomy(inspection, "s1", "ok")
        self.assertIn("session_id", result)

    def test_evaluate_does_not_raise_with_smart_tracker(self) -> None:
        try:
            _ = evaluate_autonomy({}, "s1", "ok")
        except Exception:
            self.fail("evaluate_autonomy raised with smart tracker")


class ExistingBehaviorPreservedTest(unittest.TestCase):
    def setUp(self) -> None:
        reset_controller_for_testing()

    def test_continue_on_success(self) -> None:
        result = evaluate_autonomy({}, "s1", "ok")
        self.assertEqual(result["decision"], DecisionType.CONTINUE.value)

    def test_retry_on_failure(self) -> None:
        inspection = _make_inspection(failure_class="timeout")
        result = evaluate_autonomy(inspection, "s1", "ok")
        self.assertEqual(result["decision"], DecisionType.RETRY.value)

    def test_advisory_flag_true(self) -> None:
        result = evaluate_autonomy({}, "s1", "ok")
        self.assertTrue(result["advisory"])

    def test_result_has_required_keys(self) -> None:
        result = evaluate_autonomy({}, "s1", "test")
        for key in ("decision", "advisory", "reason", "risk_level", "session_id"):
            self.assertIn(key, result)


class RuntimeBehaviorUnchangedTest(unittest.TestCase):
    def setUp(self) -> None:
        reset_controller_for_testing()

    def test_attach_does_not_modify_inspection(self) -> None:
        inspection: dict[str, Any] = {"signals": {}}
        before = dict(inspection)
        evaluate_and_attach(inspection, "s1", "good response")
        for key, value in before.items():
            self.assertEqual(inspection[key], value)

    def test_attach_adds_autonomy_evaluation(self) -> None:
        inspection: dict[str, Any] = {"signals": {}}
        evaluate_and_attach(inspection, "s1", "good response")
        self.assertIn("autonomy_evaluation", inspection)

    def test_attach_does_not_raise_on_none(self) -> None:
        try:
            evaluate_and_attach(None, "s1", "test")
        except Exception:
            self.fail("evaluate_and_attach raised with None")


class AdvisoryAndDisabledTest(unittest.TestCase):
    def setUp(self) -> None:
        reset_controller_for_testing()

    def test_self_repair_still_disabled(self) -> None:
        self.assertIn(DecisionType.SELF_REPAIR, DISABLED_DECISIONS)

    def test_switch_provider_still_disabled(self) -> None:
        self.assertIn(DecisionType.SWITCH_PROVIDER, DISABLED_DECISIONS)

    def test_no_execution_path_in_result(self) -> None:
        result = evaluate_autonomy(None, "s1", "test")
        for exec_key in ("execute", "action", "patch", "commit", "push", "merge"):
            self.assertNotIn(exec_key, result.get("decision", "").lower())


class SanitizationTest(unittest.TestCase):
    def setUp(self) -> None:
        reset_controller_for_testing()

    def test_no_raw_prompt_in_context_via_build(self) -> None:
        ctx = build_autonomy_context({"signals": {}}, "s1", "user message here")
        as_text = str(ctx.as_dict())
        self.assertNotIn("raw_prompt", as_text)

    def test_no_api_keys_in_context(self) -> None:
        ctx = build_autonomy_context({"signals": {}}, "s1", "ok")
        values_text = str(list(ctx.as_dict().values()))
        for secret in ("api_key", "auth_token", "password"):
            self.assertNotIn(secret, values_text)


class SafetyDegradationTest(unittest.TestCase):
    def test_classify_empty_context_safe(self) -> None:
        tracker = SmartErrorProgressTracker()
        from brain.runtime.autonomy import AutonomyContext

        ctx = AutonomyContext(session_id="s1")
        try:
            _ = tracker.classify("s1", ctx, None)
        except Exception:
            self.fail("classify raised with empty context")

    def test_update_empty_context_safe(self) -> None:
        tracker = SmartErrorProgressTracker()
        from brain.runtime.autonomy import AutonomyContext, AutonomyDecision

        ctx = AutonomyContext(session_id="s1")
        dec = AutonomyDecision(decision=DecisionType.CONTINUE, reason="test")
        try:
            _ = tracker.update("s1", ctx, None, dec)
        except Exception:
            self.fail("update raised with empty context")


if __name__ == "__main__":
    unittest.main()
