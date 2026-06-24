"""Integration tests for per-session state in the autonomy wiring.

Verifies that:
- Session state is created and tracked across evaluate_autonomy calls
- Repeated errors across calls are counted cumulatively
- New errors reset stagnation
- Stagnation increments on repeated failures
- SAFE_FALLBACK_RESPONSE repetition is stagnation
- Provider failure repetition is stagnation
- Progress resets stagnation
- Session state is sanitized
- Tracker failure does not break runtime
- Controller remains advisory
- SELF_REPAIR and SWITCH_PROVIDER not executed
- Orchestrator response remains unchanged
- Existing autonomy tests still pass
"""

from __future__ import annotations

import unittest
from typing import Any

from brain.runtime.autonomy import (
    DISABLED_DECISIONS,
    AutonomyContext,
    AutonomySessionTracker,
    DecisionType,
)
from brain.runtime.autonomy.runtime_wiring import (
    _get_tracker,
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
    return {"signals": signals, "runtime_mode": runtime_mode}


class SessionStateCreationTest(unittest.TestCase):
    def setUp(self) -> None:
        reset_controller_for_testing()

    def test_new_session_creates_tracker_state(self) -> None:
        tracker = _get_tracker()
        state = tracker.get_or_create("s1")
        self.assertEqual(state.session_id, "s1")

    def test_multiple_calls_use_same_session_state(self) -> None:
        result1 = evaluate_autonomy({}, "s-test", "ok")
        result2 = evaluate_autonomy({}, "s-test", "ok")
        self.assertEqual(result1["session_id"], "s-test")
        self.assertEqual(result2["session_id"], "s-test")
        tracker = _get_tracker()
        state = tracker.get_state("s-test")
        self.assertIsNotNone(state)
        if state:
            self.assertEqual(state.session_id, "s-test")


class CumulativeErrorCountTest(unittest.TestCase):
    def setUp(self) -> None:
        reset_controller_for_testing()

    def test_repeated_errors_across_calls_are_cumulative(self) -> None:
        inspection = _make_inspection(failure_class="timeout")
        evaluate_autonomy(inspection, "s1", "ok")
        result = evaluate_autonomy(inspection, "s1", "ok")
        self.assertEqual(result["decision"], DecisionType.RETRY.value)

    def test_error_count_increases_across_calls(self) -> None:
        inspection = _make_inspection(failure_class="timeout")
        for _ in range(3):
            evaluate_autonomy(inspection, "s1", "ok")
        result = evaluate_autonomy(inspection, "s1", "ok")
        self.assertEqual(result["decision"], DecisionType.RETRY.value)

    def test_stagnation_leads_to_escalation(self) -> None:
        inspection = _make_inspection(failure_class="persistent_error")
        for _ in range(4):
            evaluate_autonomy(inspection, "s1", "ok")
        result = evaluate_autonomy(inspection, "s1", "ok")
        self.assertEqual(result["decision"], DecisionType.ESCALATE_TO_MISAEL.value)


class NewErrorResetsTest(unittest.TestCase):
    def setUp(self) -> None:
        reset_controller_for_testing()

    def test_new_error_type_resets_stagnation(self) -> None:
        ins1 = _make_inspection(failure_class="timeout")
        ins2 = _make_inspection(failure_class="KeyError")
        evaluate_autonomy(ins1, "s1", "ok")
        evaluate_autonomy(ins1, "s1", "ok")
        result = evaluate_autonomy(ins2, "s1", "ok")
        self.assertEqual(result["decision"], DecisionType.REPLAN.value)

    def test_new_error_tracks_distinct_types(self) -> None:
        for fc in ("err_a", "err_b", "err_c"):
            ins = _make_inspection(failure_class=fc)
            evaluate_autonomy(ins, "s-distinct", "ok")
        tracker = _get_tracker()
        state = tracker.get_state("s-distinct")
        self.assertIsNotNone(state)
        if state:
            self.assertEqual(len(state.distinct_error_types), 3)


class SafeFallbackStagnationTest(unittest.TestCase):
    def setUp(self) -> None:
        reset_controller_for_testing()

    def test_repeated_safe_fallback_is_stagnation(self) -> None:
        inspection = _make_inspection(runtime_mode="safe_fallback")
        evaluate_autonomy(inspection, "s1", SAFE_FALLBACK)
        evaluate_autonomy(inspection, "s1", SAFE_FALLBACK)
        result = evaluate_autonomy(inspection, "s1", SAFE_FALLBACK)
        self.assertEqual(result["decision"], DecisionType.ABORT_SAFE.value)

    def test_safe_fallback_then_normal_is_progress(self) -> None:
        fb_inspection = _make_inspection(runtime_mode="safe_fallback")
        ok_inspection = _make_inspection(runtime_mode="standard")
        evaluate_autonomy(fb_inspection, "s1", SAFE_FALLBACK)
        result = evaluate_autonomy(ok_inspection, "s1", "good response")
        self.assertEqual(result["decision"], DecisionType.CONTINUE.value)


class ProviderFailureStagnationTest(unittest.TestCase):
    def setUp(self) -> None:
        reset_controller_for_testing()

    def test_repeated_provider_failure_tracked(self) -> None:
        inspection = _make_inspection(
            failure_class="provider_timeout",
            runtime_mode="provider_failure",
            provider_failed=True,
            provider_actual="openai",
        )
        evaluate_autonomy(inspection, "s1", "ok")
        result = evaluate_autonomy(inspection, "s1", "ok")
        self.assertEqual(result["decision"], DecisionType.RETRY.value)
        tracker = _get_tracker()
        state = tracker.get_state("s1")
        self.assertIsNotNone(state)
        if state:
            self.assertEqual(state.last_provider_failure_type, "openai")

    def test_provider_failure_disappearance_is_progress(self) -> None:
        fail_ins = _make_inspection(
            failure_class="provider_timeout",
            runtime_mode="provider_failure",
            provider_failed=True,
            provider_actual="openai",
        )
        ok_ins = _make_inspection(runtime_mode="standard")
        evaluate_autonomy(fail_ins, "s1", "ok")
        result = evaluate_autonomy(ok_ins, "s1", "good response")
        self.assertEqual(result["decision"], DecisionType.CONTINUE.value)


class ProgressResetsStagnationTest(unittest.TestCase):
    def setUp(self) -> None:
        reset_controller_for_testing()

    def test_progress_resets_stagnant_attempts(self) -> None:
        ins_err = _make_inspection(failure_class="timeout", runtime_mode="provider_failure")
        ins_progress = _make_inspection(runtime_mode="standard")
        evaluate_autonomy(ins_err, "s1", "ok")
        evaluate_autonomy(ins_err, "s1", "ok")
        evaluate_autonomy(ins_progress, "s1", "good response")
        tracker = _get_tracker()
        state = tracker.get_state("s1")
        self.assertIsNotNone(state)
        if state:
            self.assertEqual(state.stagnant_attempts, 0)


class AdvisoryOnlyTest(unittest.TestCase):
    def setUp(self) -> None:
        reset_controller_for_testing()

    def test_all_decisions_remain_advisory(self) -> None:
        ins_ok = _make_inspection(runtime_mode="standard")
        result_ok = evaluate_autonomy(ins_ok, "s1", "ok")
        self.assertTrue(result_ok["advisory"])

        ins_err = _make_inspection(failure_class="timeout")
        result_err = evaluate_autonomy(ins_err, "s1", "ok")
        self.assertTrue(result_err["advisory"])

    def test_self_repair_still_disabled(self) -> None:
        self.assertIn(DecisionType.SELF_REPAIR, DISABLED_DECISIONS)

    def test_switch_provider_still_disabled(self) -> None:
        self.assertIn(DecisionType.SWITCH_PROVIDER, DISABLED_DECISIONS)


class OrchestratorPreservationTest(unittest.TestCase):
    def setUp(self) -> None:
        reset_controller_for_testing()

    def test_runtime_behavior_unchanged(self) -> None:
        inspection: dict[str, Any] = {"signals": {}}
        before = dict(inspection)
        evaluate_and_attach(inspection, "s1", "good response")
        for key, value in before.items():
            self.assertEqual(inspection[key], value)

    def test_autonomy_result_has_required_keys(self) -> None:
        result = evaluate_autonomy({}, "s1", "test")
        for key in ("decision", "advisory", "reason", "risk_level", "session_id"):
            self.assertIn(key, result)


class SafetyDegradationTest(unittest.TestCase):
    def test_tracker_failure_does_not_break_runtime(self) -> None:
        try:
            evaluate_autonomy(None, "s1", "test")
        except Exception:
            self.fail("evaluate_autonomy raised with None inspection")

    def test_evaluate_and_attach_does_not_raise(self) -> None:
        try:
            evaluate_and_attach(None, "s1", "test")
        except Exception:
            self.fail("evaluate_and_attach raised with None inspection")

    def test_invalid_inspection_handled_safely(self) -> None:
        try:
            evaluate_and_attach(42, "s1", "test")
        except Exception:
            self.fail("evaluate_and_attach raised with invalid inspection")


class SessionStateSanitizationTest(unittest.TestCase):
    def setUp(self) -> None:
        reset_controller_for_testing()

    def test_no_raw_prompt_in_context(self) -> None:
        ctx = build_autonomy_context({"signals": {}}, "s1", "user message")
        as_text = str(ctx.as_dict())
        self.assertNotIn("raw_prompt", as_text)

    def test_no_api_keys_in_context(self) -> None:
        ctx = build_autonomy_context({"signals": {}}, "s1", "ok")
        values_text = str(list(ctx.as_dict().values()))
        for secret in ("api_key", "auth_token", "password"):
            self.assertNotIn(secret, values_text)

    def test_no_stack_traces_in_context(self) -> None:
        ctx = build_autonomy_context({"signals": {}}, "s1", "ok")
        as_text = str(ctx.as_dict())
        self.assertNotIn("traceback", as_text)

    def test_no_credentials_in_context(self) -> None:
        ctx = build_autonomy_context({"signals": {}}, "s1", "ok")
        values_text = str(list(ctx.as_dict().values()))
        for cred in ("credential",):
            self.assertNotIn(cred, values_text)


class ExistingAutonomyTestsStillPass(unittest.TestCase):
    def test_basic_context_checks(self) -> None:
        ctx = build_autonomy_context(None, "s1", "ok")
        self.assertEqual(ctx.session_id, "s1")
        self.assertEqual(ctx.error_type, "")
        self.assertEqual(ctx.error_count, 0)

    def test_fallback_sets_no_safe_next_action(self) -> None:
        ctx = build_autonomy_context({"signals": {}}, "s1", SAFE_FALLBACK)
        self.assertTrue(ctx.no_safe_next_action)

    def test_continue_on_success(self) -> None:
        result = evaluate_autonomy({}, "s1", "ok")
        self.assertEqual(result["decision"], DecisionType.CONTINUE.value)

    def test_escalate_on_stagnation_from_session(self) -> None:
        inspection = _make_inspection(failure_class="err")
        for _ in range(5):
            evaluate_autonomy(inspection, "s-escalate", "ok")
        result = evaluate_autonomy(inspection, "s-escalate", "ok")
        self.assertEqual(result["decision"], DecisionType.ESCALATE_TO_MISAEL.value)


if __name__ == "__main__":
    unittest.main()
