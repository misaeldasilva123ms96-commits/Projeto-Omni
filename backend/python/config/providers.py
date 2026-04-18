"""Canonical provider → environment variable mapping (names only; never values)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderEnvSpec:
    """Logical provider id resolved from the first non-empty alias."""

    logical_id: str
    env_aliases: tuple[str, ...]
    optional: bool = True


# Order matters: first alias wins when reading.
PROVIDERS: tuple[ProviderEnvSpec, ...] = (
    ProviderEnvSpec("openai", ("OPENAI_API_KEY",)),
    ProviderEnvSpec("groq", ("GROQ_API_KEY",)),
    ProviderEnvSpec("anthropic", ("ANTHROPIC_API_KEY",)),
    ProviderEnvSpec("codex", ("CODEX_API_KEY",)),
    ProviderEnvSpec("chatgpt_account", ("CHATGPT_ACCOUNT_ID",)),
    ProviderEnvSpec("supabase_url", ("SUPABASE_URL", "VITE_SUPABASE_URL")),
    ProviderEnvSpec(
        "supabase_anon",
        (
            "SUPABASE_ANON_KEY",
            "VITE_SUPABASE_ANON_KEY",
            "VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY",
        ),
    ),
    ProviderEnvSpec("ollama", ("OLLAMA_URL",)),
)

LOGICAL_IDS = frozenset(p.logical_id for p in PROVIDERS)


def spec_for(logical_id: str) -> ProviderEnvSpec | None:
    lid = str(logical_id or "").strip().lower()
    for spec in PROVIDERS:
        if spec.logical_id == lid:
            return spec
    return None
