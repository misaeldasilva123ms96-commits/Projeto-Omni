"""Centralized provider secrets — single read path; no logging of values."""

from __future__ import annotations

import os
from typing import Any

__all__ = [
    "SecretError",
    "build_controlled_os_environ_base",
    "describe_configuration",
    "describe_configuration_safe",
    "get_secret",
    "merge_provider_credentials",
]


class SecretError(Exception):
    """Raised when a logical secret is unknown, missing, or still a placeholder."""


def _mapping() -> dict[str, str]:
    return {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "groq": "GROQ_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "codex": "CODEX_API_KEY",
        "supabase_url": "SUPABASE_URL",
        "supabase_anon": "SUPABASE_ANON_KEY",
        "ollama": "OLLAMA_URL",
    }


def get_secret(name: str) -> str:
    """Return a validated secret value for the logical provider name."""
    logical = str(name or "").strip().lower()
    env_name = _mapping().get(logical)
    if not env_name:
        raise SecretError(f"Unknown secret: {logical}")

    raw = os.environ.get(env_name)
    value = str(raw).strip() if raw is not None else ""
    if not value:
        raise SecretError(f"Missing or invalid secret: {env_name}")

    upper = value.upper()
    if "YOUR_" in value or "<<PASTE" in upper:
        raise SecretError(f"Missing or invalid secret: {env_name}")

    return value


def describe_configuration() -> dict[str, str]:
    """Safe status map for debug/health — never returns secret values."""
    mapping = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "groq": "GROQ_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "codex": "CODEX_API_KEY",
        "supabase": "SUPABASE_ANON_KEY",
    }
    result: dict[str, str] = {}
    for key, env_name in mapping.items():
        raw = os.environ.get(env_name)
        value = str(raw).strip() if raw is not None else ""
        upper = value.upper()
        if value and "YOUR_" not in value and "<<PASTE" not in upper:
            result[key] = "configured"
        else:
            result[key] = "missing"
    return result


def describe_configuration_safe() -> dict[str, Any]:
    """Backward-compatible alias for callers expecting a nested payload."""
    return {"providers": describe_configuration()}


def build_controlled_os_environ_base() -> dict[str, str]:
    """
    Minimal inherited process environment for Node subprocesses.

    Does not copy the full parent environ (reduces accidental leak surface).
    """
    env: dict[str, str] = {}
    path_val = os.environ.get("PATH") or os.environ.get("Path")
    if path_val:
        env["PATH"] = str(path_val)
    for key in (
        "PATHEXT",
        "COMSPEC",
        "SystemRoot",
        "SYSTEMROOT",
        "WINDIR",
        "TMP",
        "TEMP",
        "USERPROFILE",
        "HOME",
        "LANG",
        "LC_ALL",
        "PYTHONPATH",
        "NODE_PATH",
        "NODE_OPTIONS",
    ):
        val = os.environ.get(key)
        if val is not None and str(val).strip():
            env[key] = str(val)
    for key, val in os.environ.items():
        if key.startswith("OMINI_") and str(val).strip():
            env[key] = str(val)
    return env


def merge_provider_credentials(env: dict[str, str]) -> dict[str, str]:
    """Merge validated provider keys into env; skips missing/invalid without raising."""
    for logical in (
        "openai",
        "anthropic",
        "groq",
        "gemini",
        "deepseek",
        "codex",
        "supabase_url",
        "supabase_anon",
        "ollama",
    ):
        try:
            val = get_secret(logical)
        except SecretError:
            continue
        env_name = _mapping()[logical]
        env[env_name] = val
    cid = os.environ.get("CHATGPT_ACCOUNT_ID")
    if cid is not None:
        s = str(cid).strip()
        upper = s.upper()
        if s and "YOUR_" not in s and "<<PASTE" not in upper:
            env["CHATGPT_ACCOUNT_ID"] = s
    return env
