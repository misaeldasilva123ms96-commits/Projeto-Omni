from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.access_layer import (  # noqa: E402
    InvalidTokenQuotaError,
    build_public_quota_snapshot,
    calculate_quota_remaining,
    calculate_tokens_total,
    is_quota_exceeded,
    resolve_plan_policy,
    validate_max_input_tokens,
    validate_max_output_tokens,
)
from brain.runtime.access_layer.plan_policy import UnknownPlanModeError  # noqa: E402


class TokenQuotaTest(unittest.TestCase):
    def test_calculates_token_total(self) -> None:
        self.assertEqual(calculate_tokens_total(120, 30), 150)

    def test_negative_token_inputs_are_rejected(self) -> None:
        with self.assertRaises(InvalidTokenQuotaError):
            calculate_tokens_total(-1, 30)

        with self.assertRaises(InvalidTokenQuotaError):
            calculate_tokens_total(120, -1)

        with self.assertRaises(InvalidTokenQuotaError):
            build_public_quota_snapshot(
                plan_mode="free",
                subject_id="session-1",
                tokens_in=-1,
                tokens_out=1,
                usage_date="2026-05-22",
            )

        with self.assertRaises(InvalidTokenQuotaError):
            build_public_quota_snapshot(
                plan_mode="free",
                subject_id="session-1",
                tokens_in=1,
                tokens_out=-1,
                usage_date="2026-05-22",
            )

    def test_invalid_daily_limits_are_rejected_and_null_limit_stays_unlimited(self) -> None:
        for invalid_limit in (-1, 0):
            with self.subTest(invalid_limit=invalid_limit):
                with self.assertRaises(InvalidTokenQuotaError):
                    calculate_quota_remaining(
                        daily_token_limit=invalid_limit,
                        tokens_total=1,
                    )
                with self.assertRaises(InvalidTokenQuotaError):
                    is_quota_exceeded(
                        daily_token_limit=invalid_limit,
                        tokens_total=1,
                    )

        with self.assertRaises(InvalidTokenQuotaError):
            calculate_quota_remaining(daily_token_limit=15000, tokens_total=-1)

        self.assertIsNone(calculate_quota_remaining(daily_token_limit=None, tokens_total=1))
        self.assertFalse(is_quota_exceeded(daily_token_limit=None, tokens_total=1))

    def test_free_mode_daily_quota_remaining_uses_plan_policy_limit(self) -> None:
        snapshot = build_public_quota_snapshot(
            plan_mode="free",
            subject_id="session-1",
            tokens_in=2000,
            tokens_out=500,
            usage_date="2026-05-22",
        )

        self.assertEqual(snapshot["daily_token_limit"], 15000)
        self.assertEqual(snapshot["tokens_total"], 2500)
        self.assertEqual(snapshot["quota_remaining"], 12500)
        self.assertFalse(snapshot["quota_exceeded"])

    def test_free_mode_quota_exceeded_above_daily_limit(self) -> None:
        snapshot = build_public_quota_snapshot(
            plan_mode="free",
            subject_id="session-1",
            tokens_in=14000,
            tokens_out=1501,
            usage_date="2026-05-22",
        )

        self.assertEqual(snapshot["tokens_total"], 15501)
        self.assertEqual(snapshot["quota_remaining"], 0)
        self.assertTrue(snapshot["quota_exceeded"])

    def test_free_mode_max_input_exceeded(self) -> None:
        policy = resolve_plan_policy("free")

        self.assertTrue(validate_max_input_tokens(3000, policy))
        self.assertFalse(validate_max_input_tokens(3001, policy))

        snapshot = build_public_quota_snapshot(
            plan_mode="free",
            subject_id="session-1",
            tokens_in=3001,
            tokens_out=100,
            usage_date="2026-05-22",
        )
        self.assertTrue(snapshot["input_limit_exceeded"])

    def test_free_mode_max_output_exceeded(self) -> None:
        policy = resolve_plan_policy("free")

        self.assertTrue(validate_max_output_tokens(1500, policy))
        self.assertFalse(validate_max_output_tokens(1501, policy))

        snapshot = build_public_quota_snapshot(
            plan_mode="free",
            subject_id="session-1",
            tokens_in=100,
            tokens_out=1501,
            usage_date="2026-05-22",
        )
        self.assertTrue(snapshot["output_limit_exceeded"])

    def test_internal_unlimited_daily_limit_is_never_quota_exceeded(self) -> None:
        self.assertIsNone(calculate_quota_remaining(daily_token_limit=None, tokens_total=999999))
        self.assertFalse(is_quota_exceeded(daily_token_limit=None, tokens_total=999999))

        snapshot = build_public_quota_snapshot(
            plan_mode="internal",
            subject_id="admin-session",
            tokens_in=64000,
            tokens_out=16000,
            usage_date="2026-05-22",
        )

        self.assertIsNone(snapshot["daily_token_limit"])
        self.assertIsNone(snapshot["quota_remaining"])
        self.assertFalse(snapshot["quota_exceeded"])

    def test_public_quota_snapshot_key_set_is_safe_for_all_plan_modes(self) -> None:
        approved_keys = {
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
        forbidden_fragments = (
            "api_key",
            "billing",
            "config",
            "credential",
            "provider_mode",
            "provider_key",
            "provider_route",
            "raw_policy",
            "secret",
            "sensitive_provider",
            "sk-",
        )
        forbidden_key_fragments = (*forbidden_fragments, "access_token", "refresh_token")

        for mode in ("free", "byok", "pro", "internal"):
            with self.subTest(mode=mode):
                snapshot = build_public_quota_snapshot(
                    plan_mode=mode,
                    subject_id=f"{mode}-subject",
                    tokens_in=100,
                    tokens_out=25,
                    usage_date="2026-05-22",
                )
                serialized = str(snapshot).lower()

                self.assertEqual(set(snapshot), approved_keys)
                self.assertEqual(snapshot["subject_id"], f"{mode}-subject")
                for fragment in forbidden_fragments:
                    self.assertNotIn(fragment, serialized)
                for key in snapshot:
                    for fragment in forbidden_key_fragments:
                        self.assertNotIn(fragment, key.lower())

    def test_unknown_plan_mode_is_rejected_explicitly(self) -> None:
        with self.assertRaises(UnknownPlanModeError):
            build_public_quota_snapshot(
                plan_mode="enterprise",
                subject_id="session-1",
                tokens_in=1,
                tokens_out=1,
                usage_date="2026-05-22",
            )


if __name__ == "__main__":
    unittest.main()
