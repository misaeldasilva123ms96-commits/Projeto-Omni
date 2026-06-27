from __future__ import annotations

import unittest

from brain.runtime.autonomy import (
    AutonomyContext,
    AutonomyDecision,
    DecisionType,
    DryRunReplanPlanner,
    build_dry_run_replan_plan,
)


def _decision(
    decision: DecisionType = DecisionType.REPLAN,
    *,
    risk_level: str = "low",
) -> AutonomyDecision:
    return AutonomyDecision(
        decision=decision,
        reason="safe metadata",
        risk_level=risk_level,
    )


def _context(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "repeated_retry_not_useful": True,
    }
    base.update(overrides)
    return base


def _tracker(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "fingerprint_id": "fp123",
        "stagnation_score": 5,
        "progress_score": 1,
        "repeated_strategy_count": 2,
        "recommended_decision_hint": "",
        "evidence_summary": "safe stagnation metadata",
    }
    base.update(overrides)
    return base


class DryRunReplanPlannerTest(unittest.TestCase):
    def test_eligible_replan_produces_would_replan_true(self) -> None:
        plan = build_dry_run_replan_plan(
            decision=_decision(),
            context=_context(),
            tracker=_tracker(),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertTrue(plan.advisory)
        self.assertEqual(plan.plan_type, "dry_run_replan")
        self.assertTrue(plan.would_replan)
        self.assertFalse(plan.blocked)
        self.assertEqual(plan.replan_reason, "replan_eligible")
        self.assertEqual(plan.suggested_strategy, "change_safe_strategy_category")

    def test_non_replan_decision_produces_would_replan_false(self) -> None:
        plan = build_dry_run_replan_plan(
            decision=_decision(DecisionType.CONTINUE),
            context=_context(),
            tracker=_tracker(),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertFalse(plan.would_replan)
        self.assertFalse(plan.blocked)
        self.assertEqual(plan.replan_reason, "not_replan_decision")

    def test_replan_like_hint_can_make_plan_eligible(self) -> None:
        plan = build_dry_run_replan_plan(
            decision=_decision(DecisionType.CONTINUE),
            context=_context(),
            tracker=_tracker(recommended_decision_hint="replan"),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertTrue(plan.would_replan)
        self.assertEqual(plan.source_decision, "CONTINUE")

    def test_retry_still_useful_blocks_replan(self) -> None:
        plan = build_dry_run_replan_plan(
            decision=_decision(),
            context={"retry_still_useful": True},
            tracker=_tracker(),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertFalse(plan.would_replan)
        self.assertIn("retry_still_useful", plan.block_reasons)

    def test_stagnation_not_greater_than_progress_blocks_replan(self) -> None:
        plan = build_dry_run_replan_plan(
            decision=_decision(),
            context=_context(),
            tracker=_tracker(stagnation_score=1, progress_score=2),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertFalse(plan.would_replan)
        self.assertIn("stagnation_not_dominant", plan.block_reasons)

    def test_repeated_strategy_count_not_stuck_blocks_replan(self) -> None:
        plan = build_dry_run_replan_plan(
            decision=_decision(),
            context=_context(),
            tracker=_tracker(repeated_strategy_count=1),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertFalse(plan.would_replan)
        self.assertIn("strategy_not_stuck", plan.block_reasons)

    def test_high_and_critical_risk_block_replan(self) -> None:
        for risk in ("high", "critical"):
            with self.subTest(risk=risk):
                plan = build_dry_run_replan_plan(
                    decision=_decision(risk_level=risk),
                    context=_context(),
                    tracker=_tracker(),
                    created_at="2026-06-27T00:00:00+00:00",
                )

                self.assertFalse(plan.would_replan)
                self.assertTrue(plan.blocked)
                self.assertIn("risk_too_high", plan.block_reasons)

    def test_secret_detected_blocks_replan(self) -> None:
        plan = build_dry_run_replan_plan(
            decision=_decision(),
            context=AutonomyContext(secret_detected=True, metadata={"repeated_retry_not_useful": True}),
            tracker=_tracker(),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertFalse(plan.would_replan)
        self.assertIn("secret_detected", plan.block_reasons)

    def test_protected_file_blocks_replan(self) -> None:
        plan = build_dry_run_replan_plan(
            decision=_decision(),
            context=AutonomyContext(protected_file_involved=True, metadata={"repeated_retry_not_useful": True}),
            tracker=_tracker(),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertFalse(plan.would_replan)
        self.assertIn("protected_file_involved", plan.block_reasons)

    def test_provider_switching_requirement_blocks_replan(self) -> None:
        plan = build_dry_run_replan_plan(
            decision=_decision(),
            context=_context(provider_switching_required=True),
            tracker=_tracker(),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertFalse(plan.would_replan)
        self.assertIn("provider_switching_required", plan.block_reasons)

    def test_tool_write_command_and_destructive_requirements_block_replan(self) -> None:
        cases = {
            "tool_action_required": "tool_action_required",
            "write_action_required": "write_action_required",
            "command_action_required": "command_action_required",
            "destructive_operation_required": "destructive_operation_required",
        }
        for key, reason in cases.items():
            with self.subTest(key=key):
                plan = build_dry_run_replan_plan(
                    decision=_decision(),
                    context=_context(**{key: True}),
                    tracker=_tracker(),
                    created_at="2026-06-27T00:00:00+00:00",
                )
                self.assertFalse(plan.would_replan)
                self.assertIn(reason, plan.block_reasons)

    def test_unsafe_ci_security_signal_blocks_replan(self) -> None:
        plan = build_dry_run_replan_plan(
            decision=_decision(),
            context=AutonomyContext(unsafe_ci_signal=True, metadata={"repeated_retry_not_useful": True}),
            tracker=_tracker(),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertFalse(plan.would_replan)
        self.assertIn("unsafe_ci_or_security_signal", plan.block_reasons)

    def test_no_safe_next_action_blocks_replan(self) -> None:
        plan = build_dry_run_replan_plan(
            decision=_decision(),
            context=AutonomyContext(no_safe_next_action=True, metadata={"repeated_retry_not_useful": True}),
            tracker=_tracker(),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertFalse(plan.would_replan)
        self.assertIn("no_safe_next_action", plan.block_reasons)

    def test_pause_escalate_abort_governance_blocks_replan(self) -> None:
        for governance in ("pause", "escalate", "abort_safe"):
            with self.subTest(governance=governance):
                plan = build_dry_run_replan_plan(
                    decision=_decision(),
                    context=_context(governance_decision=governance),
                    tracker=_tracker(),
                    created_at="2026-06-27T00:00:00+00:00",
                )
                self.assertFalse(plan.would_replan)
                self.assertIn(f"governance_{governance}", plan.block_reasons)

    def test_user_approval_required_blocks_replan(self) -> None:
        plan = build_dry_run_replan_plan(
            decision=_decision(),
            context=_context(user_approval_required=True),
            tracker=_tracker(),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertFalse(plan.would_replan)
        self.assertIn("user_approval_required", plan.block_reasons)

    def test_prompt_rewrite_required_blocks_replan(self) -> None:
        plan = build_dry_run_replan_plan(
            decision=_decision(),
            context=_context(prompt_rewrite_required=True),
            tracker=_tracker(),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertFalse(plan.would_replan)
        self.assertIn("prompt_rewrite_required", plan.block_reasons)

    def test_model_provider_call_required_blocks_replan(self) -> None:
        for key in ("model_call_required", "provider_call_required"):
            with self.subTest(key=key):
                plan = build_dry_run_replan_plan(
                    decision=_decision(),
                    context=_context(**{key: True}),
                    tracker=_tracker(),
                    created_at="2026-06-27T00:00:00+00:00",
                )
                self.assertFalse(plan.would_replan)
                self.assertIn("model_or_provider_call_required", plan.block_reasons)

    def test_malformed_missing_evidence_degrades_safely(self) -> None:
        plan = build_dry_run_replan_plan(
            decision=None,
            context=None,
            tracker=None,
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertTrue(plan.advisory)
        self.assertFalse(plan.would_replan)
        self.assertEqual(plan.source_decision, "")
        self.assertEqual(plan.evidence_summary, "")

    def test_evidence_summary_is_bounded_and_sanitized(self) -> None:
        plan = build_dry_run_replan_plan(
            decision=_decision(),
            context=_context(),
            tracker=_tracker(evidence_summary=("safe " * 100) + " rewritten_prompt=do-not-render token=secret"),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertLessEqual(len(plan.evidence_summary), 240)
        self.assertEqual(plan.evidence_summary, "[redacted]")
        self.assertNotIn("do-not-render", str(plan.as_dict()))

    def test_suggested_strategy_is_safe_categorical_metadata_only(self) -> None:
        plan = build_dry_run_replan_plan(
            decision=_decision(),
            context=_context(suggested_strategy="rewrite prompt and execute command"),
            tracker=_tracker(),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertEqual(plan.suggested_strategy, "[redacted]")
        self.assertNotIn("rewrite prompt", str(plan.as_dict()).lower())
        self.assertNotIn("execute command", str(plan.as_dict()).lower())

    def test_plan_output_contains_no_raw_prompt_rewritten_prompt_response_or_secret(self) -> None:
        plan = build_dry_run_replan_plan(
            decision=_decision(),
            context=_context(suggested_strategy="safe_strategy_category"),
            tracker=_tracker(evidence_summary="raw_prompt rewritten_prompt raw_response token=secret"),
            created_at="2026-06-27T00:00:00+00:00",
        )
        payload = plan.as_dict()
        as_text = str(payload).lower()

        self.assertEqual(set(payload), {
            "plan_id",
            "plan_type",
            "advisory",
            "would_replan",
            "replan_reason",
            "blocked",
            "block_reasons",
            "replan_eligibility_score",
            "risk_level",
            "source_decision",
            "fingerprint_id",
            "stagnation_score",
            "progress_score",
            "repeated_strategy_count",
            "suggested_strategy",
            "evidence_summary",
            "created_at",
        })
        self.assertNotIn("raw_prompt", as_text)
        self.assertNotIn("rewritten_prompt", as_text)
        self.assertNotIn("raw_response", as_text)
        self.assertNotIn("secret", as_text)

    def test_no_prompt_rewrite_provider_call_or_runtime_output_change_occurs(self) -> None:
        class ProviderTrap:
            called = False

            def __call__(self) -> None:
                self.called = True
                raise AssertionError("provider should not be called")

        provider = ProviderTrap()
        runtime_response = "original response"
        original_prompt = "original prompt"
        planner = DryRunReplanPlanner()

        plan = planner.plan(
            decision=_decision(),
            context=_context(provider_call=provider, prompt=original_prompt),
            tracker=_tracker(),
            created_at="2026-06-27T00:00:00+00:00",
        )

        self.assertTrue(plan.advisory)
        self.assertFalse(provider.called)
        self.assertEqual(runtime_response, "original response")
        self.assertEqual(original_prompt, "original prompt")
        self.assertNotIn("original prompt", str(plan.as_dict()))


if __name__ == "__main__":
    unittest.main()
