"""Provider settings controller for BYOK credential management."""

from __future__ import annotations

import logging
import time
from typing import Any

from .encrypted_credential_store import (
    CredentialStore,
    CredentialStoreError,
    EncryptionKeyError,
    _redact_user,
)
from .provider_health import (
    invalidate_provider_health,
    provider_health_probe_allowed,
    read_provider_health,
    record_provider_health,
)
from .provider_registry import PROVIDERS, provider_execution_capability

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
ACTIVE_TEST_PROVIDERS = frozenset({"openai", "openrouter", "gemini", "groq", "anthropic"})


class ProviderSettingsController:
    """Controller for BYOK provider credential management."""

    def __init__(self, store: CredentialStore | None = None) -> None:
        self._store = store if store is not None else self._build_store()

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
        normalized = _normalize_user_id(user_id)
        by_provider = {}
        store = self._store
        if store is not None:
            try:
                metadata = store.list_credential_metadata(user_id=normalized)
                by_provider = {item.provider_id: item for item in metadata}
            except Exception as exc:  # pragma: no cover — hardened fallback
                logger.debug(
                    "provider_settings.list_failed user=%s error=%s",
                    _redact_user(normalized),
                    exc,
                )
        results: list[dict[str, Any]] = []
        for provider in ALLOWED_PROVIDERS:
            item = by_provider.get(provider)
            configured = item is not None
            capability = provider_execution_capability(provider, configured=configured)
            results.append(
                {
                    "provider": provider,
                    "configured": configured,
                    **capability,
                    "updated_at": item.updated_at if item else None,
                    **read_provider_health(normalized, provider),
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
        invalidate_provider_health(normalized_user, normalized_provider)
        logger.info(
            "Saved BYOK provider=%s user=%s",
            normalized_provider,
            _redact_user(normalized_user),
        )
        return self._provider_metadata_response(normalized_user, normalized_provider)

    def update_provider(
        self,
        user_id: str,
        provider_id: str,
        secret: str,
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
        credential_id = _extract_credential_id(credential)
        store.update_credential(credential_id=credential_id, secret=secret)
        invalidate_provider_health(normalized_user, normalized_provider)
        logger.info(
            "Updated BYOK provider=%s user=%s",
            normalized_provider,
            _redact_user(normalized_user),
        )
        return self._provider_metadata_response(normalized_user, normalized_provider)

    def delete_provider(self, user_id: str, provider_id: str) -> dict[str, Any]:
        self._require_allowed_provider(provider_id)
        normalized_user = _normalize_user_id(user_id)
        normalized_provider = _normalize_provider(provider_id)
        store = self._store
        if store is not None:
            try:
                credential = store.get_credential_by_provider(
                    user_id=normalized_user,
                    provider_id=normalized_provider,
                    decrypt=False,
                )
                credential_id = _extract_credential_id(credential)
                store.delete_credential(credential_id=credential_id)
                logger.info(
                    "Deleted BYOK provider=%s user=%s",
                    normalized_provider,
                    _redact_user(normalized_user),
                )
            except Exception as exc:  # pragma: no cover — hardened fallback
                logger.debug(
                    "provider_settings.delete_failed user=%s provider=%s error=%s",
                    _redact_user(normalized_user),
                    normalized_provider,
                    exc,
                )
        invalidate_provider_health(normalized_user, normalized_provider)
        capability = provider_execution_capability(
            normalized_provider,
            configured=False,
        )
        return {
            "provider": normalized_provider,
            "configured": False,
            **capability,
            "updated_at": None,
            **read_provider_health(normalized_user, normalized_provider),
        }

    def test_provider(self, user_id: str, provider_id: str, secret: str) -> dict[str, Any]:
        """Validate provider credentials without persisting them."""
        self._require_allowed_provider(provider_id)
        self._require_secret(secret)
        normalized_user = _normalize_user_id(user_id)
        normalized_provider = _normalize_provider(provider_id)
        capability = provider_execution_capability(
            normalized_provider,
            configured=True,
        )
        if not capability["executable"]:
            return {
                "provider": normalized_provider,
                "success": False,
                "error": "Provider adapter is not executable",
                "cached": False,
                **read_provider_health(normalized_user, normalized_provider),
            }
        if normalized_provider not in ACTIVE_TEST_PROVIDERS:
            return {
                "provider": normalized_provider,
                "success": False,
                "error": "Active health test is not supported for this provider",
                "cached": False,
                **read_provider_health(normalized_user, normalized_provider),
            }

        probe_allowed, cached_health = provider_health_probe_allowed(
            normalized_user,
            normalized_provider,
        )
        if not probe_allowed:
            return {
                "provider": normalized_provider,
                "success": False,
                "error": "Provider health circuit is open",
                "cached": True,
                **cached_health,
            }

        started = time.monotonic()
        result = _run_provider_test(provider_id=normalized_provider, secret=secret)
        latency_ms = max(0, round((time.monotonic() - started) * 1000))
        health = record_provider_health(
            normalized_user,
            normalized_provider,
            reachable=bool(result["reachable"]),
            healthy=bool(result["success"]),
            latency_ms=latency_ms,
        )
        return {
            "provider": normalized_provider,
            "success": result["success"],
            "error": result.get("error"),
            "cached": False,
            **health,
        }

    def _provider_metadata_response(
        self,
        user_id: str,
        provider_id: str,
    ) -> dict[str, Any]:
        updated_at = None
        store = self._store
        if store is not None:
            try:
                stored = store.get_credential_by_provider(
                    user_id=user_id,
                    provider_id=provider_id,
                    decrypt=False,
                )
                if hasattr(stored, "updated_at"):
                    updated_at = stored.updated_at
                credential_id = _extract_credential_id(stored)
                if not credential_id:
                    updated_at = None
            except Exception:
                updated_at = None
        configured = True
        capability = provider_execution_capability(provider_id, configured=configured)
        return {
            "provider": provider_id,
            "configured": configured,
            **capability,
            "updated_at": updated_at,
            **read_provider_health(user_id, provider_id),
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

    def _require_store(self) -> CredentialStore:
        if self._store is None:
            raise RuntimeError("CredentialStore is required but not available")
        return self._store


def _normalize_provider(provider_id: str) -> str:
    return str(provider_id or "").strip().lower()


def _normalize_user_id(user_id: str) -> str:
    return str(user_id or "").strip()


def _extract_credential_id(credential: Any) -> str:
    if hasattr(credential, "credential_id"):
        value = credential.credential_id
        return value if isinstance(value, str) else ""
    if isinstance(credential, str):
        return credential
    return ""


def list_providers(user_id: str) -> list[dict[str, Any]]:
    controller = ProviderSettingsController()
    return controller.list_providers(user_id=user_id)


def save_provider(user_id: str, provider_id: str, secret: str) -> dict[str, Any]:
    controller = ProviderSettingsController()
    return controller.save_provider(user_id=user_id, provider_id=provider_id, secret=secret)


def update_provider(
    user_id: str,
    provider_id: str,
    secret: str,
) -> dict[str, Any]:
    controller = ProviderSettingsController()
    return controller.update_provider(user_id=user_id, provider_id=provider_id, secret=secret)


def delete_provider(user_id: str, provider_id: str) -> dict[str, Any]:
    controller = ProviderSettingsController()
    return controller.delete_provider(user_id=user_id, provider_id=provider_id)


def test_provider(user_id: str, provider_id: str, secret: str) -> dict[str, Any]:
    controller = ProviderSettingsController()
    return controller.test_provider(
        user_id=user_id,
        provider_id=provider_id,
        secret=secret,
    )


def _run_provider_test(provider_id: str, secret: str) -> dict[str, Any]:
    """Execute a lightweight provider validation.

    Returns a public-safe result dict with success status and optional
    public error message. Never returns internal exception details.
    """
    try:
        if provider_id in {"openai", "openrouter", "gemini", "groq"}:
            return _test_openai_compatible(provider_id, secret)
        if provider_id == "anthropic":
            return _test_anthropic(secret)
    except Exception as exc:  # pragma: no cover — runtime hardening
        logger.debug(
            "Provider test failed provider=%s error=%s",
            provider_id,
            exc,
        )
        return {
            "success": False,
            "reachable": False,
            "error": "Unable to reach provider",
        }
    return {
        "success": False,
        "reachable": False,
        "error": "Unable to reach provider",
    }


def _test_openai_compatible(
    provider_id: str,
    secret: str,
    timeout: int = 5,
) -> dict[str, Any]:
    base_url = _provider_base_url(provider_id)
    headers = _provider_headers(provider_id, secret)
    url = f"{base_url.rstrip('/')}/models"
    try:
        response = _http_get(url=url, headers=headers, timeout=timeout)
    except Exception as exc:
        if not _is_http_error(exc):
            return {
                "success": False,
                "reachable": False,
                "error": "Unable to reach provider",
            }
        response = exc
    status = _response_status(response)
    if status in {401, 403}:
        return {"success": False, "reachable": True, "error": "Invalid API key"}
    if status == 429:
        return {
            "success": False,
            "reachable": True,
            "error": "Provider rate limited the health test",
        }
    if status == 200:
        return {"success": True, "reachable": True}
    return {
        "success": False,
        "reachable": True,
        "error": "Provider returned an unhealthy response",
    }


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
    except Exception as exc:
        if not _is_http_error(exc):
            return {
                "success": False,
                "reachable": False,
                "error": "Unable to reach provider",
            }
        response = exc
    status = _response_status(response)
    if status in {401, 403}:
        return {"success": False, "reachable": True, "error": "Invalid API key"}
    if status == 429:
        return {
            "success": False,
            "reachable": True,
            "error": "Provider rate limited the health test",
        }
    if status == 200:
        return {"success": True, "reachable": True}
    if status == 400:
        data = _safe_json(response)
        if isinstance(data, dict) and data.get("error", {}).get("type") == "authentication_error":
            return {"success": False, "reachable": True, "error": "Invalid API key"}
        return {"success": True, "reachable": True}
    return {
        "success": False,
        "reachable": True,
        "error": "Provider returned an unhealthy response",
    }


def _response_status(response: Any) -> int:
    value = getattr(response, "status_code", getattr(response, "code", 0))
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _is_http_error(error: Exception) -> bool:
    import urllib.error

    return isinstance(error, urllib.error.HTTPError)


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
    import json

    try:
        return response.json()
    except Exception:
        pass

    reader = getattr(response, "read", None)
    if not callable(reader):
        return None
    try:
        raw = reader(65_537)
        if not isinstance(raw, (bytes, bytearray)) or len(raw) > 65_536:
            return None
        return json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError, TypeError):
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
