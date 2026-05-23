from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.access_layer import (  # noqa: E402
    PUTER_CLIENT_ADAPTER_CONTRACT_VERSION,
    PUTER_CLIENT_ADAPTER_ID,
    PUTER_CLIENT_ADAPTER_PUBLIC_KEYS,
    PUTER_CLIENT_ADAPTER_SELECTION_KEYS,
    build_access_snapshot_response,
    build_public_plan_policy,
    build_public_puter_client_adapter_contract,
    build_public_puter_client_adapter_selection,
)


FORBIDDEN_FRAGMENTS = (
    "access_token",
    "api_key",
    "billing",
    "credential",
    "env_var",
    "private_endpoint",
    "provider_payload",
    "raw_provider",
    "request_payload",
    "secret",
    "sk-",
    "stack",
    "traceback",
)


class PuterClientAdapterContractTest(unittest.TestCase):
    def test_puter_adapter_metadata_exists_only_as_experimental_free_contract(self) -> None:
        contract = build_public_puter_client_adapter_contract()

        self.assertEqual(set(contract), PUTER_CLIENT_ADAPTER_PUBLIC_KEYS)
        self.assertEqual(contract["contract_version"], PUTER_CLIENT_ADAPTER_CONTRACT_VERSION)
        self.assertEqual(contract["adapter_id"], PUTER_CLIENT_ADAPTER_ID)
        self.assertEqual(contract["provider_family"], "experimental_free_provider")
        self.assertEqual(contract["provider_mode"], "experimental_free")
        self.assertTrue(contract["is_experimental"])
        self.assertTrue(contract["requires_browser_runtime"])
        self.assertTrue(contract["requires_user_session"])

    def test_puter_adapter_is_disabled_by_default(self) -> None:
        contract = build_public_puter_client_adapter_contract()
        response = self.free_allowed_boundary_response()
        selection = build_public_puter_client_adapter_selection(response)

        self.assertFalse(contract["default_enabled"])
        self.assertFalse(selection["default_enabled"])
        self.assertFalse(selection["selection_allowed"])
        self.assertTrue(selection["denied"])
        self.assertEqual(selection["reason"], "feature_disabled")

    def test_free_mode_still_denies_tools_files_sensitive_tools_and_long_memory(self) -> None:
        policy = build_public_plan_policy("free")
        contract = build_public_puter_client_adapter_contract()

        self.assertFalse(policy["files_enabled"])
        self.assertFalse(policy["tools_enabled"])
        self.assertFalse(policy["sensitive_tools_enabled"])
        self.assertFalse(policy["long_memory_enabled"])
        self.assertFalse(contract["supports_tools"])
        self.assertFalse(contract["supports_files"])
        self.assertFalse(contract["supports_long_context"])
        self.assertFalse(contract["supports_sensitive_tools"])

    def test_puter_adapter_can_only_select_when_boundary_allows_and_flag_is_enabled(self) -> None:
        response = self.free_allowed_boundary_response()
        selection = build_public_puter_client_adapter_selection(
            response,
            experimental_feature_enabled=True,
        )

        self.assertTrue(selection["selection_allowed"])
        self.assertFalse(selection["denied"])
        self.assertEqual(selection["reason"], "selection_allowed")

    def test_puter_adapter_cannot_be_selected_if_provider_router_denies_routing(self) -> None:
        response = build_access_snapshot_response(
            {
                "plan_mode": "free",
                "subject_id": "session-1",
                "usage_date": "2026-05-23",
                "tokens_in": 3001,
                "tokens_out": 1,
            }
        )
        selection = build_public_puter_client_adapter_selection(
            response,
            experimental_feature_enabled=True,
        )

        self.assertFalse(response["access_snapshot"]["routing_allowed"])
        self.assertFalse(selection["selection_allowed"])
        self.assertTrue(selection["denied"])
        self.assertEqual(selection["reason"], "input_limit_exceeded")

    def test_puter_adapter_cannot_be_selected_when_quota_is_exceeded(self) -> None:
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
        selection = build_public_puter_client_adapter_selection(
            response,
            experimental_feature_enabled=True,
        )

        self.assertTrue(response["access_snapshot"]["quota_exceeded"])
        self.assertFalse(selection["selection_allowed"])
        self.assertTrue(selection["denied"])
        self.assertEqual(selection["reason"], "quota_exceeded")

    def test_puter_adapter_cannot_accept_credentials_or_provider_secrets(self) -> None:
        unsafe_options = (
            {"api_key": "sk-secret"},
            {"access_token": "raw-token"},
            {"credential": "provider-credential"},
            {"secret": "provider-secret"},
            {"env_var": "PROVIDER_KEY"},
        )

        for request_options in unsafe_options:
            with self.subTest(request_options=request_options):
                selection = build_public_puter_client_adapter_selection(
                    self.free_allowed_boundary_response(),
                    experimental_feature_enabled=True,
                    request_options=request_options,
                )

                self.assertFalse(selection["selection_allowed"])
                self.assertTrue(selection["denied"])
                self.assertEqual(selection["reason"], "unsafe_request_options")
                self.assert_not_publicly_sensitive(selection)

    def test_puter_adapter_does_not_expose_raw_provider_payloads(self) -> None:
        selection = build_public_puter_client_adapter_selection(
            self.free_allowed_boundary_response(),
            experimental_feature_enabled=True,
            request_options={"raw_provider_payload": {"id": "hidden"}},
        )

        self.assertEqual(set(selection), PUTER_CLIENT_ADAPTER_SELECTION_KEYS)
        self.assertFalse(selection["selection_allowed"])
        self.assertEqual(selection["reason"], "unsafe_request_options")
        self.assert_not_publicly_sensitive(selection)

    def test_no_network_or_provider_call_occurs_by_default(self) -> None:
        source = (
            PROJECT_ROOT
            / "backend"
            / "python"
            / "brain"
            / "runtime"
            / "access_layer"
            / "puter_client_adapter.py"
        ).read_text(encoding="utf-8")
        lowered = source.lower()

        for fragment in ("requests.", "httpx.", "fetch(", "window.puter", ".chat(", "openai", "gemini", "groq"):
            self.assertNotIn(fragment, lowered)

    def test_public_snapshots_and_boundary_override_attempts_remain_safe(self) -> None:
        response = build_access_snapshot_response(
            {
                "plan_mode": "free",
                "subject_id": "session-1",
                "usage_date": "2026-05-23",
                "tokens_in": 1,
                "tokens_out": 1,
                "adapter_id": "puter_client_adapter",
            }
        )

        self.assertFalse(response["ok"])
        self.assertTrue(response["denied"])
        self.assertEqual(response["reason"], "unsafe_public_input")
        self.assert_not_publicly_sensitive(response)

    def test_puter_adapter_is_not_available_for_non_free_plans(self) -> None:
        response = build_access_snapshot_response(
            {
                "plan_mode": "pro",
                "subject_id": "session-1",
                "usage_date": "2026-05-23",
                "tokens_in": 1,
                "tokens_out": 1,
            }
        )
        selection = build_public_puter_client_adapter_selection(
            response,
            experimental_feature_enabled=True,
        )

        self.assertFalse(selection["selection_allowed"])
        self.assertTrue(selection["denied"])
        self.assertEqual(selection["reason"], "not_free_mode")

    def free_allowed_boundary_response(self) -> dict:
        return build_access_snapshot_response(
            {
                "plan_mode": "free",
                "subject_id": "session-1",
                "usage_date": "2026-05-23",
                "tokens_in": 100,
                "tokens_out": 25,
            }
        )

    def assert_not_publicly_sensitive(self, value: dict) -> None:
        serialized = str(value).lower()
        for fragment in FORBIDDEN_FRAGMENTS:
            self.assertNotIn(fragment, serialized)


if __name__ == "__main__":
    unittest.main()
