from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.access_layer import (  # noqa: E402
    PlanMode,
    ProviderMode,
    ToolAccessMode,
    build_public_plan_policy,
    resolve_plan_policy,
)
from brain.runtime.access_layer.plan_policy import (  # noqa: E402
    InvalidPlanPolicyError,
    UnknownPlanModeError,
)


class PlanPolicyTest(unittest.TestCase):
    def test_known_plan_modes_resolve_correctly(self) -> None:
        expectations = {
            "free": ProviderMode.EXPERIMENTAL_FREE,
            "byok": ProviderMode.USER_KEY,
            "pro": ProviderMode.MANAGED,
            "internal": ProviderMode.INTERNAL,
        }

        for mode, provider_mode in expectations.items():
            with self.subTest(mode=mode):
                policy = resolve_plan_policy(mode)
                self.assertEqual(policy.plan_mode, PlanMode(mode))
                self.assertEqual(policy.provider_mode, provider_mode)

    def test_unknown_plan_mode_is_rejected_explicitly(self) -> None:
        with self.assertRaises(UnknownPlanModeError):
            resolve_plan_policy("enterprise")

    def test_free_mode_has_strict_limits(self) -> None:
        policy = resolve_plan_policy("free")

        self.assertEqual(policy.daily_token_limit, 15000)
        self.assertEqual(policy.max_input_tokens, 3000)
        self.assertEqual(policy.max_output_tokens, 1500)
        self.assertEqual(policy.max_context_tokens, 6000)
        self.assertEqual(policy.provider_mode, ProviderMode.EXPERIMENTAL_FREE)

    def test_free_mode_disables_files_sensitive_tools_and_long_memory(self) -> None:
        policy = resolve_plan_policy(PlanMode.FREE)

        self.assertFalse(policy.files_enabled)
        self.assertFalse(policy.tools_enabled)
        self.assertFalse(policy.sensitive_tools_enabled)
        self.assertFalse(policy.long_memory_enabled)

    def test_configurable_modes_accept_safe_overrides(self) -> None:
        policy = resolve_plan_policy(
            "byok",
            overrides={
                "max_input_tokens": 12000,
                "max_output_tokens": 6000,
                "max_context_tokens": 24000,
                "long_memory_enabled": True,
                "tools_enabled": "controlled",
            },
        )

        self.assertEqual(policy.max_input_tokens, 12000)
        self.assertEqual(policy.max_output_tokens, 6000)
        self.assertEqual(policy.max_context_tokens, 24000)
        self.assertTrue(policy.long_memory_enabled)
        self.assertEqual(policy.tools_enabled, ToolAccessMode.CONTROLLED)

    def test_unknown_override_fields_are_rejected(self) -> None:
        with self.assertRaises(InvalidPlanPolicyError):
            resolve_plan_policy("pro", overrides={"provider_key": "sk-secret"})

    def test_public_policy_output_does_not_expose_provider_keys_or_secrets(self) -> None:
        public_policy = build_public_plan_policy("pro")
        serialized = str(public_policy).lower()

        self.assertEqual(public_policy["provider_mode"], "managed")
        self.assertNotIn("provider_key", public_policy)
        self.assertNotIn("api_key", public_policy)
        self.assertNotIn("secret", serialized)
        self.assertNotIn("sk-", serialized)

    def test_public_policy_key_set_is_safe_for_all_plan_modes(self) -> None:
        approved_keys = {
            "policy_version",
            "plan_mode",
            "daily_token_limit",
            "max_input_tokens",
            "max_output_tokens",
            "max_context_tokens",
            "files_enabled",
            "tools_enabled",
            "sensitive_tools_enabled",
            "long_memory_enabled",
            "provider_mode",
        }
        forbidden_fragments = (
            "api_key",
            "config",
            "credential",
            "internal_config",
            "provider_key",
            "secret",
            "sensitive_provider",
            "sk-",
        )
        forbidden_key_fragments = (*forbidden_fragments, "access_token", "refresh_token")

        for mode in ("free", "byok", "pro", "internal"):
            with self.subTest(mode=mode):
                public_policy = build_public_plan_policy(mode)
                serialized = str(public_policy).lower()

                self.assertEqual(set(public_policy), approved_keys)
                for fragment in forbidden_fragments:
                    self.assertNotIn(fragment, serialized)
                for key in public_policy:
                    for fragment in forbidden_key_fragments:
                        self.assertNotIn(fragment, key.lower())


if __name__ == "__main__":
    unittest.main()
