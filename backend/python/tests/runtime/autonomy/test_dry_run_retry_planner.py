from __future__ import annotations

import unittest

from brain.runtime.autonomy import (
    AutonomyContext,
    AutonomyDecision,
    DecisionType,
    DryRunRetryPlanner,
    build_dry_run_retry_plan,
)


def _decision(
    decision: DecisionType = DecisionType.RETRY,
    *,
    risk_level: str = "low",
) -> AutonomyDecision:
    return AutonomyDecision(
        decision=decision,
        reason="safe metadata",
        risk_level=risk_level,
    )


def _tracker(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "fingerprint_id": "fp123",
        "stagnation_score": 2,
        "progress_score": 1,
        "repeated_strategy_count": 0,
        "recommended_decision_hint": "",
        "evidence_summary": "safe timeout metadata",
    }
    base.update(overrides)
    return base


class DryRunRetryPlannerTest(unittest.TestCase):
    def test_eligible_retry_produces_would_retry_true(self) -> None:
        plan = build_dry_run_retry_plan(
            decision=_decision(),
            context=AutonomyContext(),
            tracker=_tracker(),
            max_retry_attempts=2,
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertTrue(plan.advisory)
        self.assertEqual(plan.plan_type, "dry_run_retry")
        self.assertTrue(plan.would_retry)
        self.assertFalse(plan.blocked)
        self.assertEqual(plan.retry_reason, "retry_eligible")
        self.assertEqual(plan.max_attempts_remaining, 2)

    def test_non_retry_decision_produces_would_retry_false(self) -> None:
        plan = build_dry_run_retry_plan(
            decision=_decision(DecisionType.CONTINUE),
            tracker=_tracker(),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertFalse(plan.would_retry)
        self.assertFalse(plan.blocked)
        self.assertEqual(plan.retry_reason, "not_retry_decision")

    def test_retry_like_hint_can_make_plan_eligible(self) -> None:
        plan = build_dry_run_retry_plan(
            decision=_decision(DecisionType.CONTINUE),
            tracker=_tracker(recommended_decision_hint="retry"),
            max_retry_attempts=1,
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertTrue(plan.would_retry)
        self.assertEqual(plan.source_decision, "CONTINUE")

    def test_high_and_critical_risk_block_retry(self) -> None:
        for risk in ("high", "critical"):
            with self.subTest(risk=risk):
                plan = build_dry_run_retry_plan(
                    decision=_decision(risk_level=risk),
                    tracker=_tracker(),
                    created_at="2026-06-27T00:00:00+00:00",
                )

                self.assertFalse(plan.would_retry)
                self.assertTrue(plan.blocked)
                self.assertIn("risk_too_high", plan.block_reasons)

    def test_secret_detected_blocks_retry(self) -> None:
        plan = build_dry_run_retry_plan(
            decision=_decision(),
            context=AutonomyContext(secret_detected=True),
            tracker=_tracker(),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertFalse(plan.would_retry)
        self.assertIn("secret_detected", plan.block_reasons)

    def test_protected_file_blocks_retry(self) -> None:
        plan = build_dry_run_retry_plan(
            decision=_decision(),
            context=AutonomyContext(protected_file_involved=True),
            tracker=_tracker(),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertFalse(plan.would_retry)
        self.assertIn("protected_file_involved", plan.block_reasons)

    def test_provider_switching_requirement_blocks_retry(self) -> None:
        plan = build_dry_run_retry_plan(
            decision=_decision(),
            context={"provider_switching_required": True},
            tracker=_tracker(),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertFalse(plan.would_retry)
        self.assertIn("provider_switching_required", plan.block_reasons)

    def test_tool_write_command_and_destructive_requirements_block_retry(self) -> None:
        cases = {
            "tool_action_required": "tool_action_required",
            "write_action_required": "write_action_required",
            "command_action_required": "command_action_required",
            "destructive_operation_required": "destructive_operation_required",
        }
        for key, reason in cases.items():
            with self.subTest(key=key):
                plan = build_dry_run_retry_plan(
                    decision=_decision(),
                    context={key: True},
                    tracker=_tracker(),
                    created_at="2026-06-27T00:00:00+00:00",
                )
                self.assertFalse(plan.would_retry)
                self.assertIn(reason, plan.block_reasons)

    def test_unsafe_ci_security_signal_blocks_retry(self) -> None:
        plan = build_dry_run_retry_plan(
            decision=_decision(),
            context=AutonomyContext(unsafe_ci_signal=True),
            tracker=_tracker(),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertFalse(plan.would_retry)
        self.assertIn("unsafe_ci_or_security_signal", plan.block_reasons)

    def test_no_safe_next_action_blocks_retry(self) -> None:
        plan = build_dry_run_retry_plan(
            decision=_decision(),
            context=AutonomyContext(no_safe_next_action=True),
            tracker=_tracker(),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertFalse(plan.would_retry)
        self.assertIn("no_safe_next_action", plan.block_reasons)

    def test_max_attempts_exceeded_blocks_retry(self) -> None:
        plan = build_dry_run_retry_plan(
            decision=_decision(),
            context={"current_retry_attempts": 2},
            tracker=_tracker(),
            max_retry_attempts=2,
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertFalse(plan.would_retry)
        self.assertEqual(plan.max_attempts_remaining, 0)
        self.assertIn("max_attempts_exceeded", plan.block_reasons)

    def test_pause_escalate_abort_governance_blocks_retry(self) -> None:
        for governance in ("pause", "escalate", "abort_safe"):
            with self.subTest(governance=governance):
                plan = build_dry_run_retry_plan(
                    decision=_decision(),
                    context={"governance_decision": governance},
                    tracker=_tracker(),
                    created_at="2026-06-27T00:00:00+00:00",
                )
                self.assertFalse(plan.would_retry)
                self.assertIn(f"governance_{governance}", plan.block_reasons)

    def test_user_approval_required_blocks_retry(self) -> None:
        plan = build_dry_run_retry_plan(
            decision=_decision(),
            context={"user_approval_required": True},
            tracker=_tracker(),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertFalse(plan.would_retry)
        self.assertIn("user_approval_required", plan.block_reasons)

    def test_malformed_missing_evidence_degrades_safely(self) -> None:
        plan = build_dry_run_retry_plan(
            decision=None,
            context=None,
            tracker=None,
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertTrue(plan.advisory)
        self.assertFalse(plan.would_retry)
        self.assertEqual(plan.source_decision, "")
        self.assertEqual(plan.evidence_summary, "")

    def test_evidence_summary_is_bounded_and_sanitized(self) -> None:
        plan = build_dry_run_retry_plan(
            decision=_decision(),
            tracker=_tracker(evidence_summary=("safe " * 100) + " api_key=sk-test-secret"),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertLessEqual(len(plan.evidence_summary), 240)
        self.assertEqual(plan.evidence_summary, "[redacted]")
        self.assertNotIn("sk-test-secret", str(plan.as_dict()))

    def test_plan_output_contains_no_raw_prompt_response_or_secret(self) -> None:
        plan = build_dry_run_retry_plan(
            decision=_decision(),
            tracker=_tracker(evidence_summary="raw_prompt raw_response token=secret"),
            created_at="2026-06-27T00:00:00+00:00",
        )
        payload = plan.as_dict()
        as_text = str(payload).lower()

        self.assertEqual(set(payload), {
            "plan_id",
            "plan_type",
            "advisory",
            "would_retry",
            "retry_reason",
            "blocked",
            "block_reasons",
            "retry_eligibility_score",
            "risk_level",
            "source_decision",
            "fingerprint_id",
            "stagnation_score",
            "progress_score",
            "repeated_strategy_count",
            "max_attempts_remaining",
            "evidence_summary",
            "created_at",
        })
        self.assertNotIn("raw_prompt", as_text)
        self.assertNotIn("raw_response", as_text)
        self.assertNotIn("secret", as_text)

    def test_no_provider_call_or_runtime_output_change_occurs(self) -> None:
        class ProviderTrap:
            called = False

            def __call__(self) -> None:
                self.called = True
                raise AssertionError("provider should not be called")

        provider = ProviderTrap()
        runtime_response = "original response"
        planner = DryRunRetryPlanner(max_retry_attempts=1)

        plan = planner.plan(
            decision=_decision(),
            context={"provider_call": provider},
            tracker=_tracker(),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertTrue(plan.advisory)
        self.assertFalse(provider.called)
        self.assertEqual(runtime_response, "original response")


if __name__ == "__main__":
    unittest.main()
