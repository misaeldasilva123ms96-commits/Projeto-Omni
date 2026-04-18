"""Single read surface for provider secrets and server-side public Supabase config.

Rules:
- All sensitive env reads for listed providers go through this module.
- Never log secret values; errors contain no key material.
- Missing optional providers return absent=True without raising.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping

from .providers import LOGICAL_IDS, spec_for


@dataclass(slots=True)
class SecretLookup:
    """Result of resolving one logical secret."""

    logical_id: str
    present: bool
    value: str | None
    resolved_env: str | None
    """Which physical env name supplied the value (never the value itself)."""
    error: str | None
    """Stable machine-readable reason when present is False for required use."""


def _read_raw(name: str) -> str:
    raw = os.environ.get(name)
    if raw is None:
        return ""
    return str(raw).strip()


def get_secret(logical_id: str) -> SecretLookup:
    """
    Resolve a logical provider secret.

    logical_id examples: openai, groq, supabase_url, supabase_anon
    """
    lid = str(logical_id or "").strip().lower()
    spec = spec_for(lid)
    if spec is None:
        return SecretLookup(
            logical_id=lid,
            present=False,
            value=None,
            resolved_env=None,
            error="unknown_logical_provider",
        )

    for alias in spec.env_aliases:
        candidate = _read_raw(alias)
        if candidate:
            return SecretLookup(
                logical_id=lid,
                present=True,
                value=candidate,
                resolved_env=alias,
                error=None,
            )

    if spec.optional:
        return SecretLookup(
            logical_id=lid,
            present=False,
            value=None,
            resolved_env=None,
            error=None,
        )
    return SecretLookup(
        logical_id=lid,
        present=False,
        value=None,
        resolved_env=None,
        error=f"missing_required:{lid}",
    )


def configured(logical_id: str) -> bool:
    return get_secret(logical_id).present


def apply_runtime_provider_secrets(env: Mapping[str, str] | dict[str, str]) -> dict[str, str]:
    """
    Merge canonical provider variables into a subprocess environment dict.

    - Does not remove or log existing values.
    - Writes standard names expected by Node (OPENAI_API_KEY, SUPABASE_URL, …)
      when absent, using the first configured alias from the process environment.
    """
    out: dict[str, str] = dict(env)
    # OpenAI / Anthropic / Groq — standard names only in child env
    _maybe_set(out, "OPENAI_API_KEY", get_secret("openai"))
    _maybe_set(out, "GROQ_API_KEY", get_secret("groq"))
    _maybe_set(out, "ANTHROPIC_API_KEY", get_secret("anthropic"))
    _maybe_set(out, "CODEX_API_KEY", get_secret("codex"))
    acct = get_secret("chatgpt_account")
    if acct.present and acct.value:
        out.setdefault("CHATGPT_ACCOUNT_ID", acct.value)
    # Supabase — normalize server-side names for @supabase/supabase-js in Node
    url = get_secret("supabase_url")
    if url.present and url.value:
        out.setdefault("SUPABASE_URL", url.value)
    anon = get_secret("supabase_anon")
    if anon.present and anon.value:
        out.setdefault("SUPABASE_ANON_KEY", anon.value)
    ollama = get_secret("ollama")
    if ollama.present and ollama.value:
        out.setdefault("OLLAMA_URL", ollama.value)
    return out


def _maybe_set(target: dict[str, str], env_name: str, lookup: SecretLookup) -> None:
    if not lookup.present or not lookup.value:
        return
    target.setdefault(env_name, lookup.value)


def describe_configuration_safe() -> dict[str, Any]:
    """Boolean readiness map for health checks — never includes secret values."""
    return {
        "providers": {lid: configured(lid) for lid in sorted(LOGICAL_IDS)},
    }
