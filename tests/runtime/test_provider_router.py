from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.access_layer import build_public_provider_routing_decision  # noqa: E402
from brain.runtime.access_layer.plan_policy import (  # noqa: E402
    InvalidPlanPolicyError,
    UnknownPlanModeError,
)


class ProviderRouterTest(unittest.TestCase):
    def test_free_plan_routes_to_experimental_provider_when_quota_allows(self) -> None:
        decision = build_public_provider_routing_decision(
            plan_mode="free",
            subject_id="session-1",
            tokens_in=2000,
            tokens_out=500,
            usage_date="2026-05-22",
        )

        self.assertEqual(decision["selected_provider_family"], "experimental_free_provider")
        self.assertTrue(decision["quota_allowed"])
        self.assertTrue(decision["input_allowed"])
        self.assertTrue(decision["output_allowed"])
        self.assertTrue(decision["routing_allowed"])
        self.assertFalse(decision["fallback_allowed"])
        self.assertEqual(decision["decision_reason"], "routing_allowed")

    def test_free_plan_denies_routing_when_daily_quota_exceeded(self) -> None:
        decision = build_public_provider_routing_decision(
            plan_mode="free",
            subject_id="session-1",
            tokens_in=14000,
            tokens_out=1501,
            usage_date="2026-05-22",
        )

        self.assertTrue(decision["quota_exceeded"])
        self.assertFalse(decision["quota_allowed"])
        self.assertFalse(decision["routing_allowed"])
        self.assertTrue(decision["fallback_allowed"])
        self.assertEqual(decision["decision_reason"], "quota_exceeded")

    def test_free_plan_denies_routing_when_input_limit_exceeded(self) -> None:
        decision = build_public_provider_routing_decision(
            plan_mode="free",
            subject_id="session-1",
            tokens_in=3001,
            tokens_out=100,
            usage_date="2026-05-22",
        )

        self.assertFalse(decision["input_allowed"])
        self.assertFalse(decision["routing_allowed"])
        self.assertEqual(decision["decision_reason"], "input_limit_exceeded")

    def test_free_plan_denies_routing_when_output_limit_exceeded(self) -> None:
        decision = build_public_provider_routing_decision(
            plan_mode="free",
            subject_id="session-1",
            tokens_in=100,
            tokens_out=1501,
            usage_date="2026-05-22",
        )

        self.assertFalse(decision["output_allowed"])
        self.assertFalse(decision["routing_allowed"])
        self.assertEqual(decision["decision_reason"], "output_limit_exceeded")

    def test_byok_routes_only_as_user_supplied_provider_contract(self) -> None:
        decision = build_public_provider_routing_decision(
            plan_mode="byok",
            subject_id="user-session",
            tokens_in=100,
            tokens_out=50,
            usage_date="2026-05-22",
        )

        self.assertEqual(decision["provider_mode"], "user_key")
        self.assertEqual(decision["selected_provider_family"], "user_supplied_provider")
        self.assertTrue(decision["routing_allowed"])

    def test_pro_routes_only_as_managed_provider_contract(self) -> None:
        decision = build_public_provider_routing_decision(
            plan_mode="pro",
            subject_id="pro-session",
            tokens_in=100,
            tokens_out=50,
            usage_date="2026-05-22",
        )

        self.assertEqual(decision["provider_mode"], "managed")
        self.assertEqual(decision["selected_provider_family"], "managed_provider")
        self.assertTrue(decision["routing_allowed"])

    def test_internal_routes_only_as_internal_provider_contract(self) -> None:
        decision = build_public_provider_routing_decision(
            plan_mode="internal",
            subject_id="internal-session",
            tokens_in=100,
            tokens_out=50,
            usage_date="2026-05-22",
        )

        self.assertEqual(decision["provider_mode"], "internal")
        self.assertEqual(decision["selected_provider_family"], "internal_provider")
        self.assertTrue(decision["routing_allowed"])

    def test_unknown_plan_mode_fails_closed(self) -> None:
        with self.assertRaises(UnknownPlanModeError):
            build_public_provider_routing_decision(
                plan_mode="enterprise",
                subject_id="session-1",
                tokens_in=1,
                tokens_out=1,
                usage_date="2026-05-22",
            )

    def test_provider_mode_override_attempts_fail_closed(self) -> None:
        override_attempts = (
            ("free", "user_key"),
            ("free", "managed"),
            ("byok", "managed"),
            ("byok", "internal"),
            ("pro", "user_key"),
            ("pro", "internal"),
            ("internal", "managed"),
            ("internal", "user_key"),
        )

        for plan_mode, provider_mode in override_attempts:
            with self.subTest(plan_mode=plan_mode, provider_mode=provider_mode):
                with self.assertRaises(InvalidPlanPolicyError):
                    build_public_provider_routing_decision(
                        plan_mode=plan_mode,
                        subject_id="session-1",
                        tokens_in=1,
                        tokens_out=1,
                        usage_date="2026-05-22",
                        policy_overrides={"provider_mode": provider_mode},
                    )

    def test_public_router_snapshot_exposes_only_safe_keys(self) -> None:
        approved_keys = {
            "router_version",
            "plan_mode",
            "provider_mode",
            "selected_provider_family",
            "quota_allowed",
            "quota_exceeded",
            "input_allowed",
            "output_allowed",
            "routing_allowed",
            "fallback_allowed",
            "decision_reason",
            "public_safe_snapshot",
        }
        approved_quota_keys = {
            "quota_version",
            "plan_mode",
            "subject_id",
            "usage_date",
            "tokens_in",
            "tokens_out",
            "tokens_total",
            "daily_token_limit",
            "quota_remaining",
            "quota_exceeded",
            "input_limit_exceeded",
            "output_limit_exceeded",
        }

        for mode in ("free", "byok", "pro", "internal"):
            with self.subTest(mode=mode):
                decision = build_public_provider_routing_decision(
                    plan_mode=mode,
                    subject_id=f"{mode}-subject",
                    tokens_in=100,
                    tokens_out=25,
                    usage_date="2026-05-22",
                )

                self.assertEqual(set(decision), approved_keys)
                self.assertEqual(set(decision["public_safe_snapshot"]), approved_quota_keys)

    def test_public_router_snapshot_does_not_expose_secret_fields(self) -> None:
        decision = build_public_provider_routing_decision(
            plan_mode="byok",
            subject_id="opaque-user",
            tokens_in=100,
            tokens_out=25,
            usage_date="2026-05-22",
        )
        serialized = str(decision).lower()
        forbidden_fragments = (
            "api_key",
            "billing",
            "config",
            "credential",
            "provider_key",
            "provider_secret",
            "raw_policy",
            "secret",
            "sk-",
        )
        forbidden_key_fragments = (*forbidden_fragments, "access_token", "refresh_token")

        for fragment in forbidden_fragments:
            self.assertNotIn(fragment, serialized)
        for key in decision:
            for fragment in forbidden_key_fragments:
                self.assertNotIn(fragment, key.lower())
        for key in decision["public_safe_snapshot"]:
            for fragment in forbidden_key_fragments:
                self.assertNotIn(fragment, key.lower())


if __name__ == "__main__":
    unittest.main()
