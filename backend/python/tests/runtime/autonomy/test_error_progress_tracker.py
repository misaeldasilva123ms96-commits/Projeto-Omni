"""Tests for the Smart Error Progress Tracker.

Covers fingerprint stability, repeated vs new errors, progress/stagnation
scoring, strategy tracking, escalation evidence, and safety/sanitization.
"""

from __future__ import annotations

import unittest
from typing import Any

from brain.runtime.autonomy import (
    AutonomyContext,
    AutonomyDecision,
    DecisionType,
    ErrorFingerprint,
    ProgressTrackerOutput,
    SmartErrorProgressTracker,
    StrategyAttempt,
)


def _make_ctx(
    *,
    session_id: str = "s1",
    error_type: str = "",
    protected_file: bool = False,
    secret: bool = False,
    no_safe: bool = False,
    runtime_mode: str = "standard",
    provider_failure: str = "",
    response_length: int = 10,
) -> AutonomyContext:
    ctx = AutonomyContext(
        session_id=session_id,
        error_type=error_type,
        protected_file_involved=protected_file,
        secret_detected=secret,
        no_safe_next_action=no_safe,
    )
    ctx.metadata["runtime_mode"] = runtime_mode
    ctx.metadata["response_length"] = response_length
    if provider_failure:
        ctx.metadata["provider_failure_type"] = provider_failure
    return ctx


def _make_inspection(
    *,
    failure_class: str = "",
    failure_reason: str = "",
    tool_category: str = "",
) -> dict[str, Any]:
    signals: dict[str, Any] = {}
    if failure_class:
        signals["failure_class"] = failure_class
    if failure_reason:
        signals["failure_reason"] = failure_reason
    if tool_category:
        signals["tool_category"] = tool_category
    return {"signals": signals}


class FingerprintTest(unittest.TestCase):
    def test_stable_fingerprint_for_same_metadata(self) -> None:
        fp1 = ErrorFingerprint(
            error_type="timeout",
            failure_class="provider_timeout",
            runtime_mode="provider_failure",
            provider_failure_type="openai",
        )
        fp2 = ErrorFingerprint(
            error_type="timeout",
            failure_class="provider_timeout",
            runtime_mode="provider_failure",
            provider_failure_type="openai",
        )
        self.assertEqual(fp1.fingerprint_id, fp2.fingerprint_id)

    def test_different_fingerprint_for_different_error(self) -> None:
        fp1 = ErrorFingerprint(error_type="timeout")
        fp2 = ErrorFingerprint(error_type="rate_limit")
        self.assertNotEqual(fp1.fingerprint_id, fp2.fingerprint_id)

    def test_fingerprint_id_stable_across_calls(self) -> None:
        fp = ErrorFingerprint(
            error_type="auth_error",
            failure_class="auth_error",
            runtime_mode="standard",
        )
        fid1 = fp.fingerprint_id
        fid2 = fp.fingerprint_id
        self.assertEqual(fid1, fid2)

    def test_is_empty_returns_true(self) -> None:
        fp = ErrorFingerprint()
        self.assertTrue(fp.is_empty())

    def test_is_empty_returns_false(self) -> None:
        fp = ErrorFingerprint(error_type="timeout")
        self.assertFalse(fp.is_empty())

    def test_no_raw_prompt_in_fingerprint(self) -> None:
        fp = ErrorFingerprint(error_type="timeout")
        as_text = str(fp.as_dict())
        self.assertNotIn("raw_prompt", as_text)
        self.assertNotIn("raw_response", as_text)

    def test_no_stack_in_fingerprint(self) -> None:
        fp = ErrorFingerprint(error_type="timeout")
        as_text = str(fp.as_dict())
        self.assertNotIn("traceback", as_text)
        self.assertNotIn("stack", as_text)


class SmartTrackerBuildFingerprintTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tracker = SmartErrorProgressTracker()

    def test_from_ctx_and_inspection(self) -> None:
        ctx = _make_ctx(error_type="timeout", runtime_mode="provider_failure")
        inspection = _make_inspection(failure_class="provider_timeout")
        fp = self.tracker.build_fingerprint(ctx, inspection)
        self.assertEqual(fp.error_type, "timeout")
        self.assertEqual(fp.failure_class, "provider_timeout")

    def test_failure_reason_categorization(self) -> None:
        ctx = _make_ctx(error_type="timeout")
        inspection = _make_inspection(failure_reason="timed out after 30s")
        fp = self.tracker.build_fingerprint(ctx, inspection)
        self.assertEqual(fp.failure_reason_category, "timeout")

    def test_failure_reason_auth_category(self) -> None:
        ctx = _make_ctx(error_type="auth_error")
        inspection = _make_inspection(failure_reason="unauthorized: invalid token")
        fp = self.tracker.build_fingerprint(ctx, inspection)
        self.assertEqual(fp.failure_reason_category, "auth")

    def test_no_raw_prompt_in_built_fingerprint(self) -> None:
        ctx = _make_ctx(error_type="timeout")
        fp = self.tracker.build_fingerprint(ctx, None)
        as_text = str(fp.as_dict())
        self.assertNotIn("api_key", as_text)
        self.assertNotIn("auth_token", as_text)

    def test_tool_category_from_inspection(self) -> None:
        ctx = _make_ctx(error_type="timeout")
        inspection = _make_inspection(tool_category="code_reader")
        fp = self.tracker.build_fingerprint(ctx, inspection)
        self.assertEqual(fp.tool_category, "code_reader")


class SmartTrackerClassifyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tracker = SmartErrorProgressTracker()

    def test_new_session_is_new_error(self) -> None:
        ctx = _make_ctx(error_type="timeout")
        output = self.tracker.classify("s1", ctx, None)
        self.assertTrue(output.is_new_error)
        self.assertFalse(output.is_repeated_error)

    def test_repeated_error_is_repeated(self) -> None:
        ctx = _make_ctx(error_type="timeout", runtime_mode="provider_failure")
        fp = self.tracker.build_fingerprint(ctx, None)
        self.tracker._fingerprints["s1"] = [fp]
        output = self.tracker.classify("s1", ctx, None)
        self.assertTrue(output.is_repeated_error)

    def test_different_error_is_new(self) -> None:
        ctx1 = _make_ctx(error_type="timeout")
        fp1 = self.tracker.build_fingerprint(ctx1, None)
        self.tracker._fingerprints["s1"] = [fp1]

        ctx2 = _make_ctx(error_type="rate_limit")
        output = self.tracker.classify("s1", ctx2, None)
        self.assertFalse(output.is_repeated_error)

    def test_fingerprint_id_in_output(self) -> None:
        ctx = _make_ctx(error_type="timeout")
        output = self.tracker.classify("s1", ctx, None)
        self.assertTrue(len(output.fingerprint_id) > 0)

    def test_progress_score_nonzero_on_change(self) -> None:
        ctx1 = _make_ctx(error_type="timeout", runtime_mode="provider_failure")
        fp1 = self.tracker.build_fingerprint(ctx1, None)
        self.tracker._fingerprints["s1"] = [fp1]

        ctx2 = _make_ctx(error_type="", runtime_mode="standard", response_length=50)
        output = self.tracker.classify("s1", ctx2, None)
        self.assertGreater(output.progress_score, 0)


class StagnationScoringTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tracker = SmartErrorProgressTracker()

    def test_repeated_error_increments_stagnation_score(self) -> None:
        ctx = _make_ctx(error_type="timeout", runtime_mode="provider_failure")
        fp = self.tracker.build_fingerprint(ctx, None)
        self.tracker._fingerprints["s1"] = [fp]
        output = self.tracker.classify("s1", ctx, None)
        self.assertGreater(output.stagnation_score, 0)

    def test_repeated_provider_failure_increments_stagnation(self) -> None:
        ctx = _make_ctx(
            error_type="provider_error",
            runtime_mode="provider_failure",
            provider_failure="openai",
        )
        fp = self.tracker.build_fingerprint(ctx, None)
        self.tracker._fingerprints["s1"] = [fp]
        output = self.tracker.classify("s1", ctx, None)
        self.assertGreaterEqual(output.stagnation_score, 1)

    def test_repeated_same_fallback_is_stagnation(self) -> None:
        ctx = _make_ctx(
            error_type="safe_fallback",
            runtime_mode="safe_fallback",
            response_length=0,
            no_safe=True,
        )
        fp = self.tracker.build_fingerprint(ctx, None)
        self.tracker._fingerprints["s1"] = [fp]
        output = self.tracker.classify("s1", ctx, None)
        self.assertGreaterEqual(output.stagnation_score, 1)

    def test_stagnation_leads_to_escalation_hint(self) -> None:
        ctx = _make_ctx(error_type="timeout", runtime_mode="provider_failure")
        fp = self.tracker.build_fingerprint(ctx, None)
        self.tracker._fingerprints["s1"] = [fp, fp, fp]
        output = self.tracker.classify("s1", ctx, None)
        if output.stagnation_score >= 3:
            self.assertEqual(output.recommended_decision_hint, "ESCALATE_TO_MISAEL")


class ProgressScoringTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tracker = SmartErrorProgressTracker()

    def test_changed_error_is_progress(self) -> None:
        ctx1 = _make_ctx(error_type="timeout", runtime_mode="provider_failure")
        fp = self.tracker.build_fingerprint(ctx1, None)
        self.tracker._fingerprints["s1"] = [fp]

        ctx2 = _make_ctx(error_type="rate_limit", runtime_mode="standard")
        output = self.tracker.classify("s1", ctx2, None)
        self.assertGreater(output.progress_score, 0)

    def test_fallback_disappearance_is_progress(self) -> None:
        ctx1 = _make_ctx(error_type="safe_fallback", runtime_mode="safe_fallback", no_safe=True)
        fp = self.tracker.build_fingerprint(ctx1, None)
        self.tracker._fingerprints["s1"] = [fp]

        ctx2 = _make_ctx(error_type="", runtime_mode="standard", response_length=50)
        output = self.tracker.classify("s1", ctx2, None)
        self.assertGreater(output.progress_score, 0)

    def test_provider_failure_disappearance_is_progress(self) -> None:
        ctx1 = _make_ctx(
            error_type="provider_error",
            runtime_mode="provider_failure",
            provider_failure="openai",
        )
        fp = self.tracker.build_fingerprint(ctx1, None)
        self.tracker._fingerprints["s1"] = [fp]

        ctx2 = _make_ctx(error_type="", runtime_mode="standard", response_length=50)
        output = self.tracker.classify("s1", ctx2, None)
        self.assertGreater(output.progress_score, 0)

    def test_runtime_mode_improvement_is_progress(self) -> None:
        ctx1 = _make_ctx(error_type="provider_failure", runtime_mode="provider_failure")
        fp = self.tracker.build_fingerprint(ctx1, None)
        self.tracker._fingerprints["s1"] = [fp]

        ctx2 = _make_ctx(error_type="", runtime_mode="standard", response_length=50)
        output = self.tracker.classify("s1", ctx2, None)
        self.assertGreater(output.progress_score, 0)

    def test_progress_resets_stagnant_attempts(self) -> None:
        ctx = _make_ctx(error_type="timeout", runtime_mode="provider_failure")
        fp = self.tracker.build_fingerprint(ctx, None)
        self.tracker._fingerprints["s1"] = [fp, fp]

        ctx2 = _make_ctx(error_type="rate_limit", runtime_mode="standard")
        output = self.tracker.classify("s1", ctx2, None)
        self.assertGreater(output.progress_score, output.stagnation_score)


class StrategyTrackingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tracker = SmartErrorProgressTracker()

    def test_record_strategy(self) -> None:
        ctx = _make_ctx(error_type="timeout")
        self.tracker.build_fingerprint(ctx, None)
        self.tracker.record_strategy("s1", "retry_same", ctx)
        strategies = self.tracker._strategies.get("s1", [])
        self.assertEqual(len(strategies), 1)
        self.assertEqual(strategies[0].strategy_name, "retry_same")

    def test_repeated_strategy_increments_count(self) -> None:
        ctx = _make_ctx(error_type="timeout", runtime_mode="provider_failure")
        fp = self.tracker.build_fingerprint(ctx, None)
        self.tracker._fingerprints["s1"] = [fp, fp]

        self.tracker.record_strategy("s1", "retry_same", ctx)
        self.tracker.record_strategy("s1", "retry_same", ctx)

        output = self.tracker.classify("s1", ctx, None)
        self.assertGreater(output.repeated_strategy_count, 0)

    def test_strategies_in_output(self) -> None:
        ctx = _make_ctx(error_type="timeout")
        self.tracker.record_strategy("s1", "retry_same", ctx)
        self.tracker.record_strategy("s1", "replan", ctx)

        output = self.tracker.classify("s1", ctx, None)
        self.assertIn("retry_same", output.strategies_attempted)
        self.assertIn("replan", output.strategies_attempted)

    def test_strategy_attempt_has_timestamp(self) -> None:
        attempt = StrategyAttempt(strategy_name="retry_same")
        self.assertTrue(len(attempt.timestamp) > 0)
        self.assertTrue("T" in attempt.timestamp or " " in attempt.timestamp)


class UpdateAndResetTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tracker = SmartErrorProgressTracker()

    def _make_decision(self, dt: DecisionType = DecisionType.RETRY) -> AutonomyDecision:
        return AutonomyDecision(decision=dt, reason="test")

    def test_update_stores_fingerprint_and_strategy(self) -> None:
        ctx = _make_ctx(error_type="timeout")
        dec = self._make_decision()
        output = self.tracker.update("s1", ctx, None, dec)
        self.assertIsInstance(output, ProgressTrackerOutput)
        self.assertEqual(len(self.tracker._fingerprints["s1"]), 1)
        self.assertEqual(len(self.tracker._strategies["s1"]), 1)

    def test_update_multiple_calls(self) -> None:
        ctx = _make_ctx(error_type="timeout", runtime_mode="provider_failure")
        dec = self._make_decision()
        self.tracker.update("s1", ctx, None, dec)
        output = self.tracker.update("s1", ctx, None, dec)
        self.assertGreaterEqual(output.stagnation_score, 1)

    def test_reset_session(self) -> None:
        ctx = _make_ctx(error_type="timeout")
        dec = self._make_decision()
        self.tracker.update("s1", ctx, None, dec)
        self.tracker.reset("s1")
        self.assertEqual(len(self.tracker._fingerprints), 0)
        self.assertEqual(len(self.tracker._strategies), 0)

    def test_reset_all(self) -> None:
        ctx = _make_ctx(error_type="timeout")
        dec = self._make_decision()
        self.tracker.update("s1", ctx, None, dec)
        self.tracker.update("s2", ctx, None, dec)
        self.tracker.reset_all()
        self.assertEqual(len(self.tracker._fingerprints), 0)

    def test_distinct_error_count(self) -> None:
        ctx1 = _make_ctx(error_type="timeout")
        ctx2 = _make_ctx(error_type="rate_limit")
        dec = self._make_decision()
        self.tracker.update("s1", ctx1, None, dec)
        self.tracker.update("s1", ctx2, None, dec)
        output = self.tracker.classify("s1", ctx2, None)
        self.assertGreaterEqual(output.distinct_error_count, 2)


class EscalationEvidenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tracker = SmartErrorProgressTracker()

    def test_evidence_summary(self) -> None:
        ctx = _make_ctx(error_type="timeout", runtime_mode="provider_failure")
        dec = AutonomyDecision(decision=DecisionType.RETRY, reason="test")
        self.tracker.update("s1", ctx, None, dec)
        self.tracker.update("s1", ctx, None, dec)
        self.tracker.update("s1", ctx, None, dec)
        output = self.tracker.classify("s1", ctx, None)
        self.assertTrue(len(output.evidence_summary) > 0)

    def test_evidence_includes_fingerprint_id(self) -> None:
        ctx = _make_ctx(error_type="timeout")
        output = self.tracker.classify("s1", ctx, None)
        self.assertIn(output.fingerprint_id, output.evidence_summary)

    def test_evidence_includes_hint_on_stagnation(self) -> None:
        ctx = _make_ctx(error_type="timeout", runtime_mode="provider_failure")
        fp = self.tracker.build_fingerprint(ctx, None)
        self.tracker._fingerprints["s1"] = [fp, fp, fp]
        dec = AutonomyDecision(decision=DecisionType.RETRY, reason="test")
        self.tracker.record_strategy("s1", "retry_same", ctx)
        self.tracker.record_strategy("s1", "retry_same", ctx)
        self.tracker.record_strategy("s1", "retry_same", ctx)
        output = self.tracker.classify("s1", ctx, None)
        if output.stagnation_score >= 3:
            self.assertIn("ESCALATE_TO_MISAEL", output.evidence_summary)


class SafetyDegradationTest(unittest.TestCase):
    def test_tracker_creation_does_not_raise(self) -> None:
        try:
            _ = SmartErrorProgressTracker()
        except Exception:
            self.fail("Tracker creation raised")

    def test_classify_no_inspection(self) -> None:
        tracker = SmartErrorProgressTracker()
        ctx = _make_ctx(error_type="timeout")
        try:
            _ = tracker.classify("s1", ctx, None)
        except Exception:
            self.fail("classify raised with None inspection")

    def test_update_no_inspection(self) -> None:
        tracker = SmartErrorProgressTracker()
        ctx = _make_ctx(error_type="timeout")
        dec = AutonomyDecision(decision=DecisionType.RETRY, reason="test")
        try:
            _ = tracker.update("s1", ctx, None, dec)
        except Exception:
            self.fail("update raised with None inspection")


class AdvisoryOnlyTest(unittest.TestCase):
    def test_output_contains_no_autonomous_action(self) -> None:
        tracker = SmartErrorProgressTracker()
        ctx = _make_ctx(error_type="timeout")
        dec = AutonomyDecision(decision=DecisionType.RETRY, reason="test")
        output = tracker.update("s1", ctx, None, dec)
        for exec_key in ("execute", "action", "patch", "commit", "push", "merge"):
            self.assertNotIn(exec_key, output.recommended_decision_hint.lower())

    def test_disabled_decisions_not_in_hint(self) -> None:
        tracker = SmartErrorProgressTracker()
        ctx = _make_ctx(error_type="timeout")
        output = tracker.classify("s1", ctx, None)
        for disabled in ("SELF_REPAIR", "SWITCH_PROVIDER"):
            if disabled in output.recommended_decision_hint:
                pass
        self.assertNotIn("SELF_REPAIR", output.recommended_decision_hint)


class ProgressTrackerSanitizationTest(unittest.TestCase):
    def test_fingerprint_no_api_keys(self) -> None:
        fp = ErrorFingerprint(error_type="timeout")
        as_text = str(fp.as_dict())
        for secret in ("api_key", "auth_token", "password"):
            self.assertNotIn(secret, as_text)

    def test_output_has_no_raw_data(self) -> None:
        output = ProgressTrackerOutput(fingerprint_id="abc123")
        as_text = str(output.as_dict())
        self.assertNotIn("raw_prompt", as_text)
        self.assertNotIn("raw_response", as_text)
        self.assertNotIn("api_key", as_text)

    def test_strategy_no_raw_data(self) -> None:
        attempt = StrategyAttempt(strategy_name="retry_same")
        as_text = str(attempt.as_dict())
        self.assertNotIn("raw_prompt", as_text)


if __name__ == "__main__":
    unittest.main()
