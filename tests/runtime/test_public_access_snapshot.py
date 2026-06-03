from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.access_layer import (  # noqa: E402
    PUBLIC_ACCESS_SNAPSHOT_VERSION,
    build_public_access_snapshot,
)


APPROVED_KEYS = {
    "snapshot_version",
    "plan_mode",
    "provider_mode",
    "subject_id",
    "usage_date",
    "tokens_in",
    "tokens_out",
    "tokens_total",
    "daily_token_limit",
    "quota_remaining",
    "quota_exceeded",
    "input_allowed",
    "output_allowed",
    "quota_allowed",
    "routing_allowed",
    "fallback_allowed",
    "selected_provider_family",
    "selected_adapter_id",
    "adapter_display_name",
    "adapter_capabilities",
    "decision_reason",
}

APPROVED_CAPABILITY_KEYS = {
    "supports_streaming",
    "supports_tools",
    "supports_files",
    "supports_long_context",
    "supports_sensitive_tools",
    "is_experimental",
    "is_user_key_required",
    "is_managed",
    "is_internal",
}

FORBIDDEN_FRAGMENTS = (
    "access_token",
    "api_key",
    "billing",
    "command_args",
    "credential",
    "debug",
    "env_var",
    "private_endpoint",
    "provider_payload",
    "raw_config",
    "raw_provider",
    "request_payload",
    "secret",
    "sk-",
    "stack",
    "traceback",
)


class PublicAccessSnapshotTest(unittest.TestCase):
    def test_free_allowed_snapshot_when_quota_allows(self) -> None:
        snapshot = build_public_access_snapshot(
            plan_mode="free",
            subject_id="session-1",
            usage_date="2026-05-22",
            tokens_in=2000,
            tokens_out=500,
            existing_daily_tokens=1000,
        )

        self.assertEqual(snapshot["snapshot_version"], PUBLIC_ACCESS_SNAPSHOT_VERSION)
        self.assertEqual(snapshot["plan_mode"], "free")
        self.assertEqual(snapshot["provider_mode"], "experimental_free")
        self.assertEqual(snapshot["tokens_total"], 2500)
        self.assertEqual(snapshot["daily_token_limit"], 15000)
        self.assertEqual(snapshot["quota_remaining"], 11500)
        self.assertFalse(snapshot["quota_exceeded"])
        self.assertTrue(snapshot["routing_allowed"])
        self.assertEqual(snapshot["selected_provider_family"], "experimental_free_provider")
        self.assertEqual(snapshot["selected_adapter_id"], "experimental_free_adapter")
        self.assertTrue(snapshot["adapter_capabilities"]["is_experimental"])
        self.assertFalse(snapshot["adapter_capabilities"]["supports_files"])
        self.assertFalse(snapshot["adapter_capabilities"]["supports_sensitive_tools"])
        self.assertFalse(snapshot["adapter_capabilities"]["supports_long_context"])

    def test_free_denied_when_daily_quota_exceeded(self) -> None:
        snapshot = build_public_access_snapshot(
            plan_mode="free",
            subject_id="session-1",
            usage_date="2026-05-22",
            tokens_in=2000,
            tokens_out=500,
            existing_daily_tokens=13000,
        )

        self.assertEqual(snapshot["quota_remaining"], 0)
        self.assertTrue(snapshot["quota_exceeded"])
        self.assertFalse(snapshot["quota_allowed"])
        self.assertFalse(snapshot["routing_allowed"])
        self.assertTrue(snapshot["fallback_allowed"])
        self.assertEqual(snapshot["decision_reason"], "quota_exceeded")

    def test_free_denied_when_input_limit_exceeded(self) -> None:
        snapshot = build_public_access_snapshot(
            plan_mode="free",
            subject_id="session-1",
            usage_date="2026-05-22",
            tokens_in=3001,
            tokens_out=100,
        )

        self.assertFalse(snapshot["input_allowed"])
        self.assertFalse(snapshot["routing_allowed"])
        self.assertEqual(snapshot["decision_reason"], "input_limit_exceeded")

    def test_free_denied_when_output_limit_exceeded(self) -> None:
        snapshot = build_public_access_snapshot(
            plan_mode="free",
            subject_id="session-1",
            usage_date="2026-05-22",
            tokens_in=100,
            tokens_out=1501,
        )

        self.assertFalse(snapshot["output_allowed"])
        self.assertFalse(snapshot["routing_allowed"])
        self.assertEqual(snapshot["decision_reason"], "output_limit_exceeded")

    def test_byok_snapshot_is_contract_only_and_key_free(self) -> None:
        snapshot = build_public_access_snapshot(
            plan_mode="byok",
            subject_id="user-session",
            usage_date="2026-05-22",
            tokens_in=100,
            tokens_out=25,
        )

        self.assertEqual(snapshot["selected_provider_family"], "user_supplied_provider")
        self.assertTrue(snapshot["adapter_capabilities"]["is_user_key_required"])
        self.assert_not_publicly_sensitive(snapshot)

    def test_pro_snapshot_is_contract_only_and_billing_free(self) -> None:
        snapshot = build_public_access_snapshot(
            plan_mode="pro",
            subject_id="pro-session",
            usage_date="2026-05-22",
            tokens_in=100,
            tokens_out=25,
        )

        self.assertEqual(snapshot["selected_provider_family"], "managed_provider")
        self.assertTrue(snapshot["adapter_capabilities"]["is_managed"])
        self.assertNotIn("billing", str(snapshot).lower())

    def test_internal_snapshot_is_public_safe(self) -> None:
        snapshot = build_public_access_snapshot(
            plan_mode="internal",
            subject_id="internal-session",
            usage_date="2026-05-22",
            tokens_in=100,
            tokens_out=25,
        )

        self.assertEqual(snapshot["selected_provider_family"], "internal_provider")
        self.assertTrue(snapshot["adapter_capabilities"]["is_internal"])
        self.assert_not_publicly_sensitive(snapshot)

    def test_unknown_plan_and_negative_existing_usage_fail_closed(self) -> None:
        unknown = build_public_access_snapshot(
            plan_mode="enterprise",
            subject_id="session-1",
            usage_date="2026-05-22",
            tokens_in=1,
            tokens_out=1,
        )
        invalid_usage = build_public_access_snapshot(
            plan_mode="free",
            subject_id="session-1",
            usage_date="2026-05-22",
            tokens_in=1,
            tokens_out=1,
            existing_daily_tokens=-1,
        )

        self.assertFalse(unknown["routing_allowed"])
        self.assertEqual(unknown["decision_reason"], "invalid_plan_or_policy")
        self.assertFalse(invalid_usage["routing_allowed"])
        self.assertEqual(invalid_usage["decision_reason"], "invalid_token_usage")
        self.assert_not_publicly_sensitive(unknown)
        self.assert_not_publicly_sensitive(invalid_usage)

    def test_provider_registry_mismatch_fails_closed(self) -> None:
        with patch(
            "brain.runtime.access_layer.public_access_snapshot.validate_router_decision_adapter",
            return_value=False,
        ):
            snapshot = build_public_access_snapshot(
                plan_mode="free",
                subject_id="session-1",
                usage_date="2026-05-22",
                tokens_in=100,
                tokens_out=25,
            )

        self.assertFalse(snapshot["routing_allowed"])
        self.assertTrue(snapshot["fallback_allowed"])
        self.assertEqual(snapshot["decision_reason"], "provider_registry_mismatch")
        self.assertEqual(snapshot["selected_adapter_id"], "")

    def test_policy_override_provider_mode_attempts_fail_closed(self) -> None:
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
                snapshot = build_public_access_snapshot(
                    plan_mode=plan_mode,
                    subject_id="opaque-subject",
                    usage_date="2026-05-23",
                    tokens_in=1,
                    tokens_out=1,
                    policy_overrides={"provider_mode": provider_mode},
                )

                self.assertFalse(snapshot["routing_allowed"])
                self.assertTrue(snapshot["fallback_allowed"])
                self.assertEqual(snapshot["decision_reason"], "invalid_plan_or_policy")
                self.assert_not_publicly_sensitive(snapshot)

    def test_public_snapshot_key_sets_are_exact(self) -> None:
        for mode in ("free", "byok", "pro", "internal"):
            with self.subTest(mode=mode):
                snapshot = build_public_access_snapshot(
                    plan_mode=mode,
                    subject_id=f"{mode}-subject",
                    usage_date="2026-05-22",
                    tokens_in=100,
                    tokens_out=25,
                )

                self.assertEqual(set(snapshot), APPROVED_KEYS)
                self.assertEqual(set(snapshot["adapter_capabilities"]), APPROVED_CAPABILITY_KEYS)

    def test_snapshot_version_is_stable(self) -> None:
        snapshot = build_public_access_snapshot(
            plan_mode="free",
            subject_id="session-1",
            usage_date="2026-05-22",
            tokens_in=1,
            tokens_out=1,
        )

        self.assertEqual(snapshot["snapshot_version"], "public_access_snapshot_v1")

    def test_no_sensitive_fields_are_exposed(self) -> None:
        snapshot = build_public_access_snapshot(
            plan_mode="byok",
            subject_id="opaque-user",
            usage_date="2026-05-22",
            tokens_in=100,
            tokens_out=25,
        )

        self.assert_not_publicly_sensitive(snapshot)
        for key in snapshot:
            lowered = key.lower()
            for fragment in FORBIDDEN_FRAGMENTS:
                self.assertNotIn(fragment, lowered)

    def assert_not_publicly_sensitive(self, snapshot: dict) -> None:
        serialized = str(snapshot).lower()
        for fragment in FORBIDDEN_FRAGMENTS:
            self.assertNotIn(fragment, serialized)


if __name__ == "__main__":
    unittest.main()
