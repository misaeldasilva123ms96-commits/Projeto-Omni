"""Tests for SmartErrorProgressTracker integration into autonomy policy.

Verifies that tracker-aware rules in evaluate_policy() correctly consume
metadata["error_progress_tracker"] and produce appropriate advisory decisions.
"""

from __future__ import annotations

import unittest

from brain.runtime.autonomy import (
    AutonomyContext,
    AutonomyDecision,
    DecisionType,
    evaluate_policy,
)


def _tracker_dict(**kwargs) -> dict:
    base = {
        "fingerprint_id": "abc123",
        "is_new_error": False,
        "is_repeated_error": False,
        "progress_score": 0,
        "stagnation_score": 0,
        "is_progress": False,
        "is_stagnation": False,
        "stagnant_attempts": 0,
        "distinct_error_count": 0,
        "strategies_attempted": [],
        "repeated_strategy_count": 0,
        "recommended_decision_hint": "",
        "evidence_summary": "",
    }
    base.update(kwargs)
    return base


class TrackerDefaultsTest(unittest.TestCase):
    def test_default_constants_defined(self) -> None:
        from brain.runtime.autonomy.autonomy_policy import (
            DEFAULT_TRACKER_STAGNATION_ESCALATE_SCORE,
            DEFAULT_TRACKER_STAGNANT_ATTEMPTS_THRESHOLD,
            DEFAULT_TRACKER_REPEATED_STRATEGY_THRESHOLD,
            DEFAULT_TRACKER_STAGNATION_MODERATE_SCORE,
        )
        self.assertEqual(DEFAULT_TRACKER_STAGNATION_ESCALATE_SCORE, 5)
        self.assertEqual(DEFAULT_TRACKER_STAGNANT_ATTEMPTS_THRESHOLD, 3)
        self.assertEqual(DEFAULT_TRACKER_REPEATED_STRATEGY_THRESHOLD, 3)
        self.assertEqual(DEFAULT_TRACKER_STAGNATION_MODERATE_SCORE, 3)

    def test_no_tracker_data_preserves_behavior(self) -> None:
        ctx = AutonomyContext()
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.CONTINUE)

    def test_empty_tracker_dict_preserves_behavior(self) -> None:
        ctx = AutonomyContext(metadata={"error_progress_tracker": {}})
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.CONTINUE)

    def test_partial_tracker_dict_ignores_missing_keys(self) -> None:
        ctx = AutonomyContext(metadata={"error_progress_tracker": {"fingerprint_id": "x"}})
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.CONTINUE)


class TrackerSafetyGatesWinTest(unittest.TestCase):
    def test_safety_gate_still_wins_over_tracker(self) -> None:
        ctx = AutonomyContext(
            secret_detected=True,
            metadata={
                "error_progress_tracker": _tracker_dict(
                    stagnation_score=10,
                    is_stagnation=True,
                    stagnant_attempts=5,
                )
            },
        )
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)
        self.assertIn("Secret detected", decision.reason)

    def test_no_safe_next_action_still_wins(self) -> None:
        ctx = AutonomyContext(
            no_safe_next_action=True,
            metadata={
                "error_progress_tracker": _tracker_dict(
                    progress_score=5,
                    is_progress=True,
                )
            },
        )
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.ABORT_SAFE)


class TrackerHighStagnationEscalateTest(unittest.TestCase):
    def test_high_stagnation_escalates(self) -> None:
        ctx = AutonomyContext(
            metadata={
                "error_progress_tracker": _tracker_dict(
                    stagnation_score=7,
                    is_stagnation=True,
                    stagnant_attempts=5,
                )
            },
        )
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)
        self.assertIn("high stagnation", decision.reason.lower())
        self.assertIn("score=7", decision.reason)
        self.assertIn("attempts=5", decision.reason)

    def test_high_stagnation_at_threshold(self) -> None:
        ctx = AutonomyContext(
            metadata={
                "error_progress_tracker": _tracker_dict(
                    stagnation_score=5,
                    is_stagnation=True,
                    stagnant_attempts=3,
                )
            },
        )
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)

    def test_high_stagnation_below_threshold_cascades_to_persistent(self) -> None:
        ctx = AutonomyContext(
            metadata={
                "error_progress_tracker": _tracker_dict(
                    stagnation_score=5,
                    is_stagnation=True,
                    stagnant_attempts=2,
                )
            },
        )
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)
        self.assertIn("persistent stagnation", decision.reason.lower())

    def test_high_stagnation_low_score_cascades_to_persistent(self) -> None:
        ctx = AutonomyContext(
            metadata={
                "error_progress_tracker": _tracker_dict(
                    stagnation_score=4,
                    is_stagnation=True,
                    stagnant_attempts=5,
                )
            },
        )
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)
        self.assertIn("persistent stagnation", decision.reason.lower())


class TrackerRepeatedStrategyReplanTest(unittest.TestCase):
    def test_repeated_strategy_triggers_replan(self) -> None:
        ctx = AutonomyContext(
            metadata={
                "error_progress_tracker": _tracker_dict(
                    repeated_strategy_count=4,
                )
            },
        )
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.REPLAN)
        self.assertIn("same strategy repeated", decision.reason.lower())

    def test_repeated_strategy_at_threshold(self) -> None:
        ctx = AutonomyContext(
            metadata={
                "error_progress_tracker": _tracker_dict(
                    repeated_strategy_count=3,
                )
            },
        )
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.REPLAN)

    def test_repeated_strategy_below_threshold(self) -> None:
        ctx = AutonomyContext(
            metadata={
                "error_progress_tracker": _tracker_dict(
                    repeated_strategy_count=2,
                )
            },
        )
        decision = evaluate_policy(ctx)
        self.assertNotEqual(decision.decision, DecisionType.REPLAN)


class TrackerPersistentStagnationEscalateTest(unittest.TestCase):
    def test_persistent_stagnation_escalates(self) -> None:
        ctx = AutonomyContext(
            metadata={
                "error_progress_tracker": _tracker_dict(
                    stagnation_score=3,
                    is_stagnation=True,
                    stagnant_attempts=1,
                )
            },
        )
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)
        self.assertIn("persistent stagnation", decision.reason.lower())

    def test_moderate_stagnation_below_threshold(self) -> None:
        ctx = AutonomyContext(
            metadata={
                "error_progress_tracker": _tracker_dict(
                    stagnation_score=2,
                    is_stagnation=True,
                    stagnant_attempts=1,
                )
            },
        )
        decision = evaluate_policy(ctx)
        self.assertNotEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)

    def test_not_stagnation_does_not_escalate(self) -> None:
        ctx = AutonomyContext(
            metadata={
                "error_progress_tracker": _tracker_dict(
                    stagnation_score=3,
                    is_stagnation=False,
                )
            },
        )
        decision = evaluate_policy(ctx)
        self.assertNotEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)


class TrackerStagnationRetryTest(unittest.TestCase):
    def test_stagnation_low_triggers_retry(self) -> None:
        ctx = AutonomyContext(
            metadata={
                "error_progress_tracker": _tracker_dict(
                    stagnation_score=1,
                    is_stagnation=True,
                    stagnant_attempts=1,
                )
            },
        )
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.RETRY)
        self.assertIn("stagnation detected", decision.reason.lower())

    def test_stagnation_without_is_stagnation_flag(self) -> None:
        ctx = AutonomyContext(
            metadata={
                "error_progress_tracker": _tracker_dict(
                    stagnation_score=1,
                    is_stagnation=False,
                )
            },
        )
        decision = evaluate_policy(ctx)
        self.assertNotEqual(decision.decision, DecisionType.RETRY)


class TrackerProgressContinueTest(unittest.TestCase):
    def test_progress_triggers_continue(self) -> None:
        ctx = AutonomyContext(
            error_count=0,
            metadata={
                "error_progress_tracker": _tracker_dict(
                    progress_score=5,
                    is_progress=True,
                )
            },
        )
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.CONTINUE)
        self.assertIn("progress detected", decision.reason.lower())

    def test_progress_with_errors_does_not_short_circuit(self) -> None:
        ctx = AutonomyContext(
            error_count=1,
            error_type="ValueError",
            metadata={
                "error_progress_tracker": _tracker_dict(
                    progress_score=5,
                    is_progress=True,
                )
            },
        )
        decision = evaluate_policy(ctx)
        self.assertNotEqual(decision.decision, DecisionType.CONTINUE)

    def test_progress_zero_score_does_not_trigger(self) -> None:
        ctx = AutonomyContext(
            error_count=0,
            metadata={
                "error_progress_tracker": _tracker_dict(
                    progress_score=0,
                    is_progress=False,
                )
            },
        )
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.CONTINUE)


class TrackerEvidenceInMetadataTest(unittest.TestCase):
    def test_evidence_included_on_escalation(self) -> None:
        ctx = AutonomyContext(
            metadata={
                "error_progress_tracker": _tracker_dict(
                    stagnation_score=7,
                    is_stagnation=True,
                    stagnant_attempts=5,
                    evidence_summary="Stuck on same error for 5 attempts.",
                )
            },
        )
        decision = evaluate_policy(ctx)
        meta = decision.metadata
        self.assertIsNotNone(meta)
        if meta:
            self.assertIn("evidence_summary", meta)
            self.assertEqual(meta["evidence_summary"], "Stuck on same error for 5 attempts.")

    def test_evidence_included_on_replan(self) -> None:
        ctx = AutonomyContext(
            metadata={
                "error_progress_tracker": _tracker_dict(
                    repeated_strategy_count=4,
                    evidence_summary="Strategy 'retry' used 4 times.",
                )
            },
        )
        decision = evaluate_policy(ctx)
        meta = decision.metadata
        self.assertIsNotNone(meta)
        if meta:
            self.assertIn("evidence_summary", meta)

    def test_no_evidence_when_empty(self) -> None:
        ctx = AutonomyContext(
            metadata={
                "error_progress_tracker": _tracker_dict(
                    stagnation_score=7,
                    is_stagnation=True,
                    stagnant_attempts=5,
                    evidence_summary="",
                )
            },
        )
        decision = evaluate_policy(ctx)
        meta = decision.metadata
        if meta:
            self.assertNotIn("evidence_summary", meta)


class TrackerPriorityOrderTest(unittest.TestCase):
    def test_tracker_high_stagnation_before_existing_stagnation(self) -> None:
        ctx = AutonomyContext(
            stagnation_count=5,
            metadata={
                "error_progress_tracker": _tracker_dict(
                    stagnation_score=7,
                    is_stagnation=True,
                    stagnant_attempts=5,
                )
            },
        )
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)
        self.assertIn("smart tracker", decision.reason.lower())

    def test_tracker_repeated_before_multiple_distinct(self) -> None:
        ctx = AutonomyContext(
            error_count=2,
            error_type="ValueError",
            distinct_errors=2,
            metadata={
                "error_progress_tracker": _tracker_dict(
                    repeated_strategy_count=4,
                )
            },
        )
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.REPLAN)
        self.assertIn("smart tracker", decision.reason.lower())


class TrackerCustomThresholdsTest(unittest.TestCase):
    def test_custom_stagnation_escalate_score(self) -> None:
        ctx = AutonomyContext(
            metadata={
                "error_progress_tracker": _tracker_dict(
                    stagnation_score=3,
                    is_stagnation=True,
                    stagnant_attempts=2,
                )
            },
        )
        decision = evaluate_policy(
            ctx,
            tracker_stagnation_escalate_score=3,
            tracker_stagnant_attempts_threshold=2,
        )
        self.assertEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)

    def test_custom_repeated_strategy_threshold(self) -> None:
        ctx = AutonomyContext(
            metadata={
                "error_progress_tracker": _tracker_dict(
                    repeated_strategy_count=2,
                )
            },
        )
        decision = evaluate_policy(ctx, tracker_repeated_strategy_threshold=2)
        self.assertEqual(decision.decision, DecisionType.REPLAN)

    def test_custom_stagnation_moderate_score(self) -> None:
        ctx = AutonomyContext(
            metadata={
                "error_progress_tracker": _tracker_dict(
                    stagnation_score=2,
                    is_stagnation=True,
                    stagnant_attempts=1,
                )
            },
        )
        decision = evaluate_policy(ctx, tracker_stagnation_moderate_score=2)
        self.assertEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)


class TrackerIntegrationTest(unittest.TestCase):
    def test_receipt_still_builds_with_tracker_data(self) -> None:
        from brain.runtime.autonomy import build_receipt
        ctx = AutonomyContext(
            metadata={
                "error_progress_tracker": _tracker_dict(
                    progress_score=5,
                    is_progress=True,
                )
            },
        )
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.CONTINUE)
        receipt = build_receipt(decision)
        self.assertTrue(receipt.receipt_id)
        self.assertEqual(receipt.decision, "CONTINUE")

    def test_decision_metadata_preserved_in_receipt(self) -> None:
        from brain.runtime.autonomy import build_receipt
        ctx = AutonomyContext(
            metadata={
                "error_progress_tracker": _tracker_dict(
                    stagnation_score=7,
                    is_stagnation=True,
                    stagnant_attempts=5,
                    evidence_summary="Test evidence.",
                )
            },
        )
        decision = evaluate_policy(ctx)
        receipt = build_receipt(decision)
        self.assertIn("evidence_summary", decision.metadata)
        self.assertIn("evidence_summary", receipt.metadata)


class TrackerNonDictMetadataTest(unittest.TestCase):
    def test_non_dict_tracker_metadata_ignored(self) -> None:
        ctx = AutonomyContext(
            metadata={"error_progress_tracker": "not_a_dict"},
        )
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.CONTINUE)

    def test_missing_tracker_key_ignored(self) -> None:
        ctx = AutonomyContext(
            metadata={"some_other_key": 42},
        )
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.CONTINUE)


if __name__ == "__main__":
    unittest.main()
