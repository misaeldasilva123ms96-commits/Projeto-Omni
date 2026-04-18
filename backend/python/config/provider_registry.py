"""Logical LLM provider ids configured via environment (validated through secrets_manager)."""

from __future__ import annotations

from .secrets_manager import SecretError, get_secret

PROVIDERS: tuple[str, ...] = (
    "openai",
    "anthropic",
    "groq",
    "gemini",
    "deepseek",
)


def get_available_providers() -> list[str]:
    """Return provider ids that have valid, non-placeholder credentials."""
    available: list[str] = []
    for provider in PROVIDERS:
        try:
            get_secret(provider)
        except SecretError:
            continue
        available.append(provider)
    return available


def providers_capability() -> dict[str, list[str]]:
    """Safe JSON fragment for APIs — keys only, no secret material."""
    return {"providers": list(get_available_providers())}
