"""BYOK credential adapter — bridges CredentialStore into runtime env resolution.

The adapter sits between the encrypted credential store (P5D) and the
existing provider env-merge pipeline. It introduces a precedence model:

1. User-supplied CredentialStore entries (BYOK) — highest priority
2. Existing environment variables
3. Existing runtime fallback behavior

Contract
--------
- Never log plaintext secrets.
- Never return encrypted payloads, nonces, or raw StoredCredential fields.
- Fail closed when the store or key is misconfigured.
- Preserve backward compatibility: callers passing ``user_id=None`` get
  unchanged behavior.
"""

from __future__ import annotations

import logging
from typing import Any

from .encrypted_credential_store import (
    CredentialStore,
    CredentialStoreError,
    EncryptionKeyError,
    _redact_user,
)

__all__ = [
    "ProviderCredentialAdapter",
    "resolve_provider_credentials",
    "inject_credential_store_credentials",
    "BYOKResolutionError",
]

logger = logging.getLogger(__name__)

# Logical provider id -> primary env var name. Keep as a single source of
# truth here to avoid duplicating allowlists around the codebase.
_LOGICAL_TO_ENV_NAME: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "ollama": "OLLAMA_URL",
    "lmstudio": "LMSTUDIO_URL",
    "codex": "CODEX_API_KEY",
}


class BYOKResolutionError(Exception):
    """Raised when BYOK resolution fails for reasons other than missing data."""


class ProviderCredentialAdapter:
    """Stateful adapter around a CredentialStore instance."""

    def __init__(self, store: CredentialStore | None = None) -> None:
        self._store = store

    def _get_store(self) -> CredentialStore | None:
        return self._store

    def load_credential(
        self, user_id: str, provider_id: str
    ) -> str | None:
        """Return decrypted secret for a single provider, or None.

        Logs only provider + redacted user identifiers, never the secret.
        """
        store = self._get_store()
        if store is None:
            return None

        try:
            secret = store.get_credential_by_provider(
                user_id=user_id,
                provider_id=provider_id,
                decrypt=True,
            )
        except (CredentialStoreError, LookupError, KeyError):
            logger.debug(
                "BYOK miss user=%s provider=%s",
                _redact_user(user_id),
                provider_id,
            )
            return None

        if not isinstance(secret, str) or not secret.strip():
            logger.debug(
                "BYOK empty secret user=%s provider=%s",
                _redact_user(user_id),
                provider_id,
            )
            return None

        return secret

    def resolve_provider_credentials(
        self, user_id: str | None = None
    ) -> dict[str, str]:
        """Resolve credentials for registered providers.

        Returns env-style mappings where keys are env var names and values
        are decrypted secrets from CredentialStore when available.
        """
        if not user_id or not str(user_id).strip():
            return {}

        user_id = str(user_id).strip()
        store = self._get_store()
        if store is None:
            return {}

        resolved: dict[str, str] = {}

        for provider_id, env_name in _LOGICAL_TO_ENV_NAME.items():
            try:
                secret = self.load_credential(user_id, provider_id)
            except Exception as exc:  # pragma: no cover — defensive guard
                logger.debug(
                    "BYOK resolution failed user=%s provider=%s error=%s",
                    _redact_user(user_id),
                    provider_id,
                    exc,
                )
                continue

            if secret is None:
                continue

            resolved[env_name] = secret

        return resolved

    def inject_credential_store_credentials(
        self,
        user_id: str | None,
        env: dict[str, str],
    ) -> dict[str, str]:
        """Merge BYOK credentials into an existing env mapping.

        Applies precedence: BYOK credentials override environment variables.
        The input env dict is not mutated; a new dict is returned.
        """
        merged = dict(env)

        if user_id is None:
            return merged

        normalized = str(user_id).strip()
        if not normalized:
            return merged

        byok_map = self.resolve_provider_credentials(user_id=normalized)
        if not byok_map:
            return merged

        merged.update(byok_map)
        return merged


def _build_adapter_from_env() -> ProviderCredentialAdapter | None:
    """Try to construct an adapter backed by a real CredentialStore.

    Returns None when the encryption key is missing or the store path is
    invalid. Callers MUST handle None as "BYOK disabled".
    """
    try:
        store = CredentialStore()
    except (CredentialStoreError, EncryptionKeyError):
        logger.debug("CredentialStore unavailable; BYOK disabled")
        return None
    except Exception as exc:  # pragma: no cover — defensive guard
        logger.debug("CredentialStore initialization failed: %s", exc)
        return None
    return ProviderCredentialAdapter(store=store)


def resolve_provider_credentials(user_id: str | None = None) -> dict[str, str]:
    """Module-level helper matching the requested signature.

    Returns env-style provider mappings derived from CredentialStore when
    available. Falls back to empty mapping on any failure.
    """
    adapter = _build_adapter_from_env()
    if adapter is None:
        return {}
    return adapter.resolve_provider_credentials(user_id=user_id)


def inject_credential_store_credentials(
    user_id: str | None,
    env: dict[str, str],
) -> dict[str, str]:
    """Module-level helper matching the requested signature.

    Merges CredentialStore credentials into an existing env mapping
    without mutating the input dict.
    """
    adapter = _build_adapter_from_env()
    if adapter is None:
        return dict(env)
    return adapter.inject_credential_store_credentials(user_id=user_id, env=env)
