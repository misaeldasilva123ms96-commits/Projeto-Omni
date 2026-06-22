"""Tests for the governed Autonomy Controller.

Tests cover all decision types, policy evaluation, receipt generation,
escalation reports, safe defaults, advisory-only behavior, and
disabled decisions.
"""

from __future__ import annotations

import unittest

from brain.runtime.autonomy import (
    ADVISORY_ONLY_DECISIONS,
    DECISION_RISK_MAP,
    DISABLED_DECISIONS,
    AutonomyController,
    AutonomyContext,
    AutonomyDecision,
    AutonomyReceipt,
    AutonomyReceiptLog,
    DecisionType,
    EscalationReport,
    build_escalation_report,
    build_receipt,
    evaluate_policy,
)


class DecisionTypeTest(unittest.TestCase):
    def test_all_decisions_defined(self) -> None:
        expected = {
            "CONTINUE",
            "RETRY",
            "REPLAN",
            "SELF_REPAIR",
            "SWITCH_PROVIDER",
            "PAUSE",
            "ESCALATE_TO_MISAEL",
            "ABORT_SAFE",
        }
        actual = {d.value for d in DecisionType}
        self.assertEqual(actual, expected)

    def test_advisory_only_does_not_include_risky(self) -> None:
        self.assertNotIn(DecisionType.SELF_REPAIR, ADVISORY_ONLY_DECISIONS)
        self.assertNotIn(DecisionType.SWITCH_PROVIDER, ADVISORY_ONLY_DECISIONS)

    def test_disabled_decisions_are_defined(self) -> None:
        self.assertIn(DecisionType.SELF_REPAIR, DISABLED_DECISIONS)
        self.assertIn(DecisionType.SWITCH_PROVIDER, DISABLED_DECISIONS)

    def test_risk_map_covers_all(self) -> None:
        for dt in DecisionType:
            self.assertIn(dt, DECISION_RISK_MAP)


class ContinueDecisionTest(unittest.TestCase):
    def test_continue_no_errors(self) -> None:
        ctx = AutonomyContext()
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.CONTINUE)
        self.assertTrue(decision.advisory)

    def test_continue_non_supervised_level(self) -> None:
        ctx = AutonomyContext()
        decision = evaluate_policy(ctx, autonomy_level="L1_ADVISORY")
        self.assertEqual(decision.decision, DecisionType.CONTINUE)
        self.assertTrue(decision.advisory)


class RetryDecisionTest(unittest.TestCase):
    def test_retry_on_error(self) -> None:
        ctx = AutonomyContext(
            error_type="ValueError",
            error_count=1,
        )
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.RETRY)
        self.assertTrue(decision.advisory)

    def test_retry_on_transient_error(self) -> None:
        ctx = AutonomyContext(
            error_type="timeout",
            error_count=1,
        )
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.RETRY)

    def test_retry_on_rate_limit(self) -> None:
        ctx = AutonomyContext(
            error_type="rate_limit_exceeded",
            error_count=1,
        )
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.RETRY)


class ReplanDecisionTest(unittest.TestCase):
    def test_replan_on_multiple_distinct_errors(self) -> None:
        ctx = AutonomyContext(
            error_type="ValueError",
            error_count=2,
            distinct_errors=2,
        )
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.REPLAN)
        self.assertTrue(decision.advisory)


class PauseDecisionTest(unittest.TestCase):
    def test_pause_on_cycle_limit(self) -> None:
        ctx = AutonomyContext(
            total_progressive_cycles=50,
        )
        decision = evaluate_policy(ctx, max_total_progressive_cycles=50)
        self.assertEqual(decision.decision, DecisionType.PAUSE)
        self.assertTrue(decision.advisory)


class EscalateToMisaelDecisionTest(unittest.TestCase):
    def test_escalate_on_secret_detected(self) -> None:
        ctx = AutonomyContext(secret_detected=True)
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)

    def test_escalate_on_protected_file(self) -> None:
        ctx = AutonomyContext(protected_file_involved=True)
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)

    def test_escalate_on_unsafe_ci(self) -> None:
        ctx = AutonomyContext(unsafe_ci_signal=True)
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)

    def test_escalate_on_security_signal(self) -> None:
        ctx = AutonomyContext(security_signal=True)
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)

    def test_escalate_on_conflict(self) -> None:
        ctx = AutonomyContext(conflict_detected=True)
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)

    def test_escalate_on_production_action(self) -> None:
        ctx = AutonomyContext(production_action_required=True)
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)

    def test_escalate_on_direct_main_push(self) -> None:
        ctx = AutonomyContext(direct_main_push_attempted=True)
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)

    def test_escalate_on_merge_attempt(self) -> None:
        ctx = AutonomyContext(merge_attempted=True)
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)

    def test_escalate_on_stagnation(self) -> None:
        ctx = AutonomyContext(stagnation_count=5)
        decision = evaluate_policy(ctx, escalate_after_stagnation=5)
        self.assertEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)

    def test_escalate_on_max_attempts(self) -> None:
        ctx = AutonomyContext(
            error_type="ValueError",
            error_count=5,
            consecutive_same_error=3,
        )
        decision = evaluate_policy(ctx, max_attempts_per_error=5)
        self.assertEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)

    def test_escalate_on_distinct_strategies_failed(self) -> None:
        ctx = AutonomyContext(distinct_errors=3)
        decision = evaluate_policy(ctx, max_stagnant_attempts=3)
        self.assertEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)


class AbortSafeDecisionTest(unittest.TestCase):
    def test_abort_safe_on_no_safe_next_action(self) -> None:
        ctx = AutonomyContext(no_safe_next_action=True)
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.ABORT_SAFE)
        self.assertTrue(decision.advisory)


class DisabledDecisionsTest(unittest.TestCase):
    def test_self_repair_falls_back_to_continue(self) -> None:
        ctx = AutonomyContext()
        from brain.runtime.autonomy.autonomy_policy import _make_decision
        from brain.runtime.autonomy.autonomy_models import DISABLED_DECISIONS

        decision = _make_decision(DecisionType.SELF_REPAIR, "test", ctx)
        self.assertEqual(decision.decision, DecisionType.CONTINUE)
        self.assertIn("disabled", decision.reason.lower())

    def test_switch_provider_falls_back_to_continue(self) -> None:
        ctx = AutonomyContext()
        from brain.runtime.autonomy.autonomy_policy import _make_decision

        decision = _make_decision(DecisionType.SWITCH_PROVIDER, "test", ctx)
        self.assertEqual(decision.decision, DecisionType.CONTINUE)
        self.assertIn("disabled", decision.reason.lower())


class SafeDefaultsTest(unittest.TestCase):
    def test_default_autonomy_level_is_supervised(self) -> None:
        from brain.runtime.autonomy.autonomy_policy import DEFAULT_AUTONOMY_LEVEL
        self.assertEqual(DEFAULT_AUTONOMY_LEVEL, "supervised")

    def test_default_max_attempts(self) -> None:
        from brain.runtime.autonomy.autonomy_policy import DEFAULT_MAX_ATTEMPTS_PER_ERROR
        self.assertEqual(DEFAULT_MAX_ATTEMPTS_PER_ERROR, 5)

    def test_default_stagnation_settings(self) -> None:
        from brain.runtime.autonomy.autonomy_policy import (
            DEFAULT_MAX_STAGNANT_ATTEMPTS,
            DEFAULT_ESCALATE_AFTER_STAGNATION,
        )
        self.assertEqual(DEFAULT_MAX_STAGNANT_ATTEMPTS, 3)
        self.assertEqual(DEFAULT_ESCALATE_AFTER_STAGNATION, 5)

    def test_default_cycle_limit(self) -> None:
        from brain.runtime.autonomy.autonomy_policy import DEFAULT_MAX_TOTAL_PROGRESSIVE_CYCLES
        self.assertEqual(DEFAULT_MAX_TOTAL_PROGRESSIVE_CYCLES, 50)


class AdvisoryOnlyBehaviorTest(unittest.TestCase):
    def test_all_decisions_are_advisory_true(self) -> None:
        ctx = AutonomyContext()
        decision = evaluate_policy(ctx)
        self.assertTrue(decision.advisory)

    def test_receipt_marks_advisory(self) -> None:
        ctx = AutonomyContext()
        decision = evaluate_policy(ctx)
        receipt = build_receipt(decision)
        self.assertTrue(receipt.advisory)

    def test_controller_marks_advisory(self) -> None:
        controller = AutonomyController()
        ctx = AutonomyContext()
        decision = controller.decide(ctx)
        self.assertTrue(decision.advisory)
        self.assertTrue(decision.decision == DecisionType.CONTINUE)


class ReceiptGenerationTest(unittest.TestCase):
    def test_receipt_has_required_fields(self) -> None:
        ctx = AutonomyContext()
        decision = evaluate_policy(ctx)
        receipt = build_receipt(decision)
        self.assertTrue(receipt.receipt_id)
        self.assertEqual(receipt.decision_id, decision.decision_id)
        self.assertEqual(receipt.decision, decision.decision.value)
        self.assertEqual(receipt.risk_level, decision.risk_level)
        self.assertTrue(receipt.reason)

    def test_receipt_log_tracks_multiple_decisions(self) -> None:
        log = AutonomyReceiptLog()
        self.assertIsNone(log.last())

        ctx1 = AutonomyContext(secret_detected=True)
        d1 = evaluate_policy(ctx1)
        r1 = build_receipt(d1)
        log.add(r1)

        ctx2 = AutonomyContext(error_type="timeout", error_count=1)
        d2 = evaluate_policy(ctx2)
        r2 = build_receipt(d2)
        log.add(r2)

        self.assertEqual(log.count(), 2)
        self.assertIsNotNone(log.last())
        if log.last():
            self.assertEqual(log.last().decision, d2.decision.value)

    def test_receipt_log_count_by_decision(self) -> None:
        log = AutonomyReceiptLog()
        for _ in range(3):
            ctx = AutonomyContext()
            d = evaluate_policy(ctx)
            log.add(build_receipt(d))
        self.assertEqual(log.count(decision=DecisionType.CONTINUE), 3)
        self.assertEqual(log.count(decision=DecisionType.RETRY), 0)

    def test_receipt_log_all_as_dict(self) -> None:
        log = AutonomyReceiptLog()
        ctx = AutonomyContext()
        d = evaluate_policy(ctx)
        log.add(build_receipt(d))
        entries = log.all_as_dict()
        self.assertEqual(len(entries), 1)
        self.assertIn("receipt_id", entries[0])
        self.assertIn("decision", entries[0])


class EscalationReportTest(unittest.TestCase):
    def test_escalation_report_builds(self) -> None:
        ctx = AutonomyContext(secret_detected=True)
        decision = evaluate_policy(ctx)
        report = build_escalation_report(decision, ctx)
        self.assertIsInstance(report, EscalationReport)
        self.assertEqual(report.escalation_category, "secret_detected")
        self.assertEqual(report.decision_id, decision.decision_id)
        self.assertTrue(report.report_id)

    def test_escalation_report_protected_file(self) -> None:
        ctx = AutonomyContext(protected_file_involved=True)
        decision = evaluate_policy(ctx)
        report = build_escalation_report(decision, ctx)
        self.assertEqual(report.escalation_category, "protected_file")

    def test_escalation_report_stagnation(self) -> None:
        ctx = AutonomyContext(stagnation_count=5)
        decision = evaluate_policy(ctx, escalate_after_stagnation=5)
        report = build_escalation_report(decision, ctx)
        self.assertEqual(report.escalation_category, "stagnation")

    def test_escalation_report_unsafe_ci(self) -> None:
        ctx = AutonomyContext(unsafe_ci_signal=True)
        decision = evaluate_policy(ctx)
        report = build_escalation_report(decision, ctx)
        self.assertEqual(report.escalation_category, "unsafe_ci")

    def test_escalation_report_conflict(self) -> None:
        ctx = AutonomyContext(conflict_detected=True)
        decision = evaluate_policy(ctx)
        report = build_escalation_report(decision, ctx)
        self.assertEqual(report.escalation_category, "conflict")

    def test_escalation_report_main_push(self) -> None:
        ctx = AutonomyContext(direct_main_push_attempted=True)
        decision = evaluate_policy(ctx)
        report = build_escalation_report(decision, ctx)
        self.assertEqual(report.escalation_category, "main_push_attempt")

    def test_escalation_report_raises_on_non_escalation(self) -> None:
        ctx = AutonomyContext()
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.CONTINUE)
        with self.assertRaises(ValueError):
            build_escalation_report(decision, ctx)

    def test_abort_safe_does_not_produce_escalation_report(self) -> None:
        ctx = AutonomyContext(no_safe_next_action=True)
        decision = evaluate_policy(ctx)
        self.assertEqual(decision.decision, DecisionType.ABORT_SAFE)
        with self.assertRaises(ValueError):
            build_escalation_report(decision, ctx)

    def test_escalation_report_as_dict(self) -> None:
        ctx = AutonomyContext(secret_detected=True)
        decision = evaluate_policy(ctx)
        report = build_escalation_report(decision, ctx)
        d = report.as_dict()
        self.assertIn("report_id", d)
        self.assertIn("escalation_category", d)
        self.assertIn("reason", d)


class ControllerIntegrationTest(unittest.TestCase):
    def test_controller_decide_returns_decision(self) -> None:
        ctrl = AutonomyController()
        ctx = AutonomyContext()
        decision = ctrl.decide(ctx)
        self.assertIsInstance(decision, AutonomyDecision)

    def test_controller_tracks_receipts(self) -> None:
        ctrl = AutonomyController()
        ctx1 = AutonomyContext()
        ctrl.decide(ctx1)
        ctx2 = AutonomyContext(error_type="timeout", error_count=1)
        ctrl.decide(ctx2)
        self.assertEqual(ctrl.receipt_log.count(), 2)

    def test_controller_decide_with_report_escalation(self) -> None:
        ctrl = AutonomyController()
        ctx = AutonomyContext(secret_detected=True)
        decision, receipt, escalation = ctrl.decide_with_report(ctx)
        self.assertEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)
        self.assertIsNotNone(escalation)
        if escalation:
            self.assertEqual(escalation.escalation_category, "secret_detected")

    def test_controller_decide_with_report_no_escalation(self) -> None:
        ctrl = AutonomyController()
        ctx = AutonomyContext()
        decision, receipt, escalation = ctrl.decide_with_report(ctx)
        self.assertEqual(decision.decision, DecisionType.CONTINUE)
        self.assertIsNone(escalation)

    def test_controller_custom_config(self) -> None:
        ctrl = AutonomyController(
            autonomy_level="L0_READ_ONLY",
            max_attempts_per_error=2,
            max_stagnant_attempts=2,
        )
        self.assertEqual(ctrl.autonomy_level, "L0_READ_ONLY")

    def test_controller_property_access(self) -> None:
        ctrl = AutonomyController()
        self.assertEqual(ctrl.autonomy_level, "supervised")


class DecisionModelSerializationTest(unittest.TestCase):
    def test_autonomy_context_as_dict(self) -> None:
        ctx = AutonomyContext(
            session_id="s1",
            error_type="timeout",
            error_count=3,
            secret_detected=True,
        )
        d = ctx.as_dict()
        self.assertEqual(d["session_id"], "s1")
        self.assertEqual(d["error_type"], "timeout")
        self.assertEqual(d["error_count"], 3)
        self.assertTrue(d["secret_detected"])

    def test_autonomy_decision_as_dict(self) -> None:
        ctx = AutonomyContext(error_type="timeout", error_count=1)
        decision = evaluate_policy(ctx)
        d = decision.as_dict()
        self.assertEqual(d["decision"], "RETRY")
        self.assertTrue(d["advisory"])
        self.assertIn("decision_id", d)
        self.assertIn("created_at", d)
        self.assertIn("context_snapshot", d)

    def test_receipt_as_dict(self) -> None:
        ctx = AutonomyContext()
        decision = evaluate_policy(ctx)
        receipt = build_receipt(decision)
        d = receipt.as_dict()
        self.assertIn("receipt_id", d)
        self.assertIn("decision", d)
        self.assertIn("created_at", d)

    def test_escalation_report_as_dict(self) -> None:
        ctx = AutonomyContext(secret_detected=True)
        decision = evaluate_policy(ctx)
        report = build_escalation_report(decision, ctx)
        d = report.as_dict()
        self.assertIn("report_id", d)
        self.assertIn("escalation_category", d)


class EdgeCasesTest(unittest.TestCase):
    def test_controller_decide_with_empty_context(self) -> None:
        ctrl = AutonomyController()
        ctx = AutonomyContext()
        decision = ctrl.decide(ctx)
        self.assertEqual(decision.decision, DecisionType.CONTINUE)

    def test_error_count_less_than_max_returns_retry(self) -> None:
        ctx = AutonomyContext(error_type="Timeout", error_count=1)
        decision = evaluate_policy(ctx, max_attempts_per_error=5)
        self.assertEqual(decision.decision, DecisionType.RETRY)

    def test_consecutive_same_error_at_max_escalates(self) -> None:
        ctx = AutonomyContext(
            error_type="ValueError",
            error_count=5,
            consecutive_same_error=5,
        )
        decision = evaluate_policy(ctx, max_attempts_per_error=5)
        self.assertEqual(decision.decision, DecisionType.ESCALATE_TO_MISAEL)

    def test_context_snapshot_in_decision(self) -> None:
        ctx = AutonomyContext(error_type="timeout", error_count=2)
        decision = evaluate_policy(ctx)
        snapshot = decision.context_snapshot
        self.assertEqual(snapshot.get("error_type"), "timeout")
        self.assertEqual(snapshot.get("error_count"), 2)

    def test_receipt_has_decision_id_matching(self) -> None:
        ctx = AutonomyContext()
        decision = evaluate_policy(ctx)
        receipt = build_receipt(decision)
        self.assertEqual(receipt.decision_id, decision.decision_id)


if __name__ == "__main__":
    unittest.main()
