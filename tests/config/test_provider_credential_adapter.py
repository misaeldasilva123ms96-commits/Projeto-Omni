from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

BACKEND = os.path.join(ROOT, "backend", "python")
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from config.provider_credential_adapter import (
    BYOKResolutionError,
    ProviderCredentialAdapter,
    inject_credential_store_credentials,
    resolve_provider_credentials,
)
from config.secrets_manager import merge_provider_credentials


class ProviderCredentialAdapterTest(unittest.TestCase):
    def test_byok_overrides_env_variable(self) -> None:
        adapter = ProviderCredentialAdapter(store=_FakeStore.openai())
        env = {"OPENAI_API_KEY": "env-key"}
        merged = adapter.inject_credential_store_credentials(
            user_id="user-1", env=env
        )
        self.assertEqual(merged["OPENAI_API_KEY"], "byok-openai")

    def test_env_used_when_credential_store_missing(self) -> None:
        adapter = ProviderCredentialAdapter(store=None)
        env = {"OPENAI_API_KEY": "env-key"}
        merged = adapter.inject_credential_store_credentials(
            user_id="user-1", env=env
        )
        self.assertEqual(merged["OPENAI_API_KEY"], "env-key")

    def test_user_id_none_preserves_old_behavior(self) -> None:
        adapter = ProviderCredentialAdapter(store=_FakeStore.openai())
        env = {"OPENAI_API_KEY": "env-key"}
        merged = adapter.inject_credential_store_credentials(
            user_id=None, env=env
        )
        self.assertEqual(merged["OPENAI_API_KEY"], "env-key")

    def test_missing_encryption_key_preserves_old_behavior(self) -> None:
        env = {"OPENAI_API_KEY": "env-key"}
        merged = inject_credential_store_credentials(
            user_id="user-1", env=env
        )
        # CredentialStore default path/env likely unavailable under test; must not raise.
        self.assertIn("OPENAI_API_KEY", merged)

    def test_unknown_provider_ignored_safely(self) -> None:
        adapter = ProviderCredentialAdapter(store=_FakeStore.empty())
        env = {}
        merged = adapter.inject_credential_store_credentials(
            user_id="user-1", env=env
        )
        self.assertEqual(merged, {})

    def test_multiple_providers_resolve_correctly(self) -> None:
        adapter = ProviderCredentialAdapter(
            store=_FakeStore.multi(["openai", "groq"])
        )
        env: dict[str, str] = {}
        merged = adapter.inject_credential_store_credentials(
            user_id="user-1", env=env
        )
        self.assertEqual(merged["OPENAI_API_KEY"], "byok-openai")
        self.assertEqual(merged["GROQ_API_KEY"], "byok-groq")

    def test_resolve_provider_credentials_returns_only_env_var_names(self) -> None:
        adapter = ProviderCredentialAdapter(store=_FakeStore.openai())
        resolved = adapter.resolve_provider_credentials("user-1")
        self.assertEqual(set(resolved.keys()), {"OPENAI_API_KEY"})

    def test_no_secret_fields_in_metadata_returned(self) -> None:
        adapter = ProviderCredentialAdapter(store=_FakeStore.openai())
        resolved = adapter.resolve_provider_credentials("user-1")
        self.assertNotIn("encrypted_secret", resolved)
        self.assertNotIn("nonce", resolved)
        self.assertNotIn("user_id", resolved)

    def test_backward_compatibility_with_merge_provider_credentials(self) -> None:
        env = merge_provider_credentials(
            env={}, user_id="user-without-store"
        )
        self.assertIsInstance(env, dict)

    def test_resolution_priority_byok_over_env_over_fallback(self) -> None:
        adapter = ProviderCredentialAdapter(store=_FakeStore.openai())
        env = {"OPENAI_API_KEY": "env-key"}
        merged = adapter.inject_credential_store_credentials(
            user_id="user-1", env=env
        )
        self.assertEqual(merged["OPENAI_API_KEY"], "byok-openai")


class _FakeStore:
    @staticmethod
    def _record(provider_id: str, secret: str):
        expected_provider_id = provider_id

        class _Cred:
            def __init__(self) -> None:
                self.provider_id = expected_provider_id
                self.user_id = "user-1"

            def to_metadata(self):
                raise AssertionError("should not be serialized")

        class _Store:
            def get_credential_by_provider(self, *, user_id, provider_id, decrypt):
                if user_id == "user-1" and provider_id == expected_provider_id:
                    if decrypt:
                        return secret
                    return _Cred()
                raise LookupError

            def list_credential_metadata(self, *_, **__):
                return []

        return _Store()

    @classmethod
    def openai(cls):
        return cls._record("openai", "byok-openai")

    @classmethod
    def groq(cls):
        return cls._record("groq", "byok-groq")

    @classmethod
    def empty(cls):
        class _Store:
            def get_credential_by_provider(self, *_, **__):
                raise LookupError

            def list_credential_metadata(self, *_, **__):
                return []

        return _Store()

    @classmethod
    def multi(cls, providers):
        class _Store:
            mapping = {
                "openai": "byok-openai",
                "groq": "byok-groq",
            }

            def get_credential_by_provider(self, *, user_id, provider_id, decrypt):
                secret = self.mapping.get(provider_id)
                if secret and user_id == "user-1" and decrypt:
                    return secret
                raise LookupError

            def list_credential_metadata(self, *_, **__):
                return []

        return _Store()


if __name__ == "__main__":
    unittest.main()
