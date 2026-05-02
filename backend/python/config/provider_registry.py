"""Logical LLM provider ids configured via environment (validated through secrets_manager)."""

from __future__ import annotations

from typing import Any

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


def describe_provider_diagnostics(
    *,
    selected_provider: str = "",
    actual_provider: str = "",
    attempted_provider: str = "",
    succeeded_provider: str = "",
    failure_class: str = "",
    failure_reason: str = "",
    latency_ms: int | None = None,
    include_embedded_local: bool = False,
) -> list[dict[str, Any]]:
    """
    Public-safe provider diagnostics.

    ``configured`` and ``available`` are configuration-level truths only.
    They do not claim network reachability.
    """
    available = set(get_available_providers())
    selected = str(selected_provider or "").strip().lower()
    actual = str(actual_provider or "").strip().lower()
    attempted = str(attempted_provider or actual or "").strip().lower()
    succeeded = str(succeeded_provider or actual if not failure_class else "").strip().lower()
    failure_kind = str(failure_class or "").strip().lower()
    failure_detail = str(failure_reason or "").strip()

    names = list(PROVIDERS)
    if include_embedded_local and "local-heuristic" not in names:
        names.append("local-heuristic")
    for candidate in (selected, actual, attempted, succeeded):
        if candidate and candidate not in names:
            names.append(candidate)

    rows: list[dict[str, Any]] = []
    for provider in names:
        configured = provider == "local-heuristic" or provider in available
        selected_here = provider == selected
        attempted_here = provider == attempted
        succeeded_here = provider == succeeded and not failure_kind
        failed_here = attempted_here and bool(failure_kind)
        row: dict[str, Any] = {
            "provider": provider,
            "configured": configured,
            "key_present": configured if provider != "local-heuristic" else False,
            "model_configured": True,
            "available": configured,
            "selected": selected_here,
            "attempted": attempted_here,
            "succeeded": succeeded_here,
            "failed": failed_here,
            "failure_class": failure_kind if failed_here else None,
            "failure_reason": failure_detail if failed_here else None,
            "latency_ms": int(latency_ms) if failed_here is False and attempted_here and latency_ms is not None else None,
        }
        rows.append(row)
    return rows
