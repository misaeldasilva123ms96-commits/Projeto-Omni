from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.access_layer import (  # noqa: E402
    UnknownProviderFamilyError,
    build_provider_routing_decision,
    build_public_provider_adapter_snapshot,
    get_provider_adapter,
    list_public_provider_adapters,
    validate_router_decision_adapter,
)


class ProviderRegistryTest(unittest.TestCase):
    def test_all_expected_provider_families_exist(self) -> None:
        families = {item["provider_family"] for item in list_public_provider_adapters()}

        self.assertEqual(
            families,
            {
                "experimental_free_provider",
                "user_supplied_provider",
                "managed_provider",
                "internal_provider",
            },
        )

    def test_unknown_provider_family_fails_safely(self) -> None:
        with self.assertRaises(UnknownProviderFamilyError):
            get_provider_adapter("unknown_provider")

        with self.assertRaises(UnknownProviderFamilyError):
            build_public_provider_adapter_snapshot("unknown_provider")

    def test_public_snapshots_expose_only_approved_safe_keys(self) -> None:
        approved_keys = {
            "registry_version",
            "provider_family",
            "adapter_id",
            "display_name",
            "provider_mode",
            "supports_streaming",
            "supports_tools",
            "supports_files",
            "supports_long_context",
            "supports_sensitive_tools",
            "is_experimental",
            "is_user_key_required",
            "is_managed",
            "is_internal",
            "default_enabled",
            "public_description",
        }

        for item in list_public_provider_adapters():
            with self.subTest(provider_family=item["provider_family"]):
                self.assertEqual(set(item), approved_keys)

    def test_public_snapshots_do_not_expose_sensitive_fields(self) -> None:
        forbidden_fragments = (
            "api_key",
            "billing_config",
            "credential",
            "env_var",
            "private_endpoint",
            "provider_payload",
            "raw_credential",
            "request_payload",
            "secret",
            "sk-",
        )
        forbidden_key_fragments = (*forbidden_fragments, "access_token", "refresh_token")

        for item in list_public_provider_adapters():
            with self.subTest(provider_family=item["provider_family"]):
                serialized = str(item).lower()
                for fragment in forbidden_fragments:
                    self.assertNotIn(fragment, serialized)
                for key in item:
                    for fragment in forbidden_key_fragments:
                        self.assertNotIn(fragment, key.lower())

    def test_provider_router_decisions_validate_against_registry(self) -> None:
        for mode in ("free", "byok", "pro", "internal"):
            with self.subTest(mode=mode):
                decision = build_provider_routing_decision(
                    plan_mode=mode,
                    subject_id=f"{mode}-subject",
                    tokens_in=100,
                    tokens_out=25,
                    usage_date="2026-05-22",
                )

                self.assertTrue(validate_router_decision_adapter(decision))
                self.assertTrue(validate_router_decision_adapter(decision.as_public_dict()))

    def test_unknown_router_decision_provider_family_fails_safely(self) -> None:
        decision = build_provider_routing_decision(
            plan_mode="free",
            subject_id="free-subject",
            tokens_in=100,
            tokens_out=25,
            usage_date="2026-05-22",
        ).as_public_dict()
        decision["selected_provider_family"] = "unknown_provider"

        with self.assertRaises(UnknownProviderFamilyError):
            validate_router_decision_adapter(decision)

    def test_free_provider_metadata_is_experimental_and_restricted(self) -> None:
        snapshot = build_public_provider_adapter_snapshot("experimental_free_provider")

        self.assertEqual(snapshot["provider_mode"], "experimental_free")
        self.assertTrue(snapshot["is_experimental"])
        self.assertFalse(snapshot["supports_sensitive_tools"])
        self.assertFalse(snapshot["supports_files"])
        self.assertFalse(snapshot["supports_long_context"])
        self.assertFalse(snapshot["is_user_key_required"])

    def test_byok_provider_metadata_requires_user_key_but_contains_no_key(self) -> None:
        snapshot = build_public_provider_adapter_snapshot("user_supplied_provider")

        self.assertEqual(snapshot["provider_mode"], "user_key")
        self.assertTrue(snapshot["is_user_key_required"])
        self.assertNotIn("key", snapshot)
        self.assertNotIn("api_key", str(snapshot).lower())

    def test_managed_provider_metadata_is_managed_without_billing_or_secrets(self) -> None:
        snapshot = build_public_provider_adapter_snapshot("managed_provider")
        serialized = str(snapshot).lower()

        self.assertEqual(snapshot["provider_mode"], "managed")
        self.assertTrue(snapshot["is_managed"])
        self.assertFalse(snapshot["is_user_key_required"])
        self.assertNotIn("billing", serialized)
        self.assertNotIn("secret", serialized)

    def test_internal_provider_metadata_is_internal_and_public_safe(self) -> None:
        snapshot = build_public_provider_adapter_snapshot("internal_provider")
        serialized = str(snapshot).lower()

        self.assertEqual(snapshot["provider_mode"], "internal")
        self.assertTrue(snapshot["is_internal"])
        self.assertNotIn("internal_config", serialized)
        self.assertNotIn("credential", serialized)


if __name__ == "__main__":
    unittest.main()
