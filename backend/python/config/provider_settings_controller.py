"""Provider settings controller for BYOK credential management."""

from __future__ import annotations

import logging
from typing import Any

from .encrypted_credential_store import (
    CredentialStore,
    CredentialStoreError,
    EncryptionKeyError,
    _redact_user,
)
from .provider_registry import PROVIDERS, provider_metadata

__all__ = [
    "ProviderSettingsController",
    "list_providers",
    "save_provider",
    "update_provider",
    "delete_provider",
    "test_provider",
    "ALLOWED_PROVIDERS",
]

logger = logging.getLogger(__name__)

ALLOWED_PROVIDERS = tuple(str(provider) for provider in PROVIDERS)


class ProviderSettingsController:
    """Controller for BYOK provider credential management."""

    def __init__(self, store: CredentialStore | None = None) -> None:
        self._store = store or self._build_store()

    @staticmethod
    def _build_store() -> CredentialStore | None:
        try:
            from .encrypted_credential_store import CredentialStore  # noqa: F401
        except ModuleNotFoundError:
            return None
        try:
            return CredentialStore()
        except (CredentialStoreError, EncryptionKeyError):
            return None

    def list_providers(self, user_id: str) -> list[dict[str, Any]]:
        """Return credential metadata for available providers."""
        store = self._store
        if store is None:
            return []
        normalized = _normalize_user_id(user_id)
        metadata = store.list_credential_metadata(user_id=normalized)
        by_provider = {item.provider_id: item for item in metadata}
        results: list[dict[str, Any]] = []
        for provider in ALLOWED_PROVIDERS:
            item = by_provider.get(provider)
            results.append(
                {
                    "provider": provider,
                    "configured": item is not None,
                    "updated_at": item.updated_at if item else None,
                }
            )
        return results

    def save_provider(self, user_id: str, provider_id: str, secret: str) -> dict[str, Any]:
        self._require_allowed_provider(provider_id)
        self._require_secret(secret)
        store = self._require_store()
        normalized_user = _normalize_user_id(user_id)
        normalized_provider = _normalize_provider(provider_id)
        store.save_credential(
            user_id=normalized_user,
            provider_id=normalized_provider,
            secret=secret,
        )
        logger.info(
            "Saved BYOK provider=%s user=%s",
            normalized_provider,
            _redact_user(normalized_user),
        )
        return self._provider_metadata_response(normalized_user, normalized_provider)

    def update_provider(
        self, user_id: str, provider_id: str, secret: str
    ) -> dict[str, Any]:
        self._require_allowed_provider(provider_id)
        self._require_secret(secret)
        store = self._require_store()
        normalized_user = _normalize_user_id(user_id)
        normalized_provider = _normalize_provider(provider_id)
        credential = store.get_credential_by_provider(
            user_id=normalized_user,
            provider_id=normalized_provider,
            decrypt=False,
        )
        if hasattr(credential, "credential_id"):
            credential_id = credential.credential_id
        else:
            credential_id = credential if isinstance(credential, str) else ""
        store.update_credential(credential_id=credential_id, secret=secret)
        logger.info(
            "Updated BYOK provider=%s user=%s",
            normalized_provider,
            _redact_user(normalized_user),
        )
        return self._provider_metadata_response(normalized_user, normalized_provider)

    def delete_provider(self, user_id: str, provider_id: str) -> dict[str, Any]:
        self._require_allowed_provider(provider_id)
        store = self._require_store()
        normalized_user = _normalize_user_id(user_id)
        normalized_provider = _normalize_provider(provider_id)
        try:
            credential = store.get_credential_by_provider(
                user_id=normalized_user,
                provider_id=normalized_provider,
                decrypt=False,
            )
        except Exception:
            return {
                "provider": normalized_provider,
                "configured": False,
                "updated_at": None,
            }
        if hasattr(credential, "credential_id"):
            credential_id = credential.credential_id
        else:
            credential_id = credential if isinstance(credential, str) else ""
        store.delete_credential(credential_id=credential_id)
        logger.info(
            "Deleted BYOK provider=%s user=%s",
            normalized_provider,
            _redact_user(normalized_user),
        )
        return {
            "provider": normalized_provider,
            "configured": False,
            "updated_at": None,
        }

    def test_provider(self, provider_id: str, secret: str) -> dict[str, Any]:
        """Validate provider credentials without persisting them."""
        self._require_allowed_provider(provider_id)
        self._require_secret(secret)
        normalized_provider = _normalize_provider(provider_id)
        result = _run_provider_test(provider_id=normalized_provider, secret=secret)
        return {
            "provider": normalized_provider,
            "success": result["success"],
            "error": result.get("error"),
        }

    def _provider_metadata_response(
        self, user_id: str, provider_id: str
    ) -> dict[str, Any]:
        store = self._store
        if store is None:
            return {
                "provider": provider_id,
                "configured": True,
                "updated_at": None,
            }
        try:
            stored = store.get_credential_by_provider(
                user_id=user_id,
                provider_id=provider_id,
                decrypt=False,
            )
        except Exception:
            return {
                "provider": provider_id,
                "configured": True,
                "updated_at": None,
            }
        if hasattr(stored, "updated_at"):
            updated_at = stored.updated_at
        else:
            updated_at = None
        return {
            "provider": provider_id,
            "configured": True,
            "updated_at": updated_at,
        }

    @staticmethod
    def _require_allowed_provider(provider_id: str) -> None:
        normalized = _normalize_provider(provider_id)
        if normalized not in ALLOWED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider_id}")

    @staticmethod
    def _require_secret(secret: str) -> None:
        if not isinstance(secret, str) or not secret.strip():
            raise ValueError("Secret must be a non-empty string")

    @staticmethod
    def _require_store() -> CredentialStore:
        raise RuntimeError("CredentialStore is required but not available")


def _normalize_provider(provider_id: str) -> str:
    return str(provider_id or "").strip().lower()


def _normalize_user_id(user_id: str) -> str:
    return str(user_id or "").strip()


def list_providers(user_id: str) -> list[dict[str, Any]]:
    controller = ProviderSettingsController()
    return controller.list_providers(user_id=user_id)


def save_provider(user_id: str, provider_id: str, secret: str) -> dict[str, Any]:
    controller = ProviderSettingsController()
    return controller.save_provider(
        user_id=user_id, provider_id=provider_id, secret=secret
    )


def update_provider(
    user_id: str, provider_id: str, secret: str
) -> dict[str, Any]:
    controller = ProviderSettingsController()
    return controller.update_provider(
        user_id=user_id, provider_id=provider_id, secret=secret
    )


def delete_provider(user_id: str, provider_id: str) -> dict[str, Any]:
    controller = ProviderSettingsController()
    return controller.delete_provider(user_id=user_id, provider_id=provider_id)


def test_provider(provider_id: str, secret: str) -> dict[str, Any]:
    controller = ProviderSettingsController()
    return controller.test_provider(provider_id=provider_id, secret=secret)


def _run_provider_test(provider_id: str, secret: str) -> dict[str, Any]:
    """Execute a lightweight provider validation.

    Returns a public-safe result dict with success status and optional
    public error message. Never returns internal exception details.
    """
    try:
        if provider_id in {"openai", "openrouter", "gemini", "groq"}:
            result = _test_openai_compatible(provider_id, secret)
            return result
        if provider_id == "anthropic":
            return _test_anthropic(secret)
    except Exception as exc:  # pragma: no cover — runtime hardening
        logger.debug(
            "Provider test failed provider=%s error=%s",
            provider_id,
            exc,
        )
        return {"success": False, "error": "Unable to reach provider"}
    return {"success": False, "error": "Unable to reach provider"}


def _test_openai_compatible(
    provider_id: str, secret: str, timeout: int = 5
) -> dict[str, Any]:
    base_url = _provider_base_url(provider_id)
    headers = _provider_headers(provider_id, secret)
    url = f"{base_url.rstrip('/')}/models"
    try:
        response = _http_get(url=url, headers=headers, timeout=timeout)
    except Exception:
        return {"success": False, "error": "Unable to reach provider"}
    if response.status_code == 401:
        return {"success": False, "error": "Invalid API key"}
    if response.status_code == 403:
        return {"success": False, "error": "Invalid API key"}
    if response.status_code == 429:
        return {"success": False, "error": "Unable to reach provider"}
    if response.status_code == 200:
        return {"success": True}
    return {"success": False, "error": "Unable to reach provider"}


def _test_anthropic(secret: str, timeout: int = 5) -> dict[str, Any]:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": secret,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": "claude-3-5-sonnet-latest",
        "max_tokens": 1,
        "messages": [{"role": "user", "content": "ping"}],
    }
    try:
        response = _http_post(url=url, headers=headers, body=body, timeout=timeout)
    except Exception:
        return {"success": False, "error": "Unable to reach provider"}
    if response.status_code == 401:
        return {"success": False, "error": "Invalid API key"}
    if response.status_code == 403:
        return {"success": False, "error": "Invalid API key"}
    if response.status_code == 429:
        return {"success": False, "error": "Unable to reach provider"}
    if response.status_code == 200:
        return {"success": True}
    if response.status_code == 400:
        data = _safe_json(response)
        if isinstance(data, dict) and data.get("error", {}).get("type") == "authentication_error":
            return {"success": False, "error": "Invalid API key"}
        return {"success": True}
    return {"success": False, "error": "Unable to reach provider"}


def _provider_base_url(provider_id: str) -> str:
    mapping = {
        "openai": "https://api.openai.com/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "gemini": "https://generativelanguage.googleapis.com/v1beta",
        "groq": "https://api.groq.com/openai/v1",
    }
    return mapping.get(provider_id, "")


def _provider_headers(provider_id: str, secret: str) -> dict[str, str]:
    headers: dict[str, str] = {"Authorization": f"Bearer {secret}"}
    if provider_id == "openai":
        headers.setdefault("openai-version", "v1")
    if provider_id == "openrouter":
        headers.setdefault("HTTP-Referer", "https://omni.local")
        headers.setdefault("X-Title", "Omni BYOK")
    return headers


def _safe_json(response: Any) -> Any:
    try:
        return response.json()
    except Exception:
        return None


def _http_get(url: str, headers: dict[str, str], timeout: int = 5) -> Any:
    import urllib.error
    import urllib.request

    req = urllib.request.Request(url=url, headers=headers, method="GET")
    return urllib.request.urlopen(req, timeout=timeout)


def _http_post(
    url: str,
    headers: dict[str, str],
    body: dict[str, Any],
    timeout: int = 5,
) -> Any:
    import json
    import urllib.error
    import urllib.request

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=data,
        headers=headers,
        method="POST",
    )
    return urllib.request.urlopen(req, timeout=timeout)
