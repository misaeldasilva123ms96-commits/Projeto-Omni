from __future__ import annotations

import os
from typing import Any

SESSION_BYOK_ALLOWED_PROVIDERS = {
    "groq",
    "openrouter",
    "openai",
    "anthropic",
    "gemini",
    "ollama",
    "lmstudio",
}
SESSION_BYOK_ENV_MAP = {
    "groq": ("GROQ_API_KEY", "GROQ_MODEL"),
    "openrouter": ("OPENROUTER_API_KEY", "OPENROUTER_MODEL"),
    "openai": ("OPENAI_API_KEY", "OPENAI_MODEL"),
    "anthropic": ("ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"),
    "gemini": ("GEMINI_API_KEY", "GEMINI_MODEL"),
    "ollama": ("OLLAMA_API_KEY", "OLLAMA_MODEL"),
    "lmstudio": ("LMSTUDIO_API_KEY", "LMSTUDIO_MODEL"),
}
SESSION_BYOK_MAX_API_KEY_CHARS = 4096
SESSION_BYOK_MAX_MODEL_CHARS = 128
SESSION_BYOK_CLOUD_PROVIDERS = {"groq", "openrouter", "openai", "anthropic", "gemini"}
SESSION_BYOK_PUBLIC_RESPONSE = (
    "[degraded:byok_session] Session BYOK credentials could not be used safely for this request."
)
DEFAULT_SESSION_ID = "python-session"


def session_id() -> str:
    """Prefer explicit operator `AI_SESSION_ID`, then Rust bridge `OMNI_BRIDGE_CLIENT_SESSION_ID`."""
    configured = os.getenv("AI_SESSION_ID", "").strip()
    if configured:
        return configured
    bridge_sid = os.getenv("OMNI_BRIDGE_CLIENT_SESSION_ID", "").strip()
    if bridge_sid:
        return bridge_sid[:512]
    return DEFAULT_SESSION_ID


def normalize_session_provider_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if not normalized or normalized not in SESSION_BYOK_ALLOWED_PROVIDERS:
        return None
    if any(ord(ch) < 32 for ch in normalized):
        return None
    return normalized


def private_bridge_source(bridge: dict[str, Any]) -> dict[str, Any]:
    client_context = bridge.get("client_context")
    if isinstance(client_context, dict):
        return {**bridge, **client_context}
    return dict(bridge)


def safe_session_secret(value: Any, *, max_chars: int) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    if not trimmed or len(trimmed) > max_chars:
        return None
    if any(ord(ch) < 32 for ch in trimmed):
        return None
    return trimmed


def extract_session_byok_bridge(bridge: dict[str, Any]) -> dict[str, Any]:
    source = private_bridge_source(bridge)
    raw_credentials = source.get("session_provider_credentials")
    provider_preference_raw = source.get("provider_preference")
    provider_preference = normalize_session_provider_id(provider_preference_raw)
    if not isinstance(raw_credentials, dict):
        return {
            "active": False,
            "provider": provider_preference,
            "env_overlay": {},
            "error_reason": None,
        }
    if not raw_credentials:
        return {
            "active": False,
            "provider": provider_preference,
            "env_overlay": {},
            "error_reason": None,
        }
    if isinstance(provider_preference_raw, str) and provider_preference_raw.strip() and not provider_preference:
        return {
            "active": True,
            "provider": None,
            "env_overlay": {},
            "error_reason": "byok_provider_not_allowed",
        }
    if not provider_preference:
        return {
            "active": True,
            "provider": None,
            "env_overlay": {},
            "error_reason": "byok_provider_preference_required",
        }
    if provider_preference not in raw_credentials:
        return {
            "active": True,
            "provider": provider_preference,
            "env_overlay": {},
            "error_reason": "byok_credentials_missing_for_provider",
        }

    env_overlay: dict[str, str] = {}
    raw_credential = raw_credentials.get(provider_preference)
    if not isinstance(raw_credential, dict):
        return {
            "active": True,
            "provider": provider_preference,
            "env_overlay": {},
            "error_reason": "byok_credentials_incomplete",
        }

    key_env, model_env = SESSION_BYOK_ENV_MAP[provider_preference]
    api_key = safe_session_secret(
        raw_credential.get("api_key"),
        max_chars=SESSION_BYOK_MAX_API_KEY_CHARS,
    )
    model = safe_session_secret(
        raw_credential.get("model"),
        max_chars=SESSION_BYOK_MAX_MODEL_CHARS,
    )
    if provider_preference in SESSION_BYOK_CLOUD_PROVIDERS and not api_key:
        return {
            "active": True,
            "provider": provider_preference,
            "env_overlay": {},
            "error_reason": "byok_credentials_incomplete",
        }
    if provider_preference not in SESSION_BYOK_CLOUD_PROVIDERS and not api_key and not model:
        return {
            "active": True,
            "provider": provider_preference,
            "env_overlay": {},
            "error_reason": "byok_credentials_incomplete",
        }
    if api_key:
        env_overlay[key_env] = api_key
    if model:
        env_overlay[model_env] = model
    return {
        "active": True,
        "provider": provider_preference,
        "env_overlay": env_overlay,
        "error_reason": None,
    }
