"""Logical LLM provider ids configured via environment (validated through secrets_manager)."""

from __future__ import annotations

import os
from typing import Any

from .secrets_manager import SecretError, get_secret

PROVIDER_METADATA: tuple[dict[str, Any], ...] = (
    {
        "provider": "groq",
        "env_var": "GROQ_API_KEY",
        "model_env_var": "GROQ_MODEL",
        "registered": True,
        "adapter_implemented": True,
        "enabled_by_default": True,
        "execution_status": "credential_gated",
    },
    {
        "provider": "openrouter",
        "env_var": "OPENROUTER_API_KEY",
        "model_env_var": "OPENROUTER_MODEL",
        "registered": True,
        "adapter_implemented": True,
        "enabled_by_default": False,
        "execution_status": "credential_gated",
    },
    {
        "provider": "openai",
        "env_var": "OPENAI_API_KEY",
        "model_env_var": "OPENAI_MODEL",
        "registered": True,
        "adapter_implemented": False,
        "enabled_by_default": False,
        "execution_status": "unsupported",
    },
    {
        "provider": "anthropic",
        "env_var": "ANTHROPIC_API_KEY",
        "model_env_var": "ANTHROPIC_MODEL",
        "registered": True,
        "adapter_implemented": False,
        "enabled_by_default": False,
        "execution_status": "unsupported",
    },
    {
        "provider": "gemini",
        "env_var": "GEMINI_API_KEY",
        "model_env_var": "GEMINI_MODEL",
        "registered": True,
        "adapter_implemented": False,
        "enabled_by_default": False,
        "execution_status": "unsupported",
    },
    {
        "provider": "deepseek",
        "env_var": "DEEPSEEK_API_KEY",
        "model_env_var": "DEEPSEEK_MODEL",
        "registered": True,
        "adapter_implemented": False,
        "enabled_by_default": False,
        "execution_status": "unsupported",
    },
    {
        "provider": "ollama",
        "env_var": "OLLAMA_URL",
        "model_env_var": "OLLAMA_MODEL",
        "registered": True,
        "adapter_implemented": False,
        "enabled_by_default": False,
        "execution_status": "local_config_gated",
    },
    {
        "provider": "lmstudio",
        "env_var": "LMSTUDIO_URL",
        "model_env_var": "LMSTUDIO_MODEL",
        "registered": True,
        "adapter_implemented": False,
        "enabled_by_default": False,
        "execution_status": "local_config_gated",
    },
)

PROVIDERS: tuple[str, ...] = tuple(str(row["provider"]) for row in PROVIDER_METADATA)
_PROVIDER_BY_NAME = {str(row["provider"]): row for row in PROVIDER_METADATA}


def provider_metadata() -> list[dict[str, Any]]:
    """Safe provider registry metadata; names and env var names only, never values."""
    return [dict(row) for row in PROVIDER_METADATA]


def _looks_configured_env(env_name: str) -> bool:
    raw = os.environ.get(env_name)
    value = str(raw).strip() if raw is not None else ""
    if not value:
        return False
    upper = value.upper()
    return "YOUR_" not in value and "<<PASTE" not in upper


def _provider_configured(provider: str) -> bool:
    meta = _PROVIDER_BY_NAME.get(provider)
    if not meta:
        return False
    try:
        get_secret(provider)
    except SecretError:
        env_name = str(meta.get("env_var", "") or "")
        return bool(env_name and _looks_configured_env(env_name))
    return True


def _execution_status(meta: dict[str, Any], configured: bool) -> str:
    base = str(meta.get("execution_status", "unsupported") or "unsupported")
    if not bool(meta.get("adapter_implemented", False)):
        return base
    return "active" if configured else "credential_gated"


def _provider_executable(meta: dict[str, Any], configured: bool) -> bool:
    return bool(meta.get("adapter_implemented", False) and configured)


def _diagnostic_row(
    meta: dict[str, Any],
    *,
    configured: bool,
    selected: str,
    attempted: str,
    succeeded: str,
    failure_kind: str,
    failure_detail: str,
    latency_ms: int | None,
) -> dict[str, Any]:
    provider = str(meta.get("provider", "") or "")
    attempted_here = provider == attempted
    succeeded_here = provider == succeeded and not failure_kind
    failed_here = attempted_here and bool(failure_kind)
    executable = _provider_executable(meta, configured)
    return {
        "provider": provider,
        "registered": bool(meta.get("registered", True)),
        "configured": configured,
        "key_present": configured and str(meta.get("env_var", "") or "").endswith("_API_KEY"),
        "model_configured": True,
        "adapter_implemented": bool(meta.get("adapter_implemented", False)),
        "enabled_by_default": bool(meta.get("enabled_by_default", False)),
        "execution_status": _execution_status(meta, configured),
        "executable": executable,
        "available": executable,
        "selected": provider == selected,
        "attempted": attempted_here,
        "succeeded": succeeded_here,
        "failed": failed_here,
        "failure_class": failure_kind if failed_here else None,
        "failure_reason": failure_detail if failed_here else None,
        "latency_ms": int(latency_ms) if failed_here is False and attempted_here and latency_ms is not None else None,
    }


def _local_heuristic_row(
    *,
    selected: str,
    attempted: str,
    succeeded: str,
    failure_kind: str,
    failure_detail: str,
    latency_ms: int | None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "provider": "local-heuristic",
        "registered": True,
        "adapter_implemented": True,
        "enabled_by_default": True,
        "execution_status": "active",
    }
    row = _diagnostic_row(
        meta,
        configured=True,
        selected=selected,
        attempted=attempted,
        succeeded=succeeded,
        failure_kind=failure_kind,
        failure_detail=failure_detail,
        latency_ms=latency_ms,
    )
    row["key_present"] = False
    return row


def get_available_providers() -> list[str]:
    """Return provider ids that have valid, non-placeholder credentials."""
    return [provider for provider in PROVIDERS if _provider_configured(provider)]


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

    ``configured`` means required env/config appears present.
    ``available``/``executable`` require both configuration and an implemented adapter.
    """
    selected = str(selected_provider or "").strip().lower()
    actual = str(actual_provider or "").strip().lower()
    attempted = str(attempted_provider or actual or "").strip().lower()
    succeeded = str(succeeded_provider or actual if not failure_class else "").strip().lower()
    failure_kind = str(failure_class or "").strip().lower()
    failure_detail = str(failure_reason or "").strip()

    rows: list[dict[str, Any]] = []
    for meta in PROVIDER_METADATA:
        provider = str(meta["provider"])
        rows.append(
            _diagnostic_row(
                meta,
                configured=_provider_configured(provider),
                selected=selected,
                attempted=attempted,
                succeeded=succeeded,
                failure_kind=failure_kind,
                failure_detail=failure_detail,
                latency_ms=latency_ms,
            )
        )
    if include_embedded_local:
        rows.append(
            _local_heuristic_row(
                selected=selected,
                attempted=attempted,
                succeeded=succeeded,
                failure_kind=failure_kind,
                failure_detail=failure_detail,
                latency_ms=latency_ms,
            )
        )
    return rows
