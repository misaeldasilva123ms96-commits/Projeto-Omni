from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.access_layer import (  # noqa: E402
    ACCESS_SNAPSHOT_BOUNDARY_VERSION,
    APPROVED_ACCESS_SNAPSHOT_ENVELOPE_KEYS,
    APPROVED_ACCESS_SNAPSHOT_KEYS,
    APPROVED_ADAPTER_CAPABILITY_KEYS,
    build_access_snapshot_response,
)


FORBIDDEN_FRAGMENTS = (
    "access_token",
    "api_key",
    "billing_config",
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


class AccessSnapshotBoundaryTest(unittest.TestCase):
    def test_successful_free_snapshot_boundary_response(self) -> None:
        response = build_access_snapshot_response(
            {
                "plan_mode": "free",
                "subject_id": "session-1",
                "usage_date": "2026-05-23",
                "tokens_in": 1000,
                "tokens_out": 250,
            },
            existing_daily_tokens=1000,
        )

        snapshot = response["access_snapshot"]
        self.assertTrue(response["ok"])
        self.assertFalse(response["denied"])
        self.assertEqual(response["reason"], "ok")
        self.assertEqual(snapshot["plan_mode"], "free")
        self.assertEqual(snapshot["provider_mode"], "experimental_free")
        self.assertEqual(snapshot["daily_token_limit"], 15000)
        self.assertEqual(snapshot["quota_remaining"], 12750)
        self.assertEqual(snapshot["selected_provider_family"], "experimental_free_provider")
        self.assertFalse(snapshot["adapter_capabilities"]["supports_files"])
        self.assertFalse(snapshot["adapter_capabilities"]["supports_sensitive_tools"])
        self.assertFalse(snapshot["adapter_capabilities"]["supports_long_context"])

    def test_denied_free_response_when_quota_exceeded(self) -> None:
        response = build_access_snapshot_response(
            {
                "plan_mode": "free",
                "subject_id": "session-1",
                "usage_date": "2026-05-23",
                "tokens_in": 2000,
                "tokens_out": 500,
            },
            existing_daily_tokens=13000,
        )

        self.assertFalse(response["ok"])
        self.assertTrue(response["denied"])
        self.assertEqual(response["reason"], "quota_exceeded")
        self.assertTrue(response["access_snapshot"]["quota_exceeded"])
        self.assertFalse(response["access_snapshot"]["routing_allowed"])

    def test_unknown_plan_fails_closed(self) -> None:
        response = build_access_snapshot_response(
            {
                "plan_mode": "enterprise",
                "subject_id": "session-1",
                "usage_date": "2026-05-23",
                "tokens_in": 1,
                "tokens_out": 1,
            }
        )

        self.assert_denied(response, "invalid_plan_or_policy")

    def test_negative_token_input_fails_closed(self) -> None:
        for field in ("tokens_in", "tokens_out"):
            request = {
                "plan_mode": "free",
                "subject_id": "session-1",
                "usage_date": "2026-05-23",
                "tokens_in": 1,
                "tokens_out": 1,
            }
            request[field] = -1

            with self.subTest(field=field):
                response = build_access_snapshot_response(request)
                self.assert_denied(response, "invalid_token_usage")

    def test_public_input_cannot_override_provider_mode(self) -> None:
        response = build_access_snapshot_response(
            {
                "plan_mode": "free",
                "subject_id": "session-1",
                "usage_date": "2026-05-23",
                "tokens_in": 1,
                "tokens_out": 1,
                "provider_mode": "managed",
            }
        )

        self.assert_denied(response, "unsafe_public_input")

    def test_public_input_cannot_pass_policy_overrides(self) -> None:
        response = build_access_snapshot_response(
            {
                "plan_mode": "free",
                "subject_id": "session-1",
                "usage_date": "2026-05-23",
                "tokens_in": 1,
                "tokens_out": 1,
                "policy_overrides": {"provider_mode": "managed"},
            }
        )

        self.assert_denied(response, "unsafe_public_input")

    def test_public_input_cannot_override_quota_limits(self) -> None:
        for field in ("daily_token_limit", "max_input_tokens", "max_output_tokens", "max_context_tokens"):
            with self.subTest(field=field):
                response = build_access_snapshot_response(
                    {
                        "plan_mode": "free",
                        "subject_id": "session-1",
                        "usage_date": "2026-05-23",
                        "tokens_in": 1,
                        "tokens_out": 1,
                        field: 999999,
                    }
                )

                self.assert_denied(response, "unsafe_public_input")

    def test_public_input_cannot_override_provider_family(self) -> None:
        for field in ("provider_family", "selected_provider_family"):
            with self.subTest(field=field):
                response = build_access_snapshot_response(
                    {
                        "plan_mode": "free",
                        "subject_id": "session-1",
                        "usage_date": "2026-05-23",
                        "tokens_in": 1,
                        "tokens_out": 1,
                        field: "managed_provider",
                    }
                )

                self.assert_denied(response, "unsafe_public_input")

    def test_public_input_cannot_override_adapter_identifiers(self) -> None:
        for field in ("selected_adapter_id", "adapter_id"):
            with self.subTest(field=field):
                response = build_access_snapshot_response(
                    {
                        "plan_mode": "free",
                        "subject_id": "session-1",
                        "usage_date": "2026-05-23",
                        "tokens_in": 1,
                        "tokens_out": 1,
                        field: "managed_adapter",
                    }
                )

                self.assert_denied(response, "unsafe_public_input")

    def test_negative_trusted_existing_daily_tokens_fails_closed(self) -> None:
        response = build_access_snapshot_response(
            {
                "plan_mode": "free",
                "subject_id": "session-1",
                "usage_date": "2026-05-23",
                "tokens_in": 1,
                "tokens_out": 1,
            },
            existing_daily_tokens=-1,
        )

        self.assert_denied(response, "invalid_token_usage")

    def test_subject_id_must_be_opaque_public_identifier(self) -> None:
        for subject_id in ("user@example.com", "sk-secret", "bearer raw-token", "token-value"):
            with self.subTest(subject_id=subject_id):
                response = build_access_snapshot_response(
                    {
                        "plan_mode": "free",
                        "subject_id": subject_id,
                        "usage_date": "2026-05-23",
                        "tokens_in": 1,
                        "tokens_out": 1,
                    }
                )

                self.assert_denied(response, "unsafe_subject_id")
                self.assertNotIn(subject_id.lower(), str(response).lower())

    def test_response_envelope_exact_approved_key_set(self) -> None:
        response = build_access_snapshot_response(
            {
                "plan_mode": "free",
                "subject_id": "session-1",
                "usage_date": "2026-05-23",
                "tokens_in": 1,
                "tokens_out": 1,
            }
        )

        self.assertEqual(set(response), APPROVED_ACCESS_SNAPSHOT_ENVELOPE_KEYS)

    def test_access_snapshot_exact_approved_key_set(self) -> None:
        response = build_access_snapshot_response(
            {
                "plan_mode": "free",
                "subject_id": "session-1",
                "usage_date": "2026-05-23",
                "tokens_in": 1,
                "tokens_out": 1,
            }
        )

        snapshot = response["access_snapshot"]
        self.assertEqual(set(snapshot), APPROVED_ACCESS_SNAPSHOT_KEYS)
        self.assertEqual(set(snapshot["adapter_capabilities"]), APPROVED_ADAPTER_CAPABILITY_KEYS)

    def test_no_sensitive_fields_are_exposed(self) -> None:
        response = build_access_snapshot_response(
            {
                "plan_mode": "byok",
                "subject_id": "opaque-subject",
                "usage_date": "2026-05-23",
                "tokens_in": 10,
                "tokens_out": 5,
            }
        )

        self.assert_not_publicly_sensitive(response)
        for key in response:
            lowered = key.lower()
            for fragment in FORBIDDEN_FRAGMENTS:
                self.assertNotIn(fragment, lowered)

    def test_boundary_version_is_stable(self) -> None:
        response = build_access_snapshot_response(
            {
                "plan_mode": "free",
                "subject_id": "session-1",
                "usage_date": "2026-05-23",
                "tokens_in": 1,
                "tokens_out": 1,
            }
        )

        self.assertEqual(response["boundary_version"], ACCESS_SNAPSHOT_BOUNDARY_VERSION)
        self.assertEqual(response["boundary_version"], "access_snapshot_boundary_v1")

    def test_no_real_provider_call_or_public_endpoint_was_added(self) -> None:
        source = (
            PROJECT_ROOT
            / "backend"
            / "python"
            / "brain"
            / "runtime"
            / "access_layer"
            / "access_snapshot_boundary.py"
        ).read_text(encoding="utf-8")
        lowered = source.lower()

        for fragment in ("requests.", "httpx.", "openai", "gemini", "groq", "puter", "@app.route", "fastapi"):
            self.assertNotIn(fragment, lowered)

    def assert_denied(self, response: dict, reason: str) -> None:
        self.assertFalse(response["ok"])
        self.assertTrue(response["denied"])
        self.assertFalse(response["access_snapshot"]["routing_allowed"])
        self.assertEqual(response["reason"], reason)
        self.assertEqual(response["access_snapshot"]["decision_reason"], reason)
        self.assert_not_publicly_sensitive(response)

    def assert_not_publicly_sensitive(self, response: dict) -> None:
        serialized = str(response).lower()
        for fragment in FORBIDDEN_FRAGMENTS:
            self.assertNotIn(fragment, serialized)


if __name__ == "__main__":
    unittest.main()
